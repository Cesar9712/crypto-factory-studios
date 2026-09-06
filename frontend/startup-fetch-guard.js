(()=>{
  if(window.__nexusStartupFetchGuard)return;
  const nativeFetch=window.fetch.bind(window);
  const bootStartedAt=Date.now();
  const BOOT_WINDOW_MS=15000;
  const RETRY_DELAYS_MS=[250,650];

  const meta=(input,init={})=>{
    const request=input instanceof Request?input:null;
    const url=new URL(request?.url||String(input),location.href);
    const method=String(init.method||request?.method||'GET').toUpperCase();
    return{url,method};
  };
  const isBootState=m=>m.url.origin===location.origin&&m.url.pathname==='/api/state'&&m.method==='GET'&&Date.now()-bootStartedAt<BOOT_WINDOW_MS;
  const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const transientStatus=status=>status===500||status===502||status===503||status===504;
  const transientBody=async response=>{
    if(!response||response.ok)return false;
    if(transientStatus(response.status))return true;
    try{
      const data=await response.clone().json();
      return /request[_ ]failed|upstream (?:timeout|unavailable)/i.test(String(data?.error||''));
    }catch{return false;}
  };

  window.fetch=async(input,init={})=>{
    const requestMeta=meta(input,init);
    if(!isBootState(requestMeta))return nativeFetch(input,init);

    let lastError=null;
    let lastResponse=null;
    for(let attempt=0;attempt<=RETRY_DELAYS_MS.length;attempt++){
      try{
        const response=await nativeFetch(input,init);
        lastResponse=response;
        if(!(await transientBody(response))||attempt===RETRY_DELAYS_MS.length)return response;
      }catch(error){
        lastError=error;
        if(attempt===RETRY_DELAYS_MS.length)throw error;
      }
      await wait(RETRY_DELAYS_MS[attempt]);
    }
    if(lastResponse)return lastResponse;
    throw lastError||new Error('Request failed');
  };

  window.__nexusStartupFetchGuard={bootWindowMs:BOOT_WINDOW_MS,maxAttempts:RETRY_DELAYS_MS.length+1};
})();
