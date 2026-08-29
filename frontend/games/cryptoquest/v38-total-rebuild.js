(()=>{
'use strict';
const AS='/games/cryptoquest/assets/';
const SVG=id=>`<svg aria-hidden="true"><use href="#${id}"></use></svg>`;
const text=el=>(el?.textContent||'').replace(/\s+/g,' ').trim();
const num=(v,fallback='0')=>{const m=String(v||'').match(/[\d.,]+(?:\s*\/\s*[\d.,]+)?/);return m?m[0]:fallback};
function classAsset(){const t=(text(document.querySelector('.home-identity span'))||text(document.querySelector('.player-hud .identity span'))||'GUERRERO').toUpperCase();if(/MAGO/.test(t))return AS+'v34-hero-warrior.svg';if(/PÍCARO|ASESINO/.test(t))return AS+'v34-hero-warrior.svg';if(/PALADÍN/.test(t))return AS+'v34-hero-warrior.svg';if(/NIGROMANTE/.test(t))return AS+'v34-hero-warrior.svg';return AS+'v34-hero-warrior.svg'}
function sceneAsset(){return AS+'v34-scene-bastion.svg'}
function make(tag,cls,html=''){const el=document.createElement(tag);if(cls)el.className=cls;if(html)el.innerHTML=html;return el}
function button(label,tab,icon,source){const b=source?source.cloneNode(true):document.createElement('button');b.type='button';b.className='';if(!source)b.dataset.tab=tab;if(source){b.removeAttribute('style');b.className=''}b.innerHTML=SVG(icon)+`<b>${label}</b>`;return b}
function findBtn(screen,re){return [...screen.querySelectorAll('button,[role="button"]')].find(b=>re.test(text(b)))}
function getResources(screen){const strip=screen.querySelector('.home-resource-strip');const spans=strip?[...strip.querySelectorAll(':scope > span')]:[];const read=(re,fb)=>{const hit=spans.find(x=>re.test(text(x)));return num(text(hit),fb)};return {energy:read(/energ/i,'60/60'),gold:read(/oro/i,'0'),premium:read(/premium|gema|cristal/i,'0')};}
function buildHome(screen){
 if(screen.dataset.cq38==='1')return;screen.dataset.cq38='1';
 const name=text(screen.querySelector('.home-identity strong'))||'HÉROE';
 const role=text(screen.querySelector('.home-identity span'))||'AVENTURERO';
 const lvl=num(text(screen.querySelector('.home-avatar-level')),'1');
 const mission=text(screen.querySelector('.main-quest h3'))||'AVENTURA ACTIVA';
 const objective=text(screen.querySelector('.main-quest .quest-objective,.main-quest p'))||'Continúa la historia principal.';
 const r=getResources(screen);
 const hub=make('div','cq38-hub');
 const bg=document.createElement('img');bg.src=sceneAsset();bg.className='cq38-bg';bg.alt='';hub.append(bg);
 const hero=document.createElement('img');hero.src=classAsset();hero.className='cq38-hero';hero.alt='Héroe de CryptoQuest';hub.append(hero,make('div','cq38-vignette'));
 const resources=make('div','cq38-resources',
   `<div class="cq38-resource">${SVG('energy')}<span><small>ENERGÍA</small><b>${r.energy}</b></span></div>`+
   `<div class="cq38-resource">${SVG('gold')}<span><small>ORO</small><b>${r.gold}</b></span></div>`+
   `<div class="cq38-resource">${SVG('gem')}<span><small>CRISTALES</small><b>${r.premium}</b></span></div>`);hub.append(resources);
 const profile=make('div','cq38-profile');profile.innerHTML=`<div class="cq38-portrait"><img src="${classAsset()}" alt=""></div><div class="cq38-profile-main"><b>${name}</b><small>NV. ${lvl} · ${role}</small></div><div class="cq38-level"><span>PROGRESO</span><i></i></div>`;hub.append(profile);
 const acts=make('div','cq38-top-actions');acts.append(button('','more','mail',findBtn(screen,/mensaje|correo/i)),button('','more','settings',findBtn(screen,/ajustes/i)||findBtn(screen,/\.\.\./i)));hub.append(acts);
 const event=findBtn(screen,/evento/i);const eventCard=make('button','cq38-event',`<small>EVENTO ACTIVO</small><b>${mission}</b><span>Desafío temporal disponible</span>`);eventCard.type='button';eventCard.dataset.tab=event?.dataset.tab||'more';hub.append(eventCard);
 const left=make('div','cq38-rail left'),right=make('div','cq38-rail right');
 left.append(button('MISIONES','more','quest',findBtn(screen,/mision/i)),button('LOGROS','more','exp',findBtn(screen,/logro/i)),button('TIENDA','more','shop',findBtn(screen,/tienda/i)));
 right.append(button('COFRE','more','loot',findBtn(screen,/cofre|recompensa/i)),button('EVENTOS','more','arcane',event),button('MÁS','more','more',findBtn(screen,/^MÁS$/i)));
 hub.append(left,right);
 const missionBox=make('div','cq38-mission',`<small>HISTORIA PRINCIPAL</small><h3>${mission}</h3><p>${objective}</p><div class="cq38-mission-reward"><span>RECOMPENSA</span><b>AVANZAR</b></div>`);
 const continueSrc=findBtn(screen,/CONTINUAR AVENTURA|CONTINUAR/i);const c=continueSrc?continueSrc.cloneNode(true):button('CONTINUAR','adventure','sword');c.className='cq38-continue';c.textContent='CONTINUAR';missionBox.append(c);hub.append(missionBox);
 const power=make('button','cq38-power','<span>PODER DEL PERSONAJE</span><b>VER</b>');power.type='button';power.dataset.tab='hero';hub.append(power);
 const grid=make('div','cq38-feature-grid');grid.append(button('MAPA','adventure','map'),button('MAZMORRA','more','dungeon'),button('HABILIDADES','hero','talents'),button('PERSONAJE','hero','hero'));hub.append(grid);
 screen.append(hub);
}
function enhanceHero(root){root.querySelectorAll('.hero-screen .summary-avatar').forEach(h=>{if(h.dataset.cq38)return;h.dataset.cq38='1';h.textContent='';const i=document.createElement('img');i.src=classAsset();i.alt='Héroe';h.append(i)})}
function ensureInventory(root){root.querySelectorAll('.inventory-slot').forEach(card=>card.classList.add('cq38-item'))}
function ensureCombat(root){root.querySelectorAll('.combat-screen .utility-actions button,.combat-screen .skill-actions button').forEach(btn=>{const host=btn.querySelector('i');if(host&&host.children.length===0&&!text(host)){const t=text(btn);host.textContent=/defen/i.test(t)?'🛡':/poci|antídoto/i.test(t)?'✚':/maná/i.test(t)?'◆':'⚔'}})}
function refresh(){document.documentElement.classList.add('cq38-active');document.body?.classList.add('cq38-active');const root=document.getElementById('game');if(!root)return;root.querySelectorAll('.home-screen').forEach(buildHome);enhanceHero(root);ensureInventory(root);ensureCombat(root);window.CQTotalRebuild={version:'38.0.0',checkpoint:'checkpoint/cryptoquest-v37-before-total-rebuild-20260829'}}
let p=false;const queue=()=>{if(p)return;p=true;requestAnimationFrame(()=>{p=false;refresh()})};const start=()=>{refresh();new MutationObserver(queue).observe(document.getElementById('game')||document.documentElement,{subtree:true,childList:true,characterData:true})};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
