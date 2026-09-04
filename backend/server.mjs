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

await mkdir(DATA_DIR, {recursive:true});
let world;
try { world = JSON.parse(await readFile(DATA_FILE, 'utf8')); }
catch { world = createDefaultWorld(); await persist(); }

async function persist(){ await writeFile(DATA_FILE, JSON.stringify(world,null,2)); }
function json(res, status, payload){ res.writeHead(status, {'content-type':'application/json; charset=utf-8','cache-control':'no-store'}); res.end(JSON.stringify(payload)); }
async function body(req){ let s=''; for await (const chunk of req){ s += chunk; if(s.length>1_000_000) throw new Error('body too large'); } return s?JSON.parse(s):{}; }
function player(id='demo'){ if(!world.players[id]) world.players[id]=createDefaultWorld().players.demo; return world.players[id]; }

const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
const server=http.createServer(async (req,res)=>{
  try{
    const url=new URL(req.url, `http://${req.headers.host||'localhost'}`);
    if(url.pathname==='/api/health') return json(res,200,{ok:true,mode:'demo',time:Date.now()});
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
    try { const data=await readFile(fp); res.writeHead(200,{'content-type':mime[extname(fp)]||'application/octet-stream'}); res.end(data); }
    catch { json(res,404,{error:'not found'}); }
  }catch(e){ json(res,400,{error:e.message||'request failed'}); }
});
server.listen(PORT,()=>console.log(`Nexus Realms running on http://localhost:${PORT}`));
