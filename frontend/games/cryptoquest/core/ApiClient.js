export class ApiClient {
  constructor({ baseUrl = '', timeoutMs = 10000, fetchImpl = fetch } = {}) { this.baseUrl=baseUrl;this.timeoutMs=timeoutMs;this.fetchImpl=fetchImpl; }
  async request(path,{method='GET',body,headers={},signal}={}) { const controller=new AbortController();const timeoutError=()=>typeof DOMException==='function'?new DOMException('Timeout','AbortError'):new Error('Timeout');const timer=setTimeout(()=>controller.abort(timeoutError()),this.timeoutMs);const linkedAbort=()=>controller.abort(signal?.reason);signal?.addEventListener('abort',linkedAbort,{once:true});try{const response=await this.fetchImpl(`${this.baseUrl}${path}`,{method,headers:{Accept:'application/json',...(body!==undefined?{'Content-Type':'application/json'}:{}),...headers},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal,credentials:'same-origin'});const type=response.headers.get('content-type')||'';const payload=type.includes('application/json')?await response.json():await response.text();if(!response.ok)throw Object.assign(new Error(`HTTP ${response.status}`),{status:response.status,payload});return payload;}finally{clearTimeout(timer);signal?.removeEventListener('abort',linkedAbort);} }
  get(path,options){return this.request(path,options);}
  post(path,body,options={}){return this.request(path,{...options,method:'POST',body});}
  put(path,body,options={}){return this.request(path,{...options,method:'PUT',body});}
  delete(path,options={}){return this.request(path,{...options,method:'DELETE'});}
}
