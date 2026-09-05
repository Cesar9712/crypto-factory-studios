const lang=()=>localStorage.getItem('nexus-lang')||'es';
let currentState=window.__NEXUS_STATE__||null;
let busy=false;

function tr(es,en){return lang()==='es'?es:en;}
function ensureNetBadge(){
  const header=document.querySelector('.header-actions');
  if(!header)return null;
  let el=document.querySelector('#qol-net');
  if(!el){el=document.createElement('span');el.id='qol-net';el.className='qol-net';header.prepend(el);}
  el.classList.toggle('offline',!navigator.onLine);
  el.textContent=navigator.onLine?tr('● En línea','● Online'):tr('● Sin conexión','● Offline');
  return el;
}
function ensureBusy(){
  let el=document.querySelector('#qol-busy');
  if(!el){el=document.createElement('div');el.id='qol-busy';el.innerHTML='<i></i>';document.body.prepend(el);}
  el.classList.toggle('show',busy);
}
function questReady(s){
  const p=s?.player;if(!p)return 0;
  return (s.quests||[]).filter(q=>{
    const v=p.questProgressById?.[q.id]??p.questProgress?.[q.kind]??0;
    return v>=q.target&&!p.completedQuests?.includes(q.id);
  }).length;
}
function dailyReady(s){return (s?.dailyBounties||[]).filter(x=>x.progress>=x.target&&!x.claimed).length;}
function codexReady(s){return (s?.codex||[]).filter(x=>x.nextThreshold&&x.kills>=x.nextThreshold&&x.claimedTier<3).length;}
function worldReady(s){const w=s?.worldEvent;return w&&(w.status==='defeated'||w.currentHp<=0)&&w.contribution>0&&!w.claimed?1:0;}
function clickMore(section){
  document.querySelector('[data-tab="More"]')?.click();
  setTimeout(()=>document.querySelector(`[data-more="${section}"]`)?.click(),60);
}
function clickWorld(){document.querySelector('[data-tab="World"]')?.click();}
function renderAlerts(){
  if(!currentState?.player)return;
  const tabs=document.querySelector('#tabs');if(!tabs)return;
  let strip=document.querySelector('#qol-strip');
  if(!strip){strip=document.createElement('div');strip.id='qol-strip';tabs.after(strip);}
  const q=questReady(currentState),d=dailyReady(currentState),c=codexReady(currentState),w=worldReady(currentState);
  const rewards=q+d+c+w;
  const stat=Number(currentState.player.unspentPoints||0);
  const energy=Number(currentState.player.energy||0),maxEnergy=Math.max(1,Number(currentState.player.maxEnergy||1));
  const lowEnergy=currentState.player.zoneId!=='bastion'&&energy/maxEnergy<.2;
  const chips=[];
  if(rewards>0){
    const section=d?'daily':q?'quests':c?'codex':'web3';
    chips.push(`<button class="qol-chip reward" data-qol-more="${section}">🎁 ${rewards} ${tr(rewards===1?'recompensa lista':'recompensas listas',rewards===1?'reward ready':'rewards ready')}</button>`);
  }
  if(stat>0)chips.push(`<button class="qol-chip" data-qol-stats>⭐ ${stat} ${tr(stat===1?'punto de atributo':'puntos de atributos',stat===1?'stat point':'stat points')}</button>`);
  if(lowEnergy)chips.push(`<button class="qol-chip warn" data-qol-world>⚡ ${tr('Energía baja · Bastión recomendado','Low energy · Bastion recommended')}</button>`);
  const latency=Number(window.__NEXUS_LAST_LATENCY__||0);
  if(latency>1800)chips.push(`<span class="qol-chip muted">📶 ${tr('Conexión lenta','Slow connection')} · ${latency} ms</span>`);
  strip.innerHTML=chips.join('');
  strip.hidden=!chips.length;
  strip.querySelectorAll('[data-qol-more]').forEach(b=>b.onclick=()=>clickMore(b.dataset.qolMore));
  strip.querySelector('[data-qol-world]')?.addEventListener('click',clickWorld);
  strip.querySelector('[data-qol-stats]')?.addEventListener('click',()=>{const btn=document.querySelector('[data-pv2-toggle]');if(btn&&btn.textContent.trim().length)btn.click();document.querySelector('#progression-v2')?.scrollIntoView({behavior:'smooth',block:'start'});});
  const more=document.querySelector('[data-tab="More"]');
  if(more){let badge=more.querySelector('.qol-badge');if(rewards>0){if(!badge){badge=document.createElement('b');badge.className='qol-badge';more.append(badge);}badge.textContent=String(rewards);}else badge?.remove();}
}
function refreshFromGlobal(){if(window.__NEXUS_STATE__)currentState=window.__NEXUS_STATE__;ensureNetBadge();ensureBusy();renderAlerts();}

window.addEventListener('nexus:state',e=>{currentState=e.detail?.state||currentState;renderAlerts();});
window.addEventListener('nexus:network',()=>renderAlerts());
window.addEventListener('nexus:busy',e=>{busy=Boolean(e.detail?.busy);ensureBusy();});
window.addEventListener('nexus:connectivity',()=>ensureNetBadge());
window.addEventListener('online',ensureNetBadge);window.addEventListener('offline',ensureNetBadge);

// Guard against accidental double-taps on actions in mobile browsers.
let lastActionAt=0,lastActionKey='';
document.addEventListener('click',e=>{
  const b=e.target?.closest?.('button');if(!b)return;
  const actionKey=['enemy','a','zone','craft','enhance','quest','daily','codex','buy','sell','expedition'].find(k=>b.dataset?.[k]!=null);
  if(!actionKey)return;
  const key=`${actionKey}:${b.dataset[actionKey]}`;const now=Date.now();
  if(key===lastActionKey&&now-lastActionAt<900){e.preventDefault();e.stopImmediatePropagation();return;}
  lastActionAt=now;lastActionKey=key;
  if(navigator.vibrate)navigator.vibrate(12);
},true);

new MutationObserver(()=>{if(document.querySelector('#tabs'))refreshFromGlobal();}).observe(document.documentElement,{childList:true,subtree:true});
setTimeout(refreshFromGlobal,350);