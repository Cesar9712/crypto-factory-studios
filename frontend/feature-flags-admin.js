(()=>{
  const API='/api/v1';
  const state={cryptoquest_enabled:false,crypto_factory_game_enabled:false};
  const q=document.getElementById('toggleCryptoQuest');
  const f=document.getElementById('toggleCryptoFactory');
  function csrf(){return document.cookie.split('; ').find(x=>x.startsWith('cfs_csrf='))?.split('=')[1]||''}
  function toast(message){const el=document.getElementById('toast');if(!el)return;el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2600)}
  async function read(r){const text=await r.text();if(!text)return{};try{return JSON.parse(text)}catch{return{detail:{message:`HTTP ${r.status}`}}}}
  async function api(path,opt={}){opt.credentials='same-origin';opt.headers={...(opt.headers||{})};if((opt.method||'GET').toUpperCase()!=='GET'){opt.headers['Content-Type']='application/json';opt.headers['X-CSRF-Token']=csrf()}const r=await fetch(API+path,opt);const d=await read(r);if(!r.ok)throw new Error(d.detail?.message||`HTTP ${r.status}`);return d}
  function paintButton(button,enabled){if(!button)return;button.textContent=enabled?'ON':'OFF';button.classList.toggle('primary',enabled);button.classList.toggle('ghost',!enabled);button.setAttribute('aria-pressed',enabled?'true':'false')}
  function paint(){paintButton(q,state.cryptoquest_enabled);paintButton(f,state.crypto_factory_game_enabled)}
  async function refresh(){try{const data=await api('/platform/features');Object.assign(state,data.features||{});paint()}catch(e){if(q)q.textContent='ERROR';if(f)f.textContent='ERROR';console.warn('feature flags unavailable',e.message)}}
  async function toggle(key,button){button.disabled=true;try{const data=await api(`/admin/platform/features/${encodeURIComponent(key)}`,{method:'PUT',body:JSON.stringify({enabled:!state[key]})});Object.assign(state,data.features||{});paint();toast(`${key}: ${state[key]?'ON':'OFF'}`)}catch(e){toast(e.message)}finally{button.disabled=false}}
  q?.addEventListener('click',()=>toggle('cryptoquest_enabled',q));
  f?.addEventListener('click',()=>toggle('crypto_factory_game_enabled',f));
  refresh();
})();
