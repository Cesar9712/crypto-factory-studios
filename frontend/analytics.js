(()=>{
  const PROJECT_TOKEN='phc_z2fyPA8VD655xhTSGBfFQgJC3ugUSCgvFLK49da86p4i';
  const ENDPOINT='https://us.i.posthog.com/i/v0/e/';
  const STORAGE_KEY='cfs_analytics_distinct_id';
  const recentEvents=new Map();
  const blocked=()=>navigator.globalPrivacyControl===true||navigator.doNotTrack==='1'||window.doNotTrack==='1';
  const safeText=v=>String(v??'').slice(0,120);
  const isPromptFactory=()=>location.pathname.startsWith('/prompt-factory');
  function distinctId(){
    try{
      let id=localStorage.getItem(STORAGE_KEY);
      if(!id){id=`anon_${crypto.randomUUID?.()||Math.random().toString(36).slice(2)}_${Date.now().toString(36)}`;localStorage.setItem(STORAGE_KEY,id)}
      return id;
    }catch{return `anon_session_${Math.random().toString(36).slice(2)}`}
  }
  function utm(){
    const q=new URLSearchParams(location.search),out={};
    for(const key of ['utm_source','utm_medium','utm_campaign','utm_content','utm_term']){const v=q.get(key);if(v)out[key]=safeText(v)}
    return out;
  }
  function referrerHost(){try{return document.referrer?new URL(document.referrer).hostname:''}catch{return''}}
  async function capture(event,props={}){
    if(blocked()||!event)return false;
    const name=safeText(event),now=Date.now(),last=recentEvents.get(name)||0;
    if(now-last<500)return false;
    recentEvents.set(name,now);
    const id=distinctId();
    const payload={api_key:PROJECT_TOKEN,distinct_id:id,event:name,properties:{$process_person_profile:false,$current_url:`${location.origin}${location.pathname}`,path:location.pathname,referrer_host:referrerHost(),viewport_width:window.innerWidth,viewport_height:window.innerHeight,...utm(),...props}};
    try{
      const r=await fetch(ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),keepalive:true,credentials:'omit'});
      return r.ok;
    }catch{return false}
  }
  function clickEvent(target){
    const el=target.closest?.('a,button');if(!el)return;
    const href=el instanceof HTMLAnchorElement?el.getAttribute('href')||'':'';
    const text=safeText((el.textContent||'').trim());
    if(isPromptFactory()){
      if(el.matches('[data-open-listing]'))capture('pf_listing_view_clicked',{slug:safeText(el.dataset.openListing||'')});
      else if(el.matches('[data-buy-listing]'))capture('pf_buy_clicked',{listing_id:safeText(el.dataset.buyListing||''),surface:'market_card'});
      else if(el.matches('[data-dialog-buy]'))capture('pf_buy_clicked',{listing_id:safeText(el.dataset.dialogBuy||''),surface:'listing_dialog'});
      else if(el.id==='createOrder')capture('pf_checkout_order_started');
      else if(el.id==='verifyPayment')capture('pf_payment_verification_attempted');
      else if(el.matches('.method-choice'))capture('pf_payment_method_selected',{method_id:safeText(el.dataset.id||'')});
      else if(el.matches('[data-section]'))capture('pf_section_opened',{section:safeText(el.dataset.section||''),cta:text||'button'});
    }
    if(el.matches('.select-plan'))capture('billing_plan_selected',{product_id:safeText(el.dataset.productId||'')});
    else if(!isPromptFactory()&&el.matches('.method-choice'))capture('billing_network_selected',{method_id:safeText(el.dataset.id||'')});
    else if(el.id==='createOrderBtn')capture('billing_order_attempted');
    else if(el.id==='submitTx')capture('billing_verification_attempted');
    else if(href.startsWith('/games/cryptoquest'))capture('game_play_clicked',{game:'cryptoquest',cta:text||'link'});
    else if(href.includes('creator.html')||href==='#creators')capture('creator_cta_clicked',{cta:text||'link'});
    else if(href.includes('billing.html'))capture('billing_view_clicked',{cta:text||'link'});
    else if(el.matches('[data-open="register"]'))capture('signup_opened',{cta:text||'register'});
    else if(el.matches('[data-open="login"]'))capture('login_opened',{cta:text||'login'});
  }
  window.cfsAnalytics={capture};
  document.addEventListener('click',e=>clickEvent(e.target),{capture:true});
  if(isPromptFactory()){
    let searchTimer;
    document.addEventListener('input',e=>{
      if(e.target?.id!=='marketSearch')return;
      clearTimeout(searchTimer);
      searchTimer=setTimeout(()=>capture('pf_market_search',{query_length:String(e.target.value||'').trim().length}),500);
    });
    document.addEventListener('change',e=>{
      if(e.target?.id==='categoryFilter')capture('pf_market_filter_changed',{filter:'category',value:safeText(e.target.value||'all')});
      else if(e.target?.id==='sortFilter')capture('pf_market_filter_changed',{filter:'sort',value:safeText(e.target.value||'trending')});
    });
    capture('prompt_factory_loaded',{surface:'prompt_factory'});
  }
  capture('$pageview',{page_title:safeText(document.title)});
})();
