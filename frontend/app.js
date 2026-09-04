import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const SUPABASE_URL='https://culwlrspkwbcbtmopgcp.supabase.co';
const SUPABASE_PUBLISHABLE_KEY='sb_publishable_JfDoNvnecRDooAOK6dTg2A_2fRV5zRZ';
const supabase=createClient(SUPABASE_URL,SUPABASE_PUBLISHABLE_KEY,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});

const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
let state=null,session=null,polling=false,lastLog=[];
let tab='Adventure',inventorySection='items',craftFilter='all',lang=localStorage.getItem('nexus-lang')||'es';

const T={
  es:{
    language:'Idioma',logout:'Salir',reset:'Reiniciar demo',level:'Nivel',gold:'Oro',energy:'Energía',life:'Vida',mana:'Maná',next:'Próximo +',full:'Lleno',field:'Mundo',bastion:'Bastión',regen:'Regeneración',boost:'Bonificación x2 activa',adventure:'Mundo',combat:'Combate',inventory:'Mochila',crafting:'Forja',more:'Más',market:'Mercado',quests:'Misiones',web3:'Web3',travel:'Viajar',current:'Actual',locked:'Bloqueado',requires:'Requiere nivel',gather:'Recolectar',mine:'Minar',fish:'Pescar',harvest:'Cortar madera',items:'Objetos',equipment:'Equipo',resources:'Recursos',empty:'Inventario vacío',equipped:'Equipado',equip:'Equipar',sell:'Vender',weapon:'Arma',armor:'Armadura',boots:'Botas',ring:'Anillo',recipeCost:'Costo',craft:'Fabricar',reward:'Recompensa',claim:'Reclamar',claimed:'Reclamada',boss:'JEFE',mobs:'Mobs',enemiesHere:'Enemigos de la zona',noEnemies:'No hay enemigos aquí',login:'Iniciar sesión',signup:'Crear cuenta',playerName:'Nombre de jugador',password:'Contraseña',class:'Clase',createCharacter:'Crear personaje',saved:'Tu progreso se guarda permanentemente',emailConfirm:'Cuenta creada. Revisa el correo de confirmación y después inicia sesión',sessionClosed:'Sesión cerrada. Tu progreso sigue guardado',walletOptional:'Wallet opcional',connectWallet:'Conectar wallet EVM',disconnect:'Desconectar',realMoneyOff:'Dinero real bloqueado',moneyText:'Pagos, depósitos y retiros siguen desactivados hasta la fase final',demoMarket:'Mercado DEMO con oro interno. No mueve criptomonedas ni dinero real',combatLog:'Registro de combate',fight:'Combatir',zone:'Zona',xp:'XP',tonic:'Acelera la regeneración durante un tiempo; no restaura nada al instante',ore:'Mineral',wood:'Madera',fishRes:'Pez',essence:'Esencia',allGood:'Listo',destinations:'Destinos',actions:'Acciones',status:'Estado',normalRegen:'Regeneración normal',bastionRegen:'Regeneración acelerada',toFull:'Hasta llenar',active:'Activas',ready:'Listas',completed:'Completadas',all:'Todo',gear:'Equipo',consumables:'Consumibles',back:'Volver',account:'Cuenta',settings:'Ajustes',safeZone:'Zona segura',dangerZone:'Zona de aventura',currentZone:'Zona actual',noListings:'No hay anuncios',buy:'Comprar',emptySlot:'Vacío',summary:'Resumen',availableGold:'Oro disponible'
  },
  en:{
    language:'Language',logout:'Logout',reset:'Reset demo',level:'Level',gold:'Gold',energy:'Energy',life:'Health',mana:'Mana',next:'Next +',full:'Full',field:'World',bastion:'Bastion',regen:'Regeneration',boost:'Temporary x2 boost active',adventure:'World',combat:'Combat',inventory:'Bag',crafting:'Forge',more:'More',market:'Market',quests:'Quests',web3:'Web3',travel:'Travel',current:'Current',locked:'Locked',requires:'Requires level',gather:'Gather',mine:'Mine',fish:'Fish',harvest:'Gather wood',items:'Items',equipment:'Equipment',resources:'Resources',empty:'Inventory empty',equipped:'Equipped',equip:'Equip',sell:'Sell',weapon:'Weapon',armor:'Armor',boots:'Boots',ring:'Ring',recipeCost:'Cost',craft:'Craft',reward:'Reward',claim:'Claim',claimed:'Claimed',boss:'BOSS',mobs:'Mobs',enemiesHere:'Enemies in this zone',noEnemies:'No enemies here',login:'Login',signup:'Create account',playerName:'Player name',password:'Password',class:'Class',createCharacter:'Create character',saved:'Your progress is saved permanently',emailConfirm:'Account created. Confirm your email, then sign in',sessionClosed:'Signed out. Your progress remains saved',walletOptional:'Optional wallet',connectWallet:'Connect EVM wallet',disconnect:'Disconnect',realMoneyOff:'Real money disabled',moneyText:'Payments, deposits and withdrawals remain disabled until the final phase',demoMarket:'DEMO market using internal gold. No cryptocurrency or real money moves',combatLog:'Combat log',fight:'Fight',zone:'Zone',xp:'XP',tonic:'Accelerates regeneration for a while; it restores nothing instantly',ore:'Ore',wood:'Wood',fishRes:'Fish',essence:'Essence',allGood:'Done',destinations:'Destinations',actions:'Actions',status:'Status',normalRegen:'Normal regeneration',bastionRegen:'Accelerated regeneration',toFull:'Until full',active:'Active',ready:'Ready',completed:'Completed',all:'All',gear:'Gear',consumables:'Consumables',back:'Back',account:'Account',settings:'Settings',safeZone:'Safe zone',dangerZone:'Adventure zone',currentZone:'Current zone',noListings:'No listings',buy:'Buy',emptySlot:'Empty',summary:'Summary',availableGold:'Available gold'
  }
};

