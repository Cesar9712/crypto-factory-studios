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
    with TestClient(app) as client:
        registered = client.post('/api/v1/auth/register', json=account)
        assert registered.status_code == 200
        first_token = registered.json()['access_token']

        # Remove the first session cookie before logging in again so the
        # second login represents a genuinely distinct session/client.
        client.cookies.clear()
        second_login = client.post(
            '/api/v1/auth/login',
            json={'email': account['email'], 'password': account['password']},
        )
        assert second_login.status_code == 200
        second_token = second_login.json()['access_token']
        assert first_token != second_token

        first_headers = {'Authorization': f'Bearer {first_token}'}
        second_headers = {'Authorization': f'Bearer {second_token}'}
        assert client.get('/api/v1/me', headers=first_headers).status_code == 200
        assert client.get('/api/v1/me', headers=second_headers).status_code == 200

        response = client.post('/api/v1/auth/logout-all', headers=first_headers)
        assert response.status_code == 200
        assert client.get('/api/v1/me', headers=first_headers).status_code == 401
        assert client.get('/api/v1/me', headers=second_headers).status_code == 401
