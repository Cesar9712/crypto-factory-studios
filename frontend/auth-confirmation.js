// Production email-confirmation guard for Nexus Realms.
// It forces password-signup confirmation links back to the public game instead of localhost.
const NEXUS_PUBLIC_ORIGIN='https://nexus-realms-web3.onrender.com';
const NEXUS_EMAIL_CALLBACK=`${NEXUS_PUBLIC_ORIGIN}/auth/callback`;
const nativeFetch=window.fetch.bind(window);

window.fetch=function(input,init={}){
  try{
    const raw=typeof input==='string'?input:input?.url;
    if(raw){
      const url=new URL(raw,window.location.href);
      if(url.hostname.endsWith('.supabase.co')&&url.pathname.endsWith('/auth/v1/signup')){
        url.searchParams.set('redirect_to',NEXUS_EMAIL_CALLBACK);
        input=typeof input==='string'?url.toString():new Request(url.toString(),input);
      }
    }
  }catch{}
  return nativeFetch(input,init);
};

const currentUrl=new URL(window.location.href);
const hashParams=new URLSearchParams(currentUrl.hash.replace(/^#/,''));
const callbackEntry=currentUrl.pathname==='/auth/callback';
const authError=hashParams.get('error_description')||currentUrl.searchParams.get('error_description')||'';
const noticeKey='nexus-email-confirmation-notice';

if(callbackEntry){
  const notice={type:authError?'error':'success',message:authError,at:Date.now()};
  try{sessionStorage.setItem(noticeKey,JSON.stringify(notice));}catch{}
  // Keep the auth hash intact so supabase-js can still recover the confirmed session.
  const clean=`/?email_confirmed=${authError?'0':'1'}${currentUrl.hash||''}`;
  history.replaceState({},'',clean);
}

function readNotice(){
  try{
    const raw=sessionStorage.getItem(noticeKey);
    if(raw){
      const n=JSON.parse(raw);
      if(Date.now()-Number(n.at||0)<15*60*1000)return n;
      sessionStorage.removeItem(noticeKey);
    }
  }catch{}
  const q=new URLSearchParams(location.search);
  if(q.get('email_confirmed')==='1')return{type:'success',message:'',at:Date.now()};
  if(q.get('email_confirmed')==='0')return{type:'error',message:'',at:Date.now()};
  return null;
}

function showConfirmationNotice(){
  const notice=readNotice();
  if(!notice)return;
  const card=document.querySelector('.auth-card');
  if(!card||document.getElementById('email-confirmation-notice'))return;
  const es=(localStorage.getItem('nexus-lang')||'es')!=='en';
  const el=document.createElement('div');
  el.id='email-confirmation-notice';
  el.className=notice.type==='success'?'success-note':'info-note';
  el.setAttribute('role','status');
  if(notice.type==='success'){
    el.innerHTML=es
      ?'<b>✅ Correo confirmado correctamente.</b><br>Ya puedes iniciar sesión en Nexus Realms.'
      :'<b>✅ Email confirmed successfully.</b><br>You can now sign in to Nexus Realms.';
  }else{
    const detail=String(notice.message||'').replace(/[<>]/g,'');
    el.textContent=es
      ?`No pudimos completar la confirmación. ${detail||'Vuelve a abrir el enlace del correo o solicita uno nuevo.'}`
      :`We could not complete confirmation. ${detail||'Open the email link again or request a new one.'}`;
  }
  const heading=card.querySelector('h2');
  if(heading)heading.insertAdjacentElement('afterend',el);else card.prepend(el);
}

[100,300,700,1500,3000,5000].forEach(ms=>setTimeout(showConfirmationNotice,ms));
window.addEventListener('pageshow',()=>setTimeout(showConfirmationNotice,100));
