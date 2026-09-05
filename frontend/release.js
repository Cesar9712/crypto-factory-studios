const lang=()=>localStorage.getItem('nexus-lang')||'es';
const OLD_ES='Pagos, depósitos, retiros, cash-out y tesorería real permanecen desactivados hasta la fase final.';
const OLD_EN='Payments, deposits, withdrawals, cash-out and real treasury stay disabled until the final phase.';
const NEW_ES='Nexus Realms está en Acceso Anticipado. El Pack Fundador acepta USDT BEP20. Earn y los retiros siguen en modo DEMO y no tienen valor monetario.';
const NEW_EN='Nexus Realms is in Early Access. The Founder Pack accepts USDT BEP20. Earn and withdrawals remain DEMO-only and have no monetary value.';
function patchCopy(){
 const brand=document.querySelector('.brand');
 if(brand&&!document.querySelector('.early-access-badge')){const b=document.createElement('span');b.className='early-access-badge';b.textContent='EARLY ACCESS';brand.insertAdjacentElement('afterend',b)}
 document.querySelectorAll('#panel small,#panel p,#panel .muted').forEach(el=>{const s=(el.textContent||'').trim();if(s===OLD_ES||s===OLD_EN)el.textContent=lang()==='es'?NEW_ES:NEW_EN});
 let f=document.querySelector('.legal-footer');
 if(!f){f=document.createElement('footer');f.className='legal-footer';document.body.append(f)}
 f.innerHTML=lang()==='es'?'<a href="/terms.html">Términos</a><a href="/privacy.html">Privacidad</a><a href="/purchase-policy.html">Política de compras</a>':'<a href="/terms.html">Terms</a><a href="/privacy.html">Privacy</a><a href="/purchase-policy.html">Purchase Policy</a>';
}
function soon(){setTimeout(patchCopy,60)}
window.addEventListener('nexus:state',soon);window.addEventListener('pageshow',soon);document.addEventListener('click',soon,true);setInterval(patchCopy,2500);setTimeout(patchCopy,200);
