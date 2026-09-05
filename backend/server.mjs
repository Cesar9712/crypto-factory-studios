import http from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { extname, join, normalize, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createDefaultWorld, applyAction, tickState } from './lib/game.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const DATA_DIR = join(__dirname, 'data');
const DATA_FILE = join(DATA_DIR, 'state.json');
const PORT = Number(process.env.PORT || 4173);
const GAME_API_URL = process.env.SUPABASE_GAME_API_URL || '';
const COMBAT_API_URL = process.env.SUPABASE_COMBAT_API_URL || '';
const PROFESSION_API_URL = process.env.SUPABASE_PROFESSION_API_URL || '';
const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY || '';
const USE_SUPABASE = Boolean(GAME_API_URL && SUPABASE_PUBLISHABLE_KEY);
const USE_COMBAT_ENGINE = Boolean(COMBAT_API_URL && SUPABASE_PUBLISHABLE_KEY);
const USE_PROFESSION_ENGINE = Boolean(PROFESSION_API_URL && SUPABASE_PUBLISHABLE_KEY);
const ALLOW_DEMO_RESET = process.env.ALLOW_DEMO_RESET === 'true' && process.env.NODE_ENV !== 'production';

await mkdir(DATA_DIR, {recursive:true});
let world;
try { world = JSON.parse(await readFile(DATA_FILE, 'utf8')); }
catch { world = createDefaultWorld(); await persist(); }

async function persist(){ await writeFile(DATA_FILE, JSON.stringify(world,null,2)); }
const securityHeaders = {
  'x-content-type-options':'nosniff',
  'x-frame-options':'DENY',
  'referrer-policy':'no-referrer',
  'permissions-policy':'camera=(), microphone=(), geolocation=()',
  'content-security-policy':"default-src 'self'; script-src 'self' https://esm.sh; connect-src 'self' https://*.supabase.co https://esm.sh; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
};
function json(res, status, payload){ res.writeHead(status, {...securityHeaders,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}); res.end(JSON.stringify(payload)); }
async function body(req){ let s=''; for await (const chunk of req){ s += chunk; if(s.length>1_000_000) throw new Error('body too large'); } return s?JSON.parse(s):{}; }
function player(id='demo'){ if(!world.players[id]) world.players[id]=createDefaultWorld().players.demo; return world.players[id]; }

const rate = new Map();
let lastRateSweep=0;
function sweepRate(now,windowMs){
  if(now-lastRateSweep<windowMs && rate.size<2000) return;
  lastRateSweep=now;
  for(const [ip,entry] of rate){ if(now-entry.start>=windowMs*2) rate.delete(ip); }
}
function rateLimited(req){
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown').split(',')[0].trim();
  const now = Date.now(), windowMs = 60_000, limit = 120;
  sweepRate(now,windowMs);
  const entry = rate.get(ip);
  if(!entry || now-entry.start >= windowMs){ rate.set(ip,{start:now,count:1}); return false; }
  entry.count++;
  return entry.count > limit;
}

async function callEdge(req,url,payload){
  const auth = req.headers.authorization;
  if(!auth) return {status:401,data:{error:'Authentication required'}};
  try{
    const r = await fetch(url,{
      method:'POST',
      headers:{'content-type':'application/json','authorization':auth,'apikey':SUPABASE_PUBLISHABLE_KEY},
      body:JSON.stringify(payload),
      signal:AbortSignal.timeout(12000),
    });
    let data={};
    try{data=await r.json();}catch{data={error:'Invalid upstream response'};}
    return {status:r.status,data};
  }catch(e){
    if(e?.name==='TimeoutError'||e?.name==='AbortError') return {status:504,data:{error:'Upstream timeout'}};
    return {status:502,data:{error:'Upstream unavailable'}};
  }
}
function mergeProgression(base,progress){
  if(!base?.player || !progress?.player) return base;
  base.player = {
    ...base.player,
    power: progress.player.power ?? base.player.power,
    combatStats: progress.player.combatStats,
    attributes: progress.player.attributes,
    unspentPoints: progress.player.unspentPoints,
    tactic: progress.player.tactic,
    skills: progress.player.skills,
    xpToNext: progress.player.xpToNext,
  };
  return base;
}
async function getMergedState(req){
  const mainPromise=callEdge(req,GAME_API_URL,{op:'state'});
  if(!USE_COMBAT_ENGINE) return mainPromise;
  const [main,progress]=await Promise.all([mainPromise,callEdge(req,COMBAT_API_URL,{op:'state'})]);
  if(main.status>=400) return main;
  if(progress.status<400) mergeProgression(main.data,progress.data);
  return main;
}

