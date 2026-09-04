/* CFS Prompt Factory advanced runtime v1.0.1 — force edge asset refresh */
(()=>{
  const adv={seller:null,analytics:null,referral:null,collections:[],offers:[],notifications:[]};
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const jbody=value=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
  const pbody=value=>({method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});

  function ensureAdvancedDialog(){
    if(document.getElementById('advancedBuyDialog'))return;
    const d=document.createElement('dialog');d.id='advancedBuyDialog';d.className='pf-dialog small-dialog';
    d.innerHTML=`<button class="dialog-close" data-close-advanced aria-label="Cerrar">×</button><span class="eyebrow">SMART CHECKOUT</span><h2 id="advBuyTitle">Configurar compra</h2><form id="advBuyForm"><input id="advListingId" type="hidden"><label>Licencia<select id="advLicense"></select></label><label id="advAmountWrap" class="hidden">Tu precio (USD)<input id="advAmount" type="number" min="0" step="0.01"></label><label>Cupón<input id="advCoupon" maxlength="40" placeholder="Opcional"></label><p id="advPromo" class="notice hidden"></p><button class="primary full" type="submit">CONTINUAR AL PAGO</button></form>`;
    document.body.appendChild(d);
    d.querySelector('[data-close-advanced]').addEventListener('click',()=>d.close());
    d.querySelector('#advBuyForm').addEventListener('submit',submitAdvancedBuy);
  }

  async function advancedBuyListing(listingId){
    if(!state.user){showSection('vault');return}
    try{
      const opt=await api(`/prompt-factory/listings/${encodeURIComponent(listingId)}/checkout-options`);
      ensureAdvancedDialog();
      $('advListingId').value=listingId;
      $('advBuyTitle').textContent='Configurar compra';
      $('advLicense').innerHTML=(opt.licenses||[]).map(x=>`<option value="${esc(x.license_type)}">${esc(x.license_type)} · ${money(x.price_usd)}</option>`).join('');
      const pwyw=String(opt.listing.pricing_model).toUpperCase()==='PAY_WHAT_YOU_WANT';
      $('advAmountWrap').classList.toggle('hidden',!pwyw);
      $('advAmount').value=pwyw?String(opt.listing.price_usd||''):'';
      $('advCoupon').value='';
      if(opt.promotion){$('advPromo').textContent=`${opt.promotion.label}: ${money(opt.promotion.sale_price_usd)}`;$('advPromo').classList.remove('hidden')}else $('advPromo').classList.add('hidden');
      $('advancedBuyDialog').showModal();
    }catch(e){toast(e.message,true)}
  }

  async function submitAdvancedBuy(e){
    e.preventDefault();
    const listingId=$('advListingId').value;
    const payload={license_type:$('advLicense').value,coupon_code:$('advCoupon').value.trim()};
    if(!$('advAmountWrap').classList.contains('hidden'))payload.amount_usd=String(Number($('advAmount').value||0).toFixed(2));
    try{
      const d=await api(`/prompt-factory/listings/${encodeURIComponent(listingId)}/checkout-advanced`,jbody(payload));
      if(d.already_owned){toast('Este prompt ya está en tu Vault');$('advancedBuyDialog').close();await loadVault();return}
      if(d.free){await api(`/prompt-factory/listings/${encodeURIComponent(listingId)}/acquire-free`,{method:'POST'});toast('Prompt añadido a tu Vault');$('advancedBuyDialog').close();await Promise.all([loadVault(),loadMarketplace()]);showSection('vault');return}
      $('advancedBuyDialog').close();
      await openCheckout({productId:d.product_id,title:`Comprar prompt · ${money(d.price_usd)}`,kind:'listing'});
    }catch(err){toast(err.message,true)}
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-buy-listing]');
    if(b){e.preventDefault();e.stopImmediatePropagation();advancedBuyListing(b.dataset.buyListing);return}
    const save=e.target.closest('[data-save-search]');
    if(save){e.preventDefault();saveCurrentSearch();return}
    const bundle=e.target.closest('[data-buy-collection]');
    if(bundle){e.preventDefault();buyCollection(bundle.dataset.buyCollection);return}
  },true);

  function augmentBaseUi(){
    const pricing=document.getElementById('sellPricing');
    if(pricing&&!pricing.querySelector('option[value="PAY_WHAT_YOU_WANT"]')){
      pricing.insertAdjacentHTML('beforeend','<option value="PAY_WHAT_YOU_WANT">Paga lo que quieras</option>');
    }
    const controls=document.querySelector('.market-controls');
    if(controls&&!controls.querySelector('[data-save-search]'))controls.insertAdjacentHTML('beforeend','<button type="button" class="ghost tiny auth-required" data-save-search>GUARDAR BÚSQUEDA</button>');
    const market=document.getElementById('market');
    if(market&&!document.getElementById('collectionOffers'))market.insertAdjacentHTML('beforeend','<div class="section-head compact"><div><span class="eyebrow">COLLECTION MARKET</span><h2>Bundles y colecciones premium</h2></div></div><div id="collectionOffers" class="prompt-grid"></div>');
    const earnings=document.getElementById('earnings');
    if(earnings&&!document.getElementById('advancedTools'))earnings.insertAdjacentHTML('beforeend','<div id="advancedTools" class="advanced-tools"></div>');
  }

  function interceptAdvancedSell(){
    const form=document.getElementById('sellForm');if(!form||form.dataset.advancedBound)return;form.dataset.advancedBound='1';
    form.addEventListener('submit',async e=>{
      if($('sellPricing').value!=='PAY_WHAT_YOU_WANT')return;
      e.preventDefault();e.stopImmediatePropagation();
      const payload={price_usd:String(Number($('sellPrice').value||0).toFixed(2)),pricing_model:'PAY_WHAT_YOU_WANT',license_type:$('sellLicense').value,preview_text:$('sellPreview').value.trim(),examples:$('sellExamples').value.split('\n').map(x=>x.trim()).filter(Boolean)};
      try{const r=await api(`/prompt-factory/prompts/${encodeURIComponent($('sellPromptId').value)}/publish-advanced`,jbody(payload));toast(r.listing.status==='PUBLISHED'?'Publicado con precio flexible':'Enviado a revisión');$('sellDialog').close();await Promise.all([loadMarketplace(),loadDashboard(),loadAdvanced()])}catch(err){toast(err.message,true)}
    },true);
  }

  async function saveCurrentSearch(){
    if(!state.user)return showSection('vault');
    const label=window.prompt('Nombre para esta búsqueda guardada','Mi búsqueda');if(!label)return;
    try{await api('/prompt-factory/saved-searches',jbody({label,query:{q:$('marketSearch')?.value||'',category:$('categoryFilter')?.value||'',sort:$('sortFilter')?.value||'trending'}}));toast('Búsqueda guardada');await loadAdvanced()}catch(e){toast(e.message,true)}
  }

  async function loadCollectionOffers(){
    try{const d=await api('/prompt-factory/collection-offers?limit=30');adv.offers=d.offers||[];const box=$('collectionOffers');if(!box)return;box.innerHTML=adv.offers.length?adv.offers.map(x=>`<article class="prompt-card"><div class="card-top"><span class="category">${esc(x.pricing_model)}</span><span class="price">${money(x.price_usd)}</span></div><h3>${esc(x.title)}</h3><p>${esc(x.description||'Colección de prompts')}</p><div class="card-meta"><span>${esc(x.creator_name)}</span><span>${Number(x.sales_count||0)} ventas</span></div><button class="primary tiny" data-buy-collection="${esc(x.offer_id)}">COMPRAR COLECCIÓN</button></article>`).join(''):'<div class="empty-card">Aún no hay bundles publicados.</div>'}catch(e){}
  }

  async function buyCollection(offerId){
    if(!state.user)return showSection('vault');
    try{const d=await api(`/prompt-factory/collection-offers/${encodeURIComponent(offerId)}/prepare-checkout`,{method:'POST'});if(d.already_owned){toast('Ya tienes acceso a esta colección');return}await openCheckout({productId:d.product_id,title:`Colección premium · ${money(d.price_usd)}`,kind:'collection'})}catch(e){toast(e.message,true)}
  }

  async function loadAdvanced(){
    if(!state.user)return;
    try{
      const results=await Promise.allSettled([
        api('/prompt-factory/creator/profile'),api('/prompt-factory/creator/analytics'),api('/prompt-factory/referrals/me'),api('/prompt-factory/notifications'),api('/prompt-factory/collections'),api('/prompt-factory/payouts'),api('/prompt-factory/saved-searches'),api('/prompt-factory/creator/promotions'),api('/prompt-factory/creator/coupons'),api('/prompt-factory/creator/collection-offers')
      ]);
      const val=i=>results[i].status==='fulfilled'?results[i].value:null;
      adv.seller=val(0)?.profile||null;adv.analytics=val(1)||null;adv.referral=val(2)||null;adv.notifications=val(3)?.notifications||[];adv.collections=val(4)?.collections||[];
      adv.payouts=val(5)?.payouts||[];adv.savedSearches=val(6)?.searches||[];adv.promotions=val(7)?.promotions||[];adv.coupons=val(8)?.coupons||[];adv.myOffers=val(9)?.offers||[];
      renderAdvancedTools();
    }catch(e){}
  }

  function renderAdvancedTools(){
    const box=$('advancedTools');if(!box)return;
    const a=adv.analytics||{};const seller=adv.seller;
    const admin=state.user&&['admin','platform_owner'].includes(state.user.role);
    box.innerHTML=`
      <div class="data-panel"><div class="section-head compact"><div><span class="eyebrow">CREATOR IDENTITY</span><h3>Perfil público de vendedor</h3></div>${admin?'<a class="ghost tiny" href="/prompt-factory/admin">ADMIN</a>':''}</div>
        <form id="sellerProfileForm" class="form-grid"><label>Username<input id="advUsername" minlength="3" value="${esc(seller?.username||'')}"></label><label>Avatar URL<input id="advAvatar" value="${esc(seller?.avatar_url||'')}"></label><label class="wide">Bio<textarea id="advBio" rows="3">${esc(seller?.bio||'')}</textarea></label><button class="primary" type="submit">GUARDAR PERFIL</button></form></div>
      <div class="metric-cards"><div class="metric"><strong>${Number(a.views||0)}</strong><span>Views</span></div><div class="metric"><strong>${Number(a.favorites||0)}</strong><span>Favoritos</span></div><div class="metric"><strong>${Number(a.reviews?.n||0)}</strong><span>Reviews</span></div><div class="metric"><strong>${Number(a.conversion_rate||0).toFixed(2)}%</strong><span>Conversión</span></div></div>
      <div class="data-panel"><h3>Referidos</h3><p class="muted">Comparte tu enlace. La recompensa sale de la comisión de plataforma, no del ingreso del vendedor.</p><div class="data-row"><code>${esc(adv.referral?.share_path||'—')}</code><span>${money(adv.referral?.earnings?.n||0)} ganados</span></div></div>
      <div class="data-panel"><h3>Retirar ganancias</h3><form id="payoutForm" class="form-grid"><label>Importe USD<input id="payoutAmount" type="number" step="0.01" min="0"></label><label>Método<input id="payoutMethod" value="USDT_TRON"></label><label class="wide">Destino / wallet<input id="payoutDestination"></label><button class="primary" type="submit">SOLICITAR RETIRO</button></form><div id="payoutList">${(adv.payouts||[]).slice(0,6).map(x=>`<div class="data-row"><b>${money(x.amount_usd)}</b><span>${esc(x.method)}</span><span>${esc(x.status)}</span></div>`).join('')||'<p class="muted">Sin retiros.</p>'}</div></div>
      <div class="data-panel"><h3>Importar / exportar Vault</h3><div class="hero-actions"><button id="exportVault" class="ghost" type="button">EXPORTAR JSON</button><label class="ghost" style="cursor:pointer">IMPORTAR JSON<input id="importVault" type="file" accept="application/json" hidden></label></div></div>
      <div class="data-panel"><h3>Crear bundle / colección premium</h3><form id="bundleForm" class="form-grid"><label>Título<input id="bundleTitle" required></label><label>Precio USD<input id="bundlePrice" type="number" step="0.01" min="0.01" value="9.00"></label><label>Modelo<select id="bundleModel"><option value="BUNDLE">Bundle</option><option value="PREMIUM_COLLECTION">Premium collection</option><option value="SUBSCRIPTION_ACCESS">Subscription access</option></select></label><label>Días de acceso<input id="bundleDays" type="number" min="0" value="30"></label><label class="wide">Prompts incluidos<div id="bundlePromptChoices" class="tags">${(state.vault.owned||[]).map(p=>`<label class="tag"><input type="checkbox" data-bundle-prompt="${esc(p.prompt_id)}"> ${esc(p.title)}</label>`).join('')||'No hay prompts propios.'}</div></label><button class="primary" type="submit">PUBLICAR COLECCIÓN</button></form></div>
      <div class="data-panel"><h3>Promoción / cupón</h3><form id="promoForm" class="form-grid"><label>Listing<select id="promoListing">${(state.market||[]).filter(x=>state.vault.owned?.some(p=>p.prompt_id===x.prompt_id)).map(x=>`<option value="${esc(x.listing_id)}">${esc(x.title)}</option>`).join('')}</select></label><label>Precio oferta<input id="promoPrice" type="number" step="0.01" min="0"></label><label>Etiqueta<input id="promoLabel" value="Flash Sale"></label><button class="ghost" type="submit">CREAR PROMO 24H</button></form><form id="couponForm" class="form-grid"><label>Listing<select id="couponListing"><option value="">Todos mis listings</option>${(state.market||[]).filter(x=>state.vault.owned?.some(p=>p.prompt_id===x.prompt_id)).map(x=>`<option value="${esc(x.listing_id)}">${esc(x.title)}</option>`).join('')}</select></label><label>Código<input id="couponCode" value="SAVE10"></label><label>% descuento<input id="couponPercent" type="number" min="1" max="100" value="10"></label><button class="ghost" type="submit">CREAR CUPÓN 7 DÍAS</button></form></div>
      <div class="data-panel"><h3>Notificaciones</h3><div>${adv.notifications.slice(0,12).map(n=>`<div class="data-row"><b>${esc(n.title)}</b><span>${esc(n.body)}</span><span>${n.read_at?'Leída':'Nueva'}</span></div>`).join('')||'<p class="muted">Sin notificaciones.</p>'}</div></div>
      <div class="data-panel"><h3>Búsquedas guardadas</h3>${(adv.savedSearches||[]).map(s=>`<div class="data-row"><b>${esc(s.label)}</b><span>${esc(JSON.stringify(s.query))}</span></div>`).join('')||'<p class="muted">No hay búsquedas guardadas.</p>'}</div>`;
    bindAdvancedForms();
  }

  function bindAdvancedForms(){
    $('sellerProfileForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('/prompt-factory/creator/profile',pbody({username:$('advUsername').value.trim(),avatar_url:$('advAvatar').value.trim(),bio:$('advBio').value.trim()}));toast('Perfil de vendedor guardado');await loadAdvanced()}catch(err){toast(err.message,true)}});
    $('payoutForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('/prompt-factory/payouts',jbody({amount_usd:String(Number($('payoutAmount').value||0).toFixed(2)),method:$('payoutMethod').value.trim(),destination:$('payoutDestination').value.trim()}));toast('Retiro solicitado');await Promise.all([loadDashboard(),loadAdvanced()])}catch(err){toast(err.message,true)}});
    $('exportVault')?.addEventListener('click',async()=>{try{const d=await api('/prompt-factory/export');const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`cfs-prompt-vault-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}catch(err){toast(err.message,true)}});
    $('importVault')?.addEventListener('change',async e=>{const f=e.target.files?.[0];if(!f)return;try{const raw=JSON.parse(await f.text());const list=Array.isArray(raw)?raw:(raw.prompts||[]);const d=await api('/prompt-factory/import',jbody({prompts:list}));toast(`${d.imported} prompts importados`);await Promise.all([loadVault(),loadPfMe(),loadAdvanced()])}catch(err){toast(err.message,true)}finally{e.target.value=''}});
    $('bundleForm')?.addEventListener('submit',async e=>{e.preventDefault();const ids=[...document.querySelectorAll('[data-bundle-prompt]:checked')].map(x=>x.dataset.bundlePrompt);if(!ids.length)return toast('Selecciona al menos un prompt',true);try{const c=await api('/prompt-factory/collections',jbody({title:$('bundleTitle').value.trim(),description:'Premium Prompt Factory collection',visibility:'PUBLIC'}));const cid=c.collection.collection_id;for(const pid of ids)await api(`/prompt-factory/collections/${encodeURIComponent(cid)}/items`,jbody({prompt_id:pid}));const model=$('bundleModel').value;const o=await api(`/prompt-factory/collections/${encodeURIComponent(cid)}/offer`,jbody({pricing_model:model,price_usd:String(Number($('bundlePrice').value||0).toFixed(2)),license_type:'COMMERCIAL',duration_days:model==='SUBSCRIPTION_ACCESS'?Number($('bundleDays').value||30):0}));toast('Colección publicada');await Promise.all([loadCollectionOffers(),loadAdvanced()])}catch(err){toast(err.message,true)}});
    $('promoForm')?.addEventListener('submit',async e=>{e.preventDefault();const id=$('promoListing').value;if(!id)return toast('No tienes listing disponible',true);const t=Math.floor(Date.now()/1000);try{await api(`/prompt-factory/listings/${encodeURIComponent(id)}/promotions`,jbody({label:$('promoLabel').value.trim(),sale_price_usd:String(Number($('promoPrice').value||0).toFixed(2)),starts_at:t-10,ends_at:t+86400}));toast('Promoción activa por 24h');await loadAdvanced()}catch(err){toast(err.message,true)}});
    $('couponForm')?.addEventListener('submit',async e=>{e.preventDefault();const t=Math.floor(Date.now()/1000);try{await api('/prompt-factory/coupons',jbody({listing_id:$('couponListing').value||null,code:$('couponCode').value.trim(),discount_type:'PERCENT',discount_value:String(Number($('couponPercent').value||10)),max_uses:100,starts_at:t-10,ends_at:t+7*86400}));toast('Cupón creado');await loadAdvanced()}catch(err){toast(err.message,true)}});
  }

  async function reconcileEverything(){
    if(!state.user)return;
    try{await api('/prompt-factory/reconcile-advanced',{method:'POST'});await api('/prompt-factory/reconcile-finishing',{method:'POST'});await Promise.allSettled([loadVault(),loadDashboard(),loadAdvanced(),loadCollectionOffers()])}catch(e){}
  }

  function hookPaymentCompletion(){
    const v=$('verifyPayment');if(!v||v.dataset.advancedHook)return;v.dataset.advancedHook='1';v.addEventListener('click',()=>{
      let n=0;const timer=setInterval(async()=>{n++;await reconcileEverything();if(n>=8)clearInterval(timer)},750);
    });
  }

  async function referralFromUrl(){
    if(!state.user)return;const code=new URLSearchParams(location.search).get('ref');if(!code)return;
    try{await api('/prompt-factory/referrals/attribute',jbody({code}));history.replaceState({},'',location.pathname+location.hash)}catch(e){}
  }

  async function refreshCategories(){
    try{const d=await api('/prompt-factory/categories');const labels=(d.categories||[]).map(x=>x.label);for(const select of [$('categoryFilter'),$('promptCategory')]){if(!select)continue;for(const label of labels){if(![...select.options].some(o=>o.value===label||o.textContent===label)){const o=document.createElement('option');o.value=label;o.textContent=label;select.appendChild(o)}}}}catch(e){}
  }

  async function boot(){
    augmentBaseUi();interceptAdvancedSell();ensureAdvancedDialog();hookPaymentCompletion();await refreshCategories();await loadCollectionOffers();
    for(let i=0;i<30&&!state.user;i++)await sleep(150);
    if(state.user){await referralFromUrl();await api('/prompt-factory/reconcile-advanced',{method:'POST'}).catch(()=>{});await api('/prompt-factory/reconcile-finishing',{method:'POST'}).catch(()=>{});await loadAdvanced()}
  }
  boot();
})();
