import io
import uuid
import zipfile

from fastapi.testclient import TestClient

from backend.app.main import app


def make_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html', '<!doctype html><title>QA Game</title><h1>OK</h1>')
        z.writestr('game.js', 'console.log("qa")')
    return buf.getvalue()


def auth_creator(client: TestClient):
    suffix = uuid.uuid4().hex[:10]
    r = client.post('/api/v1/auth/register', json={
        'email': f'platform-{suffix}@example.com',
        'password': 'VeryStrongTestPassword123!',
        'display_name': 'Platform QA',
    })
    assert r.status_code == 200
    csrf = client.cookies.get('cfs_csrf')
    headers = {'X-CSRF-Token': csrf}
    r = client.post('/api/v1/creator/activate', headers=headers, json={
        'creator_slug': f'platform-{suffix}', 'bio': 'QA'
    })
    assert r.status_code == 200
    return headers


def test_upload_publish_and_play_game():
    with TestClient(app) as client:
        headers = auth_creator(client)
        r = client.post('/api/v1/creator/games', headers=headers, json={
            'title': 'Published QA Game', 'description': 'QA', 'genre': 'RPG'
        })
        assert r.status_code == 200
        game = r.json()['game']

        r = client.post(
            f"/api/v1/creator/games/{game['game_id']}/builds",
            headers=headers,
            data={'version': '1.0.0'},
            files={'archive': ('game.zip', make_zip(), 'application/zip')},
        )
        assert r.status_code == 200
        build = r.json()
        assert build['scan_status'] == 'CLEAN'

        r = client.post(f"/api/v1/creator/builds/{build['build_id']}/publish", headers=headers)
        assert r.status_code == 200

        catalog = client.get('/api/v1/games')
        assert catalog.status_code == 200
        row = next(x for x in catalog.json()['games'] if x['game_id'] == game['game_id'])
        play = client.get(f"/play/{row['slug']}/")
        assert play.status_code == 200
        assert 'QA Game' in play.text


def test_cloud_save_revision_and_logout_all():
    with TestClient(app) as client:
        headers = auth_creator(client)
        r = client.post('/api/v1/creator/games', headers=headers, json={'title': 'Save QA', 'genre': 'Other'})
        assert r.status_code == 200
        gid = r.json()['game']['game_id']

        r = client.put(f'/api/v1/games/{gid}/save', headers=headers, json={'save_version': 1, 'revision': 0, 'state': {'level': 3}})
        assert r.status_code == 200
        assert r.json()['revision'] == 1
        saved = client.get(f'/api/v1/games/{gid}/save')
        assert saved.status_code == 200
        assert saved.json()['state']['level'] == 3

        conflict = client.put(f'/api/v1/games/{gid}/save', headers=headers, json={'save_version': 1, 'revision': 0, 'state': {}})
        assert conflict.status_code == 409

        out = client.post('/api/v1/auth/logout-all', headers=headers)
        assert out.status_code == 200
        assert client.get('/api/v1/me').status_code == 401
