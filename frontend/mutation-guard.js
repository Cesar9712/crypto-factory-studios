// Legacy compatibility refresh helper.
// Launcher modules are now event-driven and no longer depend on broad subtree
// MutationObservers, so native MutationObserver behavior is left untouched.
function refreshMoreModules(){
  setTimeout(()=>window.dispatchEvent(new CustomEvent('nexus:state',{detail:{state:window.__NEXUS_STATE__||null,source:'more-refresh'}})),60);
}

document.addEventListener('click',e=>{
  const b=e.target?.closest?.('[data-tab]');
  if(!b)return;
  const tab=String(b.dataset.tab||'').toLowerCase();
  if(tab==='more'||tab==='más'||tab==='mas')refreshMoreModules();
},true);

window.addEventListener('pageshow',refreshMoreModules);
