/* CryptoQuest RPG V31 — presentation-only runtime. */
(()=>{
  'use strict';

  const root=document.documentElement;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.dataset.cqPresentation='v31';

  const screenSelectors=[
    '.home-screen','.adventure-screen','.world-screen','.hero-screen','.bag-screen',
    '.talent-screen','.combat-screen','.more-screen','.creation-screen'
  ];
  const panelSelectors=[
    '.screen-heading','.content-card','.activity-card','.summary-card','.build-summary',
    '.equipment-stage','.inventory-grid','.bag-grid','.talent-branch','.combat-panel',
    '.combat-card','.main-quest','.game-modal','.item-sheet','.result-content'
  ];
  const iconSelectors=[
    '.quick-sigil','.skill-icon','.item-card-icon','.node-icon','.class-sigil',
    '.hero-class-sigil','.npc-portrait','.mini-avatar','.summary-avatar'
  ];

  function installAtmosphere(){
    if(reduce||document.querySelector('.cq31-atmosphere'))return;
    const host=document.querySelector('#game,.game-shell');
    if(!host)return;
    const field=document.createElement('div');
    field.className='cq31-atmosphere';
    field.setAttribute('aria-hidden','true');
    const positions=[6,14,23,31,39,48,57,66,74,82,90,96];
    positions.forEach((x,index)=>{
      const mote=document.createElement('i');
      mote.style.setProperty('--cq31-x',`${x}%`);
      mote.style.setProperty('--cq31-d',`${7.2+(index%5)*1.15}s`);
      mote.style.setProperty('--cq31-delay',`${-index*.73}s`);
      mote.style.setProperty('--cq31-drift',`${index%2?'-':''}${7+(index%4)*5}px`);
      field.appendChild(mote);
    });
    host.appendChild(field);
  }

  function tagScreens(scope=document){
    screenSelectors.forEach(selector=>scope.querySelectorAll(selector).forEach(screen=>{
      if(screen.dataset.cq31Screen)return;
      screen.dataset.cq31Screen=selector.slice(1).replace('-screen','');
    }));
  }

  function tagIcons(scope=document){
    iconSelectors.forEach(selector=>scope.querySelectorAll(selector).forEach(icon=>{
      if(icon.dataset.cq31Icon)return;
      icon.dataset.cq31Icon='1';
    }));
  }

  function animatePanels(scope=document){
    if(reduce)return;
    panelSelectors.forEach(selector=>scope.querySelectorAll(selector).forEach(panel=>{
      if(panel.dataset.cq31Animated)return;
      panel.dataset.cq31Animated='1';
      panel.classList.add('cq31-panel-enter');
      setTimeout(()=>panel.classList.remove('cq31-panel-enter'),360);
    }));
  }

  function improveTouch(scope=document){
    scope.querySelectorAll('button,[role="button"],.inventory-slot,.bag-slot,.equipment-slot').forEach(el=>{
      if(el.dataset.cq31Touch)return;
      el.dataset.cq31Touch='1';
      if(el.getAttribute('role')==='button'&&!el.hasAttribute('tabindex'))el.tabIndex=0;
    });
  }

  function clearPressed(){
    document.querySelectorAll('.cq31-pressed').forEach(el=>el.classList.remove('cq31-pressed'));
  }

  document.addEventListener('pointerdown',event=>{
    const target=event.target.closest('button,[role="button"],.inventory-slot,.bag-slot,.equipment-slot');
    if(target&&!target.disabled)target.classList.add('cq31-pressed');
  },{passive:true});
  document.addEventListener('pointerup',clearPressed,{passive:true});
  document.addEventListener('pointercancel',clearPressed,{passive:true});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clearPressed()},{passive:true});

  let frame=0;
  function visualPass(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(()=>{
      installAtmosphere();
      tagScreens();
      tagIcons();
      animatePanels();
      improveTouch();
      root.classList.add('cq31-ready');
    });
  }

  new MutationObserver(visualPass).observe(document.documentElement,{childList:true,subtree:true});
  addEventListener('resize',visualPass,{passive:true});
  addEventListener('orientationchange',visualPass,{passive:true});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',visualPass,{once:true});
  else visualPass();
})();
