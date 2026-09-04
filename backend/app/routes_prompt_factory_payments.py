from __future__ import annotations

from typing import Callable

from fastapi import Header

from .routes_prompt_factory import apply_prompt_factory_entitlement
from .routes_prompt_factory_advanced import register_prompt_factory_advanced_routes


RECONCILIATION_SCHEMA = """CREATE TABLE IF NOT EXISTS prompt_entitlement_events(
    order_id TEXT PRIMARY KEY REFERENCES orders(order_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entitlement_key TEXT NOT NULL,
    applied_at INTEGER NOT NULL
)"""


def register_prompt_factory_payment_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    db.execute(RECONCILIATION_SCHEMA)
    db.execute("CREATE INDEX IF NOT EXISTS idx_prompt_entitlement_user ON prompt_entitlement_events(user_id,applied_at)")

    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    def reconcile_user(user_id: str) -> dict:
        rows = db.all(
            """SELECT o.*,p.entitlement_key AS pf_entitlement
               FROM purchase_history ph
               JOIN orders o ON o.order_id=ph.order_id
               JOIN products p ON p.product_id=ph.product_id
               WHERE ph.user_id=? AND o.status='FULFILLED' AND p.entitlement_key LIKE ?
               ORDER BY ph.created_at ASC""",
            (user_id, "prompt_%"),
        )
        applied = 0
        for order in rows:
            order_id = order["order_id"]
            entitlement = order.get("pf_entitlement") or ""
            if db.one("SELECT order_id FROM prompt_entitlement_events WHERE order_id=?", (order_id,)):
                continue
            apply_prompt_factory_entitlement(
                db,
                user_id=user_id,
                entitlement=entitlement,
                order=order,
                order_id=order_id,
                now=now,
                audit=audit,
            )
            complete = True
            if entitlement.startswith("prompt_listing:"):
                complete = bool(db.one("SELECT purchase_id FROM prompt_purchases WHERE order_id=?", (order_id,)))
            elif entitlement.startswith("prompt_plan:"):
                plan_id = entitlement.split(":", 1)[1]
                complete = bool(db.one("SELECT user_id FROM prompt_user_plans WHERE user_id=? AND plan_id=?", (user_id, plan_id)))
            elif entitlement.startswith("prompt_storage:"):
                complete = bool(db.one("SELECT user_id FROM prompt_user_storage WHERE user_id=?", (user_id,)))
            elif entitlement.startswith("prompt_collection:"):
                complete = False
            if not complete:
                continue
            db.execute(
                "INSERT INTO prompt_entitlement_events(order_id,user_id,entitlement_key,applied_at) VALUES(?,?,?,?) ON CONFLICT(order_id) DO NOTHING",
                (order_id, user_id, entitlement, now()),
            )
            applied += 1
        return {"ok": True, "applied": applied, "checked": len(rows)}

    @app.post("/api/v1/prompt-factory/reconcile")
    def reconcile(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        result = reconcile_user(user["id"])
        if result["applied"]:
            audit(user["id"], "prompt_factory_reconciled", "user", user["id"], result)
        return result

    register_prompt_factory_advanced_routes(
        app,
        db=db,
        session_user=session_user,
        audit=audit,
        fail=fail,
        now=now,
    )
