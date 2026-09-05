const rarityOrder=['COMMON','UNCOMMON','RARE','EPIC','LEGENDARY','MYTHIC'];
const raritySet=new Set(rarityOrder);
const lang=()=>localStorage.getItem('nexus-lang')||'es';
const labels={
  es:{COMMON:'Común',UNCOMMON:'Poco común',RARE:'Raro',EPIC:'Épico',LEGENDARY:'Legendario',MYTHIC:'Mítico',all:'Todas',gear:'Rareza de objetos',atk:'ATQ',def:'DEF',weapon:'Arma',armor:'Armadura',boots:'Botas',ring:'Anillo',gearType:'Equipo',consumable:'Consumible'},
  en:{COMMON:'Common',UNCOMMON:'Uncommon',RARE:'Rare',EPIC:'Epic',LEGENDARY:'Legendary',MYTHIC:'Mythic',all:'All',gear:'Item rarity',atk:'ATK',def:'DEF',weapon:'Weapon',armor:'Armor',boots:'Boots',ring:'Ring',gearType:'Gear',consumable:'Consumable'}
};
const fixedNames={
  es:{'Worn Iron Blade':'Hoja de Hierro Desgastada','Traveler Mail':'Malla de Viajero','Silverleaf Bow':'Arco Hoja de Plata','Stoneguard Plate':'Placa Guardapiedra','Rift Loot':'Botín de la Grieta','Boss Trophy Gear':'Equipo Trofeo de Jefe'},
  en:{}
};
const enemyRarityById={
  goblin:'COMMON','dire-wolf':'COMMON','reef-raider':'COMMON','drowned-sailor':'COMMON','thorn-shaman':'COMMON',
  'tide-serpent':'UNCOMMON',wraith:'UNCOMMON','bog-stalker':'UNCOMMON',ogre:'UNCOMMON','plague-witch':'UNCOMMON',
  'ancient-treant':'RARE','kraken-spawn':'RARE','ice-wolf':'RARE','frost-revenant':'RARE','crystal-golem':'RARE',
  'mire-hydra':'EPIC','frost-wyrm':'EPIC','ash-imp':'EPIC','lava-brute':'EPIC','cinder-mage':'EPIC',
  'inferno-colossus':'LEGENDARY','rift-hound':'LEGENDARY','void-cultist':'LEGENDARY','rift-knight':'LEGENDARY',boss:'MYTHIC'
};
let active='ALL',scheduled=false,observer=null,observing=false;
const t=k=>labels[lang()]?.[k]??k;
const stateNow=()=>window.__NEXUS_STATE__||null;
const rarity=v=>{const r=String(v||'').toUpperCase();return raritySet.has(r)?r:'COMMON';};
const localizedName=n=>fixedNames[lang()]?.[n]||n;
const badge=(r,extra='rarity-badge')=>`<span class="${extra} ${r}" data-rarity-label="${r}">${t(r)}</span>`;
const slotLabel=s=>t(String(s||'gearType').toLowerCase());

function clearRarityClasses(el){if(!el)return;rarityOrder.forEach(r=>el.classList.remove(r));}
function setRarityClass(el,r){if(!el)return;clearRarityClasses(el);el.classList.add(r);}
function inventoryItemByRow(row){
  const id=row.querySelector('[data-equip]')?.dataset.equip||row.querySelector('[data-sell]')?.dataset.sell;
  return stateNow()?.player?.inventory?.find(i=>i.id===id)||null;
}
function marketItemByRow(row){
  const id=row.querySelector('[data-buy]')?.dataset.buy;
  return stateNow()?.market?.find(i=>i.id===id)||null;
}
function enhanceItemByRow(row){
  const id=row.querySelector('[data-enhance]')?.dataset.enhance;
  return stateNow()?.player?.inventory?.find(i=>i.id===id)||null;
}
function recipeByRow(row){
  const id=row.querySelector('[data-craft]')?.dataset.craft;
  return stateNow()?.recipes?.find(i=>i.id===id)||null;
}
function predictedRecipeRarity(r){
  if(!r||r.out?.type==='consumable')return null;
  if(r.out?.rarity)return rarity(r.out.rarity);
  return Number(r.goldCost||0)>=200?'RARE':'UNCOMMON';
}
function updateOrCreateBadge(host,r,cls='rarity-badge'){
  if(!host)return;
  let b=host.querySelector(`.${cls}`);
  if(!b){host.insertAdjacentHTML('beforeend',badge(r,cls));b=host.querySelector(`.${cls}`);}
  if(!b)return;
  rarityOrder.forEach(x=>b.classList.remove(x));b.classList.add(r);b.dataset.rarityLabel=r;b.textContent=t(r);
}
function statText(item){return `${t('atk')} ${Number(item?.atk||0)} · ${t('def')} ${Number(item?.def||0)}`;}

