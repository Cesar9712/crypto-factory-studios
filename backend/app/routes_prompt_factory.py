from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from fastapi import Header, Query
from pydantic import BaseModel, Field


CATEGORIES = [
    "AI AGENTS", "MARKETING", "SOCIAL MEDIA", "BUSINESS", "CODING", "WEB DEVELOPMENT",
    "GAME DEVELOPMENT", "WEB3", "CRYPTO", "DESIGN", "IMAGE GENERATION", "VIDEO GENERATION",
    "CONTENT CREATION", "SEO", "YOUTUBE", "AUTOMATION", "PRODUCTIVITY", "EDUCATION",
    "RESEARCH", "DATA ANALYSIS", "SALES", "COPYWRITING", "E-COMMERCE", "OTHER",
]

AI_MODELS = [
    "ChatGPT", "OpenAI API", "Claude", "Gemini", "Grok", "Midjourney", "Stable Diffusion",
    "Flux", "Sora", "Runway", "Kling", "Veo", "Lovable", "Replit", "Cursor", "Codex", "Rocket",
]

PLAN_SEEDS = [
    ("free", "Free", "0.00", 10, 2000, json.dumps(["vault", "search", "tags"]), 1),
    ("starter", "Starter", "1.99", 50, 1800, json.dumps(["versions", "variables", "advanced_organization"]), 1),
    ("creator", "Creator", "4.99", 250, 1500, json.dumps(["marketplace", "analytics", "collections"]), 1),
    ("pro", "Pro", "9.99", 1000, 1000, json.dumps(["advanced_analytics", "priority", "automation"]), 1),
    ("unlimited", "Unlimited", "19.99", None, 800, json.dumps(["unlimited_prompts", "marketplace", "analytics"]), 1),
]

ADDON_SEEDS = [
    ("slots_25", "+25 prompt slots", "0.99", 25, 1),
    ("slots_100", "+100 prompt slots", "2.99", 100, 1),
    ("slots_500", "+500 prompt slots", "7.99", 500, 1),
    ("slots_1000", "+1,000 prompt slots", "12.99", 1000, 1),
]

