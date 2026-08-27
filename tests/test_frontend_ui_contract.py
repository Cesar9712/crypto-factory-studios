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


def test_home_surfaces_verified_cryptoquest_runtime():
    html = read('index.html')
    assert '<h3>CryptoQuest RPG</h3>' in html
    assert 'href="/games/cryptoquest/"' in html
    assert '>Jugar ahora</a>' in html
    assert '<span class="status live">LIVE</span>' in html
    assert 'LIVE GAME' in html
    assert 'CRYPTOQUEST<br>RPG' in html
    assert 'aria-label="Jugar CryptoQuest RPG ahora"' in html
    assert 'aria-label="Abrir CryptoQuest RPG"' in html
    assert 'EN INTEGRACIÓN</button>' not in html
    assert 'ClamAV en producción' not in html
    assert 'Escaneo estructural y firmas integradas' in html


def test_billing_has_responsive_asset_and_csp_safe_plan_binding():
    html = read('billing.html')
    js = read('billing.js')
    assert '/responsive.css' in html
    assert 'viewport-fit=cover' in html
    assert "addEventListener('click',()=>chooseProduct" in js
    assert "api('/me')" in js
    assert 'onclick=' not in html.lower()


def test_billing_exposes_supported_public_payment_networks():
    js = read('billing.js')
    for method_id in ('usdt_tron', 'usdt_bsc'):
        assert method_id in js
    assert "['usdt_tron','usdt_bsc']" in js
    assert 'BNB SMART CHAIN' in js
    assert 'TRC-20' in js
    assert 'SOLANA' not in js
    assert 'clearCheckout()' in js


def test_billing_layout_has_anti_overlap_guards():
    css = read('responsive.css')
    assert 'minmax(380px,.85fr)' in css
    assert '@media(max-width:1180px)' in css
    assert '.billing-page .order-summary{grid-template-columns:1fr}' in css
    assert 'word-break:break-all' in css


def test_creator_studio_surfaces_one_click_publish_and_share_contract():
    js = read('creator.js')
    assert 'Godot detected ✓' in js
    assert 'Build root prepared ✓' in js
    assert 'Ready to publish ✓' in js
    assert '>PLAY<' in js
    assert 'COPY LINK' in js
    assert 'SHARE' in js
    assert 'navigator.share' in js
    assert "document.execCommand('copy')" in js
    assert '/billing.html?source=creator-studio' in js
    assert 'Unlock Creator Pro' in js


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


def test_public_seo_basics_exist():
    assert (FRONTEND / 'robots.txt').exists()
    assert (FRONTEND / 'sitemap.xml').exists()
    home = read('index.html')
    assert 'rel="canonical"' in home
    assert 'application/ld+json' in home
    assert 'og:title' in home
    for name in ('godot-web-hosting.html', 'publish-html5-game.html'):
        html = read(name)
        assert '<h1>' in html
        assert 'rel="canonical"' in html
        assert 'name="description"' in html