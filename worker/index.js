const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {status, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...SECURITY_HEADERS,...extraHeaders}});
}
function normalizeOrigin(value){if(!value)return null;try{const u=new URL(value);if(u.protocol!=='https:'&&u.hostname!=='127.0.0.1'&&u.hostname!=='localhost')return null;return u.origin}catch{return null}}
async function proxyUpstream(request,env){
  const origin=normalizeOrigin(env.API_ORIGIN);if(!origin)return json({ok:false,code:'API_NOT_CONFIGURED',message:'Los servicios online todavía no están conectados en este entorno.'},503);
  const incoming=new URL(request.url);const target=new URL(incoming.pathname+incoming.search,origin);const headers=new Headers(request.headers);headers.set('X-CFS-Edge','cloudflare-worker');headers.delete('host');
  try{const upstream=await fetch(new Request(target.toString(),{method:request.method,headers,body:['GET','HEAD'].includes(request.method)?undefined:request.body,redirect:'manual'}));const rh=new Headers(upstream.headers);for(const [k,v] of Object.entries(SECURITY_HEADERS)){if(!rh.has(k))rh.set(k,v)}if(incoming.pathname.startsWith('/api/'))rh.set('Cache-Control','no-store');return new Response(upstream.body,{status:upstream.status,statusText:upstream.statusText,headers:rh})}
  catch{return json({ok:false,code:'API_UPSTREAM_UNAVAILABLE',message:'El servicio online no está disponible temporalmente.'},502)}
}
export default {async fetch(request,env){const url=new URL(request.url);if(url.pathname==='/health')return json({ok:true,service:'cfs-edge',api_configured:Boolean(normalizeOrigin(env.API_ORIGIN))});if(url.pathname==='/ready'){const configured=Boolean(normalizeOrigin(env.API_ORIGIN));if(!configured)return json({ok:false,service:'cfs-edge',api_configured:false},503);const probe=new Request(new URL('/ready',normalizeOrigin(env.API_ORIGIN)),{headers:{'X-CFS-Edge':'cloudflare-worker'}});try{const r=await fetch(probe);return json({ok:r.ok,service:'cfs-edge',api_configured:true,upstream_status:r.status},r.ok?200:503)}catch{return json({ok:false,service:'cfs-edge',api_configured:true,upstream_status:0},503)}}if(url.pathname.startsWith('/api/')||url.pathname.startsWith('/play/'))return proxyUpstream(request,env);return env.ASSETS.fetch(request)}};
