// Lightweight runtime layer: keeps the UI responsive on slower mobile connections
// without changing server-authoritative game rules.
const nativeFetch=window.fetch.bind(window);
const inflight=new Map();
let stateCache=null;
let stateCacheAt=0;
const STATE_TTL=6000;

function requestInfo(input,init={}){
  const url=typeof input==='string'?input:(input?.url||'');
  const method=String(init.method||(typeof input!=='string'&&input?.method)||'GET').toUpperCase();
  let path=url;
  try{path=new URL(url,location.origin).pathname}catch{}
  return{url,path,method};
}
function synthetic(c){return new Response(c.body,{status:c.status,statusText:c.statusText,headers:c.headers});}
function emit(name,detail){window.dispatchEvent(new CustomEvent(name,{detail}));}
async function captureState(res,source){
  try{
    if(!res.ok)return;
    const data=await res.clone().json();
    if(data?.player){window.__NEXUS_STATE__=data;emit('nexus:state',{state:data,source});}
  }catch{}
}

window.fetch=async function(input,init={}){
  const info=requestInfo(input,init);
  const isState=info.method==='GET'&&info.path==='/api/state';
  const isAction=info.method==='POST'&&(info.path==='/api/action'||info.path==='/api/reset');
  const bodyKey=typeof init.body==='string'?init.body:'';
  const key=`${info.method}:${info.path}:${bodyKey}`;

  if(isState&&stateCache&&Date.now()-stateCacheAt<STATE_TTL)return synthetic(stateCache);
  if(inflight.has(key))return (await inflight.get(key)).clone();

  if(isAction)emit('nexus:busy',{busy:true});
  const started=performance.now();
  const pending=nativeFetch(input,init);
  inflight.set(key,pending);
  try{
    const res=await pending;
    const elapsed=Math.round(performance.now()-started);
    window.__NEXUS_LAST_LATENCY__=elapsed;
    emit('nexus:network',{path:info.path,elapsed,ok:res.ok});

    if(isState&&res.ok){
      try{
        const clone=res.clone();
        const body=await clone.text();
        stateCache={body,status:res.status,statusText:res.statusText,headers:[...res.headers.entries()]};
        stateCacheAt=Date.now();
      }catch{}
      captureState(res,'state');
    }else if(isAction&&res.ok){
      stateCache=null;stateCacheAt=0;
      captureState(res,'action');
    }
    return res.clone();
  }finally{
    inflight.delete(key);
    if(isAction)emit('nexus:busy',{busy:false});
  }
};

window.addEventListener('online',()=>emit('nexus:connectivity',{online:true}));
window.addEventListener('offline',()=>emit('nexus:connectivity',{online:false}));