(()=>{
  const panel=document.getElementById('panel');
  if(!panel||panel.__nexusPhase1Lifecycle)return;
  let proto=panel,descriptor=null;
  while(proto&&!descriptor){descriptor=Object.getOwnPropertyDescriptor(proto,'innerHTML');proto=Object.getPrototypeOf(proto)}
  if(!descriptor?.get||!descriptor?.set)return;
  const heading=()=>panel.querySelector('.section-head h2')?.textContent||'';
  const reattachVisuals=(world,combat)=>{
    const h=heading();
    const isWorld=/Mundo|World/i.test(h);
    const isCombat=/Combate|Combat/i.test(h);
    if(isWorld){
      panel.querySelector('.destination-list')?.closest('.content-block')?.classList.add('p1-legacy-destinations');
      if(world&&!panel.querySelector('#p1-world'))panel.querySelector('.section-head')?.insertAdjacentElement('afterend',world);
    }
    if(isCombat){
      const zone=panel.querySelector('[data-combat="zone"]');
      const zoneActive=!zone||zone.classList.contains('active');
      if(zoneActive){
        panel.querySelector('.enemy-list')?.classList.add('p1-legacy-enemies');
        if(combat&&!panel.querySelector('#p1-combat-roster'))panel.querySelector('.segmented')?.insertAdjacentElement('afterend',combat);
      }
    }
  };
  Object.defineProperty(panel,'__nexusPhase1Lifecycle',{value:true,configurable:false});
  Object.defineProperty(panel,'innerHTML',{
    configurable:true,
    enumerable:descriptor.enumerable,
    get(){return descriptor.get.call(panel)},
    set(value){
      const world=panel.querySelector('#p1-world');
      const combat=panel.querySelector('#p1-combat-roster');
      descriptor.set.call(panel,value);
      reattachVisuals(world,combat);
      document.dispatchEvent(new CustomEvent('nexus:panel-render'));
    }
  });
})();
