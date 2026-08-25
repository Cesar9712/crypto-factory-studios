from pathlib import Path
import re

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'


def read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding='utf-8')


def test_no_inline_javascript_event_handlers():
    offenders = []
    pattern = re.compile(r'\son(?:click|submit|change|input|load|error)\s*=', re.I)
    for path in FRONTEND.rglob('*.html'):
        if pattern.search(path.read_text(encoding='utf-8')):
            offenders.append(str(path.relative_to(FRONTEND)))
    assert not offenders, f'Inline CSP-blocked handlers found in: {offenders}'


def test_portal_session_state_is_server_driven():
    js = read('app.js')
    assert "api('/me')" in js
    assert "api('/auth/logout',{method:'POST'})" in js
    assert 'sessionStorage' not in js
    assert 'localStorage' not in js
    assert 'Iniciar sesión' in js and 'Crear cuenta' in js and 'Cerrar sesión' in js


def test_billing_has_responsive_asset_and_csp_safe_plan_binding():
    html = read('billing.html')
    js = read('billing.js')
    assert '/responsive.css' in html
    assert 'viewport-fit=cover' in html
    assert "addEventListener('click',()=>chooseProduct" in js
    assert "api('/me')" in js
    assert 'onclick=' not in html.lower()


def test_billing_exposes_all_three_supported_payment_networks():
    js = read('billing.js')
    for method_id in ('usdt_tron', 'usdt_bsc', 'sol'):
        assert method_id in js
    assert 'BNB SMART CHAIN' in js
    assert 'TRC-20' in js
    assert 'SOLANA' in js
    assert 'clearCheckout()' in js


def test_billing_layout_has_anti_overlap_guards():
    css = read('responsive.css')
    assert 'minmax(380px,.85fr)' in css
    assert '@media(max-width:1180px)' in css
    assert '.billing-page .order-summary{grid-template-columns:1fr}' in css
    assert 'word-break:break-all' in css
    assert '.qr-fallback.show' in css


def test_core_pages_are_mobile_viewport_ready():
    for name in ('index.html', 'billing.html', 'creator.html', 'profile.html'):
        html = read(name)
        assert 'name="viewport"' in html, name
        assert 'width=device-width' in html, name


def test_responsive_layer_covers_phone_and_desktop_breakpoints():
    css = read('responsive.css')
    for breakpoint in ('390px', '620px', '900px', '1024px', '1180px', '1200px'):
        assert breakpoint in css
    assert 'overflow-x:hidden' in css
    assert '.payment-terminal' in css
    assert '.account-grid' in css
