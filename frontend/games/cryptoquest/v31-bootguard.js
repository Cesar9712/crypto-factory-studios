(()=>{
'use strict';
const ROOT=document.documentElement;
ROOT.dataset.cqPresentation='v31';
const START=Date.now();
let handled=false;

function txt(el){return (el?.textContent||'').replace(/\s+/g,' ').trim().toLowerCase()}
function visible(el){if(!el)return false;const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity||1)>0&&r.width>2&&r.height>2}
function hasGameUI(){
  const selectors=['nav','.bottom-nav','.nav-bottom','.screen','.home-screen','.game-screen','.hud','.resource-strip','.quest-card','.combat-screen','button'];
  let score=0;
  for(const sel of selectors){
    const nodes=[...document.querySelectorAll(sel)];
    if(nodes.some(n=>{const t=txt(n);return t&&!t.includes('cryptoquest rpg')&&visible(n)}))score++;
  }
  return score>=2 || document.querySelectorAll('button').length>=2;
}
function findSplash(){
  const candidates=[...document.querySelectorAll('body *')].filter(el=>{
    const t=txt(el);return t.includes('cryptoquest rpg')&&t.includes('v18.1a')&&t.includes('dark fantasy ui');
  });
  if(!candidates.length)return null;
  candidates.sort((a,b)=>a.getBoundingClientRect().height-b.getBoundingClientRect().height);
  let el=candidates[0];
  for(let i=0;i<5&&el?.parentElement&&el.parentElement!==document.body;i++){
    const p=el.parentElement,r=p.getBoundingClientRect();
    if(r.height>=innerHeight*.65&&r.width>=innerWidth*.75)el=p;else break;
  }
  return el;
}
function dismissSplash(){
  if(handled)return;
  const splash=findSplash();
  if(!splash)return;
  try{splash.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerType:'touch'}));splash.click?.();splash.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerType:'touch'}));}catch{}
  setTimeout(()=>{
    const again=findSplash();
    if(!again||!visible(again)){handled=true;return}
    if(!hasGameUI())return;
    handled=true;
    again.style.transition='opacity .28s ease';
    again.style.pointerEvents='none';
    again.style.opacity='0';
    setTimeout(()=>{if(again?.isConnected)again.remove()},320);
  },700);
}
function recoverViewport(){
  document.body?.style.removeProperty('display');
  document.body?.style.removeProperty('place-items');
  document.documentElement.style.minHeight='100%';
  document.body?.style.setProperty('min-height','100dvh');
}
function pass(){
  recoverViewport();
  if(Date.now()-START>2600)dismissSplash();
}

addEventListener('error',e=>{
  console.error('[CQ V31]',e.error||e.message||e);
},{capture:true});
addEventListener('unhandledrejection',e=>console.error('[CQ V31 promise]',e.reason));

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{pass();setTimeout(pass,1800);setTimeout(pass,3600);},{once:true});
else {pass();setTimeout(pass,1800);setTimeout(pass,3600);}
const mo=new MutationObserver(()=>{if(!handled&&Date.now()-START>2600)pass()});
mo.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style','hidden']});
setTimeout(()=>mo.disconnect(),15000);
})();
