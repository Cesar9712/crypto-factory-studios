from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from fastapi import Header
from pydantic import BaseModel, Field


def _json_list(raw: Any) -> list:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


def _serialize_prompt(row: dict, full: bool = False) -> dict:
    out = dict(row)
    out["tags"] = _json_list(out.pop("tags_json", "[]"))
    out["ai_models"] = _json_list(out.pop("ai_models_json", "[]"))
    out["variables"] = _json_list(out.pop("variables_json", "[]"))
    if not full:
        out.pop("prompt_text", None)
        out.pop("system_instructions", None)
        out.pop("content_hash", None)
    return out


class AnalyticsOverrideIn(BaseModel):
    event_type: str = Field(min_length=2, max_length=60)
    prompt_id: str | None = Field(default=None, max_length=80)
    listing_id: str | None = Field(default=None, max_length=80)
    creator_id: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


def register_prompt_factory_override_routes(app, *, db, session_user: Callable):
    """Register narrow compatibility routes before the base Prompt Factory router.

    These routes preserve API compatibility while exposing server-side purchase
    traceability and keeping non-public marketplace analytics private.
    """

    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    @app.get("/api/v1/prompt-factory/vault")
    def vault_with_purchase_trace(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        owned = [
            _serialize_prompt(row, True)
            for row in db.all(
                "SELECT * FROM prompts WHERE owner_id=? AND status<>'ARCHIVED' ORDER BY updated_at DESC",
                (user["id"],),
            )
        ]
        bought_rows = db.all(
            """SELECT p.*,pp.purchase_id,pp.order_id,pp.listing_id,
                      pp.license_type AS purchased_license,pp.gross_usd,
                      pp.payment_asset,pp.payment_network,pp.created_at AS purchased_at
               FROM prompt_purchases pp
               JOIN prompts p ON p.prompt_id=pp.prompt_id
               WHERE pp.buyer_id=? AND pp.status='CONFIRMED'
               ORDER BY pp.created_at DESC""",
            (user["id"],),
        )
        purchased = [_serialize_prompt(row, True) for row in bought_rows]
        return {"owned": owned, "purchased": purchased}

    @app.post("/api/v1/prompt-factory/analytics/events")
    def analytics_event_override(body: AnalyticsOverrideIn, authorization: str | None = Header(default=None)):
        user = None
        if authorization:
            try:
                user = current_user(authorization)
            except Exception:
                user = None

        prompt_id = body.prompt_id
        listing_id = body.listing_id
        creator_id = None

        if listing_id:
            listing = db.one(
                "SELECT seller_id,prompt_id,status FROM prompt_listings WHERE listing_id=?",
                (listing_id,),
            )
            if not listing:
                raise _not_found("listing_not_found", "Listing not found")
            status = str(listing["status"]).upper()
            is_owner_preview = bool(user and user["id"] == listing["seller_id"] and status in {"PENDING_REVIEW", "PAUSED", "DRAFT"})
            if status != "PUBLISHED" and not is_owner_preview:
                raise _not_found("listing_not_found", "Published listing not found")
            creator_id = listing["seller_id"]
            prompt_id = listing["prompt_id"]
        elif prompt_id:
            prompt = db.one(
                "SELECT owner_id,visibility,status FROM prompts WHERE prompt_id=?",
                (prompt_id,),
            )
            if not prompt or str(prompt["status"]).upper() != "ACTIVE":
                raise _not_found("prompt_not_found", "Prompt not found")
            visibility = str(prompt["visibility"]).upper()
            is_owner_preview = bool(user and user["id"] == prompt["owner_id"])
            if visibility not in {"PUBLIC", "FOR_SALE"} and not is_owner_preview:
                raise _not_found("prompt_not_found", "Public prompt not found")
            creator_id = prompt["owner_id"]
        else:
            # Do not trust an arbitrary creator_id supplied by the client.
            raise _bad_request("analytics_target_required", "A prompt_id or listing_id is required")

        event_id = "pae_" + uuid.uuid4().hex
        db.execute(
            "INSERT INTO prompt_analytics_events(event_id,user_id,event_type,prompt_id,listing_id,creator_id,metadata_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                event_id,
                user["id"] if user else None,
                body.event_type.strip().upper(),
                prompt_id,
                listing_id,
                creator_id,
                json.dumps(body.metadata, separators=(",", ":"))[:8000],
                __import__("time").time_ns() // 1_000_000_000,
            ),
        )
        return {"ok": True}


def _not_found(code: str, message: str):
    from fastapi import HTTPException
    return HTTPException(404, detail={"error_code": code, "message": message})


def _bad_request(code: str, message: str):
    from fastapi import HTTPException
    return HTTPException(400, detail={"error_code": code, "message": message})
