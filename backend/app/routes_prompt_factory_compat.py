from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any, Callable

from fastapi import Header
from pydantic import BaseModel, Field


class PromptFactoryDbProxy:
    """Transparent DB proxy that enforces privacy and seller scoping in legacy advanced queries."""

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

    def one(self, sql: str, args=()):
        if "FROM prompt_coupons WHERE code=?" in sql and "listing_id IS NULL" in sql and len(args) == 4:
            listing_id = args[3]
            listing = self._db.one("SELECT seller_id FROM prompt_listings WHERE listing_id=?", (listing_id,))
            if not listing:
                return None
            sql = sql.replace("WHERE code=? AND", "WHERE code=? AND seller_id=? AND", 1)
            args = (args[0], listing['seller_id'], args[1], args[2], args[3])
        return self._db.one(sql, args)


class ModerationReportCompatIn(BaseModel):
    target_type: str = Field(min_length=3, max_length=30)
    target_id: str = Field(min_length=4, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    details: str = Field(min_length=4, max_length=4000)


class ReferralCompatIn(BaseModel):
    code: str = Field(min_length=4, max_length=40)


class AnalyticsCompatIn(BaseModel):
    event_type: str = Field(min_length=2, max_length=60)
    prompt_id: str | None = Field(default=None, max_length=80)
    listing_id: str | None = Field(default=None, max_length=80)
    creator_id: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


def register_prompt_factory_compat_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    """Register security overrides before the broader advanced router."""

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

    @app.post('/api/v1/prompt-factory/referrals/attribute')
    def attribute_referral_compat(body: ReferralCompatIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        existing = db.one('SELECT * FROM prompt_referral_attributions WHERE referred_user_id=?', (user['id'],))
        if existing:
            return {'attributed': True, 'existing': True}
        prior_prompt = db.one("SELECT purchase_id FROM prompt_purchases WHERE buyer_id=? AND status='CONFIRMED' LIMIT 1", (user['id'],))
        prior_collection = db.one("SELECT sale_id FROM prompt_collection_sales WHERE buyer_id=? AND status='CONFIRMED' LIMIT 1", (user['id'],))
        if prior_prompt or prior_collection:
            fail('referral_not_eligible', 'Referral attribution must happen before the first Prompt Factory purchase', 409)
        code = body.code.strip().upper()
        ref = db.one('SELECT * FROM prompt_referral_codes WHERE code=?', (code,))
        if not ref or ref['user_id'] == user['id']:
            fail('invalid_referral', 'Invalid referral code', 400)
        db.execute(
            'INSERT INTO prompt_referral_attributions(referred_user_id,affiliate_user_id,code,created_at) VALUES(?,?,?,?)',
            (user['id'], ref['user_id'], code, now()),
        )
        audit(user['id'], 'prompt_referral_attributed', 'user', user['id'], {'affiliate_user_id': ref['user_id']})
        return {'attributed': True, 'existing': False}

    @app.post('/api/v1/prompt-factory/analytics/events')
    def analytics_event_compat(body: AnalyticsCompatIn, authorization: str | None = Header(default=None)):
        user_id = None
        if authorization:
            try:
                user_id = current_user(authorization)['id']
            except Exception:
                user_id = None
        prompt_id = body.prompt_id
        listing_id = body.listing_id
        creator_id = None
        if listing_id:
            listing = db.one(
                "SELECT seller_id,prompt_id FROM prompt_listings WHERE listing_id=? AND status='PUBLISHED'",
                (listing_id,),
            )
            if not listing:
                fail('listing_not_found', 'Published listing not found', 404)
            creator_id = listing['seller_id']
            prompt_id = listing['prompt_id']
        elif prompt_id:
            prompt = db.one(
                "SELECT owner_id FROM prompts WHERE prompt_id=? AND status='ACTIVE' AND visibility IN ('PUBLIC','FOR_SALE')",
                (prompt_id,),
            )
            if not prompt:
                fail('prompt_not_found', 'Public prompt not found', 404)
            creator_id = prompt['owner_id']
        elif body.creator_id:
            creator = db.one('SELECT user_id FROM prompt_seller_profiles WHERE user_id=? AND blocked=0', (body.creator_id,))
            if not creator:
                fail('creator_not_found', 'Creator not found', 404)
            creator_id = creator['user_id']
        event_id = 'pae_' + uuid.uuid4().hex
        db.execute(
            'INSERT INTO prompt_analytics_events(event_id,user_id,event_type,prompt_id,listing_id,creator_id,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
            (event_id, user_id, body.event_type.strip().upper(), prompt_id, listing_id, creator_id, json.dumps(body.metadata, separators=(',', ':'))[:8000], now()),
        )
        return {'ok': True}

    @app.get('/api/v1/prompt-factory/creator/analytics')
    def creator_analytics_compat(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        uid = user['id']
        t = now()

        def sale_window(seconds: int):
            cutoff = t - seconds
            prompts = db.one(
                "SELECT COUNT(*) AS sales,COALESCE(SUM(gross_usd),0) AS gross,COALESCE(SUM(seller_amount_usd),0) AS net,COALESCE(SUM(platform_fee_usd),0) AS fees FROM prompt_purchases WHERE seller_id=? AND status='CONFIRMED' AND created_at>=?",
                (uid, cutoff),
            )
            collections = db.one(
                "SELECT COUNT(*) AS sales,COALESCE(SUM(gross_usd),0) AS gross,COALESCE(SUM(seller_amount_usd),0) AS net,COALESCE(SUM(platform_fee_usd),0) AS fees FROM prompt_collection_sales WHERE seller_id=? AND status='CONFIRMED' AND created_at>=?",
                (uid, cutoff),
            )
            return {
                'sales': int(prompts['sales']) + int(collections['sales']),
                'gross': Decimal(str(prompts['gross'])) + Decimal(str(collections['gross'])),
                'net': Decimal(str(prompts['net'])) + Decimal(str(collections['net'])),
                'fees': Decimal(str(prompts['fees'])) + Decimal(str(collections['fees'])),
            }

        views = db.one("SELECT COUNT(*) AS n FROM prompt_analytics_events WHERE creator_id=? AND event_type='VIEW'", (uid,))['n']
        favorites = db.one('SELECT COUNT(*) AS n FROM prompt_favorites f JOIN prompts p ON p.prompt_id=f.prompt_id WHERE p.owner_id=?', (uid,))['n']
        reviews = db.one('SELECT COUNT(*) AS n,COALESCE(AVG(r.rating),0) AS avg FROM prompt_reviews r JOIN prompts p ON p.prompt_id=r.prompt_id WHERE p.owner_id=?', (uid,))
        lifetime = sale_window(100 * 365 * 86400)
        conversion = (float(lifetime['sales']) / float(views) * 100.0) if views else 0.0
        return {
            'today': sale_window(86400),
            'days7': sale_window(7 * 86400),
            'days30': sale_window(30 * 86400),
            'lifetime': lifetime,
            'views': views,
            'favorites': favorites,
            'reviews': reviews,
            'conversion_rate': round(conversion, 2),
        }

    return PromptFactoryDbProxy(db)
