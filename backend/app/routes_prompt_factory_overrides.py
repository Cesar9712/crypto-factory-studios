from __future__ import annotations

import json
from typing import Any, Callable

from fastapi import Header


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


def register_prompt_factory_override_routes(app, *, db, session_user: Callable):
    """Register narrow compatibility routes before the base Prompt Factory router.

    These routes preserve API compatibility while exposing server-side purchase
    traceability that the advanced checkout/reconciliation layer needs.
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