function decorateInventory(){
  document.querySelectorAll('.inventory-row').forEach(row=>{
    const item=inventoryItemByRow(row);if(!item)return;
    const r=rarity(item.rarity);row.dataset.rarity=r;row.classList.add('rarity-row');
    const main=row.querySelector('.item-main'),name=main?.querySelector('b'),small=main?.querySelector('small');
    if(name){name.textContent=`${localizedName(item.name)}${item.enhancementLevel?` +${item.enhancementLevel}`:''}`;setRarityClass(name,r);name.classList.add('rarity-name');}
    if(main)updateOrCreateBadge(main,r);
    if(small)small.textContent=statText(item);
  });
}
function decorateEquipment(){
  const s=stateNow(),p=s?.player;if(!p)return;
  const slots=['weapon','armor','boots','ring'];
  document.querySelectorAll('.equipment-row').forEach((row,index)=>{
    const slot=slots[index],id=p.equipment?.[slot],item=p.inventory?.find(i=>i.id===id);
    const slotEl=row.querySelector('small'),name=row.querySelector('b'),pill=row.querySelector('.pill');
    if(slotEl)slotEl.textContent=slotLabel(slot).toUpperCase();
    if(!item){if(name)name.textContent=lang()==='es'?'Vacío':'Empty';return;}
    const r=rarity(item.rarity);row.dataset.rarity=r;row.classList.add('rarity-row');
    if(name){name.textContent=`${localizedName(item.name)}${item.enhancementLevel?` +${item.enhancementLevel}`:''}`;setRarityClass(name,r);name.classList.add('rarity-name');}
    if(pill){setRarityClass(pill,r);pill.textContent=`${t(r)} · ${statText(item)}`;}
  });
}
function decorateMarket(){
  document.querySelectorAll('.market-row').forEach(row=>{
    const item=marketItemByRow(row);if(!item)return;
    const r=rarity(item.rarity);row.dataset.rarity=r;row.classList.add('rarity-row');
    const main=row.querySelector('.item-main'),name=main?.querySelector('b'),small=main?.querySelector('small');
    if(name){name.textContent=localizedName(item.name);setRarityClass(name,r);name.classList.add('rarity-name');}
    if(main)updateOrCreateBadge(main,r);
    if(small)small.textContent=statText(item);
  });
}
function decorateEnhance(){
  document.querySelectorAll('.enhance-row').forEach(row=>{
    const item=enhanceItemByRow(row);if(!item)return;
    const r=rarity(item.rarity);row.dataset.rarity=r;row.classList.add('rarity-row');
    const box=row.querySelector('.enhance-item'),name=box?.querySelector('span'),small=box?.querySelector('small');
    if(name){name.textContent=localizedName(item.name);setRarityClass(name,r);name.classList.add('rarity-name');}
    if(box)updateOrCreateBadge(box,r,'enhance-rarity-badge');
    if(small)small.textContent=statText(item);
  });
}
function decorateRecipes(){
  document.querySelectorAll('.recipe-row').forEach(row=>{
    const rec=recipeByRow(row);if(!rec)return;
    const title=row.querySelector('.recipe-title>div'),small=title?.querySelector('small');
    if(small){const type=rec.out?.type==='consumable'?'consumable':(rec.out?.slot||rec.out?.type||'gearType');small.textContent=slotLabel(type);}
    const r=predictedRecipeRarity(rec);
    if(!r){row.removeAttribute('data-rarity');row.querySelector('.recipe-rarity-badge')?.remove();return;}
    row.dataset.rarity=r;row.classList.add('rarity-row');if(title)updateOrCreateBadge(title,r,'recipe-rarity-badge');
  });
}
function decorateEnemies(){
  document.querySelectorAll('.enemy-row').forEach(row=>{
    const id=row.querySelector('[data-enemy]')?.dataset.enemy||'';
    const r=enemyRarityById[id]||'COMMON';row.dataset.enemyRarity=r;row.classList.add('rarity-row');
    rarityOrder.forEach(x=>row.classList.remove(`enemy-${x.toLowerCase()}`));row.classList.add(`enemy-${r.toLowerCase()}`);
    const title=row.querySelector('.enemy-title>div');if(title)updateOrCreateBadge(title,r,'enemy-rarity-badge');
  });
}
function ensureTools(){
  const panel=document.querySelector('#panel'),inv=panel?.querySelector('.inventory-list');
  if(!panel||!inv)return;
  let tools=panel.querySelector('#rarity-tools');
  if(!tools){tools=document.createElement('section');tools.id='rarity-tools';tools.className='rarity-tools';inv.before(tools);tools.innerHTML=`<div class="rarity-tools-head"><b>✦ <span data-rarity-title></span></b></div><div class="rarity-filters"></div>`;}
  const title=tools.querySelector('[data-rarity-title]');if(title)title.textContent=t('gear');
  const filters=tools.querySelector('.rarity-filters');
  if(filters&&!filters.childElementCount){filters.innerHTML=`<button data-rarity-filter="ALL">${t('all')}</button>${rarityOrder.map(r=>`<button data-rarity-filter="${r}" class="${r}">${t(r)}</button>`).join('')}`;filters.querySelectorAll('[data-rarity-filter]').forEach(b=>b.addEventListener('click',()=>{active=b.dataset.rarityFilter||'ALL';syncFilterButtons();applyFilter();}));}
  filters?.querySelectorAll('[data-rarity-filter]').forEach(b=>{const k=b.dataset.rarityFilter||'ALL';b.textContent=k==='ALL'?t('all'):t(k);});
  syncFilterButtons();
}
function syncFilterButtons(){document.querySelectorAll('[data-rarity-filter]').forEach(b=>b.classList.toggle('active',(b.dataset.rarityFilter||'ALL')===active));}
function applyFilter(){document.querySelectorAll('.inventory-row').forEach(row=>{row.hidden=active!=='ALL'&&row.dataset.rarity!==active;});}
function render(){
  if(observer&&observing){observer.disconnect();observing=false;}
  try{decorateInventory();decorateEquipment();decorateMarket();decorateEnhance();decorateRecipes();decorateEnemies();ensureTools();applyFilter();}
  finally{startObserver();}
}
function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;render();});}
function startObserver(){
  if(!observer)observer=new MutationObserver(()=>schedule());
  const panel=document.querySelector('#panel');if(panel&&!observing){observer.observe(panel,{childList:true,subtree:true});observing=true;}
}
window.addEventListener('nexus:state',schedule);
window.addEventListener('storage',schedule);
window.addEventListener('focus',schedule);
setTimeout(()=>{startObserver();schedule();},450);
