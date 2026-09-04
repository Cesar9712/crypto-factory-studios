const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

const CRYPTOQUEST_CSP = "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https: wss:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'";
const LEGACY_PUBLIC_ORIGIN = 'https://crypto-factory-studios.cesargp9712.workers.dev';
const ANALYTICS_SCRIPT = '<script src="/analytics.js?v=20260828-2" defer></script>';
const PROMPT_FACTORY_ADVANCED_SCRIPT = '<script src="/prompt-factory-advanced.js?v=1" defer></script>';
const CQ_V20_STYLE = '<link rel="stylesheet" href="/games/cryptoquest/v20-premium.css?v=20.0.0">';
const CQ_V20_SCRIPT = '<script src="/games/cryptoquest/v20-battle-pass.js?v=20.0.0" defer></script>';
const CQ_V21_STYLE = '<link rel="stylesheet" href="/games/cryptoquest/v21-master.css?v=21.0.0">';

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {status, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...SECURITY_HEADERS,...extraHeaders}});
}

function normalizeOrigin(value){
  if(!value)return null;
  try{
    const u=new URL(value);
    if(u.protocol!=='https:'&&u.hostname!=='127.0.0.1'&&u.hostname!=='localhost')return null;
    return u.origin;
  }catch{return null}
}

function escapeHtml(value){
  return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function jsonLd(value){
  return JSON.stringify(value).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026');
}

function injectBeforeLastClosingTag(source, tag, insertion){
  const closing=`</${tag}>`;
  const index=source.toLowerCase().lastIndexOf(closing);
  if(index<0)return source+insertion;
  return source.slice(0,index)+insertion+source.slice(index);
}

async function proxyUpstream(request,env){
  const origin=normalizeOrigin(env.API_ORIGIN);
  if(!origin)return json({ok:false,code:'API_NOT_CONFIGURED',message:'Los servicios online todavía no están conectados en este entorno.'},503);
  const incoming=new URL(request.url);
  const target=new URL(incoming.pathname+incoming.search,origin);
  const headers=new Headers(request.headers);
  headers.set('X-CFS-Edge','cloudflare-worker');
  headers.delete('host');
  headers.delete('content-length');
  try{
    const hasBody=!['GET','HEAD'].includes(request.method);
    const body=hasBody?await request.arrayBuffer():undefined;
    const upstream=await fetch(new Request(target.toString(),{method:request.method,headers,body,redirect:'manual'}));
    const rh=new Headers(upstream.headers);
    for(const [k,v] of Object.entries(SECURITY_HEADERS)){if(!rh.has(k))rh.set(k,v)}
    if(incoming.pathname.startsWith('/api/'))rh.set('Cache-Control','no-store');
    return new Response(upstream.body,{status:upstream.status,statusText:upstream.statusText,headers:rh});
  }catch{
    return json({ok:false,code:'API_UPSTREAM_UNAVAILABLE',message:'El servicio online no está disponible temporalmente.'},502);
  }
}

async function fetchPublicListing(slug,env){
  const origin=normalizeOrigin(env.API_ORIGIN);
  if(!origin)return null;
  try{
    const r=await fetch(new URL(`/api/v1/prompt-factory/listings/${encodeURIComponent(slug)}`,origin),{headers:{'X-CFS-Edge':'cloudflare-worker','Accept':'application/json'}});
    if(!r.ok)return null;
    const data=await r.json();
    return data&&data.listing?data:null;
  }catch{return null}
}

async function servePromptProduct(request,env,slug){
  const data=await fetchPublicListing(slug,env);
  if(!data)return new Response('Prompt not found',{status:404,headers:{'Content-Type':'text/plain; charset=utf-8',...SECURITY_HEADERS}});
  const p=data.listing;
  const origin=new URL(request.url).origin;
  const canonical=`${origin}/prompts/${encodeURIComponent(p.slug)}`;
  const title=`${p.title} — Prompt Factory | Crypto Factory Studios`;
  const description=String(p.description||p.preview_text||'Prompt premium de Prompt Factory').slice(0,300);
  const price=Number(p.price_usd||0).toFixed(2);
  const ratingCount=Number(p.rating_count||0);
  const structured={
    '@context':'https://schema.org','@type':'Product',name:p.title,description,
    brand:{'@type':'Brand',name:'Crypto Factory Studios'},category:p.category||'Prompt',
    offers:{'@type':'Offer',url:canonical,priceCurrency:'USD',price,availability:'https://schema.org/InStock'},
    ...(ratingCount>0?{aggregateRating:{'@type':'AggregateRating',ratingValue:Number(p.rating_avg||0).toFixed(1),reviewCount:ratingCount}}:{}),
  };
  const reviews=(data.reviews||[]).slice(0,12);
  const tags=[...(p.ai_models||[]),...(p.tags||[])].slice(0,12);
  const body=`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#071016"><title>${escapeHtml(title)}</title><meta name="description" content="${escapeHtml(description)}"><link rel="canonical" href="${escapeHtml(canonical)}"><meta property="og:type" content="product"><meta property="og:title" content="${escapeHtml(p.title)}"><meta property="og:description" content="${escapeHtml(description)}"><meta property="og:url" content="${escapeHtml(canonical)}"><meta name="twitter:card" content="summary"><script type="application/ld+json">${jsonLd(structured)}</script><link rel="stylesheet" href="/prompt-factory.css?v=1"></head><body><div class="ambient ambient-a"></div><div class="ambient ambient-b"></div><header class="pf-topbar"><a class="brand" href="/"><span class="brandmark">CF</span><span>CRYPTO FACTORY <b>STUDIOS</b></span></a><a class="ghost tiny" href="/prompt-factory">PROMPT FACTORY</a></header><main><section class="pf-hero"><div><span class="eyebrow">${escapeHtml(p.category||'PROMPT')} · ${escapeHtml(p.license_type||'PERSONAL')} LICENSE</span><h1>${escapeHtml(p.title)}</h1><p class="hero-line">${price==='0.00'?'FREE':`$${escapeHtml(price)} USD`}</p><p class="hero-copy">${escapeHtml(description)}</p><div class="tags">${tags.map(t=>`<span class="tag">${escapeHtml(t)}</span>`).join('')}</div><div class="hero-actions"><a class="primary" href="/prompt-factory?prompt=${encodeURIComponent(p.slug)}">${price==='0.00'?'OBTENER PROMPT':'BUY NOW'}</a><a class="ghost" href="/prompt-factory">EXPLORAR MARKETPLACE</a></div></div><div class="hero-terminal"><div class="terminal-head"><span>PF://PRODUCT</span><i></i></div><div class="terminal-grid"><div><strong>${Number(p.sales_count||0)}</strong><span>ventas</span></div><div><strong>${Number(p.rating_avg||0).toFixed(1)}</strong><span>rating</span></div><div><strong>${ratingCount}</strong><span>reviews</span></div><div><strong>${escapeHtml(p.creator_name||'Creator')}</strong><span>creador</span></div></div></div></section><section class="pf-section"><div class="data-panel"><h2>Vista previa</h2><p>${escapeHtml(p.preview_text||'El contenido completo se desbloquea después de adquirir el prompt.')}</p></div><div class="data-panel"><h2>Reseñas verificadas</h2>${reviews.length?reviews.map(r=>`<div class="review-item"><b>${escapeHtml(r.display_name)} · ${'★'.repeat(Math.max(1,Math.min(5,Number(r.rating)||1)))}</b><p>${escapeHtml(r.comment||'')}</p></div>`).join(''):'<p class="muted">Aún no hay reseñas.</p>'}</div></section></main><script src="/analytics.js?v=20260828-2" defer></script></body></html>`;
  return new Response(body,{status:200,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'public, max-age=300','X-Robots-Tag':'index, follow',...SECURITY_HEADERS}});
}

