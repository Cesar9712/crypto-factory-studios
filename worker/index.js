const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

const CRYPTOQUEST_CSP = "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https: wss:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'";
const LEGACY_PUBLIC_ORIGIN = 'https://crypto-factory-studios.cesargp9712.workers.dev';
const ANALYTICS_SCRIPT = '<script src="/analytics.js?v=20260828-2" defer></script>';

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

async function serveAsset(request,env){
  const response=await env.ASSETS.fetch(request);
  const type=(response.headers.get('content-type')||'').toLowerCase();
  const isText=type.includes('text/html')||type.includes('application/xml')||type.includes('text/xml')||type.includes('text/plain');
  const headers=new Headers(response.headers);
  const pathname=new URL(request.url).pathname;
  const isCryptoQuest=pathname==='/games/cryptoquest' || pathname.startsWith('/games/cryptoquest/');

  if(isCryptoQuest){
    headers.set('Content-Security-Policy',CRYPTOQUEST_CSP);
    headers.set('Cache-Control','no-store, max-age=0');
    headers.set('Pragma','no-cache');
    headers.set('X-Content-Type-Options','nosniff');
    headers.set('X-CryptoQuest-Visual','V30-FORGED-OBSIDIAN');
  }

  if(!isText)return new Response(response.body,{status:response.status,statusText:response.statusText,headers});

  const currentOrigin=new URL(request.url).origin;
  let body=(await response.text()).split(LEGACY_PUBLIC_ORIGIN).join(currentOrigin);

  // The CryptoQuest V30 entry page contains literal "</body>" strings inside its
  // loader JavaScript. Always target the final real closing tag so edge injection
  // can never split the loader source and render JavaScript as page text.
  if(type.includes('text/html')&&!body.includes('/analytics.js')){
    body=injectBeforeLastClosingTag(body,'body',ANALYTICS_SCRIPT);
  }

  // Presentation/runtime for CryptoQuest is owned by its V30 loader. Do not inject
  // legacy V20/V21/V26 layers at the edge; they are obsolete and can corrupt boot.
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
    return serveAsset(request,env);
  }
};
