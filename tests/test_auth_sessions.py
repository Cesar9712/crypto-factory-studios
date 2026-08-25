import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


def _account():
    suffix = uuid.uuid4().hex
    return {
        'email': f'auth-{suffix}@example.com',
        'password': 'VeryStrongTestPassword123!',
        'display_name': 'Auth Test',
    }


def test_duplicate_registration_and_bad_password_are_not_500s():
    account = _account()
    with TestClient(app) as client:
        first = client.post('/api/v1/auth/register', json=account)
        assert first.status_code == 200
        duplicate = client.post('/api/v1/auth/register', json=account)
        assert duplicate.status_code == 409
        bad = client.post('/api/v1/auth/login', json={'email': account['email'], 'password': 'WrongPassword123!'})
        assert bad.status_code == 401


def test_logout_revokes_current_session():
    account = _account()
    with TestClient(app) as client:
        assert client.post('/api/v1/auth/register', json=account).status_code == 200
        csrf = client.cookies.get('cfs_csrf')
        assert csrf
        assert client.post('/api/v1/auth/logout', headers={'X-CSRF-Token': csrf}).status_code == 200
        assert client.get('/api/v1/me').status_code == 401


def test_logout_all_revokes_every_session_for_user():
    account = _account()
    with TestClient(app) as first, TestClient(app) as second:
        assert first.post('/api/v1/auth/register', json=account).status_code == 200
        assert second.post('/api/v1/auth/login', json={'email': account['email'], 'password': account['password']}).status_code == 200
        assert first.get('/api/v1/me').status_code == 200
        assert second.get('/api/v1/me').status_code == 200

        csrf = first.cookies.get('cfs_csrf')
        assert csrf
        response = first.post('/api/v1/auth/logout-all', headers={'X-CSRF-Token': csrf})
        assert response.status_code == 200
        assert first.get('/api/v1/me').status_code == 401
        assert second.get('/api/v1/me').status_code == 401