const t=k=>T[lang]?.[k]??T.es[k]??k;
const lname=o=>lang==='es'?(o?.nameEs||o?.name):o?.name;
const ldesc=o=>lang==='es'?(o?.descriptionEs||o?.description):o?.description;
const className=c=>({es:{warrior:'Guerrero',mage:'Mago',archer:'Arquero',assassin:'Asesino'},en:{warrior:'Warrior',mage:'Mage',archer:'Archer',assassin:'Assassin'}}[lang]||{})[c]||c;
const resourceName=k=>({ore:t('ore'),wood:t('wood'),fish:t('fishRes'),essence:t('essence')})[k]||k;
const fmtTime=ms=>{if(ms<=0)return '00:00';let s=Math.ceil(ms/1000),h=Math.floor(s/3600);s%=3600;const m=Math.floor(s/60),sec=s%60;return h?`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`:`${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`};
const pct=(n,m)=>Math.max(0,Math.min(100,m?Math.round(n/m*100):0));

function ensureLanguagePicker(){
  const h=document.querySelector('.header-actions');
  if(!h||$('#lang-select'))return;
  const sel=document.createElement('select');
  sel.id='lang-select';sel.className='lang-select';
  sel.innerHTML='<option value="es">🇪🇸 ES</option><option value="en">🇬🇧 EN</option>';
  sel.value=lang;
  sel.onchange=()=>{lang=sel.value;localStorage.setItem('nexus-lang',lang);refreshStaticButtons();state?render():renderAuth();};
  h.prepend(sel);refreshStaticButtons();
}
function refreshStaticButtons(){if($('#logout'))$('#logout').textContent=t('logout');if($('#reset'))$('#reset').textContent=t('reset')}
function toast(m){const x=$('#toast');x.textContent=humanError(m);x.classList.add('show');setTimeout(()=>x.classList.remove('show'),2500)}
function humanError(m=''){if(lang==='en')return m;return String(m).replace(/Not enough energy: need (\d+)/,'Energía insuficiente: necesitas $1').replace(/Need (\d+) gold/,'Necesitas $1 de oro').replace(/Level (\d+) required/,'Se requiere nivel $1').replace('Travel to an adventure zone first','Viaja primero a una zona de aventura').replace('Enemy is in another zone','Ese enemigo está en otra zona').replace('Unknown enemy','Enemigo desconocido').replace('Unknown recipe','Receta desconocida').replace('Quest not complete','Misión incompleta').replace('Already claimed','Ya reclamada')}
function authHeaders(){return session?.access_token?{authorization:`Bearer ${session.access_token}`}:{}}
async function api(path,opt={}){const r=await fetch(path,{...opt,headers:{'content-type':'application/json',...authHeaders(),...(opt.headers||{})}});let j={};try{j=await r.json()}catch{}if(r.status===401){await supabase.auth.signOut();throw new Error(lang==='es'?'Sesión expirada':'Session expired')}if(!r.ok||j.error)throw new Error(j.error||'Request failed');return j}
function setLoggedInUi(v){$('#logout').hidden=!v;$('#reset').hidden=!v}

