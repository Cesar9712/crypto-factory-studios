from __future__ import annotations

import io
from typing import Callable

import qrcode
from fastapi import Header
from fastapi.responses import Response
from qrcode.image.svg import SvgPathImage


def register_payment_extra_routes(app, *, db, settings, payment_methods, session_user: Callable, fail: Callable):
    @app.get('/api/v1/payments/orders/{order_id}/qr.svg')
    def payment_qr(order_id: str, authorization: str | None = Header(default=None)):
        user, _ = session_user(authorization)
        order = db.one('SELECT * FROM orders WHERE order_id=? AND user_id=?', (order_id, user['id']))
        if not order:
            fail('order_not_found', 'Order not found', 404)
        if settings.payments_mode != 'PRODUCTION' or not settings.production_payments_enabled:
            fail('payment_mode_test', 'Real payment QR is disabled outside production', 403)
        method = payment_methods.get(order['method_id'])
        if not method or not method.enabled or not method.production_allowed:
            fail('payment_method_unavailable', 'Payment method unavailable', 400)
        # Encode only the server-authoritative treasury address. The amount and
        # network remain visible beside the QR so wallets cannot reinterpret a
        # vendor-specific URI unexpectedly.
        image = qrcode.make(method.address, image_factory=SvgPathImage)
        out = io.BytesIO()
        image.save(out)
        return Response(content=out.getvalue(), media_type='image/svg+xml', headers={'Cache-Control': 'no-store'})
