/* CryptoQuest RPG V20 Battle Pass
   12 seasons / 50 tiers / free + premium track.
   Premium ownership is verified against the CFS payment backend; no wallet or
   token address is embedded here. */
(()=>{
'use strict';
const VERSION='20.0.0';
const STATE_VERSION=1;
const PRODUCT_PREFIX='cryptoquest_bp_';
const SEASONS=[
  {id:'s01',name:'Sombras del Bastión',theme:'Bastión sitiado · acero, sombra y juramentos',start:'2026-08-27T00:00:00Z',end:'2026-09-30T23:59:59Z',accent:'#b77b3c',glow:'rgba(129,73,34,.24)'},
  {id:'s02',name:'Corazón de Hielo',theme:'Tierras heladas · runas de escarcha',start:'2026-10-01T00:00:00Z',end:'2026-10-31T23:59:59Z',accent:'#58a8c8',glow:'rgba(65,126,159,.24)'},
  {id:'s03',name:'Sangre del Dragón',theme:'Fuego antiguo · juramento dracónico',start:'2026-11-01T00:00:00Z',end:'2026-11-30T23:59:59Z',accent:'#b44738',glow:'rgba(151,53,39,.25)'},
  {id:'s04',name:'Reino de los Muertos',theme:'Nigromancia · criptas y almas',start:'2026-12-01T00:00:00Z',end:'2026-12-31T23:59:59Z',accent:'#6f8a64',glow:'rgba(67,105,74,.24)'},
  {id:'s05',name:'Llamas del Abismo',theme:'Demonios · ceniza y magma',start:'2027-01-01T00:00:00Z',end:'2027-01-31T23:59:59Z',accent:'#c05a2d',glow:'rgba(163,61,30,.26)'},
  {id:'s06',name:'Templo Perdido',theme:'Reliquias · oro antiguo y misterio',start:'2027-02-01T00:00:00Z',end:'2027-02-28T23:59:59Z',accent:'#b79b55',glow:'rgba(153,126,56,.24)'},
  {id:'s07',name:'Plaga Eterna',theme:'Veneno · alquimia corrupta',start:'2027-03-01T00:00:00Z',end:'2027-03-31T23:59:59Z',accent:'#629449',glow:'rgba(79,128,55,.24)'},
  {id:'s08',name:'Titanes Caídos',theme:'Piedra · colosos y ruinas',start:'2027-04-01T00:00:00Z',end:'2027-04-30T23:59:59Z',accent:'#9c7e58',glow:'rgba(125,91,57,.24)'},
  {id:'s09',name:'Eclipse Arcano',theme:'Magia · vacío púrpura y estrellas',start:'2027-05-01T00:00:00Z',end:'2027-05-31T23:59:59Z',accent:'#8c55bd',glow:'rgba(115,64,159,.26)'},
  {id:'s10',name:'Guerra Celestial',theme:'Luz · guardianes y relámpagos',start:'2027-06-01T00:00:00Z',end:'2027-06-30T23:59:59Z',accent:'#d1b760',glow:'rgba(177,151,72,.23)'},
  {id:'s11',name:'Legión del Vacío',theme:'Abismo · sombras cósmicas',start:'2027-07-01T00:00:00Z',end:'2027-07-31T23:59:59Z',accent:'#70408f',glow:'rgba(84,43,118,.28)'},
  {id:'s12',name:'Corona del Abismo',theme:'Final anual · soberanos del vacío',start:'2027-08-01T00:00:00Z',end:'2027-08-31T23:59:59Z',accent:'#d0a04b',glow:'rgba(166,114,42,.28)'}
];
const PRODUCT_BY_SEASON=Object.fromEntries(SEASONS.map(s=>[s.id,PRODUCT_PREFIX+s.id]));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp=(n,a,b)=>Math.max(a,Math.min(b,Number(n)||0));
const now=()=>Date.now();
const gameReady=()=>{try{return typeof game!=='undefined'&&game&&game.player}catch{return false}};
const canDeliver=()=>{try{return typeof deliverRewards==='function'&&typeof saveGame==='function'}catch{return false}};

function currentSeason(at=now()){
  return SEASONS.find(s=>at>=Date.parse(s.start)&&at<=Date.parse(s.end)) || (at<Date.parse(SEASONS[0].start)?SEASONS[0]:SEASONS.at(-1));
}
function seasonState(s=currentSeason()){
  if(!gameReady())return null;
  game.battlePass ||= {version:STATE_VERSION,seasons:{},observer:{}};
  game.battlePass.version=STATE_VERSION;
  const states=game.battlePass.seasons ||= {};
  states[s.id] ||= {xp:0,claimedFree:[],claimedPremium:[],cosmetics:[],premiumCache:false,premiumCheckedAt:0,startedAt:now(),updatedAt:now()};
  const st=states[s.id];
  st.xp=Math.max(0,Number(st.xp)||0);st.claimedFree=Array.isArray(st.claimedFree)?st.claimedFree:[];st.claimedPremium=Array.isArray(st.claimedPremium)?st.claimedPremium:[];st.cosmetics=Array.isArray(st.cosmetics)?st.cosmetics:[];
  return st;
}
function tierCost(tier){return 320+Math.max(0,tier-1)*18;}
function cumulativeForTier(tier){let total=0;for(let i=1;i<tier;i++)total+=tierCost(i);return total;}
function levelFromXp(xp){let level=1;let used=0;for(let i=1;i<50;i++){const cost=tierCost(i);if(xp<used+cost)break;used+=cost;level=i+1;}return Math.min(50,level);}
function xpIntoLevel(xp){const level=levelFromXp(xp),base=cumulativeForTier(level),cost=level>=50?1:tierCost(level);return {level,current:Math.max(0,xp-base),need:cost,pct:level>=50?100:clamp((xp-base)/cost*100,0,100)};}
function rewardFor(tier,premium=false,season=currentSeason()){
  const milestone=tier%10===0,major=tier%25===0,final=tier===50;
  const factor=premium?1.8:1;
  const reward={gold:Math.round((42+tier*11)*factor),xp:Math.round((28+tier*7)*factor)};
  if(tier%5===0)reward.energy=premium?8:4;
  if(milestone)reward.materials={iron:premium?8+tier:4+Math.floor(tier/2)};
  if(major)reward.cosmetic=`${season.id}-${premium?'premium':'free'}-sigil-${tier}`;
  if(final){reward.gold+=premium?1400:650;reward.energy=(reward.energy||0)+(premium?20:10);reward.cosmetic=`${season.id}-${premium?'premium':'free'}-crown`;}
  return reward;
}
function rewardLabel(r){
  const parts=[];if(r.gold)parts.push(`${r.gold} oro`);if(r.xp)parts.push(`${r.xp} EXP`);if(r.energy)parts.push(`${r.energy} energía`);if(r.materials)parts.push('materiales');if(r.cosmetic)parts.push('cosmético');return parts.join(' · ');
}
function rewardIcon(r){if(r.cosmetic)return '♛';if(r.energy)return 'ϟ';if(r.materials)return '◆';if(r.gold)return '◉';return '✦';}

function progressSnapshot(){
  if(!gameReady())return null;
  return {
    kills:Number(game.progress?.kills||0),
    quests:Number(game.quests?.completed?.length||0),
    expeditions:Number(game.expeditions?.completed||0),
    dungeon:Number(game.statistics?.dungeonsCleared||game.statistics?.dungeonClears||0),
    level:Number(game.player?.level||1),
    tower:Number(game.activities?.tower?.bestFloor||0),
    bosses:Number(game.statistics?.bossesKilled||0)
  };
}
function awardPassXp(amount,reason){
  if(!gameReady()||amount<=0)return;
  const season=currentSeason(),st=seasonState(season);if(!st)return;
  st.xp=Math.max(0,st.xp+Math.floor(amount));st.updatedAt=now();
  try{saveGame(game)}catch{}
  toastPass(`+${Math.floor(amount)} XP DE PASE · ${reason}`);
  updateEntry();
}
function observeGameplay(){
  if(!gameReady())return;
  const bp=game.battlePass ||= {version:STATE_VERSION,seasons:{},observer:{}};
  const current=progressSnapshot();if(!current)return;
  const old=bp.observer||{};
  if(!Object.keys(old).length){bp.observer=current;try{saveGame(game)}catch{};return;}
  const gains=[
    ['kills',80,'COMBATE'],['quests',260,'MISIÓN'],['expeditions',210,'EXPEDICIÓN'],['dungeon',380,'MAZMORRA'],['level',320,'NIVEL'],['tower',90,'TORRE'],['bosses',420,'JEFE']
  ];
  let total=0,reasons=[];
  for(const [key,value,label] of gains){const diff=Math.max(0,(current[key]||0)-(old[key]||0));if(diff){total+=diff*value;reasons.push(label);}}
  bp.observer=current;
  if(total)awardPassXp(total,reasons.join(' + ')); else try{saveGame(game)}catch{}
}

function claimable(track,tier,season=currentSeason()){
  const st=seasonState(season);if(!st)return false;
  if(tier>levelFromXp(st.xp))return false;
  return !(track==='premium'?st.claimedPremium:st.claimedFree).includes(tier);
}
async function premiumOwned(season=currentSeason(),force=false){
  const st=seasonState(season);if(!st)return false;
  if(!force&&st.premiumCheckedAt&&now()-st.premiumCheckedAt<60000)return !!st.premiumCache;
  try{
    const r=await fetch(`/api/v1/cryptoquest/battle-pass/status?season_id=${encodeURIComponent(season.id)}`,{credentials:'include',cache:'no-store'});
    if(r.status===401){st.premiumCache=false;st.premiumCheckedAt=now();return false;}
    if(!r.ok)throw new Error('status unavailable');
    const data=await r.json();st.premiumCache=!!data.premium;st.premiumCheckedAt=now();return st.premiumCache;
  }catch{
    try{
      const r=await fetch('/api/v1/purchases',{credentials:'include',cache:'no-store'});if(!r.ok)throw new Error();const data=await r.json();
      st.premiumCache=(data.purchases||[]).some(p=>p.product_id===PRODUCT_BY_SEASON[season.id]);st.premiumCheckedAt=now();return st.premiumCache;
    }catch{return !!st.premiumCache;}
  }
}
function transactionId(season,track,tier){return `battlepass:${season.id}:${track}:${tier}`;}
function applyReward(reward,season,track,tier){
  if(!gameReady()||!canDeliver())return {ok:false,reason:'game-unavailable'};
  const tx=transactionId(season,track,tier),st=seasonState(season),ledger=game.rewardLedger||(game.rewardLedger=[]);
  if(ledger.includes(tx))return {ok:false,duplicate:true};
  const base={gold:reward.gold||0,xp:reward.xp||0,materials:reward.materials||{}};
  const result=deliverRewards(game,base,{transactionId:tx,save:false});if(!result?.ok)return result||{ok:false};
  if(reward.energy){game.energy.current=Math.min(game.energy.max,game.energy.current+reward.energy);game.energy.lastUpdate=Date.now();}
  if(reward.cosmetic&&!st.cosmetics.includes(reward.cosmetic))st.cosmetics.push(reward.cosmetic);
  (track==='premium'?st.claimedPremium:st.claimedFree).push(tier);st.updatedAt=now();
  saveGame(game);try{render()}catch{}
  return {ok:true};
}
async function claim(track,tier){
  const season=currentSeason(),st=seasonState(season);if(!st)return;
  if(tier>levelFromXp(st.xp)){toastPass('AÚN NO HAS ALCANZADO ESTE NIVEL');return;}
  const list=track==='premium'?st.claimedPremium:st.claimedFree;if(list.includes(tier)){toastPass('RECOMPENSA YA RECLAMADA');return;}
  if(track==='premium'&&!(await premiumOwned(season,true))){toastPass('SE REQUIERE PASE PREMIUM');await openCheckout();return;}
  const result=applyReward(rewardFor(tier,track==='premium',season),season,track,tier);
  if(result.ok){toastPass('RECOMPENSA RECLAMADA');renderModal();updateEntry();}else if(result.duplicate){if(!list.includes(tier))list.push(tier);toastPass('RECOMPENSA YA ENTREGADA');renderModal();}
}

function remainingText(season){const ms=Date.parse(season.end)-now();if(ms<=0)return 'TEMPORADA FINALIZADA';const d=Math.floor(ms/86400000),h=Math.floor((ms%86400000)/3600000);return `${d} DÍAS · ${h} H RESTANTES`;}
function hasClaimable(){if(!gameReady())return false;const s=currentSeason(),st=seasonState(s),lvl=levelFromXp(st.xp);for(let i=1;i<=lvl;i++)if(!st.claimedFree.includes(i))return true;return false;}
function updateEntry(){const b=document.getElementById('cq-bp-entry');if(b)b.classList.toggle('has-claim',hasClaimable());}
function installEntry(){
  if(document.getElementById('cq-bp-entry'))return;
  const b=document.createElement('button');b.id='cq-bp-entry';b.type='button';b.title='Pase de batalla';b.setAttribute('aria-label','Abrir pase de batalla');b.textContent='♛';b.addEventListener('click',openModal);document.body.appendChild(b);updateEntry();
}
function tierHtml(tier,premium,owned,season,st,lvl){
  const track=premium?'premium':'free',claimed=(premium?st.claimedPremium:st.claimedFree).includes(tier),unlocked=tier<=lvl&&(!premium||owned),available=unlocked&&!claimed,r=rewardFor(tier,premium,season);
  const state=claimed?'RECLAMADO':available?'RECLAMAR':premium&&!owned?'PREMIUM':tier>lvl?'BLOQUEADO':'LISTO';
  return `<button class="cq-bp-reward ${premium?'premium':''} ${claimed?'claimed':available?'available':'locked'}" data-bp-claim="${track}" data-tier="${tier}" ${available?'':'aria-disabled="true"'}><span class="cq-bp-icon">${rewardIcon(r)}</span><span><strong>${esc(rewardLabel(r))}</strong><small>${premium?'RUTA PREMIUM':'RUTA GRATUITA'}</small></span><em class="cq-bp-state">${state}</em></button>`;
}
async function renderModal(){
  const modal=document.getElementById('cq-bp-modal');if(!modal||!gameReady())return;
  const season=currentSeason(),st=seasonState(season),prog=xpIntoLevel(st.xp),owned=await premiumOwned(season),accent=season.accent;
  modal.style.setProperty('--bp-glow',season.glow);
  modal.innerHTML=`
    <section class="cq-bp-hero">
      <div class="cq-bp-top"><div><p class="cq-bp-kicker">PASE DE BATALLA · TEMPORADA ${String(SEASONS.indexOf(season)+1).padStart(2,'0')}</p><h2 class="cq-bp-title">${esc(season.name)}</h2><p class="cq-bp-sub">${esc(season.theme)} · ${remainingText(season)}</p></div><button class="cq-bp-close" data-bp-close aria-label="Cerrar">×</button></div>
      <div class="cq-bp-progress-row"><div class="cq-bp-level"><small>NIVEL</small>${prog.level}</div><div class="cq-bp-progress"><i style="width:${prog.pct}%;background:linear-gradient(90deg,#744d1b,${accent},#f0d47d)"></i></div><div class="cq-bp-xp">${prog.level>=50?'MÁXIMO':`${Math.floor(prog.current)} / ${prog.need} XP`}</div></div>
      <div class="cq-bp-status"><span class="cq-bp-chip live">● ACTIVA</span><span class="cq-bp-chip ${owned?'premium':''}">${owned?'♛ PREMIUM ACTIVO':'RUTA GRATUITA ACTIVA'}</span><span class="cq-bp-chip">50 NIVELES</span></div>
    </section>
    <div class="cq-bp-controls"><button data-bp-claim-all>RECLAMAR GRATIS DISPONIBLE</button><button class="premium" data-bp-premium>${owned?'PREMIUM VERIFICADO':'ACTIVAR PREMIUM'}</button></div>
    <div class="cq-bp-track-labels"><span>NV.</span><span>GRATIS</span><span>PREMIUM</span></div>
    <div class="cq-bp-tiers">${Array.from({length:50},(_,idx)=>{const tier=idx+1;return `<article class="cq-bp-tier"><div class="cq-bp-num">${tier}</div>${tierHtml(tier,false,owned,season,st,prog.level)}${tierHtml(tier,true,owned,season,st,prog.level)}</article>`}).join('')}</div>
    <div id="cq-bp-checkout-host"></div>
    <p class="cq-bp-note">El progreso gratuito se guarda con tu héroe. La ruta Premium solo se habilita tras una compra confirmada por el servidor de Crypto Factory Studios. Los pagos usan exclusivamente los métodos configurados por CFS.</p>`;
  modal.querySelector('[data-bp-close]')?.addEventListener('click',closeModal);
  modal.querySelector('[data-bp-premium]')?.addEventListener('click',async()=>owned?toastPass('PASE PREMIUM YA VERIFICADO'):openCheckout());
  modal.querySelector('[data-bp-claim-all]')?.addEventListener('click',claimAllFree);
  modal.querySelectorAll('[data-bp-claim]').forEach(el=>el.addEventListener('click',()=>{if(el.getAttribute('aria-disabled')==='true')return;claim(el.dataset.bpClaim,Number(el.dataset.tier));}));
}
function openModal(){
  if(!gameReady()){toastPass('CREA O CARGA UN HÉROE PRIMERO');return;}
  closeModal();const back=document.createElement('div');back.id='cq-bp-backdrop';back.innerHTML='<section id="cq-bp-modal" role="dialog" aria-modal="true" aria-label="Pase de batalla"></section>';back.addEventListener('click',e=>{if(e.target===back)closeModal()});document.body.appendChild(back);renderModal();
}
function closeModal(){document.getElementById('cq-bp-backdrop')?.remove();}
async function claimAllFree(){
  const s=currentSeason(),st=seasonState(s),lvl=levelFromXp(st.xp);let n=0;for(let tier=1;tier<=lvl;tier++){if(st.claimedFree.includes(tier))continue;const r=applyReward(rewardFor(tier,false,s),s,'free',tier);if(r.ok)n++;}
  toastPass(n?`${n} RECOMPENSAS RECLAMADAS`:'NO HAY RECOMPENSAS PENDIENTES');renderModal();updateEntry();
}

async function openCheckout(){
  const host=document.getElementById('cq-bp-checkout-host');if(!host){openModal();setTimeout(openCheckout,250);return;}
  const season=currentSeason(),productId=PRODUCT_BY_SEASON[season.id];
  host.innerHTML='<section class="cq-bp-checkout"><h3>ACTIVAR PASE PREMIUM</h3><p>Comprobando tu cuenta y los métodos de pago configurados…</p></section>';host.scrollIntoView({behavior:'smooth',block:'end'});
  try{
    const me=await fetch('/api/v1/me',{credentials:'include',cache:'no-store'});
    if(me.status===401){host.innerHTML='<section class="cq-bp-checkout"><h3>CUENTA CFS NECESARIA</h3><p>Para una compra verificable debes iniciar sesión en Crypto Factory Studios. Tu partida gratuita continúa funcionando sin pago.</p><button data-cfs-home>IR A CRYPTO FACTORY STUDIOS</button></section>';host.querySelector('[data-cfs-home]').onclick=()=>location.assign('/');return;}
    if(!me.ok)throw new Error('No se pudo validar la cuenta');
    const [productsRes,methodsRes]=await Promise.all([fetch('/api/v1/products',{credentials:'include',cache:'no-store'}),fetch('/api/v1/payments/methods',{credentials:'include',cache:'no-store'})]);
    if(!productsRes.ok||!methodsRes.ok)throw new Error('Checkout no disponible');
    const products=(await productsRes.json()).products||[],methods=(await methodsRes.json()).methods||[],product=products.find(p=>p.product_id===productId);
    if(!product)throw new Error('Producto de temporada aún no publicado');
    if(!methods.length)throw new Error('No hay métodos de pago disponibles');
    host.innerHTML=`<section class="cq-bp-checkout"><h3>${esc(season.name)} · PREMIUM</h3><p>Precio oficial: <b>$${esc(product.price_usd)} USD</b>. Selecciona uno de los métodos ya configurados en CFS.</p><div class="cq-bp-methods">${methods.map((m,i)=>`<button data-method="${esc(m.method_id)}" class="${i===0?'selected':''}"><b>${esc(m.display_name||`${m.asset} · ${m.network}`)}</b><br><small>${esc(m.warning||'')}</small></button>`).join('')}</div><button data-create-order>CREAR ORDEN SEGURA</button><div id="cq-bp-order"></div></section>`;
    let selected=methods[0].method_id;host.querySelectorAll('[data-method]').forEach(btn=>btn.onclick=()=>{selected=btn.dataset.method;host.querySelectorAll('[data-method]').forEach(b=>b.classList.toggle('selected',b===btn));});
    host.querySelector('[data-create-order]').onclick=()=>createOrder(productId,selected,host.querySelector('#cq-bp-order'));
  }catch(error){host.innerHTML=`<section class="cq-bp-checkout"><h3>CHECKOUT NO DISPONIBLE</h3><p>${esc(error.message||'No se pudo iniciar la compra.')}</p><p>No se activó Premium ni se realizó ningún cargo.</p></section>`;}
}
async function createOrder(productId,methodId,box){
  box.innerHTML='<div class="cq-bp-paybox">Creando cotización…</div>';
  try{
    const q=await fetch('/api/v1/payments/quotes',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json',...csrfHeaders()},body:JSON.stringify({product_id:productId,method_id:methodId})});const qd=await apiJson(q);
    const key=`cqbp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const o=await fetch('/api/v1/payments/orders',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json',...csrfHeaders()},body:JSON.stringify({quote_id:qd.quote_id,idempotency_key:key})});const od=await apiJson(o);
    const c=await fetch(`/api/v1/payments/orders/${encodeURIComponent(od.order_id)}/checkout`,{credentials:'include',cache:'no-store'});const cd=await apiJson(c);const order=cd.order,method=cd.payment_method;
    box.innerHTML=`<div class="cq-bp-paybox"><p>ENVÍA EXACTAMENTE</p><code>${esc(order.expected_amount)} ${esc(order.asset)} · ${esc(order.network)}</code><p>A ESTA DIRECCIÓN</p><code>${esc(order.receiving_address)}</code><p>${esc(method.warning||'')}</p><p>Después de enviar, pega el hash/TxID. Premium solo se activará si el servidor confirma red, activo, destinatario e importe.</p><input autocomplete="off" spellcheck="false" placeholder="Hash / TxID de la transacción"><button data-submit>VERIFICAR PAGO</button><p data-status></p></div>`;
    box.querySelector('[data-submit]').onclick=()=>submitTx(order.order_id,box.querySelector('input').value,box.querySelector('[data-status]'));
  }catch(error){box.innerHTML=`<div class="cq-bp-paybox"><p>${esc(error.message||'No se pudo crear la orden.')}</p></div>`;}
}
async function submitTx(orderId,txid,status){
  if(!txid.trim()){status.textContent='Introduce el hash/TxID.';return;}status.textContent='Verificando en la red…';
  try{
    const r=await fetch(`/api/v1/payments/orders/${encodeURIComponent(orderId)}/submit-tx`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json',...csrfHeaders()},body:JSON.stringify({transaction_hash:txid.trim()})});const data=await apiJson(r);status.textContent=`ESTADO: ${data.status}`;
    if(data.status==='FULFILLED'||data.status==='CONFIRMED'){const s=currentSeason(),st=seasonState(s);st.premiumCheckedAt=0;if(await premiumOwned(s,true)){toastPass('PASE PREMIUM ACTIVADO');renderModal();}}
  }catch(error){status.textContent=error.message||'No se pudo verificar la transacción.';}
}
function csrfHeaders(){const m=document.cookie.match(/(?:^|; )cfs_csrf=([^;]+)/);return m?{'X-CSRF-Token':decodeURIComponent(m[1])}:{};}
async function apiJson(r){let data={};try{data=await r.json()}catch{}if(!r.ok){const d=data.detail||data;throw new Error(d.message||d.error_code||`Error ${r.status}`)}return data;}

function toastPass(text){
  let el=document.getElementById('cq-bp-toast');if(!el){el=document.createElement('div');el.id='cq-bp-toast';Object.assign(el.style,{position:'fixed',zIndex:6000,left:'50%',bottom:'145px',transform:'translateX(-50%)',maxWidth:'86vw',padding:'9px 12px',border:'1px solid #8c682f',background:'#090806f2',color:'#ead49e',font:'800 8px Inter,sans-serif',letterSpacing:'.07em',boxShadow:'0 7px 22px #000c',textAlign:'center',pointerEvents:'none'});document.body.appendChild(el);}el.textContent=text;el.style.opacity='1';clearTimeout(el._t);el._t=setTimeout(()=>{el.style.opacity='0'},2200);
}
function exposeDebug(){
  // Read-only/debug helpers used by production QA. They do not grant premium.
  window.CryptoQuestBattlePass={version:VERSION,seasons:SEASONS.map(s=>({...s,productId:PRODUCT_BY_SEASON[s.id]})),currentSeason:()=>currentSeason(),level:()=>gameReady()?levelFromXp(seasonState().xp):0,open:openModal,awardTestXp:(n)=>{if(location.hostname==='localhost'||new URLSearchParams(location.search).has('qa'))awardPassXp(clamp(n,0,5000),'QA');}};
}
function init(){document.documentElement.dataset.cqVisual='v20';document.documentElement.dataset.cqBattlePass='12x50';installEntry();if(gameReady())seasonState();observeGameplay();exposeDebug();}
const observer=new MutationObserver(()=>{installEntry();updateEntry();});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{init();observer.observe(document.body,{childList:true,subtree:true});});else{init();observer.observe(document.body,{childList:true,subtree:true});}
setInterval(()=>{try{if(gameReady()){seasonState();observeGameplay();updateEntry();}}catch(error){console.warn('Battle Pass observer',error)}},1800);
})();