function renderAuth(message){
  ensureLanguagePicker();state=null;setLoggedInUi(false);$('#hud').innerHTML='';$('#tabs').innerHTML='';
  $('#panel').innerHTML=`<div class="auth-wrap"><div class="card auth-card"><span class="eyebrow">NEXUS REALMS</span><h2>${t('login')} / ${t('signup')}</h2><p>${esc(message||t('saved'))}</p><div class="auth-grid"><form id="login-form"><h3>${t('login')}</h3><label>Email<input id="login-email" type="email" autocomplete="email" required></label><label>${t('password')}<input id="login-password" type="password" autocomplete="current-password" minlength="6" required></label><button class="primary" type="submit">${t('login')}</button></form><form id="signup-form"><h3>${t('signup')}</h3><label>${t('playerName')}<input id="signup-username" maxlength="24" autocomplete="nickname" required></label><label>Email<input id="signup-email" type="email" autocomplete="email" required></label><label>${t('password')}<input id="signup-password" type="password" autocomplete="new-password" minlength="6" required></label><label>${t('class')}<select id="signup-class"><option value="warrior">${className('warrior')}</option><option value="mage">${className('mage')}</option><option value="archer">${className('archer')}</option><option value="assassin">${className('assassin')}</option></select></label><button class="primary" type="submit">${t('createCharacter')}</button></form></div><p class="muted">${t('moneyText')}</p></div></div>`;
  $('#login-form').onsubmit=async e=>{e.preventDefault();try{const {data,error}=await supabase.auth.signInWithPassword({email:$('#login-email').value.trim(),password:$('#login-password').value});if(error)throw error;session=data.session;await load()}catch(err){toast(err.message)}};
  $('#signup-form').onsubmit=async e=>{e.preventDefault();try{const username=$('#signup-username').value.trim(),email=$('#signup-email').value.trim(),password=$('#signup-password').value,playerClass=$('#signup-class').value;const {data,error}=await supabase.auth.signUp({email,password,options:{data:{username,class:playerClass}}});if(error)throw error;if(data.session){session=data.session;await load()}else renderAuth(t('emailConfirm'))}catch(err){toast(err.message)}};
}

async function load({quiet=false}={}){if(!session)return renderAuth();if(polling)return;polling=true;try{state=await api('/api/state');setLoggedInUi(true);render()}catch(e){if(!quiet)toast(e.message)}finally{polling=false}}
async function action(name,payload={}){try{const r=await api('/api/action',{method:'POST',body:JSON.stringify({action:name,payload})});state=r;if(r.log)lastLog=r.log;toast(r.message||t('allGood'));render()}catch(e){toast(e.message)}}
function stats(){const p=state.player,eq=Object.values(p.equipment).map(id=>p.inventory.find(i=>i.id===id)).filter(Boolean);return{atk:p.stats.atk+eq.reduce((n,i)=>n+(i.atk||0),0),def:p.stats.def+eq.reduce((n,i)=>n+(i.def||0),0)}}
function zone(){return state.zones?.find(z=>z.id===state.player.zoneId)||{name:'Unknown',nameEs:'Desconocida'}}
function effectiveRate(key){const r=state.player.regen||{},boost=r.boostUntil&&r.boostUntil>Date.now()?2:1;return Number(r[key]||0)*boost}
function timeToFull(current,max,rate){if(current>=max)return 0;if(rate<=0)return Infinity;const ticks=Math.ceil((max-current)/rate),first=Math.max(0,(state.player.regen?.nextTickAt||Date.now())-Date.now());return first+Math.max(0,ticks-1)*60000}

