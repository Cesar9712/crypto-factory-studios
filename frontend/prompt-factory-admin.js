const API='/api/v1';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const csrf=()=>document.cookie.split('; ').find(x=>x.startsWith('cfs_csrf='))?.split('=')[1]||'';
function toast(message,error=false){const el=$('toast');el.textContent=message;el.className='toast show'+(error?' error':'');clearTimeout(toast.t);toast.t=setTimeout(()=>el.className='toast',2800)}
async function api(path,opt={}){opt.credentials='same-origin';opt.headers={...(opt.headers||{})};const method=(opt.method||'GET').toUpperCase();if(method!=='GET'&&method!=='HEAD')opt.headers['X-CSRF-Token']=csrf();const r=await fetch(API+path,opt);let data={};try{data=await r.json()}catch{}if(!r.ok)throw new Error(data.detail?.message||data.detail?.error_code||`HTTP ${r.status}`);return data}
const jbody=(value,method='POST')=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
const money=v=>`$${Number(v||0).toFixed(2)}`;
let adminUser=null;

async function init(){
  try{
    const me=await api('/me');adminUser=me.user;$('adminBadge').textContent=adminUser.display_name;
    if(!['admin','platform_owner'].includes(adminUser.role)){showDenied();return}
    $('adminConsole').classList.remove('hidden');await loadAll();bind();
  }catch(e){showDenied()}
}
function showDenied(){$('adminDenied').classList.remove('hidden');$('adminConsole').classList.add('hidden');$('adminBadge').textContent='Sin acceso'}
async function loadAll(){
  try{
    const [overview,listings,reports,disputes,payouts,users]=await Promise.all([
      api('/prompt-factory/admin/advanced-overview'),api('/prompt-factory/admin/listings'),api('/prompt-factory/admin/reports'),api('/prompt-factory/admin/disputes'),api('/prompt-factory/admin/payouts'),api('/prompt-factory/admin/users?limit=300')
    ]);
    renderOverview(overview);renderListings(listings.listings||[]);renderReports(reports);renderDisputes(disputes.disputes||[]);renderPayouts(payouts.payouts||[]);renderUsers(users.users||[]);
  }catch(e){toast(e.message,true)}
}
function renderOverview(d){
  $('adminHeroStats').innerHTML=`<div><strong>${money(d.gmv_usd)}</strong><span>GMV</span></div><div><strong>${money(d.platform_revenue_usd)}</strong><span>CFS revenue</span></div><div><strong>${Number(d.sales||0)}</strong><span>ventas</span></div><div><strong>${Number(d.sellers||0)}</strong><span>vendedores</span></div>`;
  $('globalMetrics').innerHTML=`<div class="metric"><strong>${Number(d.users||0)}</strong><span>Usuarios</span></div><div class="metric"><strong>${Number(d.prompts||0)}</strong><span>Prompts</span></div><div class="metric"><strong>${Number(d.open_disputes||0)}</strong><span>Disputas abiertas</span></div><div class="metric"><strong>${Number(d.pending_payouts||0)}</strong><span>Retiros pendientes</span></div><div class="metric"><strong>${Number(d.open_reports||0)}</strong><span>Reportes abiertos</span></div><div class="metric"><strong>${money(d.referral_cost_usd)}</strong><span>Referidos</span></div>`;
  $('topCategories').innerHTML=(d.top_categories||[]).map(x=>`<div class="data-row"><b>${esc(x.category)}</b><span>${Number(x.sales||0)} ventas</span><span>${money(x.gmv)}</span></div>`).join('')||'<p class="muted">Sin datos todavía.</p>';
}
function renderListings(rows){$('adminListings').innerHTML=rows.map(x=>`<div class="data-row"><b>${esc(x.title)}</b><span>${esc(x.seller_name)}</span><span>${esc(x.status)}</span><span>${money(x.price_usd)}</span><div class="card-actions"><button class="ghost tiny" data-listing-status="PUBLISHED" data-id="${esc(x.listing_id)}">PUBLICAR</button><button class="ghost tiny" data-listing-status="PAUSED" data-id="${esc(x.listing_id)}">PAUSAR</button><button class="ghost tiny" data-listing-status="REJECTED" data-id="${esc(x.listing_id)}">RECHAZAR</button></div></div>`).join('')||'<p class="muted">Sin listings.</p>'}
function renderReports(d){
  const reports=(d.reports||[]).map(x=>`<div class="data-row"><b>${esc(x.category)} · ${esc(x.target_type)}</b><span>${esc(x.details)}</span><span>${esc(x.status)}</span>${x.status==='OPEN'?`<button class="ghost tiny" data-resolve-report="${esc(x.report_id)}">RESOLVER</button>`:''}</div>`).join('');
  const flags=(d.duplicate_flags||[]).map(x=>`<div class="data-row"><b>DUPLICATE ${Number(x.similarity||0).toFixed(3)}</b><span>${esc(x.prompt_id)}</span><span>${esc(x.matched_prompt_id)}</span></div>`).join('');
  $('adminReports').innerHTML=(reports||'<p class="muted">Sin reportes.</p>')+(flags?`<h4>Detección automática</h4>${flags}`:'');
}
function renderDisputes(rows){$('adminDisputes').innerHTML=rows.map(x=>`<div class="data-row"><b>${esc(x.reason)}</b><span>${money(x.frozen_usd)} congelados</span><span>${esc(x.status)}</span>${x.status==='OPEN'?`<div class="card-actions"><button class="ghost tiny" data-dispute="SELLER_WINS" data-id="${esc(x.dispute_id)}">VENDEDOR</button><button class="ghost tiny" data-dispute="BUYER_REFUNDED" data-id="${esc(x.dispute_id)}">COMPRADOR</button></div>`:''}</div>`).join('')||'<p class="muted">Sin disputas.</p>'}
function renderPayouts(rows){$('adminPayouts').innerHTML=rows.map(x=>`<div class="data-row"><b>${money(x.amount_usd)} → ${money(x.net_usd)}</b><span>${esc(x.method)}</span><code>${esc(x.destination)}</code><span>${esc(x.status)}</span>${['PENDING','PROCESSING'].includes(x.status)?`<div class="card-actions"><button class="ghost tiny" data-payout="PROCESSING" data-id="${esc(x.payout_id)}">PROCESAR</button><button class="primary tiny" data-payout="PAID" data-id="${esc(x.payout_id)}">PAGADO</button><button class="ghost tiny" data-payout="REJECTED" data-id="${esc(x.payout_id)}">RECHAZAR</button></div>`:''}</div>`).join('')||'<p class="muted">Sin retiros.</p>'}
function renderUsers(rows){$('adminUsers').innerHTML=rows.map(x=>`<div class="data-row"><b>${esc(x.display_name)}</b><span>${esc(x.email)}</span><span>${esc(x.username||'no seller')}</span><span>${Number(x.prompt_count||0)} prompts</span>${x.username?`<button class="ghost tiny" data-block-user="${esc(x.id)}" data-blocked="${x.blocked?0:1}">${x.blocked?'DESBLOQUEAR':'BLOQUEAR SELLER'}</button>`:''}</div>`).join('')||'<p class="muted">Sin usuarios.</p>'}

