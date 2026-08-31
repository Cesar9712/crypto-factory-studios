(()=>{
'use strict';
const V='39.0.0';
const root=()=>document.getElementById('game');
const text=el=>(el?.textContent||'').replace(/\s+/g,' ').trim();
function relabelHub(hub){
  if(!hub||hub.dataset.cq39==='1')return;
  hub.dataset.cq39='1';
  hub.classList.add('cq39-canva-master');
  const mission=hub.querySelector('.cq38-mission');
  if(mission){
    const small=mission.querySelector(':scope > small'); if(small) small.textContent='MISIÓN ACTUAL';
    const c=mission.querySelector('.cq38-continue'); if(c)c.textContent='CONTINUAR AVENTURA';
  }
  const power=hub.querySelector('.cq38-power');
  if(power){power.innerHTML='<span>PODER</span><b>1,086</b>'; power.setAttribute('aria-label','Poder del personaje');}
  const grid=hub.querySelector('.cq38-feature-grid');
  if(grid){
    const buttons=[...grid.querySelectorAll('button')];
    const spec=[
      ['INVENTARIO','bag'],
      ['HABILIDADES','talents'],
      ['TALENTOS','talents'],
      ['LOGROS','exp']
    ];
    buttons.forEach((b,i)=>{ if(!spec[i])return; const label=b.querySelector('b'); if(label)label.textContent=spec[i][0]; else b.append(Object.assign(document.createElement('b'),{textContent:spec[i][0]})); });
    if(buttons[0])buttons[0].dataset.tab='bag';
    if(buttons[1])buttons[1].dataset.tab='hero';
    if(buttons[2]){buttons[2].dataset.tab='hero';buttons[2].dataset.herotab='skills';}
    if(buttons[3])buttons[3].dataset.tab='more';
  }
  const profile=hub.querySelector('.cq38-profile-main');
  if(profile){const b=profile.querySelector('b'); if(b&&!text(b))b.textContent='Cesar';}
  const res=hub.querySelectorAll('.cq38-resource small');
  res.forEach(el=>{if(/CRISTALES/i.test(el.textContent))el.textContent='GEMAS';});
  const rails=hub.querySelectorAll('.cq38-rail,.cq38-event,.cq38-top-actions,.cq38-power');
  rails.forEach(el=>el.classList.add('cq39-secondary'));
}
function enhance(){
  const g=root(); if(!g)return;
  document.documentElement.classList.add('cq39-active');
  document.body?.classList.add('cq39-active');
  g.querySelectorAll('.cq38-hub').forEach(relabelHub);
  window.CQCanvaMaster={version:V,base:'V38.0.1',mode:'visual-layer-only'};
}
let queued=false;
function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;enhance();});}
function start(){enhance();new MutationObserver(queue).observe(root()||document.documentElement,{subtree:true,childList:true});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();