function resourceGauge(label,current,max,key,kind){
  const rate=effectiveRate(key),next=Math.max(0,(state.player.regen?.nextTickAt||Date.now())-Date.now()),full=timeToFull(current,max,rate);
  return `<div class="resource-gauge ${kind}"><div class="gauge-head"><b>${label}</b><span>${current}/${max}</span></div><div class="meter"><i style="width:${pct(current,max)}%"></i></div><div class="gauge-foot"><span>+${rate}/min</span><span>${t('next')} <strong data-next>${fmtTime(next)}</strong></span><span>${t('toFull')} <strong data-full data-current="${current}" data-max="${max}" data-rate-key="${key}">${current>=max?'✓':fmtTime(full)}</strong></span></div></div>`;
}

function renderHud(){
  const p=state.player,s=stats(),z=zone(),isBastion=p.regen?.mode==='bastion';
  $('#hud').innerHTML=`<section class="player-summary"><div class="player-main"><div><span class="eyebrow">${esc(className(p.class))}</span><h2>${esc(p.name)}</h2></div><div class="summary-chips"><span>${t('level')} <b>${p.level}</b></span><span>🪙 <b>${p.gold}</b></span><span>⚔ <b>${s.atk}</b></span><span>🛡 <b>${s.def}</b></span></div></div><div class="zone-line"><span>${t('currentZone')}</span><b>${esc(lname(z))}</b><span class="mode-badge ${isBastion?'safe':'field'}">${isBastion?t('bastionRegen'):t('normalRegen')}</span></div></section><section class="resource-panel">${resourceGauge(t('life'),p.hp,p.maxHp,'hpPerMinute','hp')}${resourceGauge(t('mana'),p.mana,p.maxMana,'manaPerMinute','mana')}${resourceGauge(t('energy'),p.energy,p.maxEnergy,'energyPerMinute','energy')}</section>${p.regen?.boostUntil&&p.regen.boostUntil>Date.now()?`<div class="boost-banner">⚡ ${t('boost')} · ${fmtTime(p.regen.boostUntil-Date.now())}</div>`:''}`;
  updateTimers();
}

function updateTimers(){if(!state)return;const next=Math.max(0,(state.player.regen?.nextTickAt||Date.now())-Date.now());document.querySelectorAll('[data-next]').forEach(x=>x.textContent=fmtTime(next));document.querySelectorAll('[data-full]').forEach(x=>{const cur=Number(x.dataset.current),max=Number(x.dataset.max),rate=effectiveRate(x.dataset.rateKey);x.textContent=cur>=max?'✓':fmtTime(timeToFull(cur,max,rate))})}

function renderTabs(){
  const primary=['Adventure','Combat','Inventory','Crafting','More'];
  const labels={Adventure:`🌍 ${t('adventure')}`,Combat:`⚔ ${t('combat')}`,Inventory:`🎒 ${t('inventory')}`,Crafting:`🔨 ${t('crafting')}`,More:`☰ ${t('more')}`};
  const active=primary.includes(tab)?tab:['Market','Quests','Web3'].includes(tab)?'More':'Adventure';
  $('#tabs').innerHTML=primary.map(x=>`<button data-tab="${x}" class="${active===x?'active':''}">${labels[x]}</button>`).join('');
}

