from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_catalog_and_payment_methods():
    with TestClient(app) as client:
        health = client.get('/health')
        assert health.status_code == 200
        assert health.json()['ok'] is True

        products = client.get('/api/v1/products')
        assert products.status_code == 200
        ids = {p['product_id'] for p in products.json()['products']}
        assert 'creator_plus_monthly' in ids
        assert 'creator_pro_monthly' in ids

        methods = client.get('/api/v1/payments/methods')
        assert methods.status_code == 200
        assert methods.json()['mode'] in {'MOCK', 'TEST'}
        assert {'usdt_tron', 'usdt_bsc', 'sol'} <= {m['method_id'] for m in methods.json()['methods']}


def test_register_creator_and_create_game():
    with TestClient(app) as client:
        email = 'smoke-live-api@example.test'
        register = client.post('/api/v1/auth/register', json={
            'email': email,
            'password': 'VeryStrongTestPassword123!',
            'display_name': 'Smoke Creator',
        })
        if register.status_code == 409:
            login = client.post('/api/v1/auth/login', json={
                'email': email,
                'password': 'VeryStrongTestPassword123!',
            })
            assert login.status_code == 200
        else:
            assert register.status_code == 200

        me = client.get('/api/v1/me')
        assert me.status_code == 200

        csrf = client.cookies.get('cfs_csrf')
        assert csrf
        headers = {'X-CSRF-Token': csrf}

        if me.json()['creator'] is None:
            activated = client.post('/api/v1/creator/activate', headers=headers, json={
                'creator_slug': 'smoke-creator-live-api',
                'bio': 'Automated smoke test creator.',
            })
            assert activated.status_code == 200

        created = client.post('/api/v1/creator/games', headers=headers, json={
            'title': 'Smoke Test Game',
            'description': 'Created by automated QA.',
            'genre': 'RPG',
        })
        assert created.status_code in {200, 403}
        if created.status_code == 200:
            assert created.json()['game']['status'] == 'DRAFT'
