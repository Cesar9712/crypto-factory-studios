from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Header
from pydantic import BaseModel, Field


class PromptFactoryDbProxy:
    """Transparent DB proxy that keeps private vault content out of cross-user duplicate scans."""

    def __init__(self, db):
        self._db = db

    def __getattr__(self, name):
        return getattr(self._db, name)

    def all(self, sql: str, args=()):
        marker = "FROM prompts WHERE prompt_id<>? AND status='ACTIVE' AND category=?"
        if marker in sql:
            sql = sql.replace(
                marker,
                "FROM prompts WHERE prompt_id<>? AND status='ACTIVE' AND visibility IN ('PUBLIC','FOR_SALE') AND category=?",
            )
        return self._db.all(sql, args)


class ModerationReportCompatIn(BaseModel):
    target_type: str = Field(min_length=3, max_length=30)
    target_id: str = Field(min_length=4, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    details: str = Field(min_length=4, max_length=4000)


def register_prompt_factory_compat_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    """Register compatibility/security overrides before the broader advanced router."""

    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    @app.post('/api/v1/prompt-factory/moderation/reports')
    def report_content_compat(body: ModerationReportCompatIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        target_type = body.target_type.strip().upper()
        if target_type not in {'PROMPT', 'LISTING', 'CREATOR', 'COLLECTION'}:
            fail('invalid_target', 'Invalid moderation target', 400)
        category = body.category.strip().upper()
        report_id = 'pmr_' + uuid.uuid4().hex
        t = now()
        db.execute(
            "INSERT INTO prompt_moderation_reports(report_id,reporter_id,target_type,target_id,category,details,status,created_at,updated_at) VALUES(?,?,?,?,?,?,'OPEN',?,?)",
            (report_id, user['id'], target_type, body.target_id, category, body.details.strip(), t, t),
        )
        audit(user['id'], 'prompt_content_reported', target_type.lower(), body.target_id, {'category': category})
        return {'report_id': report_id, 'status': 'OPEN'}

    return PromptFactoryDbProxy(db)
