// Fast mobile runtime: coalesces duplicate requests and bypasses the Render proxy
// for JWT-verified Supabase Edge Function reads/actions. Direct game responses are
// merged with combat progression so the UI keeps the same authoritative stats.
const nativeFetch=window.fetch.bind(window);
const inflight=new Map();
let stateCache=null;
let stateCacheAt=0;
const STATE_TTL=6000;

const SUPABASE_URL='https://culwlrspkwbcbtmopgcp.supabase.co';
const SUPABASE_KEY='sb_publishable_JfDoNvnecRDooAOK6dTg2A_2fRV5zRZ';
const GAME_EDGE=`${SUPABASE_URL}/functions/v1/game-api`;
const COMBAT_EDGE=`${SUPABASE_URL}/functions/v1/combat-engine`;
const PROF_EDGE=`${SUPABASE_URL}/functions/v1/profession-engine`;
const ENGINE_ACTIONS=new Set(['combat','allocateStat','setTactic']);

function requestInfo(input,init={}){
  const url=typeof input==='string'?input:(input?.url||'');
  const method=String(init.method||(typeof input!=='string'&&input?.method)||'GET').toUpperCase();
  let path=url;
  try{path=new URL(url,location.origin).pathname}catch{}
  return{url,path,method};
}
function synthetic(c){return new Response(c.body,{status:c.status,statusText:c.statusText,headers:c.headers});}
function emit(name,detail){window.dispatchEvent(new CustomEvent(name,{detail}));}
function bodyJson(init){try{return typeof init?.body==='string'?JSON.parse(init.body):{};}catch{return {};}}
function authHeaders(input,init){
  const h=new Headers(typeof input!=='string'&&input?.headers?input.headers:undefined);
  if(init?.headers)new Headers(init.headers).forEach((v,k)=>h.set(k,v));
  h.set('content-type','application/json');h.set('apikey',SUPABASE_KEY);return h;
}
async function edgePost(url,payload,headers){return nativeFetch(url,{method:'POST',headers,body:JSON.stringify(payload),cache:'no-store'});}
function mergeProgress(base,progress){
  if(!base?.player||!progress?.player)return base;
  base.player={...base.player,power:progress.player.power??base.player.power,combatStats:progress.player.combatStats,attributes:progress.player.attributes,unspentPoints:progress.player.unspentPoints,tactic:progress.player.tactic,skills:progress.player.skills,xpToNext:progress.player.xpToNext};
  return base;
}
async function responseJson(res){try{return await res.clone().json();}catch{return null;}}
function jsonResponse(data,status=200){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});}
async function captureState(res,source){
  try{if(!res.ok)return;const data=await res.clone().json();if(data?.player){window.__NEXUS_STATE__=data;emit('nexus:state',{state:data,source});}}catch{}
}

async function directRequest(info,input,init){
  const headers=authHeaders(input,init);if(!headers.get('authorization'))return null;
  if(info.method==='GET'&&info.path==='/api/state'){
    const [g,c]=await Promise.all([edgePost(GAME_EDGE,{op:'state'},headers),edgePost(COMBAT_EDGE,{op:'state'},headers)]);
    if(!g.ok)return g;const gd=await responseJson(g),cd=c.ok?await responseJson(c):null;window.__NEXUS_ROUTE__='direct-merged-state';return jsonResponse(mergeProgress(gd,cd),g.status);
  }
  if(info.method==='GET'&&info.path==='/api/progression'){window.__NEXUS_ROUTE__='direct-progression';return edgePost(COMBAT_EDGE,{op:'state'},headers);}
  if(info.method==='GET'&&info.path==='/api/professions'){window.__NEXUS_ROUTE__='direct-professions';return edgePost(PROF_EDGE,{op:'state'},headers);}
  if(info.method==='POST'&&info.path==='/api/profession-action'){
    const b=bodyJson(init);window.__NEXUS_ROUTE__='direct-profession-action';return edgePost(PROF_EDGE,{op:'action',action:String(b.action||''),payload:b.payload||{}},headers);
  }
  if(info.method==='POST'&&info.path==='/api/reset'){
    const g=await edgePost(GAME_EDGE,{op:'reset'},headers);if(!g.ok)return g;const gd=await responseJson(g);const c=await edgePost(COMBAT_EDGE,{op:'state'},headers);const cd=c.ok?await responseJson(c):null;window.__NEXUS_ROUTE__='direct-reset';return jsonResponse(mergeProgress(gd,cd),g.status);
  }
  if(info.method==='POST'&&info.path==='/api/action'){
    const b=bodyJson(init),action=String(b.action||'');if(ENGINE_ACTIONS.has(action))return null;
    const g=await edgePost(GAME_EDGE,{op:'action',action,payload:b.payload||{}},headers);if(!g.ok)return g;
    const gd=await responseJson(g);const c=await edgePost(COMBAT_EDGE,{op:'state'},headers);const cd=c.ok?await responseJson(c):null;window.__NEXUS_ROUTE__=`direct-${action||'action'}`;return jsonResponse(mergeProgress(gd,cd),g.status);
  }
  return null;
}
async function fetchWithFallback(info,input,init){
  try{const direct=await directRequest(info,input,init);if(direct&&direct.status<500)return direct;}catch{}
  window.__NEXUS_ROUTE__='render-fallback';return nativeFetch(input,init);
}

window.fetch=async function(input,init={}){
  const info=requestInfo(input,init);
  const isState=info.method==='GET'&&info.path==='/api/state';
  const isAction=info.method==='POST'&&(info.path==='/api/action'||info.path==='/api/reset'||info.path==='/api/profession-action');
  const bodyKey=typeof init.body==='string'?init.body:'';
  const key=`${info.method}:${info.path}:${bodyKey}`;
  if(isState&&stateCache&&Date.now()-stateCacheAt<STATE_TTL)return synthetic(stateCache);
  if(inflight.has(key))return (await inflight.get(key)).clone();
  if(isAction)emit('nexus:busy',{busy:true});
  const started=performance.now();const pending=fetchWithFallback(info,input,init);inflight.set(key,pending);
  try{
    const res=await pending;const elapsed=Math.round(performance.now()-started);window.__NEXUS_LAST_LATENCY__=elapsed;emit('nexus:network',{path:info.path,elapsed,ok:res.ok,route:window.__NEXUS_ROUTE__||'render'});
    if(isState&&res.ok){try{const clone=res.clone(),body=await clone.text();stateCache={body,status:res.status,statusText:res.statusText,headers:[...res.headers.entries()]};stateCacheAt=Date.now();}catch{}captureState(res,'state');}
    else if(isAction&&res.ok){stateCache=null;stateCacheAt=0;captureState(res,'action');}
    return res.clone();
  }finally{inflight.delete(key);if(isAction)emit('nexus:busy',{busy:false});}
};

window.addEventListener('online',()=>emit('nexus:connectivity',{online:true}));
window.addEventListener('offline',()=>emit('nexus:connectivity',{online:false}));