function sectionHeader(title,sub=''){return `<div class="section-head"><div><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div></div>`}
function backToMore(){return `<button class="back-btn" data-tab="More">← ${t('back')}</button>`}

function adventure(){
  const p=state.player,z=zone(),inBastion=p.zoneId==='bastion';
  const actions=inBastion?`<div class="empty-state"><b>🏰 ${t('bastion')}</b><p>${lang==='es'?'Aquí descansas y la regeneración es más rápida. Viaja para recolectar y combatir.':'You rest here with faster regeneration. Travel to gather and fight.'}</p></div>`:`<div class="action-grid"><button class="action-tile" data-a="mine"><span>⛏</span><b>${t('mine')}</b><small>5⚡ · ${t('ore')} ${p.resources.ore}</small></button><button class="action-tile" data-a="harvest"><span>🌲</span><b>${t('harvest')}</b><small>5⚡ · ${t('wood')} ${p.resources.wood}</small></button><button class="action-tile" data-a="fish"><span>🎣</span><b>${t('fish')}</b><small>7⚡ · ${t('fishRes')} ${p.resources.fish}</small></button></div>`;
  const zones=state.zones.map(x=>{const locked=p.level<x.requiredLevel,current=p.zoneId===x.id;return `<article class="destination ${current?'current-destination':''} ${locked?'locked-destination':''}"><div><span class="zone-icon">${x.safe?'🏰':'🗺'}</span><div><b>${esc(lname(x))}</b><small>${x.safe?t('safeZone'):t('dangerZone')} · ${t('level')} ${x.requiredLevel}</small></div></div><p>${esc(ldesc(x))}</p><button data-zone="${x.id}" ${current||locked?'disabled':''}>${current?t('current'):locked?`${t('locked')} · ${t('level')} ${x.requiredLevel}`:t('travel')}</button></article>`}).join('');
  return `${sectionHeader(`🌍 ${t('adventure')}`)}<div class="current-zone-card"><div><span>${t('currentZone')}</span><h3>${esc(lname(z))}</h3><p>${esc(ldesc(z))}</p></div><span class="pill">${inBastion?t('safeZone'):t('dangerZone')}</span></div><section class="content-block"><h3>${t('actions')}</h3>${actions}</section><section class="content-block"><h3>${t('destinations')}</h3><div class="destination-list">${zones}</div></section>`;
}

function combat(){
  const p=state.player,z=zone(),enemies=state.enemies.filter(e=>e.zoneId===p.zoneId),bosses=enemies.filter(e=>e.boss),mobs=enemies.filter(e=>!e.boss);
  if(!enemies.length)return `${sectionHeader(`⚔ ${t('combat')}`,esc(lname(z)))}<div class="empty-state"><b>${t('noEnemies')}</b><p>${lang==='es'?'Ve al Mundo y viaja a una zona de aventura.':'Go to World and travel to an adventure zone.'}</p><button data-tab="Adventure">${t('adventure')}</button></div>`;
  const enemyCards=list=>list.map(e=>`<article class="enemy-row ${e.boss?'boss-row':''}"><div class="enemy-title"><div><b>${esc(lname(e))}</b><small>${e.boss?t('boss'):`${t('level')} ${e.level}`}</small></div><span>HP ${e.hp}</span></div><div class="enemy-stats"><span>⚔ ${e.atk}</span><span>🛡 ${e.def}</span><span>🪙 ${e.reward.gold}</span><span>XP ${e.reward.xp}</span></div><button class="primary" data-enemy="${e.id}">${t('fight')} · ${10+e.level}⚡</button></article>`).join('');
  return `${sectionHeader(`⚔ ${t('combat')}`,`${t('zone')}: ${esc(lname(z))}`)}${bosses.length?`<section class="content-block"><h3>👑 ${t('boss')}</h3><div class="enemy-list">${enemyCards(bosses)}</div></section>`:''}${mobs.length?`<section class="content-block"><h3>👾 ${t('mobs')}</h3><div class="enemy-list">${enemyCards(mobs)}</div></section>`:''}${lastLog.length?`<section class="content-block"><h3>📜 ${t('combatLog')}</h3><div class="log">${lastLog.map(x=>`<div>${esc(x)}</div>`).join('')}</div></section>`:''}`;
}

