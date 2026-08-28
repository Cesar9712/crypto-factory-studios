/* CryptoQuest structural presentation rebuild.
   Reorders existing live DOM only; gameplay data/actions remain owned by game.html. */
(()=>{
'use strict';
const ROOT_ID='game';
let busy=false;

function mark(){
  document.documentElement.dataset.cqVisual='v24';
  document.documentElement.dataset.cqReference='structural-rebuild';
}
function wrap(children,className){
  const node=document.createElement('div');
  node.className=className;
  children.filter(Boolean).forEach(child=>node.appendChild(child));
  return node;
}
function ensureHome(root){
  const home=root.querySelector('.home-screen');
  const hud=root.querySelector(':scope > .home-profile-hud');
  if(!home||!hud||home.dataset.cq24==='1')return;
  const hero=home.querySelector('.home-hero-stage');
  const vitals=home.querySelector('.home-vitals');
  const quest=home.querySelector('.main-quest');
  const cta=home.querySelector('.adventure-cta');
  const quick=home.querySelector('.home-quick');
  if(!hero||!vitals||!quest||!cta)return;

  home.dataset.cq24='1';
  hud.dataset.cq24Integrated='1';
  hero.dataset.cq24Integrated='1';
  vitals.dataset.cq24Integrated='1';

  const profile=hud.querySelector('.home-avatar');
  const identity=hud.querySelector('.home-identity');
  const settings=hud.querySelector('.home-settings');
  const resources=hud.querySelector('.home-resource-strip');
  const heroTop=wrap([profile,identity,settings],'cq24-hero-identity');
  const heroRail=wrap([resources],'cq24-resource-rail');
  hud.replaceChildren(heroTop,heroRail);

  hero.prepend(hud);
  hero.append(vitals);

  const mission=wrap([quest,cta],'cq24-mission-deck');
  const dashboard=wrap([hero,mission],'cq24-dashboard');
  home.prepend(dashboard);
  if(quick){quick.classList.add('cq24-home-actions');home.append(quick);}
}

function ensureCombat(root){
  const screen=root.querySelector('.combat-screen');
  if(!screen||screen.dataset.cq24==='1')return;
  const top=screen.querySelector('.combat-top');
  const enemy=screen.querySelector('.enemy-zone');
  const player=screen.querySelector('.combat-player');
  const actions=screen.querySelector('.combat-actions');
  const log=screen.querySelector('.battle-log');
  const allies=screen.querySelector('.ally-strip');
  if(!top||!enemy||!player||!actions)return;
  screen.dataset.cq24='1';

  const name=enemy.querySelector('.combat-name');
  const hp=enemy.querySelector(':scope > .bar');
  const intent=enemy.querySelector('.enemy-intent');
  const breakBar=enemy.querySelector('.break-bar');
  const telegraph=enemy.querySelector('.boss-telegraph');
  const statuses=enemy.querySelector(':scope > .status-icons');
  const figure=enemy.querySelector('.enemy-figure');
  const enemyHud=wrap([name,hp,intent,breakBar,telegraph,statuses],'cq24-enemy-hud');
  const battlefield=wrap([figure],'cq24-battlefield');
  enemy.replaceChildren(enemyHud,battlefield);

  const lower=wrap([allies,log,player],'cq24-player-dock');
  screen.insertBefore(lower,actions);
}

function ensureAdventure(root){
  const map=root.querySelector('.world-screen .world-map');
  if(!map||map.dataset.cq24==='1')return;
  map.dataset.cq24='1';
  map.querySelectorAll('.world-zone').forEach((zone,index)=>{
    zone.style.setProperty('--cq24-zone-index',String(index));
    const route=zone.querySelector('.world-route');
    if(route)route.classList.add('cq24-world-route');
  });
}

function ensureHero(root){
  const hero=root.querySelector('.hero-screen');
  if(!hero||hero.dataset.cq24==='1')return;
  hero.dataset.cq24='1';
  const summary=hero.querySelector('.summary-card');
  const build=hero.querySelector('.build-summary');
  if(summary&&build){
    const deck=wrap([summary,build],'cq24-hero-deck');
    hero.append(deck);
  }
}

function ensureTalents(root){
  const forest=root.querySelector('.talent-forest');
  if(!forest||forest.dataset.cq24==='1')return;
  forest.dataset.cq24='1';
  forest.querySelectorAll('.talent-branch').forEach((branch,index)=>{
    branch.style.setProperty('--branch-index',String(index));
    branch.querySelectorAll('.talent-node-wrap').forEach((node,i)=>node.style.setProperty('--node-index',String(i)));
  });
}

function apply(){
  if(busy)return;
  busy=true;
  try{
    mark();
    const root=document.getElementById(ROOT_ID);
    if(!root)return;
    root.classList.add('cq24-live');
    ensureHome(root);
    ensureCombat(root);
    ensureAdventure(root);
    ensureHero(root);
    ensureTalents(root);
  }finally{busy=false;}
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply,{once:true});else apply();
window.addEventListener('load',apply,{once:true});
const observer=new MutationObserver(()=>queueMicrotask(apply));
observer.observe(document.documentElement,{subtree:true,childList:true});
setTimeout(apply,120);setTimeout(apply,600);setTimeout(apply,1600);
})();
