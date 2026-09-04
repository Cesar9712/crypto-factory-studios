from __future__ import annotations

from typing import Callable

from fastapi import Header


def register_prompt_factory_finishing_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    @app.post('/api/v1/prompt-factory/reconcile-finishing')
    def reconcile_finishing(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all(
            """SELECT i.product_id,i.license_type,i.redeemed_order_id
               FROM prompt_checkout_intents i
               WHERE i.buyer_id=? AND i.redeemed_order_id IS NOT NULL""",
            (user['id'],),
        )
        updated = 0
        for row in rows:
            purchase = db.one(
                "SELECT purchase_id,license_type FROM prompt_purchases WHERE buyer_id=? AND order_id=? AND status='CONFIRMED'",
                (user['id'], row['redeemed_order_id']),
            )
            if purchase and purchase['license_type'] != row['license_type']:
                db.execute(
                    "UPDATE prompt_purchases SET license_type=? WHERE purchase_id=? AND buyer_id=?",
                    (row['license_type'], purchase['purchase_id'], user['id']),
                )
                updated += 1
        if updated:
            audit(user['id'], 'prompt_checkout_license_reconciled', 'user', user['id'], {'updated': updated})
        return {'ok': True, 'licenses_updated': updated, 'checked': len(rows)}
