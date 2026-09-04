from fastapi.testclient import TestClient

from backend.app.main import app, db
from backend.app.owner_accounts import OWNER_ACCOUNTS, platform_owner_accounts_ready
from backend.app.security import new_token, now, token_hash


def bearer_for(user_id: str) -> dict[str, str]:
    raw = new_token()
    t = now()
    db.execute(
        'INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)',
        (token_hash(raw), user_id, t, t + 3600),
    )
    return {'Authorization': f'Bearer {raw}'}


def test_global_platform_owners_are_provisioned_and_unlimited():
    assert platform_owner_accounts_ready(db) is True

    with TestClient(app) as client:
        for account in OWNER_ACCOUNTS:
            user = db.one('SELECT * FROM users WHERE email=?', (account['email'],))
            assert user is not None
            assert user['role'] == 'platform_owner'
            assert int(user.get('disabled') or 0) == 0
            assert str(user['password_hash']).startswith('$argon2id$')

            creator = db.one('SELECT * FROM creator_profiles WHERE user_id=?', (user['id'],))
            assert creator is not None
            assert creator['plan_id'] == 'internal_unlimited'
            assert int(creator['billing_exempt']) == 1

            headers = bearer_for(user['id'])

            me = client.get('/api/v1/me', headers=headers)
            assert me.status_code == 200
            assert me.json()['user']['role'] == 'platform_owner'
            assert me.json()['plan']['limits']['plan_id'] == 'internal_unlimited'

            prompt_me = client.get('/api/v1/prompt-factory/me', headers=headers)
            assert prompt_me.status_code == 200
            assert prompt_me.json()['plan']['plan_id'] == 'unlimited'
            assert prompt_me.json()['plan']['internal'] is True
            assert prompt_me.json()['storage']['limit'] is None

            prompt_admin = client.get('/api/v1/prompt-factory/admin/overview', headers=headers)
            assert prompt_admin.status_code == 200

            feature_admin = client.put(
                '/api/v1/admin/platform/features/cryptoquest_enabled',
                headers=headers,
                json={'enabled': False},
            )
            assert feature_admin.status_code == 200
            assert feature_admin.json()['features']['cryptoquest_enabled'] is False
