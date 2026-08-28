(()=>{
  const ROOT=document.documentElement;
  ROOT.dataset.cqPresentation='v28';
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;

  function enhanceTouch(root=document){
    root.querySelectorAll('button,[role="button"],.inventory-slot,.bag-slot,.equipment-slot').forEach(el=>{
      if(el.dataset.cq28Touch)return;
      el.dataset.cq28Touch='1';
      if(!el.hasAttribute('tabindex') && el.getAttribute('role')==='button') el.tabIndex=0;
    });
  }

  function rarityFromText(el){
    const t=(el.getAttribute('data-rarity')||el.textContent||'').toLowerCase();
    const map=[['legendary','legendary'],['legendario','legendary'],['epic','epic'],['épico','epic'],['epico','epic'],['rare','rare'],['raro','rare'],['uncommon','uncommon'],['poco común','uncommon'],['poco comun','uncommon'],['common','common'],['común','common'],['comun','common']];
    for(const [needle,value] of map) if(t.includes(needle)) return value;
    return el.getAttribute('data-rarity')||'common';
  }

  function tagRarities(root=document){
    root.querySelectorAll('.inventory-slot,.bag-slot,.equipment-slot').forEach(el=>{
      if(!el.dataset.rarity) el.dataset.rarity=rarityFromText(el);
    });
  }

  function inventoryItems(container){
    return [...container.querySelectorAll('.inventory-slot,.bag-slot')];
  }

  function ensureInventoryTools(root=document){
    const grids=[...root.querySelectorAll('.inventory-grid,.bag-grid')];
    grids.forEach(grid=>{
      const host=grid.parentElement;
      if(!host || host.querySelector(':scope > .cq28-inventory-tools')) return;
      const items=inventoryItems(grid);
      if(items.length<2) return;
      const tools=document.createElement('div');
      tools.className='cq28-inventory-tools';
      tools.setAttribute('role','toolbar');
      tools.setAttribute('aria-label','Filtros de inventario');
      const filters=[['all','Todo'],['common','Común'],['uncommon','Poco común'],['rare','Raro'],['epic','Épico'],['legendary','Legendario']];
      const counts=Object.fromEntries(filters.map(([k])=>[k,0]));
      counts.all=items.length;
      items.forEach(i=>{counts[rarityFromText(i)]=(counts[rarityFromText(i)]||0)+1;});
      filters.forEach(([key,label],idx)=>{
        const b=document.createElement('button');
        b.type='button';
        b.className='cq28-filter'+(idx===0?' active':'');
        b.dataset.filter=key;
        b.innerHTML=`${label}<span class="cq28-filter-count">${counts[key]||0}</span>`;
        b.addEventListener('click',()=>{
          tools.querySelectorAll('.cq28-filter').forEach(x=>x.classList.toggle('active',x===b));
          items.forEach(item=>{const show=key==='all'||rarityFromText(item)===key;item.hidden=!show;});
        });
        tools.appendChild(b);
      });
      host.insertBefore(tools,grid);
    });
  }

  function animatePanels(root=document){
    if(reduce)return;
    root.querySelectorAll('.screen,.content-card,.activity-card,.equipment-stage,.inventory-grid,.bag-grid,.talent-branch,.combat-panel').forEach(el=>{
      if(el.dataset.cq28Animated)return;
      el.dataset.cq28Animated='1';
      el.classList.add('cq28-panel-enter');
      setTimeout(()=>el.classList.remove('cq28-panel-enter'),320);
    });
  }

  function hardenOverflow(root=document){
    root.querySelectorAll('.screen h1,.screen h2,.screen h3,.screen p,.screen span,.screen b,.screen small').forEach(el=>{
      if(el.scrollWidth>el.clientWidth+2 && el.clientWidth>0) el.title=el.textContent.trim();
    });
  }

  let raf=0;
  function pass(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      enhanceTouch();
      tagRarities();
      ensureInventoryTools();
      animatePanels();
      hardenOverflow();
    });
  }

  new MutationObserver(pass).observe(document.documentElement,{childList:true,subtree:true});
  addEventListener('resize',pass,{passive:true});
  addEventListener('orientationchange',pass,{passive:true});
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',pass,{once:true}); else pass();
})();
