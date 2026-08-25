from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from fastapi import File, Form, Header, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field


class SaveIn(BaseModel):
    save_version: int = Field(ge=1)
    revision: int = Field(ge=0)
    state: dict[str, Any]


class ReportIn(BaseModel):
    game_id: str | None = None
    creator_id: str | None = None
    category: str = Field(min_length=3, max_length=40)
    details: str = Field(min_length=4, max_length=2000)


def register_platform_routes(app, *, db, settings, scanner, storage, session_user: Callable, creator_profile: Callable,
                             effective_plan: Callable, audit: Callable, fail: Callable, now: Callable,
                             sha256_bytes: Callable):
    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    def creator_game(user_id: str, game_id: str):
        row = db.one('SELECT * FROM games WHERE game_id=? AND creator_id=?', (game_id, user_id))
        if not row:
            fail('game_not_found', 'Game not found', 404)
        return row

    def admin_user(authorization: str | None):
        user = current_user(authorization)
        if user['role'] not in {'admin', 'platform_owner'}:
            fail('forbidden', 'Admin access required', 403)
        return user

    @app.post('/api/v1/auth/logout-all')
    def logout_all(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        db.execute('UPDATE sessions SET revoked_at=? WHERE user_id=? AND revoked_at=0', (now(), user['id']))
        audit(user['id'], 'logout_all', 'user', user['id'])
        return {'ok': True}

    @app.post('/api/v1/admin/bootstrap')
    def admin_bootstrap(x_owner_bootstrap: str | None = Header(default=None), authorization: str | None = Header(default=None)):
        if not settings.owner_bootstrap_token or x_owner_bootstrap != settings.owner_bootstrap_token:
            fail('invalid_bootstrap', 'Invalid owner bootstrap token', 403)
        user = current_user(authorization)
        db.execute("UPDATE users SET role='platform_owner',updated_at=? WHERE id=?", (now(), user['id']))
        cp = creator_profile(user['id'])
        if cp:
            db.execute("UPDATE creator_profiles SET plan_id='internal_unlimited',billing_exempt=1 WHERE user_id=?", (user['id'],))
        audit(user['id'], 'owner_bootstrap', 'user', user['id'])
        return {'ok': True, 'role': 'platform_owner'}

    @app.post('/api/v1/creator/games/{game_id}/builds')
    async def upload_build(game_id: str, version: str = Form(...), archive: UploadFile = File(...),
                           authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        cp = creator_profile(user['id'])
        if not cp:
            fail('creator_required', 'Creator account required', 403)
        creator_game(user['id'], game_id)
        plan = effective_plan(user['id']) or {}
        limits = plan.get('limits') or {}
        count = db.one('SELECT COUNT(*) AS n FROM game_builds WHERE game_id=?', (game_id,))['n']
        max_builds = limits.get('max_builds_per_game')
        if max_builds is not None and count >= max_builds:
            fail('plan_limit', 'Build limit reached for current plan', 403)
        data = await archive.read()
        max_upload = limits.get('max_upload_bytes')
        if max_upload is not None and len(data) > max_upload:
            fail('upload_too_large', 'Upload exceeds current plan limit', 413)
        try:
            manifest = scanner.validate_zip(data)
        except ValueError as exc:
            fail('unsafe_archive', str(exc), 400)
        scan = scanner.scan(data)
        bid = 'build_' + uuid.uuid4().hex
        try:
            archive_ref = storage.store_archive(bid, data)
        except Exception:
            fail('storage_unavailable', 'Persistent storage is unavailable', 503)
        status = 'READY_FOR_REVIEW' if scan.status == 'CLEAN' else 'QUARANTINED'
        t = now()
        db.execute('''INSERT INTO game_builds(build_id,game_id,creator_id,version,status,archive_path,manifest_json,
                    compressed_bytes,uncompressed_bytes,file_count,sha256,scan_status,created_at,published_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)''',
                   (bid, game_id, user['id'], version[:40], status, archive_ref, json.dumps(manifest, separators=(',', ':')),
                    len(data), manifest['uncompressed_bytes'], manifest['file_count'], sha256_bytes(data), scan.status, t))
        db.execute('INSERT INTO security_scans(scan_id,build_id,engine,status,details,created_at) VALUES(?,?,?,?,?,?)',
                   ('scan_' + uuid.uuid4().hex, bid, scan.engine, scan.status, scan.details[:2000], t))
        audit(user['id'], 'build_uploaded', 'build', bid, {'scan_status': scan.status})
        return {'build_id': bid, 'scan_status': scan.status, 'status': status, 'version': version}

    @app.get('/api/v1/creator/games/{game_id}/builds')
    def list_builds(game_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        creator_game(user['id'], game_id)
        rows = db.all('''SELECT build_id,version,status,compressed_bytes,uncompressed_bytes,file_count,sha256,scan_status,created_at,published_at
                         FROM game_builds WHERE game_id=? AND creator_id=? ORDER BY created_at DESC''', (game_id, user['id']))
        return {'builds': rows}

    @app.post('/api/v1/creator/builds/{build_id}/publish')
    def publish_build(build_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        build = db.one('SELECT * FROM game_builds WHERE build_id=? AND creator_id=?', (build_id, user['id']))
        if not build:
            fail('build_not_found', 'Build not found', 404)
        if build['scan_status'] != 'CLEAN':
            fail('build_not_clean', 'Only clean builds can be published', 409)
        try:
            data = storage.read_archive(build['archive_path'])
            storage.publish_zip(build['game_id'], build_id, data, scanner)
        except ValueError:
            fail('unsafe_archive', 'Published archive failed path validation', 400)
        except Exception:
            fail('storage_unavailable', 'Persistent storage is unavailable', 503)
        t = now()
        db.execute("UPDATE game_builds SET status='PUBLISHED',published_at=? WHERE build_id=?", (t, build_id))
        db.execute("UPDATE games SET status='PUBLISHED',published_build_id=?,updated_at=? WHERE game_id=? AND creator_id=?",
                   (build_id, t, build['game_id'], user['id']))
        audit(user['id'], 'build_published', 'build', build_id)
        return {'ok': True, 'build_id': build_id}

    @app.get('/play/{slug}/')
    @app.get('/play/{slug}/{asset_path:path}')
    def play_game(slug: str, asset_path: str = 'index.html'):
        game = db.one("SELECT game_id,published_build_id FROM games WHERE slug=? AND status='PUBLISHED' AND visibility='PUBLIC'", (slug,))
        if not game or not game['published_build_id']:
            fail('game_not_found', 'Published game not found', 404)
        try:
            asset = storage.get_published(game['game_id'], game['published_build_id'], asset_path or 'index.html')
        except ValueError:
            fail('invalid_path', 'Invalid asset path', 400)
        except Exception:
            fail('storage_unavailable', 'Persistent storage is unavailable', 503)
        if not asset:
            fail('asset_not_found', 'Asset not found', 404)
        data, media_type = asset
        return Response(content=data, media_type=media_type, headers={'Cache-Control': 'public, max-age=300'})

    @app.get('/api/v1/games/{game_id}/save')
    def get_save(game_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        row = db.one('SELECT save_version,revision,save_json,updated_at FROM game_saves WHERE user_id=? AND game_id=?', (user['id'], game_id))
        if not row:
            return {'save_version': 1, 'revision': 0, 'state': {}, 'updated_at': 0}
        return {'save_version': row['save_version'], 'revision': row['revision'], 'state': json.loads(row['save_json']), 'updated_at': row['updated_at']}

    @app.put('/api/v1/games/{game_id}/save')
    def put_save(game_id: str, body: SaveIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        existing = db.one('SELECT revision FROM game_saves WHERE user_id=? AND game_id=?', (user['id'], game_id))
        current = existing['revision'] if existing else 0
        if body.revision != current:
            fail('revision_conflict', 'Save revision conflict', 409)
        next_revision = current + 1
        db.execute('''INSERT INTO game_saves(user_id,game_id,save_version,revision,save_json,updated_at) VALUES(?,?,?,?,?,?)
                      ON CONFLICT(user_id,game_id) DO UPDATE SET save_version=excluded.save_version,revision=excluded.revision,
                      save_json=excluded.save_json,updated_at=excluded.updated_at''',
                   (user['id'], game_id, body.save_version, next_revision, json.dumps(body.state, separators=(',', ':')), now()))
        return {'ok': True, 'revision': next_revision}

    @app.post('/api/v1/reports')
    def create_report(body: ReportIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if not body.game_id and not body.creator_id:
            fail('report_target_required', 'Game or creator is required', 400)
        rid = 'report_' + uuid.uuid4().hex
        db.execute('INSERT INTO reports(report_id,reporter_id,game_id,creator_id,category,details,status,created_at) VALUES(?,?,?,?,?,?,?,?)',
                   (rid, user['id'], body.game_id, body.creator_id, body.category, body.details, 'OPEN', now()))
        audit(user['id'], 'report_created', 'report', rid)
        return {'report_id': rid, 'status': 'OPEN'}

    @app.get('/api/v1/admin/overview')
    def admin_overview(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {
            'users': db.one('SELECT COUNT(*) AS n FROM users')['n'],
            'creators': db.one('SELECT COUNT(*) AS n FROM creator_profiles')['n'],
            'games': db.one('SELECT COUNT(*) AS n FROM games')['n'],
            'published': db.one("SELECT COUNT(*) AS n FROM games WHERE status='PUBLISHED'")['n'],
            'open_reports': db.one("SELECT COUNT(*) AS n FROM reports WHERE status='OPEN'")['n'],
            'orders': db.one('SELECT COUNT(*) AS n FROM orders')['n'],
        }

    @app.get('/api/v1/admin/moderation')
    def admin_moderation(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {'reports': db.all("SELECT * FROM reports WHERE status='OPEN' ORDER BY created_at DESC LIMIT 100")}

    @app.get('/api/v1/admin/payments')
    def admin_payments(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        orders = db.all('''SELECT o.order_id,o.expected_amount,o.asset,o.network,o.status,o.transaction_hash,o.created_at,
                           u.display_name,p.label AS product_label
                           FROM orders o JOIN users u ON u.id=o.user_id JOIN products p ON p.product_id=o.product_id
                           ORDER BY o.created_at DESC LIMIT 200''')
        return {'orders': orders}