async function augmentSitemap(body,request,env){
  const origin=normalizeOrigin(env.API_ORIGIN);
  if(!origin||!body.includes('</urlset>'))return body;
  try{
    const r=await fetch(new URL('/api/v1/prompt-factory/marketplace?sort=new&limit=100&offset=0',origin),{headers:{'X-CFS-Edge':'cloudflare-worker','Accept':'application/json'}});
    if(!r.ok)return body;
    const data=await r.json();
    const publicOrigin=new URL(request.url).origin;
    const urls=(data.listings||[]).filter(x=>x.slug).map(x=>`<url><loc>${escapeHtml(`${publicOrigin}/prompts/${encodeURIComponent(x.slug)}`)}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>`).join('');
    if(!urls)return body;
    return body.replace('</urlset>',`${urls}</urlset>`);
  }catch{return body}
}

async function serveAsset(request,env){
  let response;
  try{
    response=await env.ASSETS.fetch(request);
  }catch{
    return new Response('Service temporarily unavailable',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store',...SECURITY_HEADERS}});
  }
  const type=(response.headers.get('content-type')||'').toLowerCase();
  const headers=new Headers(response.headers);

  // RFC 9110 no-content responses cannot legally carry a body. Cloudflare Assets
  // can return 304 to browser conditional requests; rebuilding that response with
  // response.text() would throw inside the Worker and surface as Cloudflare 1101.
  if(request.method==='HEAD'||response.status===204||response.status===205||response.status===304){
    return new Response(null,{status:response.status,statusText:response.statusText,headers});
  }

  const isText=type.includes('text/html')||type.includes('application/xml')||type.includes('text/xml')||type.includes('text/plain');
  const pathname=new URL(request.url).pathname;
  const isCryptoQuest=pathname==='/games/cryptoquest' || pathname.startsWith('/games/cryptoquest/');
  const isPromptFactory=pathname==='/prompt-factory' || pathname==='/prompt-factory/' || pathname==='/prompt-factory.html';

  if(isCryptoQuest){
    headers.set('Content-Security-Policy',CRYPTOQUEST_CSP);
    headers.set('Cache-Control','no-store, max-age=0');
    headers.set('Pragma','no-cache');
    headers.set('X-Content-Type-Options','nosniff');
    headers.set('X-CryptoQuest-Visual','V18.2.1-LAYOUTFIX');
  }

  if(!isText)return new Response(response.body,{status:response.status,statusText:response.statusText,headers});

  const currentOrigin=new URL(request.url).origin;
  let body=(await response.text()).split(LEGACY_PUBLIC_ORIGIN).join(currentOrigin);

  if(isCryptoQuest&&type.includes('text/html')){
    const standaloneV1821=body.includes('CQ-V18.2.1-LAYOUTFIX');
    if(!standaloneV1821){
      if(!body.includes('/games/cryptoquest/v20-premium.css'))body=injectBeforeLastClosingTag(body,'head',CQ_V20_STYLE);
      if(!body.includes('/games/cryptoquest/v21-master.css'))body=injectBeforeLastClosingTag(body,'head',CQ_V21_STYLE);
      if(!body.includes('/games/cryptoquest/v20-battle-pass.js'))body=injectBeforeLastClosingTag(body,'body',CQ_V20_SCRIPT);
    }
  }

  if(isPromptFactory&&type.includes('text/html')){
    body=body.replace('/prompt-factory.html','/prompt-factory');
    if(!body.includes('/prompt-factory-advanced.js'))body=injectBeforeLastClosingTag(body,'body',PROMPT_FACTORY_ADVANCED_SCRIPT);
  }

  if(pathname==='/sitemap.xml'&&(type.includes('xml')||type.includes('text/plain'))){
    body=await augmentSitemap(body,request,env);
  }

  if(type.includes('text/html')&&(pathname==='/'||pathname==='/index.html')&&!body.includes('href="/prompt-factory"')){
    body=body.replace('<a href="/billing.html">Billing</a>','<a href="/billing.html">Billing</a><a href="/prompt-factory">Prompt Factory</a>');
  }

  if(type.includes('text/html')&&!body.includes('/analytics.js')){
    body=injectBeforeLastClosingTag(body,'body',ANALYTICS_SCRIPT);
  }

  headers.delete('content-length');
  return new Response(body,{status:response.status,statusText:response.statusText,headers});
}

export default {
  async fetch(request,env){
    const url=new URL(request.url);
    if(url.pathname==='/health')return json({ok:true,service:'cfs-edge',api_configured:Boolean(normalizeOrigin(env.API_ORIGIN))});
    if(url.pathname==='/ready'){
      const configured=Boolean(normalizeOrigin(env.API_ORIGIN));
      if(!configured)return json({ok:false,service:'cfs-edge',api_configured:false},503);
      const probe=new Request(new URL('/ready',normalizeOrigin(env.API_ORIGIN)),{headers:{'X-CFS-Edge':'cloudflare-worker'}});
      try{
        const r=await fetch(probe);
        return json({ok:r.ok,service:'cfs-edge',api_configured:true,upstream_status:r.status},r.ok?200:503);
      }catch{
        return json({ok:false,service:'cfs-edge',api_configured:true,upstream_status:0},503);
      }
    }
    if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/play/'))return proxyUpstream(request,env);
    if(/^\/prompts\/[a-z0-9-]+\/?$/.test(url.pathname)){
      const slug=decodeURIComponent(url.pathname.split('/')[2]||'');
      return servePromptProduct(request,env,slug);
    }
    if(url.pathname==='/bitshelf'||url.pathname==='/bitshelf/'){
      const target=new URL(request.url);target.pathname='/bitshelf.html';
      return serveAsset(new Request(target.toString(),request),env);
    }
    if(url.pathname==='/prompt-factory'||url.pathname==='/prompt-factory/'){
      const target=new URL(request.url);target.pathname='/prompt-factory.html';
      return serveAsset(new Request(target.toString(),request),env);
    }
    if(url.pathname==='/prompt-factory/admin'||url.pathname==='/prompt-factory/admin/'){
      const target=new URL(request.url);target.pathname='/prompt-factory-admin.html';
      return serveAsset(new Request(target.toString(),request),env);
    }
    return serveAsset(request,env);
  }
};