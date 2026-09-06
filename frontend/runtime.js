// Fast mobile runtime: coalesces duplicate requests and bypasses the Render proxy
// for JWT-verified Supabase Edge Function reads/actions. Direct game responses are
// merged with combat progression so the UI keeps the same authoritative stats.
const nativeFetch=window.fetch.bind(window);
const inflight=new Map();
let stateCache=null;
let stateCacheAt=0;
let mutationEpoch=0;
let activeMutations=0;
const STATE_TTL=15000;
const STALE_STATE_MAX_AGE=120000;
const DIRECT_TIMEOUT=9000;
const FALLBACK_TIMEOUT=15000;
const DIRECT_RETRY_DELAYS=[220,550];
const FALLBACK_RETRY_DELAYS=[350,800];

const SUPABASE_URL='https://culwlrspkwbcbtmopgcp.supabase.co';
const SUPABASE_KEY='sb_publishable_JfDoNvnecRDooAOK6dTg2A_2fRV5zRZ';
const GAME_EDGE=`${SUPABASE_URL}/functions/v1/game-api`;
const COMBAT_EDGE=`${SUPABASE_URL}/functions/v1/combat-engine`;
const PROF_EDGE=`${SUPABASE_URL}/functions/v1/profession-engine`;
const ENGINE_ACTIONS=new Set(['combat','allocateStat','setTactic']);
const READ_PATHS=new Set(['/api/state','/api/progression','/api/professions']);

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
function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms));}
function authHeaders(input,init){
  const h=new Headers(typeof input!=='string'&&input?.headers?input.headers:undefined);
  if(init?.headers)new Headers(init.headers).forEach((v,k)=>h.set(k,v));
  h.set('content-type','application/json');h.set('apikey',SUPABASE_KEY);return h;
}
async function timedFetch(input,init={},timeoutMs=FALLBACK_TIMEOUT){
  if(init?.signal)return nativeFetch(input,init);
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{return await nativeFetch(input,{...init,signal:controller.signal});}
  finally{clearTimeout(timer);}
}
async function edgePost(url,payload,headers){return timedFetch(url,{method:'POST',headers,body:JSON.stringify(payload),cache:'no-store'},DIRECT_TIMEOUT);}
function mergeProgress(base,progress){
  if(!base?.player||!progress?.player)return base;
  base.player={...base.player,power:progress.player.power??base.player.power,combatStats:progress.player.combatStats,attributes:progress.player.attributes,unspentPoints:progress.player.unspentPoints,tactic:progress.player.tactic,skills:progress.player.skills,xpToNext:progress.player.xpToNext};
  return base;
}
async function responseJson(res){try{return await res.clone().json();}catch{return null;}}
function jsonResponse(data,status=200){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});}
function isRead(info){return info.method==='GET'&&READ_PATHS.has(info.path);}
async function isTransientDirectResponse(res){
  if(!res)return true;
  if([500,502,503,504].includes(res.status))return true;
  if(res.ok)return false;
  const data=await responseJson(res);
  const message=String(data?.error||'').toLowerCase();
  return /request[_ ]failed|upstream (?:timeout|unavailable)|fetch failed|connection (?:closed|reset|timeout)|gateway timeout/.test(message);
}
function friendlyTransientResponse(){return jsonResponse({error:'Problema temporal de conexión. Reintenta en unos segundos.'},503);}
async function storeStateSnapshot(res,source){
  try{
    if(!res?.ok)return false;
    const copy=res.clone();
    const body=await copy.text();
    const data=JSON.parse(body);
    if(!data?.player||!data?.zones)return false;
    stateCache={body,status:res.status,statusText:res.statusText,headers:[...res.headers.entries()]};
    stateCacheAt=Date.now();
    window.__NEXUS_STATE__=data;
    emit('nexus:state',{state:data,source});
    return true;
  }catch{return false;}
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
    window.__NEXUS_ROUTE__='reset-disabled';return jsonResponse({error:'Reset disabled in Early Access'},403);
  }
  if(info.method==='POST'&&info.path==='/api/action'){
    const b=bodyJson(init),action=String(b.action||'');if(ENGINE_ACTIONS.has(action))return null;
    const g=await edgePost(GAME_EDGE,{op:'action',action,payload:b.payload||{}},headers);if(!g.ok)return g;
    const gd=await responseJson(g);const c=await edgePost(COMBAT_EDGE,{op:'state'},headers);const cd=c.ok?await responseJson(c):null;window.__NEXUS_ROUTE__=`direct-${action||'action'}`;return jsonResponse(mergeProgress(gd,cd),g.status);
  }
  return null;
}
async function retryDirectRequest(info,input,init){
  if(!isRead(info))return directRequest(info,input,init);
  let last=null;
  for(let attempt=0;attempt<=DIRECT_RETRY_DELAYS.length;attempt++){
    last=await directRequest(info,input,init);
    if(!last||!(await isTransientDirectResponse(last)))return last;
    emit('nexus:network-error',{path:info.path,stage:'direct',message:'transient-response',attempt:attempt+1});
    if(attempt<DIRECT_RETRY_DELAYS.length)await sleep(DIRECT_RETRY_DELAYS[attempt]);
  }
  return last;
}
async function retryFallbackRead(info,input,init){
  let last=null;
  for(let attempt=0;attempt<=FALLBACK_RETRY_DELAYS.length;attempt++){
    last=await timedFetch(input,init,FALLBACK_TIMEOUT);
    if(!(await isTransientDirectResponse(last)))return last;
    emit('nexus:network-error',{path:info.path,stage:'render-fallback',message:'transient-response',attempt:attempt+1});
    if(attempt<FALLBACK_RETRY_DELAYS.length)await sleep(FALLBACK_RETRY_DELAYS[attempt]);
  }
  return last;
}
async function fetchWithFallback(info,input,init){
  try{
    const direct=await retryDirectRequest(info,input,init);
    if(direct&&!(await isTransientDirectResponse(direct)))return direct;
  }catch(e){emit('nexus:network-error',{path:info.path,stage:'direct',message:e?.name==='AbortError'?'timeout':'unavailable'});}
  window.__NEXUS_ROUTE__='render-fallback';
  try{
    const fallback=isRead(info)?await retryFallbackRead(info,input,init):await timedFetch(input,init,FALLBACK_TIMEOUT);
    if(!(await isTransientDirectResponse(fallback)))return fallback;
  }catch(e){emit('nexus:network-error',{path:info.path,stage:'render-fallback',message:e?.name==='AbortError'?'timeout':'unavailable'});}
  if(info.path==='/api/state'&&stateCache&&Date.now()-stateCacheAt<STALE_STATE_MAX_AGE){
    window.__NEXUS_ROUTE__='stale-state-fallback';
    emit('nexus:network-error',{path:info.path,stage:'stale-cache',message:'served-last-good-state'});
    return synthetic(stateCache);
  }
  return friendlyTransientResponse();
}

