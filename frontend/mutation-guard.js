// Compatibility refresh helper for launcher modules rendered inside #panel.
// The main app replaces #panel contents on navigation/state refreshes, so use a
// narrow root-level observer to restore launchers after that replacement without
// observing the whole subtree.
let moreRefreshTimer=0;

function isMoreScreen(){
  const heading=document.querySelector('#panel .section-head h2');
  return Boolean(heading&&/Más|More/i.test(heading.textContent||''));
}

function refreshMoreModules(delay=24){
  clearTimeout(moreRefreshTimer);
  moreRefreshTimer=setTimeout(()=>{
    if(!isMoreScreen())return;
    window.dispatchEvent(new CustomEvent('nexus:state',{detail:{state:window.__NEXUS_STATE__||null,source:'more-refresh'}}));
  },delay);
}

const panel=document.getElementById('panel');
if(panel){
  new MutationObserver(records=>{
    if(!records.some(record=>record.type==='childList'))return;
    if(isMoreScreen())refreshMoreModules();
  }).observe(panel,{childList:true});
}

document.addEventListener('click',e=>{
  const b=e.target?.closest?.('[data-tab],[data-more]');
  if(!b)return;
  const tab=String(b.dataset.tab||'').toLowerCase();
  if(tab==='more'||tab==='más'||tab==='mas'||b.hasAttribute('data-more'))refreshMoreModules(0);
},true);

window.addEventListener('pageshow',()=>refreshMoreModules(0));
