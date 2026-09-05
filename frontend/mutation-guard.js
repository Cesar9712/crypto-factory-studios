// Prevent self-triggering MutationObserver render loops in extension modules.
// Some panels rebuild their own launcher DOM inside an observer callback; observing
// that mutation again can create an endless microtask/render loop on mobile browsers.
const NativeMutationObserver=window.MutationObserver;
if(NativeMutationObserver){
  window.MutationObserver=function(callback){
    const src=Function.prototype.toString.call(callback);
    const selfRendering=/\b(renderLauncher|launcher)\b/.test(src);
    return new NativeMutationObserver(selfRendering?()=>{}:callback);
  };
  window.MutationObserver.prototype=NativeMutationObserver.prototype;
  Object.setPrototypeOf(window.MutationObserver,NativeMutationObserver);
}

function refreshMoreModules(){
  setTimeout(()=>window.dispatchEvent(new CustomEvent('nexus:state',{detail:{state:window.__NEXUS_STATE__||null,source:'mutation-guard'}})),60);
}

document.addEventListener('click',e=>{
  const b=e.target?.closest?.('[data-tab]');
  if(!b)return;
  const tab=String(b.dataset.tab||'').toLowerCase();
  if(tab==='more'||tab==='más'||tab==='mas')refreshMoreModules();
},true);

window.addEventListener('pageshow',()=>refreshMoreModules());