window.fetch=async function(input,init={}){
  const info=requestInfo(input,init);
  const isState=info.method==='GET'&&info.path==='/api/state';
  const isAction=info.method==='POST'&&(info.path==='/api/action'||info.path==='/api/reset'||info.path==='/api/profession-action');
  const bodyKey=typeof init.body==='string'?init.body:'';
  const key=`${info.method}:${info.path}:${bodyKey}`;

  if(isState&&activeMutations>0)return jsonResponse({error:'STATE_REFRESH_DEFERRED'},409);
  if(isState&&stateCache&&Date.now()-stateCacheAt<STATE_TTL)return synthetic(stateCache);
  if(inflight.has(key))return (await inflight.get(key)).clone();

  let requestEpoch=mutationEpoch;
  if(isAction){
    mutationEpoch+=1;
    requestEpoch=mutationEpoch;
    activeMutations+=1;
    stateCache=null;
    stateCacheAt=0;
    try{window.__nexusPerf?.invalidateState?.()}catch{}
    emit('nexus:busy',{busy:true});
  }

  const started=performance.now();
  const pending=fetchWithFallback(info,input,init);
  inflight.set(key,pending);
  try{
    const res=await pending;
    const elapsed=Math.round(performance.now()-started);

    if(isState&&requestEpoch!==mutationEpoch){
      emit('nexus:network',{path:info.path,elapsed,ok:false,route:window.__NEXUS_ROUTE__||'render',error:'stale-state'});
      return jsonResponse({error:'STALE_STATE_DISCARDED'},409);
    }
    if(isAction&&requestEpoch!==mutationEpoch){
      emit('nexus:network',{path:info.path,elapsed,ok:false,route:window.__NEXUS_ROUTE__||'render',error:'superseded-action'});
      if(stateCache)return synthetic(stateCache);
      return jsonResponse({error:'ACTION_RESPONSE_SUPERSEDED'},409);
    }

    window.__NEXUS_LAST_LATENCY__=elapsed;
    emit('nexus:network',{path:info.path,elapsed,ok:res.ok,route:window.__NEXUS_ROUTE__||'render'});
    if(isState&&res.ok)await storeStateSnapshot(res,'state');
    else if(isAction&&res.ok){
      const cached=await storeStateSnapshot(res,'action');
      if(!cached){stateCache=null;stateCacheAt=0;}
    }
    return res.clone();
  }catch(e){
    const elapsed=Math.round(performance.now()-started);emit('nexus:network',{path:info.path,elapsed,ok:false,route:window.__NEXUS_ROUTE__||'render',error:e?.name==='AbortError'?'timeout':'network'});throw e;
  }finally{
    inflight.delete(key);
    if(isAction){
      activeMutations=Math.max(0,activeMutations-1);
      if(activeMutations===0)emit('nexus:busy',{busy:false});
    }
  }
};

window.addEventListener('online',()=>emit('nexus:connectivity',{online:true}));
window.addEventListener('offline',()=>emit('nexus:connectivity',{online:false}));
