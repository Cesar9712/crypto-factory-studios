from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_first_party_games_are_hidden_from_public_source_surfaces():
    home = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    app_js = (ROOT / 'frontend' / 'app.js').read_text(encoding='utf-8')
    sitemap = (ROOT / 'frontend' / 'sitemap.xml').read_text(encoding='utf-8').lower()
    wrangler = (ROOT / 'wrangler.toml').read_text(encoding='utf-8')
    edge = (ROOT / 'worker' / 'public-index.js').read_text(encoding='utf-8')

    assert 'CryptoQuest RPG' not in home
    assert '/games/cryptoquest' not in home.lower()
    assert '<h3>Crypto Factory</h3>' not in home
    assert 'Crypto Factory Game' not in home

    assert 'enableCryptoQuestCard' not in app_js
    assert 'game_play_clicked' not in app_js
    assert '/games/cryptoquest' not in app_js.lower()

    assert 'cryptoquest' not in sitemap
    assert 'browser-games' not in sitemap
    assert '/game.html' not in sitemap

    assert 'main = "worker/public-index.js"' in wrangler
    assert "cryptoquest_enabled: false" in edge
    assert "crypto_factory_game_enabled: false" in edge
    assert "'X-Robots-Tag': 'noindex, nofollow'" in edge
    assert "url.pathname === '/api/v1/products'" in edge


def test_platform_feature_flags_default_to_both_games_off():
    with TestClient(app) as client:
        response = client.get('/api/v1/platform/features')
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload['source'] == 'platform_feature_flags'
        assert payload['features']['cryptoquest_enabled'] is False
        assert payload['features']['crypto_factory_game_enabled'] is False
        assert payload['games_hidden'] is True
