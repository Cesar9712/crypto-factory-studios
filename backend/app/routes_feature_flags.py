from __future__ import annotations

from typing import Callable

from fastapi import Header
from pydantic import BaseModel


FEATURE_DEFAULTS = {
    'cryptoquest_enabled': False,
    'crypto_factory_game_enabled': False,
}


class FeatureFlagUpdate(BaseModel):
    enabled: bool


def register_feature_flag_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    db.execute('''CREATE TABLE IF NOT EXISTS platform_feature_flags(
        feature_key TEXT PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 0,
        updated_at BIGINT NOT NULL,
        updated_by TEXT
    )''')
    for key, enabled in FEATURE_DEFAULTS.items():
        db.execute('INSERT OR IGNORE INTO platform_feature_flags(feature_key,enabled,updated_at,updated_by) VALUES(?,?,?,?)',
                   (key, 1 if enabled else 0, now(), 'system'))

    def flags_payload():
        rows = db.all('SELECT feature_key,enabled,updated_at,updated_by FROM platform_feature_flags ORDER BY feature_key')
        flags = {row['feature_key']: bool(row['enabled']) for row in rows}
        for key, default in FEATURE_DEFAULTS.items():
            flags.setdefault(key, default)
        return {
            'features': flags,
            'games_hidden': not flags['cryptoquest_enabled'] and not flags['crypto_factory_game_enabled'],
            'source': 'platform_feature_flags',
        }

    def admin_user(authorization: str | None):
        user, _ = session_user(authorization)
        if user['role'] not in {'admin', 'platform_owner'}:
            fail('forbidden', 'Admin access required', 403)
        return user

    @app.get('/api/v1/platform/features')
    def get_platform_features():
        return flags_payload()

    @app.put('/api/v1/admin/platform/features/{feature_key}')
    def set_platform_feature(feature_key: str, body: FeatureFlagUpdate, authorization: str | None = Header(default=None)):
        if feature_key not in FEATURE_DEFAULTS:
            fail('unknown_feature', 'Unknown platform feature flag', 404)
        user = admin_user(authorization)
        db.execute('''INSERT INTO platform_feature_flags(feature_key,enabled,updated_at,updated_by)
                      VALUES(?,?,?,?)
                      ON CONFLICT(feature_key) DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at,updated_by=excluded.updated_by''',
                   (feature_key, 1 if body.enabled else 0, now(), user['id']))
        audit(user['id'], 'platform_feature_updated', 'platform_feature', feature_key, {'enabled': body.enabled})
        return flags_payload()