function inventory(){
  const p=state.player;
  const subtabs=`<div class="segmented"><button data-inv="items" class="${inventorySection==='items'?'active':''}">${t('items')} <span>${p.inventory.length}</span></button><button data-inv="equipment" class="${inventorySection==='equipment'?'active':''}">${t('equipment')}</button><button data-inv="resources" class="${inventorySection==='resources'?'active':''}">${t('resources')}</button></div>`;
  let body='';
  if(inventorySection==='resources'){
    body=`<div class="resource-list">${Object.entries(p.resources).map(([k,v])=>`<div class="resource-row"><span>${{ore:'⛏',wood:'🌲',fish:'🎣',essence:'✨'}[k]||'•'}</span><b>${esc(resourceName(k))}</b><strong>${v}</strong></div>`).join('')}</div>`;
  }else if(inventorySection==='equipment'){
    body=`<div class="equipment-list">${['weapon','armor','boots','ring'].map(slot=>{const id=p.equipment[slot],item=p.inventory.find(i=>i.id===id);return `<div class="equipment-row"><div><span>${{weapon:'⚔',armor:'🛡',boots:'🥾',ring:'💍'}[slot]}</span><div><small>${t(slot)}</small><b>${item?esc(item.name):t('emptySlot')}</b></div></div>${item?`<span class="${item.rarity}">ATK ${item.atk||0} · DEF ${item.def||0}</span>`:'<span>—</span>'}</div>`}).join('')}</div>`;
  }else{
    body=`<div class="inventory-list">${p.inventory.map(i=>`<article class="inventory-row"><div class="item-main"><b class="${i.rarity}">${esc(i.name)}</b><small>${esc(i.type)} · ${i.rarity} · ATK ${i.atk||0} · DEF ${i.def||0}</small></div><div class="item-actions">${i.slot?`<button data-equip="${i.id}">${p.equipment[i.slot]===i.id?t('equipped'):t('equip')}</button>`:''}<button class="ghost" data-sell="${i.id}">${t('sell')}</button></div></article>`).join('')||`<div class="empty-state">${t('empty')}</div>`}</div>`;
  }
  return `${sectionHeader(`🎒 ${t('inventory')}`)}${subtabs}<section class="content-block flush">${body}</section>`;
}

function crafting(){
  const p=state.player;
  const filters=`<div class="segmented compact"><button data-craft-filter="all" class="${craftFilter==='all'?'active':''}">${t('all')}</button><button data-craft-filter="gear" class="${craftFilter==='gear'?'active':''}">${t('gear')}</button><button data-craft-filter="consumable" class="${craftFilter==='consumable'?'active':''}">${t('consumables')}</button></div>`;
  const filtered=state.recipes.filter(r=>craftFilter==='all'||(craftFilter==='consumable'?r.out?.type==='consumable':r.out?.type!=='consumable'));
  const cards=filtered.map(r=>{const resourcesOk=Object.entries(r.cost).every(([k,v])=>(p.resources[k]||0)>=v),goldOk=p.gold>=r.goldCost,energyOk=p.energy>=r.energyCost,can=resourcesOk&&goldOk&&energyOk;return `<article class="recipe-row"><div class="recipe-title"><div><b>${esc(lname(r))}</b><small>${r.out?.type==='consumable'?t('consumables'):t('gear')}</small></div><strong>${r.goldCost} 🪙</strong></div><div class="cost-line"><span>${r.energyCost}⚡</span>${Object.entries(r.cost).map(([k,v])=>`<span class="${(p.resources[k]||0)<v?'missing-text':''}">${v} ${esc(resourceName(k))}</span>`).join('')}</div>${r.out?.type==='consumable'?`<p>${t('tonic')}</p>`:`<p>ATK ${r.out?.atk||0} · DEF ${r.out?.def||0} ${r.out?.slot?`· ${t(r.out.slot)}`:''}</p>`}<button class="primary" ${can?'':'disabled'} data-craft="${r.id}">${t('craft')}</button></article>`}).join('');
  return `${sectionHeader(`🔨 ${t('crafting')}`,`${t('availableGold')}: ${p.gold}`)}${filters}<div class="recipe-list">${cards}</div>`;
}

