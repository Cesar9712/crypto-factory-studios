/* CryptoQuest V21 presentation bridge — repaired.
   Keeps stable gameplay untouched; manages only presentation helpers. */
(()=>{
'use strict';
const apply=()=>{
  document.documentElement.dataset.cqVisual='v21';
  document.documentElement.dataset.cqReference='master';
};
function openPassSafely(){
  try{
    const api=window.CryptoQuestBattlePass;
    if(api&&typeof api.open==='function'){api.open();return true;}
  }catch{}
  return false;
}
function syncHomeState(){
  const shell=document.getElementById('game');
  const home=Boolean(shell&&shell.classList.contains('home-active'));
  document.documentElement.classList.toggle('cq-home-active',home);
  const entry=document.getElementById('cq-bp-entry');
  if(entry){
    entry.setAttribute('aria-hidden',home?'false':'true');
    entry.tabIndex=home?0:-1;
  }
}
function wire(){
  apply();syncHomeState();
  const entry=document.getElementById('cq-bp-entry');
  if(entry&&!entry.dataset.v21Wired){
    entry.dataset.v21Wired='1';
    entry.addEventListener('click',()=>{
      setTimeout(()=>{if(!document.getElementById('cq-bp-backdrop'))openPassSafely();},0);
    });
  }
  document.querySelectorAll('.bottom-nav button').forEach(b=>b.setAttribute('aria-live','off'));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',wire,{once:true});else wire();
window.addEventListener('load',wire,{once:true});
const observer=new MutationObserver(()=>wire());
observer.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
setTimeout(wire,250);setTimeout(wire,1000);
})();
