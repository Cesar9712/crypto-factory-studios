(()=>{
  if(window.__nexusPerf)return;
  const nativeFetch=window.fetch.bind(window);
  const STATE_TTL=15000;
  let stateCache=null;
  let inFlight=null;

  const reqMeta=(input,init={})=>{
    const request=input instanceof Request?input:null;
    const url=new URL(request?.url||String(input),location.href);
    const method=String(init.method||request?.method||'GET').toUpperCase();
    const headers=new Headers(request?.headers||undefined);
    if(init.headers)new Headers(init.headers).forEach((v,k)=>headers.set(k,v));
    return{url,method,auth:headers.get('authorization')||''};
  };
  const cloneSnapshot=async response=>{
    if(!response?.ok)return null;
    const copy=response.clone();
    return{body:await copy.text(),status:copy.status,statusText:copy.statusText,headers:[...copy.headers],at:Date.now()};
  };
  const freshResponse=s=>new Response(s.body,{status:s.status,statusText:s.statusText,headers:s.headers});
  const isState=m=>m.url.origin===location.origin&&m.url.pathname==='/api/state'&&m.method==='GET';
  const isMutation=m=>m.url.origin===location.origin&&['/api/action','/api/reset'].includes(m.url.pathname)&&m.method!=='GET';
  const cacheValid=(auth)=>stateCache&&stateCache.auth===auth&&Date.now()-stateCache.at<STATE_TTL;
  const saveState=(snap,auth)=>{if(snap)stateCache={...snap,auth};return stateCache};
  const parseAction=(init)=>{try{return JSON.parse(String(init?.body||'{}'))?.action||''}catch{return''}};
  const afterMutation=(response,meta,init)=>{
    if(!response?.ok)return;
    cloneSnapshot(response).then(snap=>{
      if(!snap)return;
      try{
        const parsed=JSON.parse(snap.body);
        if(parsed?.player&&parsed?.zones)saveState(snap,meta.auth);
      }catch{}
      const action=parseAction(init);
      if(action==='travel')setTimeout(()=>document.getElementById('p1-travel-transition')?.remove(),120);
      setTimeout(()=>window.dispatchEvent(new Event('focus')),0);
    }).catch(()=>{});
  };

  window.fetch=async(input,init={})=>{
    const meta=reqMeta(input,init);
    if(isState(meta)){
      if(cacheValid(meta.auth))return freshResponse(stateCache);
      if(inFlight&&inFlight.auth===meta.auth){
        const snap=await inFlight.promise;
        if(snap)return freshResponse(snap);
      }
      const network=nativeFetch(input,init);
      const promise=network.then(r=>cloneSnapshot(r)).then(s=>saveState(s,meta.auth)).finally(()=>{if(inFlight?.promise===promise)inFlight=null});
      inFlight={auth:meta.auth,promise};
      return network;
    }
    if(isMutation(meta)){
      stateCache=null;
      inFlight=null;
      const response=await nativeFetch(input,init);
      afterMutation(response,meta,init);
      return response;
    }
    return nativeFetch(input,init);
  };

  if(matchMedia('(max-width:760px)').matches){
    document.documentElement.classList.add('nexus-mobile-fast');
    const style=document.createElement('style');
    style.id='nexus-mobile-fast-style';
    style.textContent=`
      .nexus-mobile-fast .p1-overlay,.nexus-mobile-fast .p3-overlay{backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
      .nexus-mobile-fast .p1-world-hero,.nexus-mobile-fast .p1-battle-stage,.nexus-mobile-fast .p1-battle-sheet{box-shadow:0 8px 24px rgba(0,0,0,.45)!important}
      .nexus-mobile-fast .p1-zone-orb,.nexus-mobile-fast .p1-fighter .p1-avatar{box-shadow:none!important}
      .nexus-mobile-fast .p1-zone-node,.nexus-mobile-fast .destination{content-visibility:auto;contain-intrinsic-size:82px}
      .nexus-mobile-fast #panel{contain:layout style paint}
      .nexus-mobile-fast .p1-travel-transition span{animation-duration:.28s!important}
    `;
    document.head.append(style);
  }

  window.__nexusPerf={
    invalidateState(){stateCache=null;inFlight=null},
    get stateCacheAge(){return stateCache?Date.now()-stateCache.at:null},
    stateTtl:STATE_TTL
  };
})();