function quests(){
  const p=state.player;
  const rows=state.quests.map(q=>{const v=p.questProgressById?.[q.id]??p.questProgress[q.kind]??0,done=v>=q.target,claimed=p.completedQuests.includes(q.id);return{q,v,done,claimed}}).sort((a,b)=>Number(b.done&&!b.claimed)-Number(a.done&&!a.claimed)||Number(a.claimed)-Number(b.claimed));
  const ready=rows.filter(x=>x.done&&!x.claimed).length,completed=rows.filter(x=>x.claimed).length,active=rows.length-completed;
  const html=rows.map(({q,v,done,claimed})=>{const qz=q.zoneId?state.zones.find(z=>z.id===q.zoneId):null;return `<article class="quest-row ${claimed?'quest-claimed':done?'quest-ready':''}"><div class="quest-title"><div><b>${esc(lname(q))}</b>${qz?`<small>${esc(lname(qz))}</small>`:''}</div><span>${v}/${q.target}</span></div><div class="progress"><i style="width:${Math.min(100,v/q.target*100)}%"></i></div><div class="quest-foot"><span>🪙 ${q.reward.gold} · XP ${q.reward.xp}</span><button data-quest="${q.id}" ${!done||claimed?'disabled':''}>${claimed?t('claimed'):t('claim')}</button></div></article>`}).join('');
  return `${backToMore()}${sectionHeader(`📜 ${t('quests')}`)}<div class="overview-chips"><span>${t('active')} <b>${active}</b></span><span>${t('ready')} <b>${ready}</b></span><span>${t('completed')} <b>${completed}</b></span></div><div class="quest-list">${html}</div>`;
}

function market(){
  const rows=state.market.map(m=>`<article class="market-row"><div><b class="${m.rarity}">${esc(m.name)}</b><small>${m.rarity} · ATK ${m.atk||0} · DEF ${m.def||0}</small></div><div class="market-buy"><strong>${m.price}g</strong><button data-buy="${m.id}" ${m.seller===state.player.id?'disabled':''}>${t('buy')}</button></div></article>`).join('');
  return `${backToMore()}${sectionHeader(`🛒 ${t('market')}`)}<div class="info-note">${t('demoMarket')}</div><div class="market-list">${rows||`<div class="empty-state">${t('noListings')}</div>`}</div>`;
}

function web3(){
  const p=state.player;
  return `${backToMore()}${sectionHeader(`🔗 ${t('web3')}`)}<div class="settings-list"><section class="setting-row"><div><b>${t('walletOptional')}</b><small>${p.wallet?esc(p.wallet):(lang==='es'?'El juego funciona sin wallet blockchain':'The game works without a blockchain wallet')}</small></div><div class="actions"><button id="wallet">${p.wallet?(lang==='es'?'Reconectar':'Reconnect'):t('connectWallet')}</button><button id="disconnect" class="ghost">${t('disconnect')}</button></div></section><section class="setting-row"><div><b>${t('realMoneyOff')}</b><small>${t('moneyText')}</small></div></section></div>`;
}