SETTING_SEEDS = {
    "marketplace_enabled": "true",
    "default_commission_bps": "1500",
    "minimum_prompt_price_usd": "0.00",
    "maximum_prompt_price_usd": "1000.00",
    "minimum_withdrawal_usd": "10.00",
    "manual_listing_approval": "false",
    "reviews_enabled": "true",
}

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS prompt_plans(
        plan_id TEXT PRIMARY KEY,label TEXT NOT NULL,price_usd TEXT NOT NULL,max_prompts INTEGER,
        commission_bps INTEGER NOT NULL,features_json TEXT NOT NULL DEFAULT '[]',active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS prompt_user_plans(
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,plan_id TEXT NOT NULL REFERENCES prompt_plans(plan_id),
        starts_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_user_storage(
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,extra_slots INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_storage_addons(
        addon_id TEXT PRIMARY KEY,label TEXT NOT NULL,price_usd TEXT NOT NULL,extra_slots INTEGER NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS prompt_platform_settings(
        setting_key TEXT PRIMARY KEY,setting_value TEXT NOT NULL,updated_at INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS prompts(
        prompt_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,slug TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',prompt_text TEXT NOT NULL,system_instructions TEXT NOT NULL DEFAULT '',
        category TEXT NOT NULL DEFAULT 'OTHER',subcategory TEXT NOT NULL DEFAULT '',tags_json TEXT NOT NULL DEFAULT '[]',
        ai_models_json TEXT NOT NULL DEFAULT '[]',difficulty TEXT NOT NULL DEFAULT 'INTERMEDIATE',language TEXT NOT NULL DEFAULT 'en',
        variables_json TEXT NOT NULL DEFAULT '[]',visibility TEXT NOT NULL DEFAULT 'PRIVATE',status TEXT NOT NULL DEFAULT 'ACTIVE',
        content_hash TEXT NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,archived_at INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS prompt_versions(
        version_id TEXT PRIMARY KEY,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
        version_number INTEGER NOT NULL,prompt_text TEXT NOT NULL,system_instructions TEXT NOT NULL DEFAULT '',
        variables_json TEXT NOT NULL DEFAULT '[]',changelog TEXT NOT NULL DEFAULT '',content_hash TEXT NOT NULL,
        created_at INTEGER NOT NULL,UNIQUE(prompt_id,version_number))""",
    """CREATE TABLE IF NOT EXISTS prompt_listings(
        listing_id TEXT PRIMARY KEY,prompt_id TEXT NOT NULL UNIQUE REFERENCES prompts(prompt_id) ON DELETE CASCADE,
        seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,product_id TEXT NOT NULL UNIQUE REFERENCES products(product_id),
        price_usd TEXT NOT NULL,pricing_model TEXT NOT NULL DEFAULT 'FIXED',license_type TEXT NOT NULL DEFAULT 'PERSONAL',
        preview_text TEXT NOT NULL DEFAULT '',examples_json TEXT NOT NULL DEFAULT '[]',status TEXT NOT NULL DEFAULT 'DRAFT',
        commission_bps INTEGER NOT NULL,featured INTEGER NOT NULL DEFAULT 0,sales_count INTEGER NOT NULL DEFAULT 0,
        rating_avg REAL NOT NULL DEFAULT 0,rating_count INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_purchases(
        purchase_id TEXT PRIMARY KEY,buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        seller_id TEXT REFERENCES users(id) ON DELETE SET NULL,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
        listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,order_id TEXT UNIQUE,
        license_type TEXT NOT NULL,gross_usd NUMERIC NOT NULL DEFAULT 0,platform_fee_usd NUMERIC NOT NULL DEFAULT 0,
        seller_amount_usd NUMERIC NOT NULL DEFAULT 0,payment_asset TEXT NOT NULL DEFAULT 'FREE',payment_network TEXT NOT NULL DEFAULT 'FREE',
        status TEXT NOT NULL DEFAULT 'CONFIRMED',created_at INTEGER NOT NULL,UNIQUE(buyer_id,listing_id))""",
    """CREATE TABLE IF NOT EXISTS prompt_reviews(
        review_id TEXT PRIMARY KEY,purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
        buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
        rating INTEGER NOT NULL,comment TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_favorites(
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,PRIMARY KEY(user_id,prompt_id))""",
    """CREATE TABLE IF NOT EXISTS prompt_collections(
        collection_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',visibility TEXT NOT NULL DEFAULT 'PRIVATE',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompt_collection_items(
        collection_id TEXT NOT NULL REFERENCES prompt_collections(collection_id) ON DELETE CASCADE,
        prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,position INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(collection_id,prompt_id))""",
    """CREATE TABLE IF NOT EXISTS seller_balances(
        seller_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,available_usd NUMERIC NOT NULL DEFAULT 0,
        pending_usd NUMERIC NOT NULL DEFAULT 0,lifetime_earnings_usd NUMERIC NOT NULL DEFAULT 0,
        platform_fees_usd NUMERIC NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS seller_ledger(
        ledger_id TEXT PRIMARY KEY,seller_id TEXT REFERENCES users(id) ON DELETE SET NULL,purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
        gross_usd NUMERIC NOT NULL,platform_fee_usd NUMERIC NOT NULL,seller_amount_usd NUMERIC NOT NULL,
        event_type TEXT NOT NULL DEFAULT 'SALE',created_at INTEGER NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_prompts_owner ON prompts(owner_id,updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category,status)",
    "CREATE INDEX IF NOT EXISTS idx_prompt_listings_status ON prompt_listings(status,updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_prompt_purchases_buyer ON prompt_purchases(buyer_id,created_at)",
    "CREATE INDEX IF NOT EXISTS idx_prompt_purchases_seller ON prompt_purchases(seller_id,created_at)",
]


class PromptCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=4000)
    prompt_text: str = Field(min_length=1, max_length=120000)
    system_instructions: str = Field(default="", max_length=40000)
    category: str = Field(default="OTHER", max_length=60)
    subcategory: str = Field(default="", max_length=80)
    tags: list[str] = Field(default_factory=list)
    ai_models: list[str] = Field(default_factory=list)
    difficulty: str = Field(default="INTERMEDIATE", max_length=30)
    language: str = Field(default="en", max_length=20)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    visibility: str = Field(default="PRIVATE", max_length=20)


class PromptUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    prompt_text: str | None = Field(default=None, min_length=1, max_length=120000)
    system_instructions: str | None = Field(default=None, max_length=40000)
    category: str | None = Field(default=None, max_length=60)
    subcategory: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = None
    ai_models: list[str] | None = None
    difficulty: str | None = Field(default=None, max_length=30)
    language: str | None = Field(default=None, max_length=20)
    variables: list[dict[str, Any]] | None = None
    visibility: str | None = Field(default=None, max_length=20)
    changelog: str = Field(default="", max_length=1000)


class ListingIn(BaseModel):
    price_usd: str = Field(default="0.00", max_length=20)
    pricing_model: str = Field(default="FIXED", max_length=30)
    license_type: str = Field(default="PERSONAL", max_length=30)
    preview_text: str = Field(default="", max_length=3000)
    examples: list[str] = Field(default_factory=list)


class RenderIn(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


class CollectionIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    visibility: str = Field(default="PRIVATE", max_length=20)


class CollectionItemIn(BaseModel):
    prompt_id: str = Field(min_length=8, max_length=80)


class AdminListingStatusIn(BaseModel):
    status: str = Field(min_length=4, max_length=30)


class AdminSettingIn(BaseModel):
    value: str = Field(max_length=500)


def _hash(prompt_text: str, system_instructions: str, variables_json: str) -> str:
    raw = (prompt_text + "\n---SYSTEM---\n" + system_instructions + "\n---VARS---\n" + variables_json).encode()
    return hashlib.sha256(raw).hexdigest()


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:72] or "prompt"


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _json_list(raw: Any) -> list:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []


def ensure_prompt_factory_schema(db, now: Callable) -> None:
    for statement in SCHEMA_STATEMENTS:
        db.execute(statement)
    t = now()
    for plan in PLAN_SEEDS:
        db.execute(
            """INSERT INTO prompt_plans(plan_id,label,price_usd,max_prompts,commission_bps,features_json,active,created_at)
               VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(plan_id) DO UPDATE SET
               label=excluded.label,price_usd=excluded.price_usd,max_prompts=excluded.max_prompts,
               commission_bps=excluded.commission_bps,features_json=excluded.features_json,active=excluded.active""",
            (*plan, t),
        )
    for addon in ADDON_SEEDS:
        db.execute(
            """INSERT INTO prompt_storage_addons(addon_id,label,price_usd,extra_slots,active,created_at)
               VALUES(?,?,?,?,?,?) ON CONFLICT(addon_id) DO UPDATE SET
               label=excluded.label,price_usd=excluded.price_usd,extra_slots=excluded.extra_slots,active=excluded.active""",
            (*addon, t),
        )
    for key, value in SETTING_SEEDS.items():
        db.execute(
            "INSERT INTO prompt_platform_settings(setting_key,setting_value,updated_at) VALUES(?,?,?) ON CONFLICT(setting_key) DO NOTHING",
            (key, value, t),
        )
    for plan_id, label, price, _limit, _commission, _features, active in PLAN_SEEDS:
        if plan_id == "free":
            continue
        db.execute(
            """INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at)
               VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET
               label=excluded.label,description=excluded.description,price_usd=excluded.price_usd,
               entitlement_key=excluded.entitlement_key,active=excluded.active""",
            (f"prompt_plan_{plan_id}_30d", f"Prompt Factory {label}", f"30 days of {label} Prompt Factory capacity", price, f"prompt_plan:{plan_id}", active, t),
        )
    for addon_id, label, price, slots, active in ADDON_SEEDS:
        db.execute(
            """INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at)
               VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET
               label=excluded.label,description=excluded.description,price_usd=excluded.price_usd,
               entitlement_key=excluded.entitlement_key,active=excluded.active""",
            (f"prompt_storage_{addon_id}", f"Prompt Factory {label}", f"Adds {slots} permanent prompt slots", price, f"prompt_storage:{addon_id}", active, t),
        )


def _settle_listing_purchase(db, *, user_id: str, listing_id: str, order: dict, order_id: str, now: Callable, audit: Callable | None = None) -> None:
    if db.one("SELECT purchase_id FROM prompt_purchases WHERE order_id=?", (order_id,)):
        return
    listing = db.one(
        """SELECT l.*,p.owner_id,p.title FROM prompt_listings l JOIN prompts p ON p.prompt_id=l.prompt_id
           WHERE l.listing_id=?""",
        (listing_id,),
    )
    if not listing or listing["status"] != "PUBLISHED":
        return
    if listing["seller_id"] == user_id:
        return
    quote = db.one("SELECT fiat_price_usd FROM payment_quotes WHERE quote_id=?", (order["quote_id"],))
    gross = _money(quote["fiat_price_usd"] if quote else listing["price_usd"])
    bps = max(0, min(10000, int(listing["commission_bps"])))
    fee = (gross * Decimal(bps) / Decimal(10000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    seller_amount = gross - fee
    purchase_id = "ppur_" + uuid.uuid4().hex
    try:
        db.execute(
            """INSERT INTO prompt_purchases(purchase_id,buyer_id,seller_id,prompt_id,listing_id,order_id,license_type,
               gross_usd,platform_fee_usd,seller_amount_usd,payment_asset,payment_network,status,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (purchase_id, user_id, listing["seller_id"], listing["prompt_id"], listing_id, order_id, listing["license_type"],
             str(gross), str(fee), str(seller_amount), order.get("asset") or "UNKNOWN", order.get("network") or "UNKNOWN", "CONFIRMED", now()),
        )
    except sqlite3.IntegrityError:
        return
    db.execute(
        """INSERT INTO seller_ledger(ledger_id,seller_id,purchase_id,gross_usd,platform_fee_usd,seller_amount_usd,event_type,created_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        ("led_" + uuid.uuid4().hex, listing["seller_id"], purchase_id, str(gross), str(fee), str(seller_amount), "SALE", now()),
    )
    db.execute(
        """INSERT INTO seller_balances(seller_id,available_usd,pending_usd,lifetime_earnings_usd,platform_fees_usd,updated_at)
           VALUES(?,?,?,?,?,?) ON CONFLICT(seller_id) DO UPDATE SET
           available_usd=seller_balances.available_usd+excluded.available_usd,
           lifetime_earnings_usd=seller_balances.lifetime_earnings_usd+excluded.lifetime_earnings_usd,
           platform_fees_usd=seller_balances.platform_fees_usd+excluded.platform_fees_usd,
           updated_at=excluded.updated_at""",
        (listing["seller_id"], str(seller_amount), "0", str(seller_amount), str(fee), now()),
    )
    db.execute("UPDATE prompt_listings SET sales_count=sales_count+1,updated_at=? WHERE listing_id=?", (now(), listing_id))
    if audit:
        audit(user_id, "prompt_marketplace_purchase", "prompt", listing["prompt_id"], {"listing_id": listing_id, "platform_fee_usd": str(fee)})


def apply_prompt_factory_entitlement(db, *, user_id: str, entitlement: str, order: dict, order_id: str, now: Callable, audit: Callable | None = None) -> None:
    if not entitlement.startswith("prompt_"):
        return
    if entitlement.startswith("prompt_plan:"):
        plan_id = entitlement.split(":", 1)[1]
        plan = db.one("SELECT plan_id FROM prompt_plans WHERE plan_id=? AND active=1", (plan_id,))
        if not plan:
            return
        existing = db.one("SELECT plan_id,expires_at FROM prompt_user_plans WHERE user_id=?", (user_id,))
        t = now()
        base = max(t, int(existing["expires_at"])) if existing and existing["plan_id"] == plan_id else t
        db.execute(
            """INSERT INTO prompt_user_plans(user_id,plan_id,starts_at,expires_at,updated_at) VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET plan_id=excluded.plan_id,starts_at=excluded.starts_at,
               expires_at=excluded.expires_at,updated_at=excluded.updated_at""",
            (user_id, plan_id, t, base + 30 * 86400, t),
        )
        return
    if entitlement.startswith("prompt_storage:"):
        addon_id = entitlement.split(":", 1)[1]
        addon = db.one("SELECT extra_slots FROM prompt_storage_addons WHERE addon_id=? AND active=1", (addon_id,))
        if not addon:
            return
        db.execute(
            """INSERT INTO prompt_user_storage(user_id,extra_slots,updated_at) VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET extra_slots=prompt_user_storage.extra_slots+excluded.extra_slots,
               updated_at=excluded.updated_at""",
            (user_id, int(addon["extra_slots"]), now()),
        )
        return
    if entitlement.startswith("prompt_listing:"):
        _settle_listing_purchase(db, user_id=user_id, listing_id=entitlement.split(":", 1)[1], order=order, order_id=order_id, now=now, audit=audit)


def register_prompt_factory_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    ensure_prompt_factory_schema(db, now)

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

    def effective_prompt_plan(user: dict) -> dict:
        if user.get("role") == "platform_owner":
            plan = db.one("SELECT * FROM prompt_plans WHERE plan_id='unlimited'")
            return {**plan, "expires_at": 0, "extra_slots": 0, "internal": True}
        t = now()
        membership = db.one("SELECT plan_id,starts_at,expires_at FROM prompt_user_plans WHERE user_id=? AND expires_at>?", (user["id"], t))
        plan_id = membership["plan_id"] if membership else "free"
        plan = db.one("SELECT * FROM prompt_plans WHERE plan_id=? AND active=1", (plan_id,)) or db.one("SELECT * FROM prompt_plans WHERE plan_id='free'")
        storage = db.one("SELECT extra_slots FROM prompt_user_storage WHERE user_id=?", (user["id"],))
        return {**plan, "expires_at": membership["expires_at"] if membership else 0, "extra_slots": int(storage["extra_slots"]) if storage else 0, "internal": False}

    def prompt_usage(user_id: str) -> int:
        return int(db.one("SELECT COUNT(*) AS n FROM prompts WHERE owner_id=? AND status<>'ARCHIVED'", (user_id,))["n"])

    def assert_capacity(user: dict) -> dict:
        plan = effective_prompt_plan(user)
        limit = plan.get("max_prompts")
        if limit is not None:
            limit = int(limit) + int(plan.get("extra_slots") or 0)
            if prompt_usage(user["id"]) >= limit:
                fail("prompt_limit", "Prompt storage limit reached for your current plan", 403)
        return plan

    def owned_prompt(user_id: str, prompt_id: str) -> dict:
        row = db.one("SELECT * FROM prompts WHERE prompt_id=? AND owner_id=?", (prompt_id, user_id))
        if not row:
            fail("prompt_not_found", "Prompt not found", 404)
        return row

    def has_access(user_id: str, prompt_id: str) -> bool:
        if db.one("SELECT prompt_id FROM prompts WHERE prompt_id=? AND owner_id=?", (prompt_id, user_id)):
            return True
        return bool(db.one("SELECT purchase_id FROM prompt_purchases WHERE buyer_id=? AND prompt_id=? AND status='CONFIRMED'", (user_id, prompt_id)))

    def serialize_prompt(row: dict, full: bool = False) -> dict:
        out = dict(row)
        out["tags"] = _json_list(out.pop("tags_json", "[]"))
        out["ai_models"] = _json_list(out.pop("ai_models_json", "[]"))
        out["variables"] = _json_list(out.pop("variables_json", "[]"))
        if not full:
            out.pop("prompt_text", None)
            out.pop("system_instructions", None)
            out.pop("content_hash", None)
        return out

    def unique_slug(title: str, ignore_prompt_id: str | None = None) -> str:
        base = _slugify(title)
        candidate = base
        suffix = 2
        while True:
            row = db.one("SELECT prompt_id FROM prompts WHERE slug=?", (candidate,))
            if not row or row["prompt_id"] == ignore_prompt_id:
                return candidate
            candidate = f"{base}-{suffix}"
            suffix += 1

    @app.get("/api/v1/prompt-factory/config")
    def config():
        plans = db.all("SELECT plan_id,label,price_usd,max_prompts,commission_bps,features_json FROM prompt_plans WHERE active=1 ORDER BY CASE plan_id WHEN 'free' THEN 0 WHEN 'starter' THEN 1 WHEN 'creator' THEN 2 WHEN 'pro' THEN 3 ELSE 4 END")
        for p in plans:
            p["features"] = _json_list(p.pop("features_json"))
        addons = db.all("SELECT addon_id,label,price_usd,extra_slots FROM prompt_storage_addons WHERE active=1 ORDER BY extra_slots")
        return {"name": "Prompt Factory", "categories": CATEGORIES, "ai_models": AI_MODELS, "plans": plans, "storage_addons": addons, "marketplace_enabled": setting("marketplace_enabled", "true") == "true"}

    @app.get("/api/v1/prompt-factory/me")
    def prompt_me(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        plan = effective_prompt_plan(user)
        used = prompt_usage(user["id"])
        limit = None if plan.get("max_prompts") is None else int(plan["max_prompts"]) + int(plan.get("extra_slots") or 0)
        balance = db.one("SELECT available_usd,pending_usd,lifetime_earnings_usd,platform_fees_usd FROM seller_balances WHERE seller_id=?", (user["id"],)) or {"available_usd": 0, "pending_usd": 0, "lifetime_earnings_usd": 0, "platform_fees_usd": 0}
        return {"plan": plan, "storage": {"used": used, "limit": limit, "remaining": None if limit is None else max(0, limit - used)}, "seller_balance": balance}

    @app.post("/api/v1/prompt-factory/plans/{plan_id}/prepare-checkout")
    def prepare_plan_checkout(plan_id: str, authorization: str | None = Header(default=None)):
        current_user(authorization)
        plan = db.one("SELECT * FROM prompt_plans WHERE plan_id=? AND active=1", (plan_id,))
        if not plan or plan_id == "free":
            fail("plan_not_found", "Paid plan not found", 404)
        return {"product_id": f"prompt_plan_{plan_id}_30d", "price_usd": plan["price_usd"], "duration_days": 30}

    @app.post("/api/v1/prompt-factory/storage/{addon_id}/prepare-checkout")
    def prepare_storage_checkout(addon_id: str, authorization: str | None = Header(default=None)):
        current_user(authorization)
        addon = db.one("SELECT * FROM prompt_storage_addons WHERE addon_id=? AND active=1", (addon_id,))
        if not addon:
            fail("addon_not_found", "Storage add-on not found", 404)
        return {"product_id": f"prompt_storage_{addon_id}", "price_usd": addon["price_usd"], "extra_slots": addon["extra_slots"]}

    @app.get("/api/v1/prompt-factory/marketplace")
    def marketplace(
        q: str = Query(default="", max_length=120), category: str = Query(default="", max_length=60),
        model: str = Query(default="", max_length=80), sort: str = Query(default="trending", max_length=30),
        limit: int = Query(default=24, ge=1, le=100), offset: int = Query(default=0, ge=0, le=10000),
    ):
        if setting("marketplace_enabled", "true") != "true":
            return {"listings": [], "disabled": True}
        where = ["l.status='PUBLISHED'", "p.status='ACTIVE'"]
        args: list[Any] = []
        if q.strip():
            where.append("(LOWER(p.title) LIKE ? OR LOWER(p.description) LIKE ? OR LOWER(p.tags_json) LIKE ?)")
            needle = f"%{q.strip().lower()}%"
            args.extend([needle, needle, needle])
        if category.strip():
            where.append("p.category=?")
            args.append(category.strip().upper())
        if model.strip():
            where.append("LOWER(p.ai_models_json) LIKE ?")
            args.append(f"%{model.strip().lower()}%")
        orders = {
            "new": "l.updated_at DESC", "rating": "l.rating_avg DESC,l.rating_count DESC",
            "sales": "l.sales_count DESC", "price_low": "CAST(l.price_usd AS DECIMAL) ASC",
            "price_high": "CAST(l.price_usd AS DECIMAL) DESC", "trending": "l.featured DESC,l.sales_count DESC,l.rating_avg DESC,l.updated_at DESC",
        }
        sql = f"""SELECT l.listing_id,l.price_usd,l.pricing_model,l.license_type,l.preview_text,l.featured,l.sales_count,l.rating_avg,l.rating_count,
                  p.prompt_id,p.slug,p.title,p.description,p.category,p.tags_json,p.ai_models_json,u.display_name AS creator_name
                  FROM prompt_listings l JOIN prompts p ON p.prompt_id=l.prompt_id JOIN users u ON u.id=l.seller_id
                  WHERE {' AND '.join(where)} ORDER BY {orders.get(sort, orders['trending'])} LIMIT ? OFFSET ?"""
        args.extend([limit, offset])
        rows = db.all(sql, tuple(args))
        for row in rows:
            row["tags"] = _json_list(row.pop("tags_json"))
            row["ai_models"] = _json_list(row.pop("ai_models_json"))
        return {"listings": rows, "offset": offset, "limit": limit}

    @app.get("/api/v1/prompt-factory/listings/{slug}")
    def listing_detail(slug: str):
        row = db.one(
            """SELECT l.*,p.slug,p.title,p.description,p.category,p.subcategory,p.tags_json,p.ai_models_json,p.difficulty,p.language,
               u.display_name AS creator_name FROM prompt_listings l JOIN prompts p ON p.prompt_id=l.prompt_id
               JOIN users u ON u.id=l.seller_id WHERE p.slug=? AND l.status='PUBLISHED'""",
            (slug,),
        )
        if not row:
            fail("listing_not_found", "Listing not found", 404)
        row["tags"] = _json_list(row.pop("tags_json"))
        row["ai_models"] = _json_list(row.pop("ai_models_json"))
        row["examples"] = _json_list(row.pop("examples_json"))
        reviews = db.all("SELECT r.rating,r.comment,r.created_at,u.display_name FROM prompt_reviews r JOIN users u ON u.id=r.buyer_id WHERE r.prompt_id=? ORDER BY r.created_at DESC LIMIT 50", (row["prompt_id"],))
        return {"listing": row, "reviews": reviews}

    @app.get("/api/v1/prompt-factory/vault")
    def vault(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        owned = [serialize_prompt(r, True) for r in db.all("SELECT * FROM prompts WHERE owner_id=? AND status<>'ARCHIVED' ORDER BY updated_at DESC", (user["id"],))]
        bought_rows = db.all(
            """SELECT p.*,pp.purchase_id,pp.license_type AS purchased_license,pp.created_at AS purchased_at
               FROM prompt_purchases pp JOIN prompts p ON p.prompt_id=pp.prompt_id
               WHERE pp.buyer_id=? AND pp.status='CONFIRMED' ORDER BY pp.created_at DESC""",
            (user["id"],),
        )
        purchased = [serialize_prompt(r, True) for r in bought_rows]
        return {"owned": owned, "purchased": purchased}

    @app.post("/api/v1/prompt-factory/prompts")
    def create_prompt(body: PromptCreateIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        assert_capacity(user)
        category = body.category.strip().upper()
        if category not in CATEGORIES:
            category = "OTHER"
        visibility = body.visibility.strip().upper()
        if visibility not in {"PRIVATE", "UNLISTED", "PUBLIC", "FOR_SALE"}:
            visibility = "PRIVATE"
        variables_json = json.dumps(body.variables[:50], separators=(",", ":"))
        content_hash = _hash(body.prompt_text, body.system_instructions, variables_json)
        pid = "prm_" + uuid.uuid4().hex
        t = now()
        slug = unique_slug(body.title)
        db.execute(
            """INSERT INTO prompts(prompt_id,owner_id,slug,title,description,prompt_text,system_instructions,category,subcategory,
               tags_json,ai_models_json,difficulty,language,variables_json,visibility,status,content_hash,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, user["id"], slug, body.title.strip(), body.description.strip(), body.prompt_text, body.system_instructions,
             category, body.subcategory.strip(), json.dumps(body.tags[:20], separators=(",", ":")), json.dumps(body.ai_models[:20], separators=(",", ":")),
             body.difficulty.strip().upper(), body.language.strip(), variables_json, visibility, "ACTIVE", content_hash, t, t),
        )
        db.execute(
            """INSERT INTO prompt_versions(version_id,prompt_id,version_number,prompt_text,system_instructions,variables_json,changelog,content_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            ("pv_" + uuid.uuid4().hex, pid, 1, body.prompt_text, body.system_instructions, variables_json, "Initial version", content_hash, t),
        )
        audit(user["id"], "prompt_created", "prompt", pid)
        return {"prompt": serialize_prompt(db.one("SELECT * FROM prompts WHERE prompt_id=?", (pid,)), True), "version": 1}

    @app.get("/api/v1/prompt-factory/prompts/{prompt_id}")
    def get_prompt(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if not has_access(user["id"], prompt_id):
            fail("prompt_not_found", "Prompt not found", 404)
        row = db.one("SELECT * FROM prompts WHERE prompt_id=? AND status<>'ARCHIVED'", (prompt_id,))
        if not row:
            fail("prompt_not_found", "Prompt not found", 404)
        return {"prompt": serialize_prompt(row, True), "owned": row["owner_id"] == user["id"]}

    @app.put("/api/v1/prompt-factory/prompts/{prompt_id}")
    def update_prompt(prompt_id: str, body: PromptUpdateIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        current = owned_prompt(user["id"], prompt_id)
        data = body.model_dump(exclude_unset=True)
        title = data.get("title", current["title"])
        prompt_text = data.get("prompt_text", current["prompt_text"])
        system_text = data.get("system_instructions", current["system_instructions"])
        vars_json = json.dumps(data["variables"][:50], separators=(",", ":")) if "variables" in data else current["variables_json"]
        new_hash = _hash(prompt_text, system_text, vars_json)
        version_changed = new_hash != current["content_hash"]
        category = data.get("category", current["category"]).strip().upper()
        if category not in CATEGORIES:
            category = "OTHER"
        visibility = data.get("visibility", current["visibility"]).strip().upper()
        if visibility not in {"PRIVATE", "UNLISTED", "PUBLIC", "FOR_SALE"}:
            visibility = current["visibility"]
        t = now()
        db.execute(
            """UPDATE prompts SET slug=?,title=?,description=?,prompt_text=?,system_instructions=?,category=?,subcategory=?,tags_json=?,ai_models_json=?,
               difficulty=?,language=?,variables_json=?,visibility=?,content_hash=?,updated_at=? WHERE prompt_id=? AND owner_id=?""",
            (unique_slug(title, prompt_id), title.strip(), data.get("description", current["description"]), prompt_text, system_text, category,
             data.get("subcategory", current["subcategory"]), json.dumps(data["tags"][:20], separators=(",", ":")) if "tags" in data else current["tags_json"],
             json.dumps(data["ai_models"][:20], separators=(",", ":")) if "ai_models" in data else current["ai_models_json"],
             data.get("difficulty", current["difficulty"]).strip().upper(), data.get("language", current["language"]), vars_json, visibility, new_hash, t, prompt_id, user["id"]),
        )
        version = db.one("SELECT COALESCE(MAX(version_number),0) AS n FROM prompt_versions WHERE prompt_id=?", (prompt_id,))["n"]
        if version_changed:
            version = int(version) + 1
            db.execute(
                """INSERT INTO prompt_versions(version_id,prompt_id,version_number,prompt_text,system_instructions,variables_json,changelog,content_hash,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                ("pv_" + uuid.uuid4().hex, prompt_id, version, prompt_text, system_text, vars_json, data.get("changelog", "Updated prompt"), new_hash, t),
            )
        audit(user["id"], "prompt_updated", "prompt", prompt_id, {"version": int(version)})
        return {"prompt": serialize_prompt(db.one("SELECT * FROM prompts WHERE prompt_id=?", (prompt_id,)), True), "version": int(version)}

    @app.delete("/api/v1/prompt-factory/prompts/{prompt_id}")
    def archive_prompt(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        owned_prompt(user["id"], prompt_id)
        t = now()
        db.execute("UPDATE prompts SET status='ARCHIVED',archived_at=?,updated_at=? WHERE prompt_id=? AND owner_id=?", (t, t, prompt_id, user["id"]))
        db.execute("UPDATE prompt_listings SET status='ARCHIVED',updated_at=? WHERE prompt_id=?", (t, prompt_id))
        audit(user["id"], "prompt_archived", "prompt", prompt_id)
        return {"ok": True, "prompt_id": prompt_id}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/duplicate")
    def duplicate_prompt(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        source = owned_prompt(user["id"], prompt_id)
        assert_capacity(user)
        body = PromptCreateIn(
            title=f"{source['title']} Copy", description=source["description"], prompt_text=source["prompt_text"], system_instructions=source["system_instructions"],
            category=source["category"], subcategory=source["subcategory"], tags=_json_list(source["tags_json"]), ai_models=_json_list(source["ai_models_json"]),
            difficulty=source["difficulty"], language=source["language"], variables=_json_list(source["variables_json"]), visibility="PRIVATE",
        )
        return create_prompt(body, authorization)

    @app.get("/api/v1/prompt-factory/prompts/{prompt_id}/versions")
    def versions(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        owned_prompt(user["id"], prompt_id)
        rows = db.all("SELECT version_id,version_number,changelog,content_hash,created_at FROM prompt_versions WHERE prompt_id=? ORDER BY version_number DESC", (prompt_id,))
        return {"versions": rows}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/versions/{version_number}/restore")
    def restore_version(prompt_id: str, version_number: int, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        current = owned_prompt(user["id"], prompt_id)
        source = db.one("SELECT * FROM prompt_versions WHERE prompt_id=? AND version_number=?", (prompt_id, version_number))
        if not source:
            fail("version_not_found", "Version not found", 404)
        latest = int(db.one("SELECT COALESCE(MAX(version_number),0) AS n FROM prompt_versions WHERE prompt_id=?", (prompt_id,))["n"]) + 1
        t = now()
        db.execute("UPDATE prompts SET prompt_text=?,system_instructions=?,variables_json=?,content_hash=?,updated_at=? WHERE prompt_id=? AND owner_id=?",
                   (source["prompt_text"], source["system_instructions"], source["variables_json"], source["content_hash"], t, prompt_id, user["id"]))
        db.execute("""INSERT INTO prompt_versions(version_id,prompt_id,version_number,prompt_text,system_instructions,variables_json,changelog,content_hash,created_at)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                   ("pv_" + uuid.uuid4().hex, prompt_id, latest, source["prompt_text"], source["system_instructions"], source["variables_json"], f"Restored v{version_number}", source["content_hash"], t))
        audit(user["id"], "prompt_version_restored", "prompt", prompt_id, {"from": version_number, "to": latest})
        return {"prompt": serialize_prompt(db.one("SELECT * FROM prompts WHERE prompt_id=?", (prompt_id,)), True), "version": latest}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/render")
    def render_prompt(prompt_id: str, body: RenderIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if not has_access(user["id"], prompt_id):
            fail("prompt_not_found", "Prompt not found", 404)
        row = db.one("SELECT prompt_text,variables_json FROM prompts WHERE prompt_id=? AND status<>'ARCHIVED'", (prompt_id,))
        if not row:
            fail("prompt_not_found", "Prompt not found", 404)
        rendered = row["prompt_text"]
        allowed = {str(v.get("name") or "").strip() for v in _json_list(row["variables_json"]) if isinstance(v, dict)}
        for key, value in body.values.items():
            if key in allowed or not allowed:
                rendered = rendered.replace("{{" + key + "}}", str(value))
        return {"rendered_prompt": rendered}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/sell")
    def sell_prompt(prompt_id: str, body: ListingIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        prompt = owned_prompt(user["id"], prompt_id)
        if setting("marketplace_enabled", "true") != "true":
            fail("marketplace_disabled", "Marketplace is disabled", 503)
        pricing_model = body.pricing_model.strip().upper()
        if pricing_model not in {"FREE", "FIXED", "SALE_PRICE"}:
            fail("pricing_model_unsupported", "This pricing model is not enabled yet", 400)
        try:
            price = _money(body.price_usd)
        except Exception:
            fail("invalid_price", "Invalid price", 400)
        if pricing_model == "FREE":
            price = Decimal("0.00")
        minimum = _money(setting("minimum_prompt_price_usd", "0.00"))
        maximum = _money(setting("maximum_prompt_price_usd", "1000.00"))
        if price < minimum or price > maximum:
            fail("invalid_price", "Price is outside marketplace limits", 400)
        license_type = body.license_type.strip().upper()
        if license_type not in {"PERSONAL", "COMMERCIAL", "EXTENDED"}:
            fail("invalid_license", "Invalid license", 400)
        existing = db.one("SELECT * FROM prompt_listings WHERE prompt_id=?", (prompt_id,))
        listing_id = existing["listing_id"] if existing else "pfl_" + uuid.uuid4().hex
        product_id = existing["product_id"] if existing else "prompt_listing_" + listing_id
        plan = effective_prompt_plan(user)
        commission_bps = int(plan.get("commission_bps") or setting("default_commission_bps", "1500"))
        status = "PENDING_REVIEW" if setting("manual_listing_approval", "false") == "true" else "PUBLISHED"
        t = now()
        db.execute(
            """INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at)
               VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET label=excluded.label,description=excluded.description,
               price_usd=excluded.price_usd,entitlement_key=excluded.entitlement_key,active=excluded.active""",
            (product_id, prompt["title"], prompt["description"], str(price), f"prompt_listing:{listing_id}", 1 if price > 0 else 0, t),
        )
        db.execute(
            """INSERT INTO prompt_listings(listing_id,prompt_id,seller_id,product_id,price_usd,pricing_model,license_type,preview_text,examples_json,status,commission_bps,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(prompt_id) DO UPDATE SET price_usd=excluded.price_usd,pricing_model=excluded.pricing_model,
               license_type=excluded.license_type,preview_text=excluded.preview_text,examples_json=excluded.examples_json,status=excluded.status,
               commission_bps=excluded.commission_bps,updated_at=excluded.updated_at""",
            (listing_id, prompt_id, user["id"], product_id, str(price), pricing_model, license_type, body.preview_text.strip(), json.dumps(body.examples[:10], separators=(",", ":")), status, commission_bps, t, t),
        )
        db.execute("UPDATE prompts SET visibility='FOR_SALE',updated_at=? WHERE prompt_id=?", (t, prompt_id))
        audit(user["id"], "prompt_listed", "prompt", prompt_id, {"listing_id": listing_id, "price_usd": str(price), "commission_bps": commission_bps})
        return {"listing": db.one("SELECT * FROM prompt_listings WHERE listing_id=?", (listing_id,)), "product_id": product_id}

    @app.post("/api/v1/prompt-factory/listings/{listing_id}/prepare-checkout")
    def prepare_listing_checkout(listing_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        listing = db.one("SELECT * FROM prompt_listings WHERE listing_id=? AND status='PUBLISHED'", (listing_id,))
        if not listing:
            fail("listing_not_found", "Listing not found", 404)
        if listing["seller_id"] == user["id"]:
            fail("self_purchase", "You cannot buy your own prompt", 409)
        if db.one("SELECT purchase_id FROM prompt_purchases WHERE buyer_id=? AND listing_id=? AND status='CONFIRMED'", (user["id"], listing_id)):
            return {"already_owned": True, "prompt_id": listing["prompt_id"]}
        if _money(listing["price_usd"]) == Decimal("0.00"):
            return {"free": True, "listing_id": listing_id}
        product = db.one("SELECT product_id,price_usd FROM products WHERE product_id=? AND active=1", (listing["product_id"],))
        if not product:
            fail("product_unavailable", "Listing checkout is unavailable", 503)
        return {"product_id": product["product_id"], "price_usd": product["price_usd"], "listing_id": listing_id}

    @app.post("/api/v1/prompt-factory/listings/{listing_id}/acquire-free")
    def acquire_free(listing_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        listing = db.one("SELECT * FROM prompt_listings WHERE listing_id=? AND status='PUBLISHED'", (listing_id,))
        if not listing:
            fail("listing_not_found", "Listing not found", 404)
        if listing["seller_id"] == user["id"]:
            fail("self_purchase", "You already own this prompt", 409)
        if _money(listing["price_usd"]) != Decimal("0.00"):
            fail("payment_required", "This prompt requires payment", 402)
        existing = db.one("SELECT * FROM prompt_purchases WHERE buyer_id=? AND listing_id=?", (user["id"], listing_id))
        if existing:
            return {"purchase": existing}
        pid = "ppur_" + uuid.uuid4().hex
        t = now()
        db.execute("""INSERT INTO prompt_purchases(purchase_id,buyer_id,seller_id,prompt_id,listing_id,license_type,gross_usd,platform_fee_usd,seller_amount_usd,payment_asset,payment_network,status,created_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (pid, user["id"], listing["seller_id"], listing["prompt_id"], listing_id, listing["license_type"], "0", "0", "0", "FREE", "FREE", "CONFIRMED", t))
        db.execute("UPDATE prompt_listings SET sales_count=sales_count+1,updated_at=? WHERE listing_id=?", (t, listing_id))
        audit(user["id"], "prompt_free_acquired", "prompt", listing["prompt_id"], {"listing_id": listing_id})
        return {"purchase": db.one("SELECT * FROM prompt_purchases WHERE purchase_id=?", (pid,))}

    @app.post("/api/v1/prompt-factory/prompts/{prompt_id}/favorite")
    def toggle_favorite(prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if not db.one("SELECT prompt_id FROM prompts WHERE prompt_id=? AND status='ACTIVE'", (prompt_id,)):
            fail("prompt_not_found", "Prompt not found", 404)
        existing = db.one("SELECT user_id FROM prompt_favorites WHERE user_id=? AND prompt_id=?", (user["id"], prompt_id))
        if existing:
            db.execute("DELETE FROM prompt_favorites WHERE user_id=? AND prompt_id=?", (user["id"], prompt_id))
            return {"favorite": False}
        db.execute("INSERT INTO prompt_favorites(user_id,prompt_id,created_at) VALUES(?,?,?)", (user["id"], prompt_id, now()))
        return {"favorite": True}

    @app.get("/api/v1/prompt-factory/favorites")
    def favorites(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all("""SELECT p.prompt_id,p.slug,p.title,p.description,p.category,f.created_at FROM prompt_favorites f
                         JOIN prompts p ON p.prompt_id=f.prompt_id WHERE f.user_id=? ORDER BY f.created_at DESC""", (user["id"],))
        return {"favorites": rows}

    @app.post("/api/v1/prompt-factory/purchases/{purchase_id}/review")
    def review_purchase(purchase_id: str, body: ReviewIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if setting("reviews_enabled", "true") != "true":
            fail("reviews_disabled", "Reviews are disabled", 403)
        purchase = db.one("SELECT * FROM prompt_purchases WHERE purchase_id=? AND buyer_id=? AND status='CONFIRMED'", (purchase_id, user["id"]))
        if not purchase:
            fail("verified_purchase_required", "Verified purchase required", 403)
        t = now()
        existing = db.one("SELECT review_id FROM prompt_reviews WHERE purchase_id=?", (purchase_id,))
        review_id = existing["review_id"] if existing else "prev_" + uuid.uuid4().hex
        db.execute("""INSERT INTO prompt_reviews(review_id,purchase_id,buyer_id,prompt_id,rating,comment,created_at,updated_at)
                      VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(purchase_id) DO UPDATE SET rating=excluded.rating,comment=excluded.comment,updated_at=excluded.updated_at""",
                   (review_id, purchase_id, user["id"], purchase["prompt_id"], body.rating, body.comment.strip(), t, t))
        stats = db.one("SELECT COUNT(*) AS n,COALESCE(AVG(rating),0) AS avg FROM prompt_reviews WHERE prompt_id=?", (purchase["prompt_id"],))
        db.execute("UPDATE prompt_listings SET rating_count=?,rating_avg=?,updated_at=? WHERE prompt_id=?", (stats["n"], stats["avg"], t, purchase["prompt_id"]))
        return {"review_id": review_id, "rating": body.rating}

    @app.get("/api/v1/prompt-factory/creator/dashboard")
    def creator_dashboard(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        balance = db.one("SELECT * FROM seller_balances WHERE seller_id=?", (user["id"],)) or {"available_usd": 0, "pending_usd": 0, "lifetime_earnings_usd": 0, "platform_fees_usd": 0}
        sales = db.one("SELECT COUNT(*) AS n,COALESCE(SUM(gross_usd),0) AS gross,COALESCE(SUM(seller_amount_usd),0) AS net,COALESCE(SUM(platform_fee_usd),0) AS fees FROM prompt_purchases WHERE seller_id=? AND status='CONFIRMED'", (user["id"],))
        top = db.all("""SELECT p.prompt_id,p.title,l.listing_id,l.sales_count,l.rating_avg,l.rating_count,l.price_usd FROM prompt_listings l
                        JOIN prompts p ON p.prompt_id=l.prompt_id WHERE l.seller_id=? ORDER BY l.sales_count DESC,l.rating_avg DESC LIMIT 10""", (user["id"],))
        return {"balance": balance, "sales": sales, "top_prompts": top}

    @app.post("/api/v1/prompt-factory/collections")
    def create_collection(body: CollectionIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        cid = "pcol_" + uuid.uuid4().hex
        t = now()
        visibility = body.visibility.strip().upper()
        if visibility not in {"PRIVATE", "PUBLIC", "UNLISTED"}:
            visibility = "PRIVATE"
        db.execute("INSERT INTO prompt_collections(collection_id,owner_id,title,description,visibility,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                   (cid, user["id"], body.title.strip(), body.description.strip(), visibility, t, t))
        return {"collection": db.one("SELECT * FROM prompt_collections WHERE collection_id=?", (cid,))}

    @app.get("/api/v1/prompt-factory/collections")
    def list_collections(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all("SELECT * FROM prompt_collections WHERE owner_id=? ORDER BY updated_at DESC", (user["id"],))
        return {"collections": rows}

    @app.post("/api/v1/prompt-factory/collections/{collection_id}/items")
    def add_collection_item(collection_id: str, body: CollectionItemIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        collection = db.one("SELECT * FROM prompt_collections WHERE collection_id=? AND owner_id=?", (collection_id, user["id"]))
        if not collection:
            fail("collection_not_found", "Collection not found", 404)
        if not has_access(user["id"], body.prompt_id):
            fail("prompt_not_found", "Prompt not found", 404)
        pos = db.one("SELECT COALESCE(MAX(position),-1)+1 AS n FROM prompt_collection_items WHERE collection_id=?", (collection_id,))["n"]
        db.execute("INSERT INTO prompt_collection_items(collection_id,prompt_id,position) VALUES(?,?,?) ON CONFLICT(collection_id,prompt_id) DO NOTHING", (collection_id, body.prompt_id, pos))
        db.execute("UPDATE prompt_collections SET updated_at=? WHERE collection_id=?", (now(), collection_id))
        return {"ok": True}

    @app.get("/api/v1/prompt-factory/admin/overview")
    def admin_overview(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {
            "prompts": db.one("SELECT COUNT(*) AS n FROM prompts WHERE status<>'ARCHIVED'")["n"],
            "published_listings": db.one("SELECT COUNT(*) AS n FROM prompt_listings WHERE status='PUBLISHED'")["n"],
            "pending_listings": db.one("SELECT COUNT(*) AS n FROM prompt_listings WHERE status='PENDING_REVIEW'")["n"],
            "sales": db.one("SELECT COUNT(*) AS n FROM prompt_purchases WHERE status='CONFIRMED'")["n"],
            "gmv_usd": db.one("SELECT COALESCE(SUM(gross_usd),0) AS n FROM prompt_purchases WHERE status='CONFIRMED'")["n"],
            "platform_fees_usd": db.one("SELECT COALESCE(SUM(platform_fee_usd),0) AS n FROM prompt_purchases WHERE status='CONFIRMED'")["n"],
        }

    @app.get("/api/v1/prompt-factory/admin/listings")
    def admin_listings(authorization: str | None = Header(default=None)):
        admin_user(authorization)
        return {"listings": db.all("""SELECT l.*,p.title,p.slug,u.display_name AS seller_name FROM prompt_listings l
                                     JOIN prompts p ON p.prompt_id=l.prompt_id JOIN users u ON u.id=l.seller_id
                                     ORDER BY l.updated_at DESC LIMIT 200""")}

    @app.post("/api/v1/prompt-factory/admin/listings/{listing_id}/status")
    def admin_listing_status(listing_id: str, body: AdminListingStatusIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        status = body.status.strip().upper()
        if status not in {"PENDING_REVIEW", "PUBLISHED", "PAUSED", "REJECTED", "ARCHIVED"}:
            fail("invalid_status", "Invalid listing status", 400)
        listing = db.one("SELECT * FROM prompt_listings WHERE listing_id=?", (listing_id,))
        if not listing:
            fail("listing_not_found", "Listing not found", 404)
        db.execute("UPDATE prompt_listings SET status=?,updated_at=? WHERE listing_id=?", (status, now(), listing_id))
        db.execute("UPDATE products SET active=? WHERE product_id=?", (1 if status == "PUBLISHED" and _money(listing["price_usd"]) > 0 else 0, listing["product_id"]))
        audit(admin["id"], "prompt_listing_moderated", "prompt_listing", listing_id, {"status": status})
        return {"ok": True, "listing_id": listing_id, "status": status}

    @app.put("/api/v1/prompt-factory/admin/settings/{key}")
    def admin_setting(key: str, body: AdminSettingIn, authorization: str | None = Header(default=None)):
        admin = admin_user(authorization)
        if key not in SETTING_SEEDS:
            fail("invalid_setting", "Unknown Prompt Factory setting", 404)
        db.execute("INSERT INTO prompt_platform_settings(setting_key,setting_value,updated_at) VALUES(?,?,?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_at=excluded.updated_at", (key, body.value.strip(), now()))
        audit(admin["id"], "prompt_factory_setting_updated", "setting", key, {"value": body.value.strip()})
        return {"ok": True, "key": key, "value": body.value.strip()}
