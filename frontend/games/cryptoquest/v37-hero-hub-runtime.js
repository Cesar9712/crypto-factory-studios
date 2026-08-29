(()=>{
'use strict';
const SVG=id=>`<svg aria-hidden="true"><use href="#${id}"></use></svg>`;
const LABEL_ICON=[[/misiones?|quest/i,'quest'],[/logros?/i,'exp'],[/tienda|shop/i,'shop'],[/recompensa|cofre/i,'loot'],[/evento/i,'arcane'],[/expedici/i,'map'],[/mazmorra/i,'dungeon'],[/mapa|aventura/i,'map'],[/inventario|bolsa/i,'bag'],[/habilidad|talento/i,'talents'],[/h[eé]roe|personaje/i,'hero'],[/m[aá]s/i,'more']];
function text(el){return (el?.textContent||'').replace(/\s+/g,' ').trim()}
function iconFor(label,fallback='arcane'){return LABEL_ICON.find(([re])=>re.test(label))?.[1]||fallback}
function copyButton(source,label){
  if(source){const b=source.cloneNode(true);b.classList.add('cq37-clone');return b}
  const b=document.createElement('button');b.type='button';b.dataset.tab='more';b.innerHTML=SVG(iconFor(label))+'<b>'+label+'</b>';return b;
}
function makeTargetButton(label,tab,icon){const b=document.createElement('button');b.type='button';b.dataset.tab=tab;b.innerHTML=SVG(icon)+'<b>'+label+'</b>';return b}
function findQuick(screen,re){return [...screen.querySelectorAll('.home-quick > button,.home-quick [role="button"]')].find(b=>re.test(text(b)))}
function buildHub(screen){
  if(screen.dataset.cq37Hub==='1')return;
  screen.dataset.cq37Hub='1';screen.classList.add('cq37-hub');
  const missionTitle=text(screen.querySelector('.main-quest h3'))||'AVENTURA ACTIVA';
  const event=document.createElement('button');event.type='button';event.className='cq37-event-card';event.dataset.tab='more';event.innerHTML=`<small>EVENTO ACTIVO</small><b>${missionTitle}</b><span>Explora desafíos y recompensas</span>`;screen.append(event);

  const left=document.createElement('div');left.className='cq37-side cq37-side-left';
  const right=document.createElement('div');right.className='cq37-side cq37-side-right';
  const leftDefs=[[/mision/i,'MISIONES'],[/logro/i,'LOGROS'],[/tienda/i,'TIENDA']];
  const rightDefs=[[/evento/i,'EVENTOS'],[/expedici/i,'EXPEDICIONES'],[/recomp|cofre/i,'RECOMPENSAS']];
  for(const [re,label] of leftDefs){const src=findQuick(screen,re);const b=copyButton(src,label);if(!src)b.dataset.tab='more';if(!b.querySelector('svg'))b.insertAdjacentHTML('afterbegin',SVG(iconFor(label)));left.append(b)}
  for(const [re,label] of rightDefs){const src=findQuick(screen,re);const b=copyButton(src,label);if(!src)b.dataset.tab='more';if(!b.querySelector('svg'))b.insertAdjacentHTML('afterbegin',SVG(iconFor(label)));right.append(b)}
  screen.append(left,right);

  const grid=document.createElement('div');grid.className='cq37-primary-grid';
  grid.append(
    makeTargetButton('MAPA','adventure','map'),
    makeTargetButton('MAZMORRA','more','dungeon'),
    makeTargetButton('HABILIDADES','hero','arcane'),
    makeTargetButton('PERSONAJE','hero','hero')
  );screen.append(grid);

  const power=document.createElement('button');power.type='button';power.className='cq37-power-strip';power.dataset.tab='hero';power.innerHTML='<span>PODER DEL PERSONAJE</span><strong>VER</strong>';screen.append(power);
}
function refresh(){document.documentElement.classList.add('cq37-active');document.body?.classList.add('cq37-active');document.querySelectorAll('.home-screen').forEach(buildHub);window.CQHeroHub={version:'37.0.0',checkpoint:'checkpoint/cryptoquest-v35-pre-risk-rebuild-20260829'}}
let pending=false;const queue=()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;refresh()})};
const start=()=>{refresh();new MutationObserver(queue).observe(document.getElementById('game')||document.documentElement,{subtree:true,childList:true,characterData:true})};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
