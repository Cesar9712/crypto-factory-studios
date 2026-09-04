from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher
from typing import Any, Callable
from urllib.parse import urlparse

from fastapi import Header, Query
from pydantic import BaseModel, Field


ADVANCED_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS prompt_dynamic_categories(
        category_id TEXT PRIMARY KEY,label TEXT NOT NULL UNIQUE,slug TEXT NOT NULL UNIQUE,active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_seller_profiles(
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,username TEXT NOT NULL UNIQUE,avatar_url TEXT NOT NULL DEFAULT '',
        bio TEXT NOT NULL DEFAULT '',badges_json TEXT NOT NULL DEFAULT '[]',blocked INTEGER NOT NULL DEFAULT 0,
        joined_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_creator_follows(
        follower_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,creator_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,PRIMARY KEY(follower_id,creator_id))""",
    """CREATE TABLE IF NOT EXISTS prompt_saved_searches(
        search_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,label TEXT NOT NULL,
        query_json TEXT NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_notifications(
        notification_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,type TEXT NOT NULL,
        title TEXT NOT NULL,body TEXT NOT NULL DEFAULT '',target_url TEXT NOT NULL DEFAULT '',source_key TEXT NOT NULL UNIQUE,
        read_at INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_assets(
        asset_id TEXT PRIMARY KEY,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        kind TEXT NOT NULL,label TEXT NOT NULL DEFAULT '',url TEXT NOT NULL,media_type TEXT NOT NULL DEFAULT '',position INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_listing_license_options(
        option_id TEXT PRIMARY KEY,listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
        license_type TEXT NOT NULL,price_usd TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,
        UNIQUE(listing_id,license_type))""",
    """CREATE TABLE IF NOT EXISTS prompt_promotions(
        promotion_id TEXT PRIMARY KEY,listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
        seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,label TEXT NOT NULL,sale_price_usd TEXT NOT NULL,
        starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_coupons(
        coupon_id TEXT PRIMARY KEY,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,listing_id TEXT REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
        code TEXT NOT NULL UNIQUE,discount_type TEXT NOT NULL,discount_value TEXT NOT NULL,max_uses INTEGER,uses_count INTEGER NOT NULL DEFAULT 0,
        starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_checkout_intents(
        product_id TEXT PRIMARY KEY,buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
        coupon_id TEXT REFERENCES prompt_coupons(coupon_id) ON DELETE SET NULL,license_type TEXT NOT NULL,amount_usd TEXT NOT NULL,
        created_at INTEGER NOT NULL,redeemed_order_id TEXT UNIQUE)""",
    """CREATE TABLE IF NOT EXISTS prompt_collection_offers(
        offer_id TEXT PRIMARY KEY,collection_id TEXT NOT NULL REFERENCES prompt_collections(collection_id) ON DELETE CASCADE,
        seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,product_id TEXT NOT NULL UNIQUE REFERENCES products(product_id),
        pricing_model TEXT NOT NULL,price_usd TEXT NOT NULL,license_type TEXT NOT NULL DEFAULT 'PERSONAL',duration_days INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'PUBLISHED',sales_count INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_collection_access(
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,offer_id TEXT NOT NULL REFERENCES prompt_collection_offers(offer_id) ON DELETE CASCADE,
        collection_id TEXT NOT NULL REFERENCES prompt_collections(collection_id) ON DELETE CASCADE,order_id TEXT UNIQUE,
        license_type TEXT NOT NULL,expires_at INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,PRIMARY KEY(user_id,offer_id))""",
    """CREATE TABLE IF NOT EXISTS prompt_collection_sales(
        sale_id TEXT PRIMARY KEY,offer_id TEXT NOT NULL REFERENCES prompt_collection_offers(offer_id) ON DELETE CASCADE,
        buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        order_id TEXT NOT NULL UNIQUE,gross_usd NUMERIC NOT NULL,platform_fee_usd NUMERIC NOT NULL,seller_amount_usd NUMERIC NOT NULL,
        status TEXT NOT NULL DEFAULT 'CONFIRMED',created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_moderation_reports(
        report_id TEXT PRIMARY KEY,reporter_id TEXT REFERENCES users(id) ON DELETE SET NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,
        category TEXT NOT NULL,details TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',resolution TEXT NOT NULL DEFAULT '',
        created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_duplicate_flags(
        flag_id TEXT PRIMARY KEY,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,matched_prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
        similarity REAL NOT NULL,exact_match INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'OPEN',created_at INTEGER NOT NULL,
        UNIQUE(prompt_id,matched_prompt_id))""",
    """CREATE TABLE IF NOT EXISTS prompt_disputes(
        dispute_id TEXT PRIMARY KEY,purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
        buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,seller_id TEXT REFERENCES users(id) ON DELETE SET NULL,
        reason TEXT NOT NULL,details TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',frozen_usd NUMERIC NOT NULL DEFAULT 0,
        resolution TEXT NOT NULL DEFAULT '',refund_tx TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_payouts(
        payout_id TEXT PRIMARY KEY,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,amount_usd NUMERIC NOT NULL,
        fee_usd NUMERIC NOT NULL,net_usd NUMERIC NOT NULL,method TEXT NOT NULL,destination TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',
        payout_tx TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_referral_codes(
        code TEXT PRIMARY KEY,user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_referral_attributions(
        referred_user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,affiliate_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code TEXT NOT NULL REFERENCES prompt_referral_codes(code),created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_referral_earnings(
        earning_id TEXT PRIMARY KEY,purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
        affiliate_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,amount_usd NUMERIC NOT NULL,created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_analytics_events(
        event_id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id) ON DELETE SET NULL,event_type TEXT NOT NULL,prompt_id TEXT REFERENCES prompts(prompt_id) ON DELETE SET NULL,
        listing_id TEXT REFERENCES prompt_listings(listing_id) ON DELETE SET NULL,creator_id TEXT REFERENCES users(id) ON DELETE SET NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_advanced_entitlement_events(
        order_id TEXT PRIMARY KEY REFERENCES orders(order_id) ON DELETE CASCADE,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        entitlement_key TEXT NOT NULL,applied_at INTEGER NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_pf_notify_user ON prompt_notifications(user_id,created_at)",
    "CREATE INDEX IF NOT EXISTS idx_pf_analytics_creator ON prompt_analytics_events(creator_id,created_at)",
    "CREATE INDEX IF NOT EXISTS idx_pf_reports_status ON prompt_moderation_reports(status,created_at)",
    "CREATE INDEX IF NOT EXISTS idx_pf_payouts_status ON prompt_payouts(status,created_at)",
    "CREATE INDEX IF NOT EXISTS idx_pf_collection_access_user ON prompt_collection_access(user_id,expires_at)",
]

ADVANCED_SETTINGS = {
    "withdrawal_fee_usd": "0.50",
    "referral_bps": "300",
    "seller_registration_enabled": "true",
    "notifications_enabled": "true",
    "duplicate_similarity_threshold": "0.92",
    "currency_settings": json.dumps(["USD", "USDT", "USDC", "BNB", "ETH", "SOL"]),
    "withdrawals_enabled": "true",
}


class SellerProfileIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    avatar_url: str = Field(default="", max_length=1000)
    bio: str = Field(default="", max_length=2000)


class SavedSearchIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    query: dict[str, Any] = Field(default_factory=dict)


class AssetIn(BaseModel):
    kind: str = Field(min_length=3, max_length=20)
    label: str = Field(default="", max_length=120)
    url: str = Field(min_length=4, max_length=2000)
    media_type: str = Field(default="", max_length=120)
    position: int = Field(default=0, ge=0, le=1000)


class LicenseOptionIn(BaseModel):
    license_type: str = Field(min_length=4, max_length=30)
    price_usd: str = Field(max_length=20)
    active: bool = True


class AdvancedListingIn(BaseModel):
    price_usd: str = Field(default="0.00", max_length=20)
    pricing_model: str = Field(default="FIXED", max_length=40)
    license_type: str = Field(default="PERSONAL", max_length=30)
    preview_text: str = Field(default="", max_length=3000)
    examples: list[str] = Field(default_factory=list)


class CheckoutIn(BaseModel):
    amount_usd: str | None = Field(default=None, max_length=20)
    coupon_code: str = Field(default="", max_length=40)
    license_type: str = Field(default="PERSONAL", max_length=30)


class PromotionIn(BaseModel):
    label: str = Field(min_length=2, max_length=100)
    sale_price_usd: str = Field(max_length=20)
    starts_at: int = Field(ge=0)
    ends_at: int = Field(ge=0)


class CouponIn(BaseModel):
    listing_id: str | None = Field(default=None, max_length=80)
    code: str = Field(min_length=3, max_length=40)
    discount_type: str = Field(default="PERCENT", max_length=20)
    discount_value: str = Field(max_length=20)
    max_uses: int | None = Field(default=None, ge=1, le=1000000)
    starts_at: int = Field(ge=0)
    ends_at: int = Field(ge=0)


class CollectionOfferIn(BaseModel):
    pricing_model: str = Field(default="BUNDLE", max_length=40)
    price_usd: str = Field(max_length=20)
    license_type: str = Field(default="PERSONAL", max_length=30)
    duration_days: int = Field(default=0, ge=0, le=3650)


class ReportIn(BaseModel):
    target_type: str = Field(min_length=3, max_length=30)
    target_id: str = Field(min_length=4, max_length=100)
    category: str = Field(min_length=3, max_length=50)
    details: str = Field(min_length=4, max_length=4000)


class DisputeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=80)
    details: str = Field(min_length=4, max_length=4000)


class DisputeResolveIn(BaseModel):
    resolution: str = Field(min_length=5, max_length=30)
    refund_tx: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)


class PayoutIn(BaseModel):
    amount_usd: str = Field(max_length=20)
    method: str = Field(min_length=2, max_length=40)
    destination: str = Field(min_length=4, max_length=300)


class PayoutStatusIn(BaseModel):
    status: str = Field(min_length=4, max_length=20)
    payout_tx: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)


class ReferralAttributeIn(BaseModel):
    code: str = Field(min_length=4, max_length=40)


class AnalyticsIn(BaseModel):
    event_type: str = Field(min_length=2, max_length=60)
    prompt_id: str | None = Field(default=None, max_length=80)
    listing_id: str | None = Field(default=None, max_length=80)
    creator_id: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CategoryIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    active: bool = True
    sort_order: int = Field(default=0, ge=0, le=10000)


class PlanAdminIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    price_usd: str = Field(max_length=20)
    max_prompts: int | None = Field(default=None, ge=1, le=1000000)
    commission_bps: int = Field(ge=0, le=10000)
    features: list[str] = Field(default_factory=list)
    active: bool = True


class ImportIn(BaseModel):
    prompts: list[dict[str, Any]] = Field(default_factory=list, max_length=250)


class ModerationIn(BaseModel):
    status: str = Field(min_length=4, max_length=20)
    resolution: str = Field(default="", max_length=2000)


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:72] or "item"


def _safe_url(value: str) -> bool:
    if not value:
        return True
    try:
        p = urlparse(value)
        return p.scheme in {"https", "http"} and bool(p.netloc)
    except Exception:
        return False


def _norm_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _hash_prompt(prompt_text: str, system_text: str, vars_json: str) -> str:
    raw = (prompt_text + "\n---SYSTEM---\n" + system_text + "\n---VARS---\n" + vars_json).encode()
    return hashlib.sha256(raw).hexdigest()


def ensure_advanced_schema(db, now: Callable) -> None:
    for statement in ADVANCED_SCHEMA:
        db.execute(statement)
    t = now()
    for key, value in ADVANCED_SETTINGS.items():
        db.execute(
            "INSERT INTO prompt_platform_settings(setting_key,setting_value,updated_at) VALUES(?,?,?) ON CONFLICT(setting_key) DO NOTHING",
            (key, value, t),
        )
    seed = [
        "AI AGENTS", "MARKETING", "SOCIAL MEDIA", "BUSINESS", "CODING", "WEB DEVELOPMENT", "GAME DEVELOPMENT", "WEB3", "CRYPTO",
        "DESIGN", "IMAGE GENERATION", "VIDEO GENERATION", "CONTENT CREATION", "SEO", "YOUTUBE", "AUTOMATION", "PRODUCTIVITY",
        "EDUCATION", "RESEARCH", "DATA ANALYSIS", "SALES", "COPYWRITING", "E-COMMERCE", "OTHER",
    ]
    for i, label in enumerate(seed):
        cid = "pcat_" + hashlib.sha256(label.encode()).hexdigest()[:16]
        db.execute(
            "INSERT INTO prompt_dynamic_categories(category_id,label,slug,active,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(category_id) DO NOTHING",
            (cid, label, _slug(label), 1, i, t, t),
        )


def register_prompt_factory_advanced_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    ensure_advanced_schema(db, now)

    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    def admin_user(authorization: str | None):
        user = current_user(authorization)
        if user["role"] not in {"admin", "platform_owner"}:
            fail("forbidden", "Admin access required", 403)
        return user

    def setting(key: str, default: str = "") -> str:
        row = db.one("SELECT setting_value FROM prompt_platform_settings WHERE setting_key=?", (key,))
        return str(row["setting_value"]) if row else default

    def seller_profile(user_id: str) -> dict | None:
        return db.one("SELECT * FROM prompt_seller_profiles WHERE user_id=?", (user_id,))

    def assert_seller(user_id: str) -> dict:
        row = seller_profile(user_id)
        if not row:
            fail("seller_profile_required", "Create your Prompt Factory seller profile first", 403)
        if int(row.get("blocked") or 0):
            fail("seller_blocked", "Seller account is blocked from marketplace actions", 403)
        return row

    def owner_prompt(user_id: str, prompt_id: str) -> dict:
        row = db.one("SELECT * FROM prompts WHERE prompt_id=? AND owner_id=? AND status<>'ARCHIVED'", (prompt_id, user_id))
        if not row:
            fail("prompt_not_found", "Prompt not found", 404)
        return row

    def capacity(user: dict) -> tuple[int | None, int]:
        t = now()
        membership = db.one("SELECT plan_id FROM prompt_user_plans WHERE user_id=? AND expires_at>?", (user["id"], t))
        plan_id = membership["plan_id"] if membership else ("unlimited" if user.get("role") == "platform_owner" else "free")
        plan = db.one("SELECT max_prompts FROM prompt_plans WHERE plan_id=? AND active=1", (plan_id,)) or {"max_prompts": 10}
        extra = db.one("SELECT extra_slots FROM prompt_user_storage WHERE user_id=?", (user["id"],)) or {"extra_slots": 0}
        used = int((db.one("SELECT COUNT(*) AS n FROM prompts WHERE owner_id=? AND status<>'ARCHIVED'", (user["id"],)) or {"n": 0})["n"])
        limit = None if plan.get("max_prompts") is None else int(plan["max_prompts"]) + int(extra.get("extra_slots") or 0)
        return limit, used

    def notify(user_id: str, kind: str, title: str, body: str, target_url: str, source_key: str):
        if setting("notifications_enabled", "true") != "true":
            return
        db.execute(
            """INSERT INTO prompt_notifications(notification_id,user_id,type,title,body,target_url,source_key,created_at)
               VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_key) DO NOTHING""",
            ("pnot_" + uuid.uuid4().hex, user_id, kind, title, body, target_url, source_key, now()),
        )

    def duplicate_candidates(prompt: dict) -> list[dict]:
        rows = db.all(
            "SELECT prompt_id,owner_id,title,prompt_text,content_hash FROM prompts WHERE prompt_id<>? AND status='ACTIVE' AND category=? ORDER BY updated_at DESC LIMIT 200",
            (prompt["prompt_id"], prompt["category"]),
        )
        base = _norm_text(prompt["prompt_text"])
        threshold = float(setting("duplicate_similarity_threshold", "0.92"))
        out = []
        for row in rows:
            exact = row["content_hash"] == prompt["content_hash"]
            similarity = 1.0 if exact else SequenceMatcher(None, base[:30000], _norm_text(row["prompt_text"])[:30000]).ratio()
            if exact or similarity >= threshold:
                out.append({"prompt_id": row["prompt_id"], "owner_id": row["owner_id"], "title": row["title"], "similarity": round(similarity, 4), "exact_match": exact})
        return out

    def active_price(listing: dict, *, license_type: str, requested: Decimal | None, coupon_code: str = "") -> tuple[Decimal, str | None]:
        t = now()
        base = _money(listing["price_usd"])
        opt = db.one("SELECT price_usd FROM prompt_listing_license_options WHERE listing_id=? AND license_type=? AND active=1", (listing["listing_id"], license_type))
        if opt:
            base = _money(opt["price_usd"])
        promo = db.one(
            "SELECT promotion_id,sale_price_usd FROM prompt_promotions WHERE listing_id=? AND active=1 AND starts_at<=? AND ends_at>=? ORDER BY sale_price_usd ASC LIMIT 1",
            (listing["listing_id"], t, t),
        )
        if promo:
            base = min(base, _money(promo["sale_price_usd"]))
        model = str(listing["pricing_model"]).upper()
        if model == "PAY_WHAT_YOU_WANT":
            if requested is None:
                fail("amount_required", "Choose an amount for this prompt", 400)
            if requested < base:
                fail("amount_too_low", f"Minimum amount is {base}", 400)
            base = requested
        coupon_id = None
        code = coupon_code.strip().upper()
        if code:
            coupon = db.one(
                """SELECT * FROM prompt_coupons WHERE code=? AND active=1 AND starts_at<=? AND ends_at>=?
                   AND (listing_id IS NULL OR listing_id=?)""",
                (code, t, t, listing["listing_id"]),
            )
            if not coupon or (coupon.get("max_uses") is not None and int(coupon["uses_count"]) >= int(coupon["max_uses"])):
                fail("coupon_invalid", "Coupon is invalid or exhausted", 400)
            value = _money(coupon["discount_value"])
            if str(coupon["discount_type"]).upper() == "PERCENT":
                percent = min(Decimal("100"), max(Decimal("0"), value))
                base = (base * (Decimal("100") - percent) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                base = max(Decimal("0.00"), base - value)
            coupon_id = coupon["coupon_id"]
        minimum = _money(setting("minimum_prompt_price_usd", "0.00"))
        maximum = _money(setting("maximum_prompt_price_usd", "1000.00"))
        if base < minimum or base > maximum:
            fail("invalid_price", "Final price is outside marketplace limits", 400)
        return base, coupon_id

    def sync_notifications(user_id: str):
        for row in db.all("SELECT pp.purchase_id,pp.gross_usd,p.title FROM prompt_purchases pp JOIN prompts p ON p.prompt_id=pp.prompt_id WHERE pp.seller_id=? AND pp.status='CONFIRMED' ORDER BY pp.created_at DESC LIMIT 100", (user_id,)):
            notify(user_id, "SALE", "Prompt vendido", f"{row['title']} · ${_money(row['gross_usd'])}", "/prompt-factory#earnings", "sale:" + row["purchase_id"])
        for row in db.all("SELECT r.review_id,r.rating,p.title FROM prompt_reviews r JOIN prompts p ON p.prompt_id=r.prompt_id WHERE p.owner_id=? ORDER BY r.created_at DESC LIMIT 100", (user_id,)):
            notify(user_id, "REVIEW", "Nueva reseña", f"{row['title']} · {row['rating']}/5", "/prompt-factory#earnings", "review:" + row["review_id"])

    @app.get("/api/v1/prompt-factory/categories")
    def categories():
        return {"categories": db.all("SELECT category_id,label,slug,sort_order FROM prompt_dynamic_categories WHERE active=1 ORDER BY sort_order,label")}

    @app.put("/api/v1/prompt-factory/creator/profile")
    def upsert_seller_profile(body: SellerProfileIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if setting("seller_registration_enabled", "true") != "true" and user["role"] not in {"admin", "platform_owner"}:
            fail("seller_registration_disabled", "Seller registration is disabled", 403)
        username = re.sub(r"[^a-zA-Z0-9_.-]", "", body.username.strip())
        if len(username) < 3:
            fail("invalid_username", "Username must contain at least 3 valid characters", 400)
        if not _safe_url(body.avatar_url.strip()):
            fail("invalid_avatar_url", "Avatar URL must be HTTP or HTTPS", 400)
        t = now()
        try:
            db.execute(
                """INSERT INTO prompt_seller_profiles(user_id,username,avatar_url,bio,joined_at,updated_at) VALUES(?,?,?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,avatar_url=excluded.avatar_url,bio=excluded.bio,updated_at=excluded.updated_at""",
                (user["id"], username, body.avatar_url.strip(), body.bio.strip(), t, t),
            )
        except sqlite3.IntegrityError:
            fail("username_taken", "Username is already in use", 409)
        audit(user["id"], "prompt_seller_profile_updated", "user", user["id"])
        return {"profile": seller_profile(user["id"])}

    @app.get("/api/v1/prompt-factory/creators/{username}")
    def public_creator(username: str):
        row = db.one("""SELECT sp.*,u.display_name,u.created_at AS account_created_at FROM prompt_seller_profiles sp
                        JOIN users u ON u.id=sp.user_id WHERE LOWER(sp.username)=LOWER(?) AND sp.blocked=0""", (username,))
        if not row:
            fail("creator_not_found", "Creator not found", 404)
        counts = db.one("SELECT COUNT(*) AS prompts,COALESCE(SUM(sales_count),0) AS sales,COALESCE(AVG(rating_avg),0) AS rating FROM prompt_listings WHERE seller_id=? AND status='PUBLISHED'", (row["user_id"],))
        followers = db.one("SELECT COUNT(*) AS n FROM prompt_creator_follows WHERE creator_id=?", (row["user_id"],))["n"]
        row["badges"] = json.loads(row.pop("badges_json") or "[]")
        row.pop("blocked", None)
        return {"creator": row, "stats": {**counts, "followers": followers}}

    @app.post("/api/v1/prompt-factory/creators/{creator_id}/follow")
    def follow_creator(creator_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if creator_id == user["id"]:
            fail("self_follow", "You cannot follow yourself", 409)
        if not seller_profile(creator_id):
            fail("creator_not_found", "Creator not found", 404)
        existing = db.one("SELECT follower_id FROM prompt_creator_follows WHERE follower_id=? AND creator_id=?", (user["id"], creator_id))
        if existing:
            db.execute("DELETE FROM prompt_creator_follows WHERE follower_id=? AND creator_id=?", (user["id"], creator_id))
            return {"following": False}
        db.execute("INSERT INTO prompt_creator_follows(follower_id,creator_id,created_at) VALUES(?,?,?)", (user["id"], creator_id, now()))
        notify(creator_id, "FOLLOW", "Nuevo seguidor", f"{user['display_name']} empezó a seguirte", "/prompt-factory#earnings", "follow:" + user["id"] + ":" + creator_id)
        return {"following": True}

    @app.get("/api/v1/prompt-factory/following")
    def following(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all("""SELECT sp.user_id,sp.username,sp.avatar_url,sp.bio,f.created_at FROM prompt_creator_follows f
                         JOIN prompt_seller_profiles sp ON sp.user_id=f.creator_id WHERE f.follower_id=? ORDER BY f.created_at DESC""", (user["id"],))
        return {"following": rows}

    @app.post("/api/v1/prompt-factory/saved-searches")
    def save_search(body: SavedSearchIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        sid = "pss_" + uuid.uuid4().hex
        t = now()
        db.execute("INSERT INTO prompt_saved_searches(search_id,user_id,label,query_json,created_at,updated_at) VALUES(?,?,?,?,?,?)", (sid, user["id"], body.label.strip(), json.dumps(body.query, separators=(",", ":"))[:8000], t, t))
        return {"search_id": sid}

    @app.get("/api/v1/prompt-factory/saved-searches")
    def saved_searches(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all("SELECT * FROM prompt_saved_searches WHERE user_id=? ORDER BY updated_at DESC", (user["id"],))
        for row in rows:
            row["query"] = json.loads(row.pop("query_json") or "{}")
        return {"searches": rows}

    @app.delete("/api/v1/prompt-factory/saved-searches/{search_id}")
    def delete_saved_search(search_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        db.execute("DELETE FROM prompt_saved_searches WHERE search_id=? AND user_id=?", (search_id, user["id"]))
        return {"ok": True}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/assets")
    def add_asset(prompt_id: str, body: AssetIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        owner_prompt(user["id"], prompt_id)
        kind = body.kind.strip().upper()
        if kind not in {"COVER", "IMAGE", "FILE", "EXAMPLE"}:
            fail("invalid_asset_kind", "Invalid asset kind", 400)
        if not _safe_url(body.url.strip()):
            fail("invalid_asset_url", "Asset URL must be HTTP or HTTPS", 400)
        aid = "passet_" + uuid.uuid4().hex
        db.execute("INSERT INTO prompt_assets(asset_id,prompt_id,owner_id,kind,label,url,media_type,position,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (aid, prompt_id, user["id"], kind, body.label.strip(), body.url.strip(), body.media_type.strip(), body.position, now()))
        return {"asset": db.one("SELECT * FROM prompt_assets WHERE asset_id=?", (aid,))}

    @app.get("/api/v1/prompt-factory/prompts/{prompt_id}/assets")
    def prompt_assets(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        owned = db.one("SELECT prompt_id FROM prompts WHERE prompt_id=? AND owner_id=?", (prompt_id, user["id"]))
        bought = db.one("SELECT purchase_id FROM prompt_purchases WHERE prompt_id=? AND buyer_id=? AND status='CONFIRMED'", (prompt_id, user["id"]))
        if not owned and not bought:
            fail("prompt_not_found", "Prompt not found", 404)
        return {"assets": db.all("SELECT asset_id,kind,label,url,media_type,position,created_at FROM prompt_assets WHERE prompt_id=? ORDER BY position,created_at", (prompt_id,))}

    @app.delete("/api/v1/prompt-factory/assets/{asset_id}")
    def delete_asset(asset_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        db.execute("DELETE FROM prompt_assets WHERE asset_id=? AND owner_id=?", (asset_id, user["id"]))
        return {"ok": True}

    @app.get("/api/v1/prompt-factory/export")
    def export_vault(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        prompts = db.all("SELECT * FROM prompts WHERE owner_id=? ORDER BY created_at", (user["id"],))
        for row in prompts:
            row["versions"] = db.all("SELECT version_number,prompt_text,system_instructions,variables_json,changelog,content_hash,created_at FROM prompt_versions WHERE prompt_id=? ORDER BY version_number", (row["prompt_id"],))
            row["assets"] = db.all("SELECT kind,label,url,media_type,position,created_at FROM prompt_assets WHERE prompt_id=? ORDER BY position", (row["prompt_id"],))
        return {"format": "cfs-prompt-vault-v1", "exported_at": now(), "prompts": prompts}

    @app.post("/api/v1/prompt-factory/import")
    def import_vault(body: ImportIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        limit, used = capacity(user)
        imported = 0
        skipped = []
        for raw in body.prompts[:250]:
            if limit is not None and used + imported >= limit:
                skipped.append({"title": str(raw.get("title") or "Untitled"), "reason": "storage_limit"})
                continue
            title = str(raw.get("title") or "Imported prompt").strip()[:120]
            text = str(raw.get("prompt_text") or "").strip()
            if len(title) < 2 or not text:
                skipped.append({"title": title, "reason": "invalid_prompt"})
                continue
            system_text = str(raw.get("system_instructions") or "")[:40000]
            variables = raw.get("variables") if isinstance(raw.get("variables"), list) else []
            vars_json = json.dumps(variables[:50], separators=(",", ":"))
            pid = "prm_" + uuid.uuid4().hex
            base = _slug(title)
            slug = base + "-" + pid[-8:]
            t = now()
            content_hash = _hash_prompt(text[:120000], system_text, vars_json)
            db.execute("""INSERT INTO prompts(prompt_id,owner_id,slug,title,description,prompt_text,system_instructions,category,subcategory,tags_json,ai_models_json,difficulty,language,variables_json,visibility,status,content_hash,created_at,updated_at)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (pid, user["id"], slug, title, str(raw.get("description") or "")[:4000], text[:120000], system_text,
                        str(raw.get("category") or "OTHER")[:60].upper(), str(raw.get("subcategory") or "")[:80],
                        json.dumps((raw.get("tags") or [])[:20], separators=(",", ":")), json.dumps((raw.get("ai_models") or [])[:20], separators=(",", ":")),
                        str(raw.get("difficulty") or "INTERMEDIATE")[:30].upper(), str(raw.get("language") or "en")[:20], vars_json, "PRIVATE", "ACTIVE", content_hash, t, t))
            db.execute("INSERT INTO prompt_versions(version_id,prompt_id,version_number,prompt_text,system_instructions,variables_json,changelog,content_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       ("pv_" + uuid.uuid4().hex, pid, 1, text[:120000], system_text, vars_json, "Imported", content_hash, t))
            imported += 1
        audit(user["id"], "prompt_vault_imported", "user", user["id"], {"imported": imported, "skipped": len(skipped)})
        return {"imported": imported, "skipped": skipped}

    @app.get("/api/v1/prompt-factory/public/{slug}")
    def public_prompt(slug: str):
        row = db.one("SELECT * FROM prompts WHERE slug=? AND status='ACTIVE' AND visibility IN ('PUBLIC','UNLISTED')", (slug,))
        if not row:
            fail("prompt_not_found", "Public prompt not found", 404)
        return {"prompt": row, "assets": db.all("SELECT kind,label,url,media_type,position FROM prompt_assets WHERE prompt_id=? ORDER BY position", (row["prompt_id"],))}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/duplicate-check")
    def duplicate_check(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        prompt = owner_prompt(user["id"], prompt_id)
        return {"matches": duplicate_candidates(prompt)}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/publish-advanced")
    def publish_advanced(prompt_id: str, body: AdvancedListingIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        assert_seller(user["id"])
        prompt = owner_prompt(user["id"], prompt_id)
        model = body.pricing_model.strip().upper()
        if model not in {"FREE", "FIXED", "SALE_PRICE", "PAY_WHAT_YOU_WANT"}:
            fail("pricing_model_invalid", "Use FREE, FIXED, SALE_PRICE or PAY_WHAT_YOU_WANT for individual prompts", 400)
        try:
            price = _money(body.price_usd)
        except Exception:
            fail("invalid_price", "Invalid price", 400)
        if model == "FREE":
            price = Decimal("0.00")
        minimum = _money(setting("minimum_prompt_price_usd", "0.00"))
        maximum = _money(setting("maximum_prompt_price_usd", "1000.00"))
        if price < minimum or price > maximum:
            fail("invalid_price", "Price is outside marketplace limits", 400)
        license_type = body.license_type.strip().upper()
        if license_type not in {"PERSONAL", "COMMERCIAL", "EXTENDED"}:
            fail("invalid_license", "Invalid license", 400)
        membership = db.one("SELECT plan_id FROM prompt_user_plans WHERE user_id=? AND expires_at>?", (user["id"], now()))
        plan_id = membership["plan_id"] if membership else "free"
        plan = db.one("SELECT commission_bps FROM prompt_plans WHERE plan_id=?", (plan_id,)) or {"commission_bps": int(setting("default_commission_bps", "1500"))}
        existing = db.one("SELECT * FROM prompt_listings WHERE prompt_id=?", (prompt_id,))
        listing_id = existing["listing_id"] if existing else "pfl_" + uuid.uuid4().hex
        product_id = existing["product_id"] if existing else "prompt_listing_" + listing_id
        matches = [m for m in duplicate_candidates(prompt) if m["owner_id"] != user["id"]]
        status = "PENDING_REVIEW" if matches or setting("manual_listing_approval", "false") == "true" else "PUBLISHED"
        t = now()
        db.execute("""INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at) VALUES(?,?,?,?,?,?,?)
                      ON CONFLICT(product_id) DO UPDATE SET label=excluded.label,description=excluded.description,price_usd=excluded.price_usd,entitlement_key=excluded.entitlement_key,active=excluded.active""",
                   (product_id, prompt["title"], prompt["description"], str(price), f"prompt_listing:{listing_id}", 1 if status == "PUBLISHED" and model != "FREE" and model != "PAY_WHAT_YOU_WANT" else 0, t))
        db.execute("""INSERT INTO prompt_listings(listing_id,prompt_id,seller_id,product_id,price_usd,pricing_model,license_type,preview_text,examples_json,status,commission_bps,created_at,updated_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(prompt_id) DO UPDATE SET price_usd=excluded.price_usd,pricing_model=excluded.pricing_model,license_type=excluded.license_type,
                      preview_text=excluded.preview_text,examples_json=excluded.examples_json,status=excluded.status,commission_bps=excluded.commission_bps,updated_at=excluded.updated_at""",
                   (listing_id, prompt_id, user["id"], product_id, str(price), model, license_type, body.preview_text.strip(), json.dumps(body.examples[:10], separators=(",", ":")), status, int(plan["commission_bps"]), t, t))
        db.execute("UPDATE prompts SET visibility='FOR_SALE',updated_at=? WHERE prompt_id=?", (t, prompt_id))
        for match in matches:
            fid = "pdf_" + uuid.uuid4().hex
            db.execute("INSERT INTO prompt_duplicate_flags(flag_id,prompt_id,matched_prompt_id,similarity,exact_match,status,created_at) VALUES(?,?,?,?,?,'OPEN',?) ON CONFLICT(prompt_id,matched_prompt_id) DO NOTHING",
                       (fid, prompt_id, match["prompt_id"], match["similarity"], 1 if match["exact_match"] else 0, t))
        audit(user["id"], "prompt_advanced_published", "prompt", prompt_id, {"listing_id": listing_id, "status": status, "duplicate_matches": len(matches)})
        return {"listing": db.one("SELECT * FROM prompt_listings WHERE listing_id=?", (listing_id,)), "duplicate_matches": matches}

    @app.put("/api/v1/prompt-factory/listings/{listing_id}/licenses")
    def set_license_options(listing_id: str, options: list[LicenseOptionIn], authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        listing = db.one("SELECT * FROM prompt_listings WHERE listing_id=? AND seller_id=?", (listing_id, user["id"]))
        if not listing:
            fail("listing_not_found", "Listing not found", 404)
        t = now()
        for option in options[:3]:
            license_type = option.license_type.strip().upper()
            if license_type not in {"PERSONAL", "COMMERCIAL", "EXTENDED"}:
                fail("invalid_license", "Invalid license", 400)
            oid = "plo_" + uuid.uuid4().hex
            db.execute("""INSERT INTO prompt_listing_license_options(option_id,listing_id,license_type,price_usd,active,created_at,updated_at)
                          VALUES(?,?,?,?,?,?,?) ON CONFLICT(listing_id,license_type) DO UPDATE SET price_usd=excluded.price_usd,active=excluded.active,updated_at=excluded.updated_at""",
                       (oid, listing_id, license_type, str(_money(option.price_usd)), 1 if option.active else 0, t, t))
        return {"licenses": db.all("SELECT license_type,price_usd,active FROM prompt_listing_license_options WHERE listing_id=? ORDER BY price_usd", (listing_id,))}

    @app.post("/api/v1/prompt-factory/listings/{listing_id}/checkout-advanced")
    def checkout_advanced(listing_id: str, body: CheckoutIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        listing = db.one("SELECT * FROM prompt_listings WHERE listing_id=? AND status='PUBLISHED'", (listing_id,))
        if not listing:
            fail("listing_not_found", "Listing not found", 404)
        if listing["seller_id"] == user["id"]:
            fail("self_purchase", "You cannot buy your own prompt", 409)
        if db.one("SELECT purchase_id FROM prompt_purchases WHERE buyer_id=? AND listing_id=? AND status='CONFIRMED'", (user["id"], listing_id)):
            return {"already_owned": True, "prompt_id": listing["prompt_id"]}
        license_type = body.license_type.strip().upper()
        if license_type not in {"PERSONAL", "COMMERCIAL", "EXTENDED"}:
            fail("invalid_license", "Invalid license", 400)
        requested = _money(body.amount_usd) if body.amount_usd is not None else None
        amount, coupon_id = active_price(listing, license_type=license_type, requested=requested, coupon_code=body.coupon_code)
        if amount == Decimal("0.00"):
            return {"free": True, "listing_id": listing_id}
        digest = hashlib.sha256(f"{user['id']}:{listing_id}:{license_type}:{amount}:{coupon_id or ''}".encode()).hexdigest()[:20]
        product_id = "prompt_checkout_" + digest
        t = now()
        prompt = db.one("SELECT title,description FROM prompts WHERE prompt_id=?", (listing["prompt_id"],))
        db.execute("""INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at) VALUES(?,?,?,?,?,?,?)
                      ON CONFLICT(product_id) DO UPDATE SET label=excluded.label,description=excluded.description,price_usd=excluded.price_usd,entitlement_key=excluded.entitlement_key,active=excluded.active""",
                   (product_id, prompt["title"], prompt["description"], str(amount), f"prompt_listing:{listing_id}", 1, t))
        db.execute("""INSERT INTO prompt_checkout_intents(product_id,buyer_id,listing_id,coupon_id,license_type,amount_usd,created_at)
                      VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET coupon_id=excluded.coupon_id,license_type=excluded.license_type,amount_usd=excluded.amount_usd,created_at=excluded.created_at""",
                   (product_id, user["id"], listing_id, coupon_id, license_type, str(amount), t))
        return {"product_id": product_id, "price_usd": str(amount), "listing_id": listing_id, "license_type": license_type, "coupon_applied": bool(coupon_id)}

    @app.post("/api/v1/prompt-factory/listings/{listing_id}/promotions")
    def create_promotion(listing_id: str, body: PromotionIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        assert_seller(user["id"])
        listing = db.one("SELECT * FROM prompt_listings WHERE listing_id=? AND seller_id=?", (listing_id, user["id"]))
        if not listing:
            fail("listing_not_found", "Listing not found", 404)
        sale = _money(body.sale_price_usd)
        if sale < Decimal("0") or sale >= _money(listing["price_usd"]):
            fail("invalid_sale_price", "Sale price must be lower than the listing price", 400)
        if body.ends_at <= body.starts_at:
            fail("invalid_window", "Promotion end must be after start", 400)
        pid = "ppromo_" + uuid.uuid4().hex
        t = now()
        db.execute("INSERT INTO prompt_promotions(promotion_id,listing_id,seller_id,label,sale_price_usd,starts_at,ends_at,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (pid, listing_id, user["id"], body.label.strip(), str(sale), body.starts_at, body.ends_at, 1, t, t))
        return {"promotion": db.one("SELECT * FROM prompt_promotions WHERE promotion_id=?", (pid,))}

    @app.post("/api/v1/prompt-factory/coupons")
    def create_coupon(body: CouponIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        assert_seller(user["id"])
        if body.listing_id and not db.one("SELECT listing_id FROM prompt_listings WHERE listing_id=? AND seller_id=?", (body.listing_id, user["id"])):
            fail("listing_not_found", "Listing not found", 404)
        dtype = body.discount_type.strip().upper()
        if dtype not in {"PERCENT", "FIXED"}:
            fail("invalid_discount", "Discount type must be PERCENT or FIXED", 400)
        value = _money(body.discount_value)
        if value <= 0 or (dtype == "PERCENT" and value > 100):
            fail("invalid_discount", "Invalid discount value", 400)
        if body.ends_at <= body.starts_at:
            fail("invalid_window", "Coupon end must be after start", 400)
        code = re.sub(r"[^A-Z0-9_-]", "", body.code.strip().upper())
        cid = "pcpn_" + uuid.uuid4().hex
        t = now()
        try:
            db.execute("INSERT INTO prompt_coupons(coupon_id,seller_id,listing_id,code,discount_type,discount_value,max_uses,starts_at,ends_at,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (cid, user["id"], body.listing_id, code, dtype, str(value), body.max_uses, body.starts_at, body.ends_at, 1, t, t))
        except sqlite3.IntegrityError:
            fail("coupon_exists", "Coupon code already exists", 409)
        return {"coupon": db.one("SELECT * FROM prompt_coupons WHERE coupon_id=?", (cid,))}

    @app.post("/api/v1/prompt-factory/collections/{collection_id}/offer")
    def create_collection_offer(collection_id: str, body: CollectionOfferIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        assert_seller(user["id"])
        collection = db.one("SELECT * FROM prompt_collections WHERE collection_id=? AND owner_id=?", (collection_id, user["id"]))
        if not collection:
            fail("collection_not_found", "Collection not found", 404)
        items = db.all("""SELECT p.prompt_id FROM prompt_collection_items ci JOIN prompts p ON p.prompt_id=ci.prompt_id
                          WHERE ci.collection_id=? AND p.owner_id=? AND p.status='ACTIVE' ORDER BY ci.position""", (collection_id, user["id"]))
        if not items:
            fail("empty_collection", "Collection must contain at least one owned prompt", 400)
        model = body.pricing_model.strip().upper()
        if model not in {"BUNDLE", "PREMIUM_COLLECTION", "SUBSCRIPTION_ACCESS"}:
            fail("invalid_pricing_model", "Invalid collection pricing model", 400)
        duration = body.duration_days
        if model == "SUBSCRIPTION_ACCESS" and duration <= 0:
            duration = 30
        if model != "SUBSCRIPTION_ACCESS":
            duration = 0
        price = _money(body.price_usd)
        if price <= 0:
            fail("invalid_price", "Collection offer price must be positive", 400)
        offer_id = "pofr_" + uuid.uuid4().hex
        product_id = "prompt_collection_" + offer_id
        t = now()
        db.execute("INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at) VALUES(?,?,?,?,?,?,?)",
                   (product_id, collection["title"], collection["description"], str(price), f"prompt_collection:{offer_id}", 1, t))
        db.execute("INSERT INTO prompt_collection_offers(offer_id,collection_id,seller_id,product_id,pricing_model,price_usd,license_type,duration_days,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (offer_id, collection_id, user["id"], product_id, model, str(price), body.license_type.strip().upper(), duration, "PUBLISHED", t, t))
        return {"offer": db.one("SELECT * FROM prompt_collection_offers WHERE offer_id=?", (offer_id,)), "items": len(items)}

    @app.get("/api/v1/prompt-factory/collection-offers")
    def collection_offers(limit: int = Query(default=30, ge=1, le=100)):
        rows = db.all("""SELECT o.*,c.title,c.description,u.display_name AS creator_name FROM prompt_collection_offers o
                         JOIN prompt_collections c ON c.collection_id=o.collection_id JOIN users u ON u.id=o.seller_id
                         WHERE o.status='PUBLISHED' ORDER BY o.sales_count DESC,o.updated_at DESC LIMIT ?""", (limit,))
        return {"offers": rows}

    @app.post("/api/v1/prompt-factory/collection-offers/{offer_id}/prepare-checkout")
    def collection_checkout(offer_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        offer = db.one("SELECT * FROM prompt_collection_offers WHERE offer_id=? AND status='PUBLISHED'", (offer_id,))
        if not offer:
            fail("offer_not_found", "Collection offer not found", 404)
        if offer["seller_id"] == user["id"]:
            fail("self_purchase", "You cannot buy your own collection", 409)
        access = db.one("SELECT * FROM prompt_collection_access WHERE user_id=? AND offer_id=?", (user["id"], offer_id))
        if access and (int(access["expires_at"]) == 0 or int(access["expires_at"]) > now()):
            return {"already_owned": True, "offer_id": offer_id}
        return {"product_id": offer["product_id"], "price_usd": offer["price_usd"], "offer_id": offer_id}

    @app.get("/api/v1/prompt-factory/collection-library")
    def collection_library(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all("""SELECT DISTINCT p.* FROM prompt_collection_access a
                         JOIN prompt_collection_items ci ON ci.collection_id=a.collection_id
                         JOIN prompts p ON p.prompt_id=ci.prompt_id
                         WHERE a.user_id=? AND (a.expires_at=0 OR a.expires_at>?) AND p.status='ACTIVE' ORDER BY p.updated_at DESC""", (user["id"], now()))
        return {"prompts": rows}

    @app.get("/api/v1/prompt-factory/collection-library/{prompt_id}")
    def collection_prompt(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        row = db.one("""SELECT p.*,a.license_type,a.expires_at FROM prompt_collection_access a
                        JOIN prompt_collection_items ci ON ci.collection_id=a.collection_id
                        JOIN prompts p ON p.prompt_id=ci.prompt_id
                        WHERE a.user_id=? AND p.prompt_id=? AND (a.expires_at=0 OR a.expires_at>?) AND p.status='ACTIVE' LIMIT 1""", (user["id"], prompt_id, now()))
        if not row:
            fail("prompt_not_found", "Collection prompt access not found", 404)
        return {"prompt": row}

    @app.post("/api/v1/prompt-factory/moderation/reports")
    def report_content(body: ReportIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        target_type = body.target_type.strip().upper()
        if target_type not in {"PROMPT", "LISTING", "CREATOR", "COLLECTION"}:
            fail("invalid_target", "Invalid moderation target", 400)
        category = body.category.strip().upper()
        rid = "pmr_" + uuid.uuid4().hex
        t = now()
        db.execute("INSERT INTO prompt_moderation_reports(report_id,reporter_id,target_type,target_id,category,details,status,created_at,updated_at) VALUES(?,?,?,?,?,?,'OPEN',?,?)",
                   (rid, user["id"], target_type, body.target_id, category, body.details.strip(), t, t))
        audit(user["id"], "prompt_content_reported", target_type.lower(), body.target_id, {"category": category})
        return {"report_id": rid, "status": "OPEN"}

    @app.post("/api/v1/prompt-factory/purchases/{purchase_id}/dispute")
    def open_dispute(purchase_id: str, body: DisputeIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        purchase = db.one("SELECT * FROM prompt_purchases WHERE purchase_id=? AND buyer_id=? AND status='CONFIRMED'", (purchase_id, user["id"]))
        if not purchase:
            fail("purchase_not_found", "Confirmed purchase not found", 404)
        if db.one("SELECT dispute_id FROM prompt_disputes WHERE purchase_id=?", (purchase_id,)):
            fail("dispute_exists", "A dispute already exists for this purchase", 409)
        frozen = Decimal("0.00")
        if purchase.get("seller_id"):
            bal = db.one("SELECT available_usd,pending_usd FROM seller_balances WHERE seller_id=?", (purchase["seller_id"],))
            if bal:
                frozen = min(_money(bal["available_usd"]), _money(purchase["seller_amount_usd"]))
                if frozen > 0:
                    db.execute("UPDATE seller_balances SET available_usd=available_usd-?,pending_usd=pending_usd+?,updated_at=? WHERE seller_id=?", (str(frozen), str(frozen), now(), purchase["seller_id"]))
        did = "pdis_" + uuid.uuid4().hex
        t = now()
        db.execute("INSERT INTO prompt_disputes(dispute_id,purchase_id,buyer_id,seller_id,reason,details,status,frozen_usd,created_at,updated_at) VALUES(?,?,?,?,?,?,'OPEN',?,?,?)",
                   (did, purchase_id, user["id"], purchase.get("seller_id"), body.reason.strip().upper(), body.details.strip(), str(frozen), t, t))
        if purchase.get("seller_id"):
            notify(purchase["seller_id"], "DISPUTE", "Venta en disputa", "Un comprador abrió una disputa.", "/prompt-factory#earnings", "dispute:" + did)
        return {"dispute_id": did, "status": "OPEN", "frozen_usd": str(frozen)}

    @app.post("/api/v1/prompt-factory/payouts")
    def request_payout(body: PayoutIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if setting("withdrawals_enabled", "true") != "true":
            fail("withdrawals_disabled", "Withdrawals are disabled", 503)
        amount = _money(body.amount_usd)
        minimum = _money(setting("minimum_withdrawal_usd", "10.00"))
        fee = _money(setting("withdrawal_fee_usd", "0.50"))
        if amount < minimum or amount <= fee:
            fail("withdrawal_too_small", f"Minimum withdrawal is {minimum}", 400)
        balance = db.one("SELECT * FROM seller_balances WHERE seller_id=?", (user["id"],))
        if not balance or _money(balance["available_usd"]) < amount:
            fail("insufficient_balance", "Insufficient available balance", 409)
        pid = "ppay_" + uuid.uuid4().hex
        t = now()
        db.execute("UPDATE seller_balances SET available_usd=available_usd-?,pending_usd=pending_usd+?,updated_at=? WHERE seller_id=?", (str(amount), str(amount), t, user["id"]))
        db.execute("INSERT INTO prompt_payouts(payout_id,seller_id,amount_usd,fee_usd,net_usd,method,destination,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'PENDING',?,?)",
                   (pid, user["id"], str(amount), str(fee), str(amount - fee), body.method.strip().upper(), body.destination.strip(), t, t))
        audit(user["id"], "prompt_payout_requested", "payout", pid, {"amount_usd": str(amount), "net_usd": str(amount - fee)})
        return {"payout": db.one("SELECT * FROM prompt_payouts WHERE payout_id=?", (pid,))}

    @app.get("/api/v1/prompt-factory/payouts")
    def my_payouts(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        return {"payouts": db.all("SELECT * FROM prompt_payouts WHERE seller_id=? ORDER BY created_at DESC", (user["id"],))}

    @app.get("/api/v1/prompt-factory/referrals/me")
    def my_referral(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        row = db.one("SELECT * FROM prompt_referral_codes WHERE user_id=?", (user["id"],))
        if not row:
            code = "PF" + hashlib.sha256(user["id"].encode()).hexdigest()[:10].upper()
            db.execute("INSERT INTO prompt_referral_codes(code,user_id,created_at) VALUES(?,?,?)", (code, user["id"], now()))
            row = db.one("SELECT * FROM prompt_referral_codes WHERE user_id=?", (user["id"],))
        total = db.one("SELECT COALESCE(SUM(amount_usd),0) AS n,COUNT(*) AS sales FROM prompt_referral_earnings WHERE affiliate_user_id=?", (user["id"],))
        return {"referral": row, "earnings": total, "share_path": "/prompt-factory?ref=" + row["code"]}

    @app.post("/api/v1/prompt-factory/referrals/attribute")
    def attribute_referral(body: ReferralAttributeIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        code = body.code.strip().upper()
        ref = db.one("SELECT * FROM prompt_referral_codes WHERE code=?", (code,))
        if not ref or ref["user_id"] == user["id"]:
            fail("invalid_referral", "Invalid referral code", 400)
        existing = db.one("SELECT * FROM prompt_referral_attributions WHERE referred_user_id=?", (user["id"],))
        if existing:
            return {"attributed": True, "existing": True}
        db.execute("INSERT INTO prompt_referral_attributions(referred_user_id,affiliate_user_id,code,created_at) VALUES(?,?,?,?)", (user["id"], ref["user_id"], code, now()))
        return {"attributed": True, "existing": False}

    @app.post("/api/v1/prompt-factory/analytics/events")
    def analytics_event(body: AnalyticsIn, authorization: str | None = Header(default=None)):
        user = None
        if authorization:
            user = current_user(authorization)
        eid = "pae_" + uuid.uuid4().hex
        db.execute("INSERT INTO prompt_analytics_events(event_id,user_id,event_type,prompt_id,listing_id,creator_id,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                   (eid, user["id"] if user else None, body.event_type.strip().upper(), body.prompt_id, body.listing_id, body.creator_id, json.dumps(body.metadata, separators=(",", ":"))[:8000], now()))
        return {"ok": True}

    @app.get("/api/v1/prompt-factory/creator/analytics")
    def creator_analytics(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        uid = user["id"]
        t = now()
        def sale_window(seconds: int):
            return db.one("SELECT COUNT(*) AS sales,COALESCE(SUM(gross_usd),0) AS gross,COALESCE(SUM(seller_amount_usd),0) AS net,COALESCE(SUM(platform_fee_usd),0) AS fees FROM prompt_purchases WHERE seller_id=? AND status='CONFIRMED' AND created_at>=?", (uid, t - seconds))
        views = db.one("SELECT COUNT(*) AS n FROM prompt_analytics_events WHERE creator_id=? AND event_type='VIEW'", (uid,))["n"]
        favorites = db.one("SELECT COUNT(*) AS n FROM prompt_favorites f JOIN prompts p ON p.prompt_id=f.prompt_id WHERE p.owner_id=?", (uid,))["n"]
        reviews = db.one("SELECT COUNT(*) AS n,COALESCE(AVG(r.rating),0) AS avg FROM prompt_reviews r JOIN prompts p ON p.prompt_id=r.prompt_id WHERE p.owner_id=?", (uid,))
        lifetime = sale_window(100 * 365 * 86400)
        conversion = (float(lifetime["sales"]) / float(views) * 100.0) if views else 0.0
        return {"today": sale_window(86400), "days7": sale_window(7 * 86400), "days30": sale_window(30 * 86400), "lifetime": lifetime, "views": views, "favorites": favorites, "reviews": reviews, "conversion_rate": round(conversion, 2)}

    @app.get("/api/v1/prompt-factory/notifications")
    def notifications(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        sync_notifications(user["id"])
        return {"notifications": db.all("SELECT * FROM prompt_notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 200", (user["id"],))}

    @app.post("/api/v1/prompt-factory/notifications/{notification_id}/read")
    def notification_read(notification_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        db.execute("UPDATE prompt_notifications SET read_at=? WHERE notification_id=? AND user_id=?", (now(), notification_id, user["id"]))
        return {"ok": True}

    @app.get("/api/v1/prompt-factory/admin/advanced-overview")
    def admin_advanced_overview(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        gmv = _money((db.one("SELECT COALESCE(SUM(gross_usd),0) AS n FROM prompt_purchases WHERE status='CONFIRMED'") or {"n": 0})["n"])
        fees = _money((db.one("SELECT COALESCE(SUM(platform_fee_usd),0) AS n FROM prompt_purchases WHERE status='CONFIRMED'") or {"n": 0})["n"])
        referral = _money((db.one("SELECT COALESCE(SUM(amount_usd),0) AS n FROM prompt_referral_earnings") or {"n": 0})["n"])
        collection_gmv = _money((db.one("SELECT COALESCE(SUM(gross_usd),0) AS n FROM prompt_collection_sales WHERE status='CONFIRMED'") or {"n": 0})["n"])
        collection_fees = _money((db.one("SELECT COALESCE(SUM(platform_fee_usd),0) AS n FROM prompt_collection_sales WHERE status='CONFIRMED'") or {"n": 0})["n"])
        return {
            "gmv_usd": str(gmv + collection_gmv), "platform_revenue_usd": str(fees + collection_fees - referral),
            "referral_cost_usd": str(referral),
            "users": db.one("SELECT COUNT(*) AS n FROM users WHERE disabled=0")["n"],
            "sellers": db.one("SELECT COUNT(*) AS n FROM prompt_seller_profiles WHERE blocked=0")["n"],
            "prompts": db.one("SELECT COUNT(*) AS n FROM prompts WHERE status='ACTIVE'")["n"],
            "sales": db.one("SELECT COUNT(*) AS n FROM prompt_purchases WHERE status='CONFIRMED'")["n"],
            "open_disputes": db.one("SELECT COUNT(*) AS n FROM prompt_disputes WHERE status='OPEN'")["n"],
            "open_reports": db.one("SELECT COUNT(*) AS n FROM prompt_moderation_reports WHERE status='OPEN'")["n"],
            "pending_payouts": db.one("SELECT COUNT(*) AS n FROM prompt_payouts WHERE status='PENDING'")["n"],
            "top_categories": db.all("SELECT p.category,COUNT(*) AS sales,COALESCE(SUM(pp.gross_usd),0) AS gmv FROM prompt_purchases pp JOIN prompts p ON p.prompt_id=pp.prompt_id WHERE pp.status='CONFIRMED' GROUP BY p.category ORDER BY sales DESC LIMIT 10"),
            "top_sellers": db.all("SELECT u.display_name,COUNT(*) AS sales,COALESCE(SUM(pp.gross_usd),0) AS gmv FROM prompt_purchases pp JOIN users u ON u.id=pp.seller_id WHERE pp.status='CONFIRMED' GROUP BY u.id,u.display_name ORDER BY sales DESC LIMIT 10"),
            "top_prompts": db.all("SELECT p.title,l.sales_count,l.rating_avg,l.price_usd FROM prompt_listings l JOIN prompts p ON p.prompt_id=l.prompt_id ORDER BY l.sales_count DESC,l.rating_avg DESC LIMIT 10"),
        }

    @app.get("/api/v1/prompt-factory/admin/reports")
    def admin_reports(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {"reports": db.all("SELECT * FROM prompt_moderation_reports ORDER BY CASE status WHEN 'OPEN' THEN 0 ELSE 1 END,created_at DESC LIMIT 500"),
                "duplicate_flags": db.all("SELECT * FROM prompt_duplicate_flags WHERE status='OPEN' ORDER BY created_at DESC LIMIT 500")}

    @app.put("/api/v1/prompt-factory/admin/reports/{report_id}")
    def admin_report_update(report_id: str, body: ModerationIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        status = body.status.strip().upper()
        if status not in {"OPEN", "IN_REVIEW", "RESOLVED", "REJECTED"}:
            fail("invalid_status", "Invalid report status", 400)
        db.execute("UPDATE prompt_moderation_reports SET status=?,resolution=?,updated_at=? WHERE report_id=?", (status, body.resolution.strip(), now(), report_id))
        audit(admin["id"], "prompt_report_moderated", "report", report_id, {"status": status})
        return {"ok": True}

    @app.get("/api/v1/prompt-factory/admin/disputes")
    def admin_disputes(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {"disputes": db.all("SELECT * FROM prompt_disputes ORDER BY CASE status WHEN 'OPEN' THEN 0 ELSE 1 END,created_at DESC LIMIT 500")}

    @app.put("/api/v1/prompt-factory/admin/disputes/{dispute_id}")
    def admin_dispute_resolve(dispute_id: str, body: DisputeResolveIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        dispute = db.one("SELECT * FROM prompt_disputes WHERE dispute_id=? AND status='OPEN'", (dispute_id,))
        if not dispute:
            fail("dispute_not_found", "Open dispute not found", 404)
        resolution = body.resolution.strip().upper()
        if resolution not in {"SELLER_WINS", "BUYER_REFUNDED"}:
            fail("invalid_resolution", "Resolution must be SELLER_WINS or BUYER_REFUNDED", 400)
        frozen = _money(dispute["frozen_usd"])
        if dispute.get("seller_id") and frozen > 0:
            if resolution == "SELLER_WINS":
                db.execute("UPDATE seller_balances SET pending_usd=pending_usd-?,available_usd=available_usd+?,updated_at=? WHERE seller_id=?", (str(frozen), str(frozen), now(), dispute["seller_id"]))
            else:
                if not body.refund_tx.strip():
                    fail("refund_tx_required", "Record the verified refund transaction before resolving for buyer", 400)
                db.execute("UPDATE seller_balances SET pending_usd=pending_usd-?,updated_at=? WHERE seller_id=?", (str(frozen), now(), dispute["seller_id"]))
                db.execute("UPDATE prompt_purchases SET status='REFUNDED' WHERE purchase_id=?", (dispute["purchase_id"],))
        db.execute("UPDATE prompt_disputes SET status='RESOLVED',resolution=?,refund_tx=?,updated_at=? WHERE dispute_id=?", (resolution, body.refund_tx.strip(), now(), dispute_id))
        audit(admin["id"], "prompt_dispute_resolved", "dispute", dispute_id, {"resolution": resolution})
        return {"ok": True, "resolution": resolution}

    @app.get("/api/v1/prompt-factory/admin/payouts")
    def admin_payouts(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {"payouts": db.all("SELECT * FROM prompt_payouts ORDER BY CASE status WHEN 'PENDING' THEN 0 WHEN 'PROCESSING' THEN 1 ELSE 2 END,created_at DESC LIMIT 500")}

    @app.put("/api/v1/prompt-factory/admin/payouts/{payout_id}")
    def admin_payout_status(payout_id: str, body: PayoutStatusIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        payout = db.one("SELECT * FROM prompt_payouts WHERE payout_id=?", (payout_id,))
        if not payout:
            fail("payout_not_found", "Payout not found", 404)
        old = str(payout["status"]).upper()
        status = body.status.strip().upper()
        if status not in {"PENDING", "PROCESSING", "PAID", "REJECTED"}:
            fail("invalid_status", "Invalid payout status", 400)
        if old in {"PAID", "REJECTED"} and status != old:
            fail("payout_final", "Finalized payout cannot be changed", 409)
        if status == "PAID" and old != "PAID":
            if not body.payout_tx.strip():
                fail("payout_tx_required", "Verified payout transaction/reference is required", 400)
            db.execute("UPDATE seller_balances SET pending_usd=pending_usd-?,updated_at=? WHERE seller_id=?", (str(_money(payout["amount_usd"])), now(), payout["seller_id"]))
        if status == "REJECTED" and old not in {"REJECTED", "PAID"}:
            amount = str(_money(payout["amount_usd"]))
            db.execute("UPDATE seller_balances SET pending_usd=pending_usd-?,available_usd=available_usd+?,updated_at=? WHERE seller_id=?", (amount, amount, now(), payout["seller_id"]))
        db.execute("UPDATE prompt_payouts SET status=?,payout_tx=?,notes=?,updated_at=? WHERE payout_id=?", (status, body.payout_tx.strip(), body.notes.strip(), now(), payout_id))
        audit(admin["id"], "prompt_payout_status", "payout", payout_id, {"status": status})
        notify(payout["seller_id"], "PAYOUT", "Retiro actualizado", f"Estado: {status}", "/prompt-factory#earnings", "payout-status:" + payout_id + ":" + status)
        return {"ok": True, "status": status}

    @app.put("/api/v1/prompt-factory/admin/sellers/{user_id}/blocked")
    def admin_block_seller(user_id: str, blocked: bool, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        profile = seller_profile(user_id)
        if not profile:
            fail("seller_not_found", "Seller not found", 404)
        db.execute("UPDATE prompt_seller_profiles SET blocked=?,updated_at=? WHERE user_id=?", (1 if blocked else 0, now(), user_id))
        if blocked:
            db.execute("UPDATE prompt_listings SET status='PAUSED',updated_at=? WHERE seller_id=? AND status='PUBLISHED'", (now(), user_id))
            db.execute("UPDATE products SET active=0 WHERE product_id IN (SELECT product_id FROM prompt_listings WHERE seller_id=?)", (user_id,))
        audit(admin["id"], "prompt_seller_blocked_changed", "user", user_id, {"blocked": blocked})
        return {"ok": True, "blocked": blocked}

    @app.post("/api/v1/prompt-factory/admin/categories")
    def admin_create_category(body: CategoryIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        label = body.label.strip().upper()
        cid = "pcat_" + uuid.uuid4().hex
        t = now()
        try:
            db.execute("INSERT INTO prompt_dynamic_categories(category_id,label,slug,active,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (cid, label, _slug(label), 1 if body.active else 0, body.sort_order, t, t))
        except sqlite3.IntegrityError:
            fail("category_exists", "Category already exists", 409)
        audit(admin["id"], "prompt_category_created", "category", cid)
        return {"category": db.one("SELECT * FROM prompt_dynamic_categories WHERE category_id=?", (cid,))}

    @app.put("/api/v1/prompt-factory/admin/plans/{plan_id}")
    def admin_plan(plan_id: str, body: PlanAdminIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        if not db.one("SELECT plan_id FROM prompt_plans WHERE plan_id=?", (plan_id,)):
            fail("plan_not_found", "Plan not found", 404)
        db.execute("UPDATE prompt_plans SET label=?,price_usd=?,max_prompts=?,commission_bps=?,features_json=?,active=? WHERE plan_id=?",
                   (body.label.strip(), str(_money(body.price_usd)), body.max_prompts, body.commission_bps, json.dumps(body.features, separators=(",", ":")), 1 if body.active else 0, plan_id))
        if plan_id != "free":
            db.execute("UPDATE products SET label=?,price_usd=?,active=? WHERE product_id=?", ("Prompt Factory " + body.label.strip(), str(_money(body.price_usd)), 1 if body.active else 0, f"prompt_plan_{plan_id}_30d"))
        audit(admin["id"], "prompt_plan_updated", "plan", plan_id)
        return {"plan": db.one("SELECT * FROM prompt_plans WHERE plan_id=?", (plan_id,))}

    @app.get("/api/v1/prompt-factory/admin/sales")
    def admin_sales(limit: int = Query(default=200, ge=1, le=1000), authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {"sales": db.all("""SELECT pp.*,p.title,b.display_name AS buyer_name,s.display_name AS seller_name FROM prompt_purchases pp
                                  JOIN prompts p ON p.prompt_id=pp.prompt_id JOIN users b ON b.id=pp.buyer_id LEFT JOIN users s ON s.id=pp.seller_id
                                  ORDER BY pp.created_at DESC LIMIT ?""", (limit,))}

    @app.get("/api/v1/prompt-factory/admin/users")
    def admin_users(limit: int = Query(default=200, ge=1, le=1000), authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {"users": db.all("""SELECT u.id,u.email,u.display_name,u.role,u.disabled,u.created_at,sp.username,sp.blocked,
                                  (SELECT COUNT(*) FROM prompts p WHERE p.owner_id=u.id AND p.status<>'ARCHIVED') AS prompt_count
                                  FROM users u LEFT JOIN prompt_seller_profiles sp ON sp.user_id=u.id ORDER BY u.created_at DESC LIMIT ?""", (limit,))}

    def reconcile_advanced_user(user_id: str) -> dict:
        applied = 0
        t = now()
        rows = db.all("""SELECT o.*,p.entitlement_key AS pf_entitlement,ph.product_id FROM purchase_history ph
                         JOIN orders o ON o.order_id=ph.order_id JOIN products p ON p.product_id=ph.product_id
                         WHERE ph.user_id=? AND o.status='FULFILLED' AND p.entitlement_key LIKE ? ORDER BY ph.created_at ASC""",
                      (user_id, "prompt_collection:%"))
        for order in rows:
            if db.one("SELECT order_id FROM prompt_advanced_entitlement_events WHERE order_id=?", (order["order_id"],)):
                continue
            entitlement = order["pf_entitlement"]
            offer_id = entitlement.split(":", 1)[1]
            offer = db.one("SELECT * FROM prompt_collection_offers WHERE offer_id=? AND status='PUBLISHED'", (offer_id,))
            if not offer or offer["seller_id"] == user_id:
                continue
            quote = db.one("SELECT fiat_price_usd FROM payment_quotes WHERE quote_id=?", (order["quote_id"],))
            gross = _money(quote["fiat_price_usd"] if quote else offer["price_usd"])
            membership = db.one("SELECT plan_id FROM prompt_user_plans WHERE user_id=? AND expires_at>?", (offer["seller_id"], t))
            plan_id = membership["plan_id"] if membership else "free"
            plan = db.one("SELECT commission_bps FROM prompt_plans WHERE plan_id=?", (plan_id,)) or {"commission_bps": 1500}
            fee = (gross * Decimal(int(plan["commission_bps"])) / Decimal(10000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            seller_amount = gross - fee
            expires = t + int(offer["duration_days"]) * 86400 if int(offer["duration_days"]) > 0 else 0
            db.execute("""INSERT INTO prompt_collection_access(user_id,offer_id,collection_id,order_id,license_type,expires_at,created_at)
                          VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,offer_id) DO UPDATE SET order_id=excluded.order_id,license_type=excluded.license_type,
                          expires_at=CASE WHEN prompt_collection_access.expires_at=0 THEN 0 WHEN excluded.expires_at=0 THEN 0 ELSE excluded.expires_at END""",
                       (user_id, offer_id, offer["collection_id"], order["order_id"], offer["license_type"], expires, t))
            sale_id = "pcs_" + uuid.uuid4().hex
            db.execute("INSERT INTO prompt_collection_sales(sale_id,offer_id,buyer_id,seller_id,order_id,gross_usd,platform_fee_usd,seller_amount_usd,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (sale_id, offer_id, user_id, offer["seller_id"], order["order_id"], str(gross), str(fee), str(seller_amount), "CONFIRMED", t))
            db.execute("""INSERT INTO seller_balances(seller_id,available_usd,pending_usd,lifetime_earnings_usd,platform_fees_usd,updated_at)
                          VALUES(?,?,?,?,?,?) ON CONFLICT(seller_id) DO UPDATE SET available_usd=seller_balances.available_usd+excluded.available_usd,
                          lifetime_earnings_usd=seller_balances.lifetime_earnings_usd+excluded.lifetime_earnings_usd,platform_fees_usd=seller_balances.platform_fees_usd+excluded.platform_fees_usd,updated_at=excluded.updated_at""",
                       (offer["seller_id"], str(seller_amount), "0", str(seller_amount), str(fee), t))
            db.execute("UPDATE prompt_collection_offers SET sales_count=sales_count+1,updated_at=? WHERE offer_id=?", (t, offer_id))
            db.execute("INSERT INTO prompt_advanced_entitlement_events(order_id,user_id,entitlement_key,applied_at) VALUES(?,?,?,?)", (order["order_id"], user_id, entitlement, t))
            notify(offer["seller_id"], "SALE", "Colección vendida", f"{gross} USD", "/prompt-factory#earnings", "collection-sale:" + sale_id)
            applied += 1

        intents = db.all("""SELECT i.*,ph.order_id FROM prompt_checkout_intents i JOIN purchase_history ph ON ph.product_id=i.product_id
                            JOIN orders o ON o.order_id=ph.order_id WHERE i.buyer_id=? AND o.status='FULFILLED' AND i.redeemed_order_id IS NULL""", (user_id,))
        for intent in intents:
            db.execute("UPDATE prompt_checkout_intents SET redeemed_order_id=? WHERE product_id=? AND redeemed_order_id IS NULL", (intent["order_id"], intent["product_id"]))
            if intent.get("coupon_id"):
                db.execute("UPDATE prompt_coupons SET uses_count=uses_count+1,updated_at=? WHERE coupon_id=?", (t, intent["coupon_id"]))

        purchases = db.all("SELECT * FROM prompt_purchases WHERE buyer_id=? AND status='CONFIRMED' ORDER BY created_at ASC", (user_id,))
        referral_bps = max(0, min(10000, int(setting("referral_bps", "300"))))
        attribution = db.one("SELECT affiliate_user_id FROM prompt_referral_attributions WHERE referred_user_id=?", (user_id,))
        if attribution and attribution["affiliate_user_id"] != user_id:
            for purchase in purchases:
                if db.one("SELECT earning_id FROM prompt_referral_earnings WHERE purchase_id=?", (purchase["purchase_id"],)):
                    continue
                gross = _money(purchase["gross_usd"])
                platform_fee = _money(purchase["platform_fee_usd"])
                referral_amount = min(platform_fee, (gross * Decimal(referral_bps) / Decimal(10000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
                if referral_amount <= 0:
                    continue
                eid = "pref_" + uuid.uuid4().hex
                db.execute("INSERT INTO prompt_referral_earnings(earning_id,purchase_id,affiliate_user_id,amount_usd,created_at) VALUES(?,?,?,?,?)", (eid, purchase["purchase_id"], attribution["affiliate_user_id"], str(referral_amount), t))
                db.execute("""INSERT INTO seller_balances(seller_id,available_usd,pending_usd,lifetime_earnings_usd,platform_fees_usd,updated_at)
                              VALUES(?,?,?,?,?,?) ON CONFLICT(seller_id) DO UPDATE SET available_usd=seller_balances.available_usd+excluded.available_usd,
                              lifetime_earnings_usd=seller_balances.lifetime_earnings_usd+excluded.lifetime_earnings_usd,updated_at=excluded.updated_at""",
                           (attribution["affiliate_user_id"], str(referral_amount), "0", str(referral_amount), "0", t))
                notify(attribution["affiliate_user_id"], "REFERRAL", "Comisión de referido", f"+${referral_amount}", "/prompt-factory#earnings", "referral:" + eid)
        return {"ok": True, "advanced_applied": applied, "collection_orders_checked": len(rows), "checkout_intents_checked": len(intents)}

    @app.post("/api/v1/prompt-factory/reconcile-advanced")
    def reconcile_advanced(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        return reconcile_advanced_user(user["id"])
