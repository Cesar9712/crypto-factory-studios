from __future__ import annotations

import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable

from fastapi import BackgroundTasks, Header, Request
from pydantic import BaseModel, Field

from .tropipay import TropiPayClient, TropiPayError


TROPIPAY_METHOD_ID = "tropipay_card"


class TropiPayCheckoutIn(BaseModel):
    product_id: str = Field(min_length=3, max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=120)


def register_tropipay_routes(
    app,
    *,
    db,
    settings,
    session_user: Callable,
    creator_profile: Callable,
    audit: Callable,
    fail: Callable,
    now: Callable,
):
    client = TropiPayClient(settings)

    def ensure_method() -> None:
        enabled = 1 if client.enabled else 0
        db.execute(
            """INSERT INTO payment_methods(method_id,asset,network,standard,address,token_contract,enabled,production_allowed,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(method_id) DO UPDATE SET
               asset=excluded.asset,network=excluded.network,standard=excluded.standard,address=excluded.address,
               token_contract=excluded.token_contract,enabled=excluded.enabled,
               production_allowed=excluded.production_allowed,updated_at=excluded.updated_at""",
            (
                TROPIPAY_METHOD_ID,
                settings.tropipay_currency,
                "TROPIPAY",
                "CARD/PAYLINK",
                "provider-hosted-checkout",
                None,
                enabled,
                enabled,
                now(),
            ),
        )

    ensure_method()

    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    def public_base(request: Request) -> str:
        configured = settings.public_base_url.strip().rstrip("/")
        return configured or str(request.base_url).rstrip("/")

    def cents(value: str) -> int:
        return int((Decimal(str(value)) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def fulfill_order(order_id: str, movement: dict[str, Any]) -> dict[str, Any]:
        order = db.one("SELECT * FROM orders WHERE order_id=?", (order_id,))
        if not order:
            raise TropiPayError("Order not found")
        if order["status"] == "FULFILLED":
            return order
        link = db.one("SELECT * FROM tropipay_payment_links WHERE order_id=?", (order_id,))
        if not link:
            raise TropiPayError("TropiPay link not found")

        movement_id = str(movement.get("id") or "")
        state = str(movement.get("state") or "").lower()
        if (
            state != "completed"
            or str(movement.get("reference") or "") != link["reference"]
            or str(movement.get("currency") or "").upper() != str(link["currency"]).upper()
            or int(movement.get("amount") or 0) != int(link["amount_cents"])
            or not movement_id
        ):
            raise TropiPayError("Movement verification mismatch")

        provider_tx = f"tropipay:{movement_id}"
        existing = db.one(
            "SELECT order_id FROM orders WHERE network='TROPIPAY' AND transaction_hash=?",
            (provider_tx,),
        )
        if existing and existing["order_id"] != order_id:
            raise TropiPayError("TropiPay movement already consumed")

        product = db.one("SELECT * FROM products WHERE product_id=?", (order["product_id"],))
        if not product:
            raise TropiPayError("Product no longer exists")
        entitlement = product["entitlement_key"] or ""
        user_id = order["user_id"]

        if entitlement.startswith("creator_plan:"):
            plan_id = entitlement.split(":", 1)[1]
            cp = creator_profile(user_id)
            if not cp:
                raise TropiPayError("Creator account required for this plan")
            if cp.get("billing_exempt"):
                raise TropiPayError("Billing-exempt account cannot be changed by payment")
            db.execute("UPDATE creator_profiles SET plan_id=? WHERE user_id=?", (plan_id, user_id))

        if entitlement:
            db.execute(
                """INSERT INTO entitlements(user_id,entitlement_key,source,granted_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(user_id,entitlement_key) DO UPDATE SET
                   source=excluded.source,granted_at=excluded.granted_at""",
                (user_id, entitlement, order_id, now()),
            )

        purchase_id = "pur_" + uuid.uuid4().hex
        db.execute(
            """INSERT OR IGNORE INTO purchase_history
               (purchase_id,user_id,order_id,product_id,amount,asset,network,transaction_hash,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                purchase_id,
                user_id,
                order_id,
                order["product_id"],
                order["expected_amount"],
                order["asset"],
                "TROPIPAY",
                provider_tx,
                now(),
            ),
        )
        db.execute(
            """UPDATE tropipay_payment_links
               SET provider_movement_id=?,provider_state='completed',raw_json=?,updated_at=?
               WHERE order_id=?""",
            (movement_id, json.dumps(movement, separators=(",", ":")), now(), order_id),
        )
        db.execute(
            """UPDATE orders
               SET status='FULFILLED',received_amount=expected_amount,transaction_hash=?,
                   confirmed_at=?,fulfilled_at=?
               WHERE order_id=?""",
            (provider_tx, now(), now(), order_id),
        )
        audit(
            user_id,
            "tropipay_payment_fulfilled",
            "order",
            order_id,
            {"movement_id": movement_id, "reference": link["reference"]},
        )
        return db.one("SELECT * FROM orders WHERE order_id=?", (order_id,))

    def verify_and_fulfill(order_id: str) -> tuple[dict[str, Any], bool]:
        order = db.one("SELECT * FROM orders WHERE order_id=? AND method_id=?", (order_id, TROPIPAY_METHOD_ID))
        if not order:
            raise TropiPayError("Order not found")
        if order["status"] == "FULFILLED":
            return order, True
        link = db.one("SELECT * FROM tropipay_payment_links WHERE order_id=?", (order_id,))
        if not link:
            raise TropiPayError("TropiPay link not found")
        movement = client.find_movement(
            reference=link["reference"],
            amount_cents=int(link["amount_cents"]),
            currency=link["currency"],
        )
        if not movement:
            return order, False
        state = str(movement.get("state") or "").lower()
        db.execute(
            "UPDATE tropipay_payment_links SET provider_state=?,raw_json=?,updated_at=? WHERE order_id=?",
            (state, json.dumps(movement, separators=(",", ":")), now(), order_id),
        )
        if state == "completed":
            return fulfill_order(order_id, movement), True
        if state in {"failed", "cancelled"}:
            db.execute("UPDATE orders SET status=? WHERE order_id=?", (state.upper(), order_id))
        else:
            db.execute("UPDATE orders SET status='CONFIRMING' WHERE order_id=?", (order_id,))
        return db.one("SELECT * FROM orders WHERE order_id=?", (order_id,)), False

    def background_verify(order_id: str) -> None:
        try:
            verify_and_fulfill(order_id)
        except Exception:
            # Return path verification provides a second recovery path.
            pass

    @app.get("/api/v1/payments/tropipay/status")
    def tropipay_status():
        return {
            "enabled": client.enabled,
            "environment": settings.tropipay_environment,
            "currency": settings.tropipay_currency,
            "provider": "tropipay",
        }

    @app.post("/api/v1/payments/tropipay/checkout")
    def create_tropipay_checkout(
        body: TropiPayCheckoutIn,
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        if not client.enabled:
            fail("tropipay_unavailable", "TropiPay card checkout is not configured yet", 503)
        user = current_user(authorization)
        existing = db.one("SELECT * FROM orders WHERE idempotency_key=?", (body.idempotency_key,))
        if existing:
            if existing["user_id"] != user["id"] or existing["method_id"] != TROPIPAY_METHOD_ID:
                fail("idempotency_conflict", "Idempotency key already used", 409)
            link = db.one("SELECT * FROM tropipay_payment_links WHERE order_id=?", (existing["order_id"],))
            if link:
                return {
                    "order_id": existing["order_id"],
                    "pay_url": link["pay_url"],
                    "status": existing["status"],
                    "provider": "tropipay",
                }

        product = db.one("SELECT * FROM products WHERE product_id=? AND active=1", (body.product_id,))
        if not product:
            fail("product_not_found", "Product not found", 404)
        cp = creator_profile(user["id"])
        if cp and cp.get("billing_exempt"):
            fail("billing_exempt", "This account is billing exempt", 403)
        entitlement = product["entitlement_key"] or ""
        if entitlement.startswith("creator_plan:") and not cp:
            fail("creator_required", "Activate a creator account before buying this plan", 409)

        amount_cents = cents(product["price_usd"])
        if amount_cents < 100:
            fail("amount_too_small", "TropiPay requires a minimum charge of 1.00", 409)

        qid = "quote_" + uuid.uuid4().hex
        oid = "ord_" + uuid.uuid4().hex
        reference = f"cfs-{oid}"
        t = now()
        amount = f"{Decimal(product['price_usd']).quantize(Decimal('0.01')):.2f}"
        db.execute(
            """INSERT INTO payment_quotes
               (quote_id,user_id,product_id,method_id,fiat_price_usd,crypto_amount,exchange_rate,rate_source,created_at,expires_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (qid, user["id"], product["product_id"], TROPIPAY_METHOD_ID, amount, amount, "1", "tropipay_fiat", t, t + 3600),
        )
        db.execute(
            """INSERT INTO orders
               (order_id,user_id,product_id,quote_id,method_id,expected_amount,asset,network,receiving_address,status,created_at,expires_at,idempotency_key)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                oid,
                user["id"],
                product["product_id"],
                qid,
                TROPIPAY_METHOD_ID,
                amount,
                settings.tropipay_currency,
                "TROPIPAY",
                "provider-hosted-checkout",
                "CREATING_PAYMENT",
                t,
                t + 86400,
                body.idempotency_key,
            ),
        )

        base = public_base(request)
        try:
            paylink = client.create_paylink(
                reference=reference,
                concept=product["label"],
                description=product["description"] or product["label"],
                amount_cents=amount_cents,
                currency=settings.tropipay_currency,
                success_url=f"{base}/billing.html?tropipay=success&order_id={oid}",
                failed_url=f"{base}/billing.html?tropipay=failed&order_id={oid}",
                notification_url=f"{base}/api/v1/payments/tropipay/webhook",
            )
        except TropiPayError:
            db.execute("UPDATE orders SET status='FAILED' WHERE order_id=?", (oid,))
            fail("tropipay_provider_error", "Could not create card checkout", 503)

        db.execute(
            """INSERT INTO tropipay_payment_links
               (order_id,reference,provider_payment_id,pay_url,amount_cents,currency,provider_state,raw_json,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                oid,
                reference,
                str(paylink.get("id") or ""),
                str(paylink["shortUrl"]),
                amount_cents,
                settings.tropipay_currency,
                str(paylink.get("state") or "active"),
                json.dumps(paylink, separators=(",", ":")),
                now(),
            ),
        )
        db.execute(
            "UPDATE orders SET status='AWAITING_PAYMENT',receiving_address=? WHERE order_id=?",
            (str(paylink["shortUrl"]), oid),
        )
        audit(user["id"], "tropipay_checkout_created", "order", oid, {"reference": reference})
        return {
            "order_id": oid,
            "pay_url": str(paylink["shortUrl"]),
            "amount": amount,
            "currency": settings.tropipay_currency,
            "status": "AWAITING_PAYMENT",
            "provider": "tropipay",
            "environment": settings.tropipay_environment,
        }

    @app.post("/api/v1/payments/tropipay/orders/{order_id}/verify")
    def verify_tropipay_order(order_id: str, authorization: str | None = Header(default=None)):
        if not client.enabled:
            fail("tropipay_unavailable", "TropiPay card checkout is not configured yet", 503)
        user = current_user(authorization)
        order = db.one(
            "SELECT * FROM orders WHERE order_id=? AND user_id=? AND method_id=?",
            (order_id, user["id"], TROPIPAY_METHOD_ID),
        )
        if not order:
            fail("order_not_found", "Order not found", 404)
        try:
            updated, verified = verify_and_fulfill(order_id)
        except TropiPayError:
            fail("tropipay_verification_error", "Could not verify card payment", 503)
        return {"order": updated, "verified": verified, "provider": "tropipay"}

    @app.post("/api/v1/payments/tropipay/webhook")
    async def tropipay_webhook(request: Request, background_tasks: BackgroundTasks):
        try:
            payload = await request.json()
        except Exception:
            return {"ok": False}
        data = payload.get("data") if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            data = {}
        reference = str(data.get("reference") or payload.get("reference") or "")
        if not reference:
            return {"ok": True}
        link = db.one("SELECT * FROM tropipay_payment_links WHERE reference=?", (reference,))
        if not link:
            return {"ok": True}
        state = str(data.get("stateStr") or data.get("state") or payload.get("state") or "")
        db.execute(
            "UPDATE tropipay_payment_links SET provider_state=?,raw_json=?,updated_at=? WHERE order_id=?",
            (state, json.dumps(payload, separators=(",", ":")), now(), link["order_id"]),
        )
        # A webhook never grants an entitlement directly. Verify independently
        # through the authenticated Movements API after returning the callback.
        background_tasks.add_task(background_verify, link["order_id"])
        return {"ok": True}