const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
const server=http.createServer(async (req,res)=>{
  try{
    const url=new URL(req.url, `http://${req.headers.host||'localhost'}`);
    if(url.pathname.startsWith('/api/') && rateLimited(req)) return json(res,429,{error:'Too many requests'});
    if(url.pathname==='/api/health') return json(res,200,{ok:true,mode:USE_SUPABASE?'supabase':'demo',combatEngine:USE_COMBAT_ENGINE,professionEngine:USE_PROFESSION_ENGINE,time:Date.now()});

    if(USE_SUPABASE && url.pathname==='/api/progression' && req.method==='GET'){
      if(!USE_COMBAT_ENGINE) return json(res,503,{error:'Combat engine not configured'});
      const result=await callEdge(req,COMBAT_API_URL,{op:'state'});
      return json(res,result.status,result.data);
    }
    if(USE_SUPABASE && url.pathname==='/api/professions' && req.method==='GET'){
      if(!USE_PROFESSION_ENGINE) return json(res,503,{error:'Profession engine not configured'});
      const result=await callEdge(req,PROFESSION_API_URL,{op:'state'});
      return json(res,result.status,result.data);
    }
    if(USE_SUPABASE && url.pathname==='/api/profession-action' && req.method==='POST'){
      if(!USE_PROFESSION_ENGINE) return json(res,503,{error:'Profession engine not configured'});
      const input=await body(req);
      const result=await callEdge(req,PROFESSION_API_URL,{op:'action',action:String(input.action||''),payload:input.payload||{}});
      return json(res,result.status,result.data);
    }
    if(USE_SUPABASE && url.pathname==='/api/state' && req.method==='GET'){
      const result=await getMergedState(req);
      return json(res,result.status,result.data);
    }
    if(USE_SUPABASE && url.pathname==='/api/action' && req.method==='POST'){
      const input=await body(req);
      const actionName=String(input.action||'');
      const engineActions=new Set(['combat','allocateStat','setTactic']);
      if(USE_COMBAT_ENGINE && engineActions.has(actionName)){
        const engine=await callEdge(req,COMBAT_API_URL,{op:'action',action:actionName,payload:input.payload||{}});
        if(engine.status>=400) return json(res,engine.status,engine.data);
        const current=await callEdge(req,GAME_API_URL,{op:'state'});
        if(current.status>=400) return json(res,current.status,current.data);
        if(engine.data.progression) mergeProgression(current.data,{player:engine.data.progression});
        else {
          const progress=await callEdge(req,COMBAT_API_URL,{op:'state'});
          if(progress.status<400) mergeProgression(current.data,progress.data);
        }
        current.data.message=engine.data.message||current.data.message;
        if(engine.data.log) current.data.log=engine.data.log;
        if(typeof engine.data.victory==='boolean') current.data.victory=engine.data.victory;
        if(engine.data.hunter) current.data.hunter=engine.data.hunter;
        return json(res,200,current.data);
      }
      const main=await callEdge(req,GAME_API_URL,{op:'action',action:actionName,payload:input.payload||{}});
      if(main.status>=400 || !USE_COMBAT_ENGINE) return json(res,main.status,main.data);
      const progress=await callEdge(req,COMBAT_API_URL,{op:'state'});
      if(progress.status<400) mergeProgression(main.data,progress.data);
      return json(res,main.status,main.data);
    }
    if(USE_SUPABASE && url.pathname==='/api/reset' && req.method==='POST'){
      if(!ALLOW_DEMO_RESET) return json(res,403,{error:'Reset disabled in Early Access'});
      const main=await callEdge(req,GAME_API_URL,{op:'reset'});
      if(main.status>=400 || !USE_COMBAT_ENGINE) return json(res,main.status,main.data);
      const current=await getMergedState(req);
      return json(res,current.status,current.data);
    }

    if(url.pathname==='/api/state' && req.method==='GET'){
      const id=url.searchParams.get('playerId')||'demo';
      tickState(player(id)); await persist();
      return json(res,200,{player:player(id),market:world.market,recipes:world.recipes,enemies:world.enemies,quests:world.quests});
    }
    if(url.pathname==='/api/action' && req.method==='POST'){
      const input=await body(req); const id=input.playerId||'demo';
      const result=applyAction(world,id,input.action,input.payload||{}); await persist();
      return json(res,200,result);
    }
    if(url.pathname==='/api/reset' && req.method==='POST'){
      if(!ALLOW_DEMO_RESET) return json(res,403,{error:'Reset disabled in Early Access'});
      world=createDefaultWorld(); await persist(); return json(res,200,{ok:true});
    }

    let rel=url.pathname==='/'?'frontend/index.html':url.pathname.replace(/^\//,'');
    if(!rel.startsWith('frontend/')) rel='frontend/'+rel;
    const fp=normalize(join(ROOT,rel));
    if(!fp.startsWith(join(ROOT,'frontend'))) return json(res,403,{error:'forbidden'});
    try {
      const data=await readFile(fp);
      const cache='no-store, max-age=0';
      res.writeHead(200,{...securityHeaders,'content-type':mime[extname(fp)]||'application/octet-stream','cache-control':cache,'pragma':'no-cache','expires':'0'});
      res.end(data);
    } catch { json(res,404,{error:'not found'}); }
  }catch(e){
    if(e?.name==='TimeoutError'||e?.name==='AbortError') return json(res,504,{error:'Upstream timeout'});
    if(e instanceof SyntaxError) return json(res,400,{error:'Invalid JSON request'});
    json(res,500,{error:'Request failed'});
  }
});
server.listen(PORT,()=>console.log(`Nexus Realms running on http://localhost:${PORT} (${USE_SUPABASE?'supabase':'demo'}, combat=${USE_COMBAT_ENGINE?'v2':'legacy'}, professions=${USE_PROFESSION_ENGINE?'v1':'off'})`));