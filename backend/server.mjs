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
const SUPABASE_PUBLISHABLE_KEY = process.env.SUPABASE_PUBLISHABLE_KEY || '';
const USE_SUPABASE = Boolean(GAME_API_URL && SUPABASE_PUBLISHABLE_KEY);

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
function rateLimited(req){
  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown').split(',')[0].trim();
  const now = Date.now(), windowMs = 60_000, limit = 120;
  const entry = rate.get(ip);
  if(!entry || now-entry.start >= windowMs){ rate.set(ip,{start:now,count:1}); return false; }
  entry.count++;
  return entry.count > limit;
}

async function proxyGame(req,res,payload){
  const auth = req.headers.authorization;
  if(!auth) return json(res,401,{error:'Authentication required'});
  const r = await fetch(GAME_API_URL,{
    method:'POST',
    headers:{'content-type':'application/json','authorization':auth,'apikey':SUPABASE_PUBLISHABLE_KEY},
    body:JSON.stringify(payload),
  });
  const text = await r.text();
  res.writeHead(r.status,{...securityHeaders,'content-type':r.headers.get('content-type')||'application/json; charset=utf-8','cache-control':'no-store'});
  res.end(text);
}

const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
const server=http.createServer(async (req,res)=>{
  try{
    const url=new URL(req.url, `http://${req.headers.host||'localhost'}`);
    if(url.pathname.startsWith('/api/') && rateLimited(req)) return json(res,429,{error:'Too many requests'});
    if(url.pathname==='/api/health') return json(res,200,{ok:true,mode:USE_SUPABASE?'supabase':'demo',time:Date.now()});

    if(USE_SUPABASE && url.pathname==='/api/state' && req.method==='GET') return proxyGame(req,res,{op:'state'});
    if(USE_SUPABASE && url.pathname==='/api/action' && req.method==='POST'){
      const input=await body(req);
      return proxyGame(req,res,{op:'action',action:input.action,payload:input.payload||{}});
    }
    if(USE_SUPABASE && url.pathname==='/api/reset' && req.method==='POST') return proxyGame(req,res,{op:'reset'});

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
      world=createDefaultWorld(); await persist(); return json(res,200,{ok:true});
    }

    let rel=url.pathname==='/'?'frontend/index.html':url.pathname.replace(/^\//,'');
    if(!rel.startsWith('frontend/')) rel='frontend/'+rel;
    const fp=normalize(join(ROOT,rel));
    if(!fp.startsWith(join(ROOT,'frontend'))) return json(res,403,{error:'forbidden'});
    try {
      const data=await readFile(fp);
      // During active development always serve frontend assets fresh so mobile browsers
      // do not remain stuck on an older JS/CSS bundle after a deploy.
      const cache='no-store, max-age=0';
      res.writeHead(200,{...securityHeaders,'content-type':mime[extname(fp)]||'application/octet-stream','cache-control':cache,'pragma':'no-cache','expires':'0'});
      res.end(data);
    } catch { json(res,404,{error:'not found'}); }
  }catch(e){ json(res,400,{error:e.message||'request failed'}); }
});
server.listen(PORT,()=>console.log(`Nexus Realms running on http://localhost:${PORT} (${USE_SUPABASE?'supabase':'demo'})`));