function bind(){
  $('refreshAdmin')?.addEventListener('click',loadAll);
  $('categoryForm')?.addEventListener('submit',async e=>{e.preventDefault();try{await api('/prompt-factory/admin/categories',jbody({label:$('adminCategoryLabel').value.trim(),active:true,sort_order:Number($('adminCategoryOrder').value||100)}));toast('Categoría creada');$('categoryForm').reset();await loadAll()}catch(err){toast(err.message,true)}});
  document.addEventListener('click',async e=>{
    const ls=e.target.closest('[data-listing-status]');if(ls){try{await api(`/prompt-factory/admin/listings/${encodeURIComponent(ls.dataset.id)}/status`,jbody({status:ls.dataset.listingStatus}));toast('Listing actualizado');await loadAll()}catch(err){toast(err.message,true)}return}
    const rr=e.target.closest('[data-resolve-report]');if(rr){const note=prompt('Resolución del reporte','Revisado por administración')||'';try{await api(`/prompt-factory/admin/reports/${encodeURIComponent(rr.dataset.resolveReport)}`,jbody({status:'RESOLVED',resolution:note},'PUT'));toast('Reporte resuelto');await loadAll()}catch(err){toast(err.message,true)}return}
    const ds=e.target.closest('[data-dispute]');if(ds){const refund=ds.dataset.dispute==='BUYER_REFUNDED'?(prompt('TX/reference del reembolso confirmado')||''):'';if(ds.dataset.dispute==='BUYER_REFUNDED'&&!refund)return;try{await api(`/prompt-factory/admin/disputes/${encodeURIComponent(ds.dataset.id)}`,jbody({resolution:ds.dataset.dispute,refund_tx:refund,notes:'Resolved in admin console'},'PUT'));toast('Disputa resuelta');await loadAll()}catch(err){toast(err.message,true)}return}
    const ps=e.target.closest('[data-payout]');if(ps){const tx=ps.dataset.payout==='PAID'?(prompt('TXID/referencia verificada del pago')||''):'';if(ps.dataset.payout==='PAID'&&!tx)return;try{await api(`/prompt-factory/admin/payouts/${encodeURIComponent(ps.dataset.id)}`,jbody({status:ps.dataset.payout,payout_tx:tx,notes:'Updated in admin console'},'PUT'));toast('Retiro actualizado');await loadAll()}catch(err){toast(err.message,true)}return}
    const bu=e.target.closest('[data-block-user]');if(bu){try{await api(`/prompt-factory/admin/sellers/${encodeURIComponent(bu.dataset.blockUser)}/blocked?blocked=${bu.dataset.blocked==='1'?'true':'false'}`,{method:'PUT'});toast('Estado del vendedor actualizado');await loadAll()}catch(err){toast(err.message,true)}return}
  });
}
init();
