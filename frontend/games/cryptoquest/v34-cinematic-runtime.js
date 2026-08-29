(()=>{
'use strict';
const ROOT='/games/cryptoquest/assets/';
const ICONS=[
 [/mapa|aventura/i,'map'],[/inventario|bolsa/i,'bag'],[/habilidad/i,'arcane'],[/talento/i,'talents'],[/personaje|héroe|heroe/i,'hero'],[/misiones?|quest/i,'quest'],[/logros?/i,'exp'],[/tienda/i,'shop'],[/craft|forja|fabric/i,'crafting'],[/mazmorra/i,'dungeon'],[/jefe/i,'boss'],[/recompensa|cofre/i,'loot']
];
function icon(id){return `<svg class="cq34-ui-icon" aria-hidden="true"><use href="#${id}"></use></svg>`;}
function addIcon(el){
 if(!el||el.dataset.cq34Icon||el.querySelector(':scope > .cq34-ui-icon')) return;
 const txt=(el.textContent||'').trim(); const match=ICONS.find(([re])=>re.test(txt));
 if(!match)return; el.insertAdjacentHTML('afterbegin',icon(match[1])); el.dataset.cq34Icon=match[1];
}
function makeImg(cls,src,alt=''){const img=document.createElement('img');img.className=cls;img.src=src;img.alt=alt;img.decoding='async';img.loading='eager';return img;}
function enhanceHome(screen){
 screen.classList.add('cq34-home');
 const stage=screen.querySelector('.home-hero-stage');
 if(stage&&!stage.querySelector('.cq34-scene-art')){
   stage.prepend(makeImg('cq34-scene-art',ROOT+'v34-bastion-scene.svg',''));
   const hero=makeImg('cq34-hero-art',ROOT+'v34-hero-warrior.svg','Héroe de CryptoQuest');
   hero.setAttribute('fetchpriority','high');stage.append(hero);
   const vignette=document.createElement('div');vignette.className='cq34-stage-vignette';stage.append(vignette);
 }
 screen.querySelectorAll('button,.quick-action,[role="button"]').forEach(addIcon);
}
function enhanceMap(screen){
 screen.classList.add('cq34-map-screen');
 if(!screen.querySelector('.cq34-world-art'))screen.prepend(makeImg('cq34-world-art',ROOT+'v34-world-map.svg',''));
 screen.querySelectorAll('.world-zone,.zone-card,.region-card,details').forEach((z,i)=>{z.classList.add('cq34-map-node');z.style.setProperty('--cq34-node-index',i)});
 screen.querySelectorAll('button,[role="button"]').forEach(addIcon);
}
function enhanceCombat(screen){
 screen.classList.add('cq34-combat-screen');
 const arena=screen.querySelector('.combat-arena,.battle-arena,.arena')||screen;
 if(!arena.querySelector(':scope > .cq34-combat-art'))arena.prepend(makeImg('cq34-combat-art',ROOT+'v34-combat-arena.svg',''));
 if(!arena.querySelector('.cq34-combat-hero'))arena.append(makeImg('cq34-combat-hero',ROOT+'v34-hero-warrior.svg','Héroe'));
 screen.querySelectorAll('button,.skill-btn,.skill-button,.combat-skill,[role="button"]').forEach(addIcon);
}
function enhanceInventory(screen){screen.classList.add('cq34-inventory-screen');screen.querySelectorAll('button,[role="button"]').forEach(addIcon)}
function enhanceTalents(screen){screen.classList.add('cq34-talents-screen');screen.querySelectorAll('button,[role="button"]').forEach(addIcon)}
function enhanceGeneric(screen){screen.classList.add('cq34-premium-screen');screen.querySelectorAll('button,[role="button"]').forEach(addIcon)}
function enhance(){
 document.documentElement.classList.add('cq34-active');document.body?.classList.add('cq34-active');
 const game=document.getElementById('game');if(!game)return;
 game.classList.add('cq34-game');
 game.querySelectorAll('.home-screen').forEach(enhanceHome);
 game.querySelectorAll('.world-screen,.adventure-screen').forEach(enhanceMap);
 game.querySelectorAll('.combat-screen,.battle-screen').forEach(enhanceCombat);
 game.querySelectorAll('.bag-screen,.inventory-screen,.hero-screen').forEach(enhanceInventory);
 game.querySelectorAll('.talent-screen,.talents-screen,.skills-screen').forEach(enhanceTalents);
 game.querySelectorAll('.creation-screen,.more-screen,.city-screen,.achievement-screen,.craft-screen').forEach(enhanceGeneric);
 document.querySelectorAll('.bottom-nav button').forEach(addIcon);
}
let queued=false;const queue=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;enhance()})};
const start=()=>{enhance();new MutationObserver(queue).observe(document.documentElement,{subtree:true,childList:true});};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.CQVisual={version:'34.0.0-cinematic-anime',enhance};
})();