function more(){
  const p=state.player,ready=state.quests.filter(q=>{const v=p.questProgressById?.[q.id]??p.questProgress[q.kind]??0;return v>=q.target&&!p.completedQuests.includes(q.id)}).length;
  return `${sectionHeader(`☰ ${t('more')}`)}<div class="more-grid"><button class="more-card" data-tab="Quests"><span>📜</span><div><b>${t('quests')}</b><small>${ready?`${ready} ${t('ready').toLowerCase()}`:lang==='es'?'Revisa tu progreso':'Check your progress'}</small></div></button><button class="more-card" data-tab="Market"><span>🛒</span><div><b>${t('market')}</b><small>${state.market.length} ${lang==='es'?'anuncios':'listings'}</small></div></button><button class="more-card" data-tab="Web3"><span>🔗</span><div><b>${t('web3')}</b><small>${p.wallet?lang==='es'?'Wallet conectada':'Wallet connected':lang==='es'?'Wallet opcional':'Optional wallet'}</small></div></button></div><section class="content-block"><h3>⚙ ${t('settings')}</h3><div class="settings-summary"><span>${t('language')}: <b>${lang==='es'?'Español':'English'}</b></span><span>${t('account')}: <b>${esc(p.name)}</b></span><span>${t('zone')}: <b>${esc(lname(zone()))}</b></span></div></section>`;
}

function render(){
  ensureLanguagePicker();refreshStaticButtons();if(!state)return;
  renderHud();renderTabs();
  const view={Adventure:adventure,Combat:combat,Inventory:inventory,Crafting:crafting,More:more,Market:market,Quests:quests,Web3:web3}[tab]||adventure;
  $('#panel').innerHTML=view();bind();
}

function bind(){
  document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;render()});
  document.querySelectorAll('[data-inv]').forEach(b=>b.onclick=()=>{inventorySection=b.dataset.inv;render()});
  document.querySelectorAll('[data-craft-filter]').forEach(b=>b.onclick=()=>{craftFilter=b.dataset.craftFilter;render()});
  document.querySelectorAll('[data-zone]').forEach(b=>b.onclick=()=>action('travel',{zoneId:b.dataset.zone}));
  document.querySelectorAll('[data-a]').forEach(b=>b.onclick=()=>action(b.dataset.a));
  document.querySelectorAll('[data-enemy]').forEach(b=>b.onclick=()=>action('combat',{enemyId:b.dataset.enemy}));
  document.querySelectorAll('[data-equip]').forEach(b=>b.onclick=()=>action('equip',{itemId:b.dataset.equip}));
  document.querySelectorAll('[data-craft]').forEach(b=>b.onclick=()=>action('craft',{recipeId:b.dataset.craft}));
  document.querySelectorAll('[data-buy]').forEach(b=>b.onclick=()=>action('buy',{listingId:b.dataset.buy}));
  document.querySelectorAll('[data-quest]').forEach(b=>b.onclick=()=>action('claimQuest',{questId:b.dataset.quest}));
  document.querySelectorAll('[data-sell]').forEach(b=>b.onclick=()=>{const price=prompt(lang==='es'?'Precio en oro':'Price in gold','25');if(price)action('sell',{itemId:b.dataset.sell,price:Number(price)})});
  const w=$('#wallet');if(w)w.onclick=async()=>{try{if(!window.ethereum)throw new Error(lang==='es'?'No se detectó wallet EVM en este navegador':'No EVM wallet detected');const [addr]=await window.ethereum.request({method:'eth_requestAccounts'});await action('wallet',{address:addr,chainId:56})}catch(e){toast(e.message)}};
  const d=$('#disconnect');if(d)d.onclick=()=>action('wallet',{address:''});
}

ensureLanguagePicker();
$('#reset').onclick=async()=>{if(confirm(lang==='es'?'¿Reiniciar únicamente tu progreso de prueba?':'Reset only your demo progress?')){try{state=await api('/api/reset',{method:'POST',body:'{}'});lastLog=[];tab='Adventure';render()}catch(e){toast(e.message)}}};
$('#logout').onclick=async()=>{await supabase.auth.signOut();session=null;renderAuth(t('sessionClosed'))};
supabase.auth.onAuthStateChange((_event,newSession)=>{session=newSession;if(newSession)load();else renderAuth()});
const {data:{session:initialSession}}=await supabase.auth.getSession();session=initialSession;if(session)await load();else renderAuth();
setInterval(updateTimers,1000);
setInterval(()=>{if(session)load({quiet:true})},15000);
