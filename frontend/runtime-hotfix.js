(()=>{
  if(window.__nexusRuntimeHotfix)return;

  const lang=()=>localStorage.getItem('nexus-lang')||'es';
  const txt=(es,en)=>lang()==='en'?en:es;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const nativeFetch=window.fetch.bind(window);
  let launcherTimer=0;

  const isMore=()=>/Más|More/i.test(document.querySelector('#panel .section-head h2')?.textContent||'');
  const notifyLaunchers=()=>{
    if(!isMore())return;
    window.dispatchEvent(new CustomEvent('nexus:panel-render',{detail:{source:'runtime-hotfix'}}));
    window.dispatchEvent(new CustomEvent('nexus:more-refresh',{detail:{source:'runtime-hotfix'}}));
  };
  const scheduleLaunchers=()=>{
    clearTimeout(launcherTimer);
    launcherTimer=setTimeout(notifyLaunchers,0);
    setTimeout(notifyLaunchers,80);
    setTimeout(notifyLaunchers,240);
  };

  const requestMeta=(input,init={})=>{
    try{
      const request=input instanceof Request?input:null;
      const url=new URL(request?.url||String(input),location.href);
      const method=String(init.method||request?.method||'GET').toUpperCase();
      return{url,method};
    }catch{return{url:null,method:'GET'}}
  };

  window.fetch=async(input,init={})=>{
    const meta=requestMeta(input,init);
    const response=await nativeFetch(input,init);
    if(meta.url?.origin===location.origin&&(
      (meta.url.pathname==='/api/state'&&meta.method==='GET')||
      (meta.url.pathname==='/api/action'&&meta.method==='POST')
    )) scheduleLaunchers();
    return response;
  };

  function zoneParts(zoneId){
    const node=document.querySelector(`.p1-zone-node[data-p1-zone="${CSS.escape(zoneId)}"]`);
    if(!node)return null;
    return{
      node,
      icon:node.querySelector('.p1-node-icon')?.textContent?.trim()||'🗺️',
      name:node.querySelector('.p1-node-body b')?.textContent?.trim()||zoneId,
    };
  }

  function showFastTravel(zoneId){
    const parts=zoneParts(zoneId);if(!parts)return;
    document.getElementById('p1-travel-transition')?.remove();
    const el=document.createElement('div');
    el.id='p1-travel-transition';
    el.className='p1-travel-transition';
    el.innerHTML=`<div><span>${parts.icon}</span><b>${esc(parts.name)}</b><small>${txt('Viajando…','Traveling…')}</small></div>`;
    document.body.append(el);
    setTimeout(()=>el.remove(),280);
  }

  function optimisticTravel(zoneId){
    const parts=zoneParts(zoneId);if(!parts)return;
    const nodes=[...document.querySelectorAll('.p1-zone-node[data-p1-zone]')];
    for(const node of nodes){
      const here=node.dataset.p1Zone===zoneId;
      node.classList.toggle('here',here);
      const button=node.querySelector('[data-p1-travel]');
      if(button){
        if(here){button.disabled=true;button.textContent='✓'}
        else if(!node.classList.contains('locked')){button.disabled=false;button.textContent=txt('Viajar','Travel')}
      }
      const label=node.querySelector('.p1-node-body > span');
      if(label&&here)label.textContent=txt('ESTÁS AQUÍ','YOU ARE HERE');
    }
    const hero=document.querySelector('#p1-world .p1-world-hero');
    const kicker=hero?.querySelector('.p1-kicker');
    const title=hero?.querySelector('h2');
    const orb=hero?.querySelector('.p1-zone-orb');
    if(kicker)kicker.textContent=txt('ESTÁS AQUÍ','YOU ARE HERE');
    if(title)title.textContent=`${parts.icon} ${parts.name}`;
    if(orb)orb.textContent=parts.icon;
    const hudZone=document.querySelector('.zone-line b');
    if(hudZone)hudZone.textContent=parts.name;
  }

  function runLegacyTravel(zoneId){
    const legacy=document.querySelector(`#panel [data-zone="${CSS.escape(zoneId)}"]`);
    if(!legacy||legacy.disabled)return false;
    if(typeof legacy.onclick==='function')legacy.onclick.call(legacy);
    else legacy.click();
    return true;
  }

  document.addEventListener('click',e=>{
    const travel=e.target?.closest?.('[data-p1-travel]');
    if(travel&&!travel.disabled){
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      const zoneId=travel.dataset.p1Travel;
      showFastTravel(zoneId);
      optimisticTravel(zoneId);
      if(!runLegacyTravel(zoneId))window.dispatchEvent(new Event('focus'));
      return;
    }
    if(e.target?.closest?.('[data-tab],[data-more]'))scheduleLaunchers();
  },true);

  window.addEventListener('focus',scheduleLaunchers);
  window.addEventListener('pageshow',scheduleLaunchers);
  setInterval(()=>{if(isMore()&&!document.getElementById('phase4-launcher'))notifyLaunchers()},500);
  setTimeout(scheduleLaunchers,250);

  window.__nexusRuntimeHotfix={notifyLaunchers,optimisticTravel};
})();
