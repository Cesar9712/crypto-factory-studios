import io
import uuid
import zipfile

from fastapi.testclient import TestClient

from backend.app.main import app, db


PASSWORD = 'VeryStrongTestPassword123!'


def register(client, prefix='hardening'):
    suffix=uuid.uuid4().hex[:10]
    email=f'{prefix}-{suffix}@example.com'
    r=client.post('/api/v1/auth/register',json={'email':email,'password':PASSWORD,'display_name':'Hardening QA'})
    assert r.status_code==200
    csrf=client.cookies.get('cfs_csrf')
    assert csrf
    return r.json()['user'], {'X-CSRF-Token':csrf}


def tiny_zip():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html','<!doctype html><h1>quota</h1>')
    return buf.getvalue()


def test_report_moderation_requires_admin_and_updates_status():
    with TestClient(app) as reporter:
        user, headers=register(reporter,'reporter')
        created=reporter.post('/api/v1/reports',headers=headers,json={'creator_id':None,'game_id':None,'category':'abuse','details':'invalid target'})
        assert created.status_code==400

        reporter.post('/api/v1/creator/activate',headers=headers,json={'creator_slug':'reporter-'+uuid.uuid4().hex[:8],'bio':'qa'})
        game=reporter.post('/api/v1/creator/games',headers=headers,json={'title':'Report Target','genre':'Other'}).json()['game']
        report=reporter.post('/api/v1/reports',headers=headers,json={'game_id':game['game_id'],'category':'abuse','details':'Please review this game.'})
        assert report.status_code==200
        report_id=report.json()['report_id']
        denied=reporter.post(f'/api/v1/admin/reports/{report_id}/status',headers=headers,json={'status':'RESOLVED'})
        assert denied.status_code==403

    with TestClient(app) as admin:
        admin_user, admin_headers=register(admin,'admin')
        db.execute("UPDATE users SET role='admin' WHERE id=?",(admin_user['id'],))
        resolved=admin.post(f'/api/v1/admin/reports/{report_id}/status',headers=admin_headers,json={'status':'RESOLVED'})
        assert resolved.status_code==200
        assert resolved.json()['status']=='RESOLVED'
        row=db.one('SELECT status FROM reports WHERE report_id=?',(report_id,))
        assert row['status']=='RESOLVED'


def test_creator_total_storage_quota_is_enforced():
    with TestClient(app) as client:
        user, headers=register(client,'quota')
        activated=client.post('/api/v1/creator/activate',headers=headers,json={'creator_slug':'quota-'+uuid.uuid4().hex[:8],'bio':'qa'})
        assert activated.status_code==200
        plan_id='qa_tiny_'+uuid.uuid4().hex[:10]
        db.execute('''INSERT INTO creator_plans(plan_id,label,max_games,max_storage_bytes,max_builds_per_game,max_upload_bytes,advanced_analytics,private_builds,priority_processing,team_members,active)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(plan_id,'QA Tiny',2,1,3,1024*1024,0,0,0,1,1))
        db.execute('UPDATE creator_profiles SET plan_id=? WHERE user_id=?',(plan_id,user['id']))
        game=client.post('/api/v1/creator/games',headers=headers,json={'title':'Quota Target','genre':'Other'})
        assert game.status_code==200
        gid=game.json()['game']['game_id']
        payload=tiny_zip()
        assert len(payload)>1
        upload=client.post(f'/api/v1/creator/games/{gid}/builds',headers=headers,data={'version':'1.0.0'},files={'archive':('game.zip',payload,'application/zip')})
        assert upload.status_code==403
        assert upload.json()['detail']['error_code']=='storage_limit'


def test_save_rejects_private_game_not_owned_by_player():
    with TestClient(app) as owner:
        owner_user, owner_headers=register(owner,'owner')
        assert owner.post('/api/v1/creator/activate',headers=owner_headers,json={'creator_slug':'private-'+uuid.uuid4().hex[:8],'bio':'qa'}).status_code==200
        game=owner.post('/api/v1/creator/games',headers=owner_headers,json={'title':'Private Save Target','genre':'Other','visibility':'PRIVATE'})
        assert game.status_code==200
        gid=game.json()['game']['game_id']

    with TestClient(app) as other:
        _, other_headers=register(other,'other')
        put=other.put(f'/api/v1/games/{gid}/save',headers=other_headers,json={'save_version':1,'revision':0,'state':{'x':1}})
        assert put.status_code==404
