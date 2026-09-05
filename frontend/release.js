const lang=()=>localStorage.getItem('nexus-lang')||'es';
const OLD_ES='Pagos, depósitos, retiros, cash-out y tesorería real permanecen desactivados hasta la fase final.';
const OLD_EN='Payments, deposits, withdrawals, cash-out and real treasury stay disabled until the final phase.';
const SEASON_OLD_ES='Las compras reales todavía no están habilitadas. El Pack Fundador es una compra de contenido interno y sus beneficios no son retirables ni representan una inversión.';
const SEASON_OLD_EN='Real purchases are not enabled yet. The Founder Pack is an in-game content purchase; its benefits are non-withdrawable and are not an investment.';
const NEW_ES='Nexus Realms está en Acceso Anticipado. El Pack Fundador acepta USDT BEP20. Earn y los retiros siguen en modo DEMO y no tienen valor monetario.';
const NEW_EN='Nexus Realms is in Early Access. The Founder Pack accepts USDT BEP20. Earn and withdrawals remain DEMO-only and have no monetary value.';
const SEASON_NEW_ES='El Pack Fundador es la única compra real habilitada actualmente. Es contenido digital del juego; sus beneficios no son retirables ni representan una inversión. Earn y retiros continúan en DEMO.';
const SEASON_NEW_EN='The Founder Pack is currently the only real purchase enabled. It is digital game content; its benefits are non-withdrawable and are not an investment. Earn and withdrawals remain DEMO-only.';
function patchCopy(){
 const brand=document.querySelector('.brand');
 if(brand&&!document.querySelector('.early-access-badge')){const b=document.createElement('span');b.className='early-access-badge';b.textContent='EARLY ACCESS';brand.insertAdjacentElement('afterend',b)}
 document.querySelectorAll('#panel small,#panel p,#panel .muted,.season-overlay p,.season-overlay small').forEach(el=>{const s=(el.textContent||'').trim();if(s===OLD_ES||s===OLD_EN)el.textContent=lang()==='es'?NEW_ES:NEW_EN;else if(s===SEASON_OLD_ES||s===SEASON_OLD_EN)el.textContent=lang()==='es'?SEASON_NEW_ES:SEASON_NEW_EN});
 document.querySelectorAll('.season-overlay .eyebrow').forEach(el=>{if(/DEMO.*sin dinero real|DEMO.*no real money/i.test(el.textContent||''))el.textContent=lang()==='es'?'ACCESO ANTICIPADO · EARN DEMO':'EARLY ACCESS · EARN DEMO'});
 const signup=document.querySelector('#signup-password');if(signup){signup.minLength=8;signup.setAttribute('minlength','8');signup.title=lang()==='es'?'Usa al menos 8 caracteres.':'Use at least 8 characters.'}
 let f=document.querySelector('.legal-footer');
 if(!f){f=document.createElement('footer');f.className='legal-footer';document.body.append(f)}
 f.innerHTML=lang()==='es'?'<a href="/terms.html">Términos</a><a href="/privacy.html">Privacidad</a><a href="/purchase-policy.html">Política de compras</a>':'<a href="/terms.html">Terms</a><a href="/privacy.html">Privacy</a><a href="/purchase-policy.html">Purchase Policy</a>';
}
function soon(){setTimeout(patchCopy,60)}
window.addEventListener('nexus:state',soon);window.addEventListener('pageshow',soon);document.addEventListener('click',soon,true);setInterval(patchCopy,2500);setTimeout(patchCopy,200);
