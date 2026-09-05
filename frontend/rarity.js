const rarityOrder=['COMMON','UNCOMMON','RARE','EPIC','LEGENDARY','MYTHIC'];
const lang=()=>localStorage.getItem('nexus-lang')||'es';
const labels={
  es:{COMMON:'Común',UNCOMMON:'Poco común',RARE:'Raro',EPIC:'Épico',LEGENDARY:'Legendario',MYTHIC:'Mítico',all:'Todas',gear:'Rareza de equipo',enemy:'Rareza',loot:'Calidad del enemigo'},
  en:{COMMON:'Common',UNCOMMON:'Uncommon',RARE:'Rare',EPIC:'Epic',LEGENDARY:'Legendary',MYTHIC:'Mythic',all:'All',gear:'Gear rarity',enemy:'Rarity',loot:'Enemy quality'}
};
const t=k=>labels[lang()]?.[k]??k;
let active='ALL',scheduled=false;

function itemRarity(el){return rarityOrder.find(r=>el?.classList?.contains(r))||null;}
function enemyRarity(row){
  const id=row.querySelector('[data-enemy]')?.dataset.enemy||'';
  const boss=row.classList.contains('boss-row');
  if(boss){
    if(id==='boss')return 'MYTHIC';
    if(id==='inferno-colossus')return 'LEGENDARY';
    if(id==='mire-hydra'||id==='frost-wyrm')return 'EPIC';
    return 'RARE';
  }
  const small=row.querySelector('.enemy-title small')?.textContent||'';
  const m=small.match(/(\d+)/);const level=Number(m?.[1]||1);
  if(level>=16)return 'LEGENDARY';
  if(level>=11)return 'EPIC';
  if(level>=7)return 'RARE';
  if(level>=4)return 'UNCOMMON';
  return 'COMMON';
}
function badge(r){return `<span class="rarity-badge ${r}">${t(r)}</span>`;}
function decorateItems(){
  document.querySelectorAll('.inventory-row,.market-row').forEach(row=>{
    const name=row.querySelector('.item-main b');const r=itemRarity(name);if(!r)return;
    let b=row.querySelector('.rarity-badge');if(!b){name.insertAdjacentHTML('afterend',badge(r));b=row.querySelector('.rarity-badge');}
    else{b.className=`rarity-badge ${r}`;b.textContent=t(r);}
    row.dataset.rarity=r;
  });
  document.querySelectorAll('.equipment-row .pill').forEach(p=>{
    const r=itemRarity(p);if(!r||p.dataset.rarityDone)return;
    p.dataset.rarityDone='1';p.insertAdjacentHTML('afterbegin',`${t(r)} · `);
  });
  applyFilter();
}
function decorateEnemies(){
  document.querySelectorAll('.enemy-row').forEach(row=>{
    const r=enemyRarity(row);row.dataset.enemyRarity=r;row.classList.add(`enemy-${r.toLowerCase()}`);
    const title=row.querySelector('.enemy-title>div');if(!title)return;
    let b=title.querySelector('.enemy-rarity-badge');
    if(!b){title.insertAdjacentHTML('beforeend',`<span class="enemy-rarity-badge ${r}">${t(r)}</span>`);}
    else{b.className=`enemy-rarity-badge ${r}`;b.textContent=t(r);}
  });
}
function ensureTools(){
  const panel=document.querySelector('#panel');if(!panel||!panel.querySelector('.inventory-list'))return;
  let tools=panel.querySelector('#rarity-tools');
  if(!tools){
    tools=document.createElement('section');tools.id='rarity-tools';tools.className='rarity-tools';
    const inv=panel.querySelector('.inventory-list');inv?.before(tools);
  }
  tools.innerHTML=`<div class="rarity-tools-head"><b>✦ ${t('gear')}</b><small>${rarityOrder.map(r=>t(r)).join(' · ')}</small></div><div class="rarity-filters"><button data-rarity-filter="ALL" class="${active==='ALL'?'active':''}">${t('all')}</button>${rarityOrder.map(r=>`<button data-rarity-filter="${r}" class="${active===r?'active':''} ${r}">${t(r)}</button>`).join('')}</div>`;
  tools.querySelectorAll('[data-rarity-filter]').forEach(b=>b.onclick=()=>{active=b.dataset.rarityFilter;ensureTools();applyFilter();});
}
function applyFilter(){
  document.querySelectorAll('.inventory-row').forEach(row=>{row.hidden=active!=='ALL'&&row.dataset.rarity!==active;});
}
function render(){decorateItems();decorateEnemies();ensureTools();}
function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;render();});}
new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
window.addEventListener('nexus:state',schedule);
window.addEventListener('storage',schedule);
setTimeout(schedule,500);
