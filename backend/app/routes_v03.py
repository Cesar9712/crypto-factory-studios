from __future__ import annotations

import json
import sqlite3
import uuid
from decimal import Decimal
from typing import Any, Callable

from fastapi import Header, Request
from pydantic import BaseModel, Field


class BecomeCreatorIn(BaseModel):
    creator_slug: str = Field(min_length=3, max_length=40)
    bio: str = Field(default='', max_length=500)


class GameCreateIn(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    description: str = Field(default='', max_length=4000)
    genre: str = Field(default='Other', max_length=40)
    tags: list[str] = []
    visibility: str = 'PUBLIC'
    web3_enabled: bool = False


class QuoteIn(BaseModel):
    product_id: str = Field(min_length=3, max_length=80)
    method_id: str = Field(min_length=3, max_length=40)


class OrderIn(BaseModel):
    quote_id: str = Field(min_length=8, max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=120)


class SubmitTxIn(BaseModel):
    transaction_hash: str = Field(min_length=6, max_length=160)


def register_routes(
    app,
    *,
    db,
    settings,
    payment_methods,
    price_service,
    payment_verifier,
    session_user: Callable,
    creator_profile: Callable,
    effective_plan: Callable,
    audit: Callable,
    fail: Callable,
    slugify: Callable,
    now: Callable,
    payment_fingerprint: Callable,
):
    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    def require_creator(user: dict[str, Any]):
        cp = creator_profile(user['id'])
        if not cp:
            fail('creator_required', 'Creator account required', 403)
        return cp

    @app.get('/api/v1/products')
    def products():
        rows = db.all('SELECT product_id,label,description,price_usd,entitlement_key FROM products WHERE active=1 ORDER BY price_usd')
        return {'products': rows}

    @app.get('/api/v1/payments/methods')
    def methods():
        return {'mode': settings.payments_mode, 'methods': payment_methods.public()}

    @app.get('/api/v1/games')
    def games():
        rows = db.all('''SELECT g.game_id,g.slug,g.title,g.description,g.genre,g.tags_json,g.status,g.web3_enabled,
                         u.display_name AS creator_name
                         FROM games g JOIN users u ON u.id=g.creator_id
                         WHERE g.status='PUBLISHED' AND g.visibility='PUBLIC'
                         ORDER BY g.updated_at DESC''')
        for row in rows:
            row['tags'] = json.loads(row.pop('tags_json') or '[]')
        return {'games': rows}

    @app.get('/api/v1/games/{slug}')
    def game_detail(slug: str):
        row = db.one('''SELECT g.game_id,g.slug,g.title,g.description,g.genre,g.tags_json,g.status,g.web3_enabled,
                        u.display_name AS creator_name
                        FROM games g JOIN users u ON u.id=g.creator_id
                        WHERE g.slug=? AND g.status='PUBLISHED' AND g.visibility='PUBLIC' ''', (slug,))
        if not row:
            fail('game_not_found', 'Game not found', 404)
        row['tags'] = json.loads(row.pop('tags_json') or '[]')
        return {'game': row, 'play_url': f'/play/{row["slug"]}/'}

    @app.post('/api/v1/creator/activate')
    def activate_creator(body: BecomeCreatorIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        existing = creator_profile(user['id'])
        if existing:
            return {'creator': existing}
        slug = slugify(body.creator_slug)
        t = now()
        try:
            db.execute('INSERT INTO creator_profiles(user_id,slug,bio,trust_level,plan_id,billing_exempt,created_at) VALUES(?,?,?,?,?,?,?)',
                       (user['id'], slug, body.bio.strip(), 'NEW', 'free', 0, t))
        except sqlite3.IntegrityError:
            fail('creator_slug_taken', 'Creator slug is already in use', 409)
        audit(user['id'], 'creator_activated', 'creator', user['id'])
        return {'creator': creator_profile(user['id'])}

    @app.get('/api/v1/creator/overview')
    def creator_overview(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        cp = require_creator(user)
        plan = effective_plan(user['id']) or {}
        limits = plan.get('limits') or {}
        game_count = db.one('SELECT COUNT(*) AS n FROM games WHERE creator_id=?', (user['id'],))['n']
        published = db.one("SELECT COUNT(*) AS n FROM games WHERE creator_id=? AND status='PUBLISHED'", (user['id'],))['n']
        builds = db.one('SELECT COUNT(*) AS n,COALESCE(SUM(compressed_bytes),0) AS bytes FROM game_builds WHERE creator_id=?', (user['id'],))
        clean = db.one("SELECT COUNT(*) AS n FROM game_builds WHERE creator_id=? AND scan_status='CLEAN'", (user['id'],))['n']
        return {
            'plan_id': cp['plan_id'],
            'games': game_count,
            'published_games': published,
            'builds': builds['n'],
            'clean_builds': clean,
            'storage_bytes': builds['bytes'],
            'limits': limits,
        }

    @app.get('/api/v1/creator/games')
    def creator_games(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        require_creator(user)
        rows = db.all('SELECT game_id,slug,title,description,genre,status,visibility,web3_enabled,created_at,updated_at FROM games WHERE creator_id=? ORDER BY updated_at DESC', (user['id'],))
        return {'games': rows}

    @app.post('/api/v1/creator/games')
    def create_game(body: GameCreateIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        cp = require_creator(user)
        plan = effective_plan(user['id']) or {}
        limits = plan.get('limits') or {}
        max_games = limits.get('max_games')
        current = db.one('SELECT COUNT(*) AS n FROM games WHERE creator_id=?', (user['id'],))['n']
        if max_games is not None and current >= max_games:
            fail('plan_limit', 'Game limit reached for current plan', 403)
        base = slugify(body.title)
        slug = base
        suffix = 2
        while db.one('SELECT game_id FROM games WHERE slug=?', (slug,)):
            slug = f'{base}-{suffix}'
            suffix += 1
        gid = 'game_' + uuid.uuid4().hex
        t = now()
        db.execute('''INSERT INTO games(game_id,creator_id,slug,title,description,genre,tags_json,status,visibility,web3_enabled,created_at,updated_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                   (gid, user['id'], slug, body.title.strip(), body.description.strip(), body.genre.strip(), json.dumps(body.tags[:12]), 'DRAFT', body.visibility.upper(), 1 if body.web3_enabled else 0, t, t))
        audit(user['id'], 'game_created', 'game', gid)
        return {'game': db.one('SELECT game_id,slug,title,description,genre,status,visibility,web3_enabled,created_at,updated_at FROM games WHERE game_id=?', (gid,))}

    @app.get('/api/v1/payments/quotes')
    def quotes_not_supported():
        fail('method_not_allowed', 'Use POST to create a payment quote', 405)

    @app.post('/api/v1/payments/quotes')
    def create_quote(body: QuoteIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        product = db.one('SELECT * FROM products WHERE product_id=? AND active=1', (body.product_id,))
        if not product:
            fail('product_not_found', 'Product not found', 404)
        cp = creator_profile(user['id'])
        if cp and cp.get('billing_exempt'):
            fail('billing_exempt', 'This account is billing exempt', 403)
        method = payment_methods.get(body.method_id)
        if not method or not method.enabled:
            fail('payment_method_unavailable', 'Payment method unavailable', 400)
        if settings.payments_mode == 'PRODUCTION' and not method.production_allowed:
            fail('payment_method_locked', 'Payment method is not enabled for production', 403)
        usd = Decimal(product['price_usd'])
        amount, rate, source = price_service.quote_amount(usd, method)
        qid = 'quote_' + uuid.uuid4().hex
        t = now()
        db.execute('''INSERT INTO payment_quotes(quote_id,user_id,product_id,method_id,fiat_price_usd,crypto_amount,exchange_rate,rate_source,created_at,expires_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?)''',
                   (qid, user['id'], product['product_id'], method.method_id, str(usd), str(amount), str(rate), source, t, t + settings.quote_seconds))
        return {'quote_id': qid, 'product_id': product['product_id'], 'method_id': method.method_id, 'fiat_price_usd': str(usd), 'crypto_amount': str(amount), 'exchange_rate': str(rate), 'rate_source': source, 'expires_at': t + settings.quote_seconds}

    @app.post('/api/v1/payments/orders')
    def create_order(body: OrderIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        existing = db.one('SELECT * FROM orders WHERE idempotency_key=?', (body.idempotency_key,))
        if existing:
            if existing['user_id'] != user['id']:
                fail('idempotency_conflict', 'Idempotency key already used', 409)
            return existing
        quote = db.one('SELECT * FROM payment_quotes WHERE quote_id=? AND user_id=?', (body.quote_id, user['id']))
        if not quote:
            fail('quote_not_found', 'Quote not found', 404)
        if quote['expires_at'] < now():
            fail('quote_expired', 'Quote expired', 409)
        method = payment_methods.get(quote['method_id'])
        if not method:
            fail('payment_method_unavailable', 'Payment method unavailable', 400)
        oid = 'ord_' + uuid.uuid4().hex
        t = now()
        db.execute('''INSERT INTO orders(order_id,user_id,product_id,quote_id,method_id,expected_amount,asset,network,receiving_address,status,created_at,expires_at,idempotency_key)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                   (oid, user['id'], quote['product_id'], quote['quote_id'], method.method_id, quote['crypto_amount'], method.asset, method.network, method.address, 'AWAITING_PAYMENT', t, t + settings.order_seconds, body.idempotency_key))
        audit(user['id'], 'payment_order_created', 'order', oid, {'method_id': method.method_id})
        return db.one('SELECT * FROM orders WHERE order_id=?', (oid,))

    @app.get('/api/v1/payments/orders/{order_id}/checkout')
    def checkout(order_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        order = db.one('SELECT * FROM orders WHERE order_id=? AND user_id=?', (order_id, user['id']))
        if not order:
            fail('order_not_found', 'Order not found', 404)
        method = payment_methods.get(order['method_id'])
        if not method:
            fail('payment_method_unavailable', 'Payment method unavailable', 400)
        return {'order': order, 'payment_method': {'method_id': method.method_id, 'asset': method.asset, 'network': method.network, 'standard': method.standard, 'address': method.address, 'warning': method.warning}}

    @app.post('/api/v1/payments/orders/{order_id}/submit-tx')
    def submit_tx(order_id: str, body: SubmitTxIn, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        order = db.one('SELECT * FROM orders WHERE order_id=? AND user_id=?', (order_id, user['id']))
        if not order:
            fail('order_not_found', 'Order not found', 404)
        if order['status'] in {'FULFILLED', 'CONFIRMED'}:
            return order
        if order['expires_at'] < now():
            db.execute("UPDATE orders SET status='EXPIRED' WHERE order_id=?", (order_id,))
            return db.one('SELECT * FROM orders WHERE order_id=?', (order_id,))
        method = payment_methods.get(order['method_id'])
        if not method:
            fail('payment_method_unavailable', 'Payment method unavailable', 400)
        txid = body.transaction_hash.strip()
        duplicate = db.one('SELECT order_id FROM blockchain_transactions WHERE network=? AND transaction_hash=?', (method.network, txid))
        if duplicate and duplicate['order_id'] != order_id:
            fail('transaction_replayed', 'Transaction already used by another order', 409)
        verification = payment_verifier.verify(method, txid, Decimal(order['expected_amount']))
        status = verification.get('status', 'FAILED')
        received = verification.get('received_amount', order['received_amount'])
        mapped = status
        if status == 'CONFIRMED':
            mapped = 'CONFIRMED'
        elif status in {'NOT_FOUND', 'WRONG_NETWORK', 'WRONG_RECIPIENT', 'WRONG_ASSET', 'FAILED'}:
            mapped = 'MANUAL_REVIEW' if status.startswith('WRONG_') else 'FAILED'
        db.execute('UPDATE orders SET status=?,received_amount=?,transaction_hash=? WHERE order_id=?', (mapped, str(received), txid, order_id))
        db.execute('INSERT INTO payment_events(order_id,event_type,details_json,created_at) VALUES(?,?,?,?)', (order_id, status, json.dumps(verification, separators=(',', ':')), now()))
        if status == 'CONFIRMED':
            fp = payment_fingerprint(method.network, txid)
            try:
                db.execute('INSERT INTO blockchain_transactions(fingerprint,network,transaction_hash,order_id,verification_json,consumed_at) VALUES(?,?,?,?,?,?)', (fp, method.network, txid, order_id, json.dumps(verification, separators=(',', ':')), now()))
            except sqlite3.IntegrityError:
                fail('transaction_replayed', 'Transaction already consumed', 409)
            product = db.one('SELECT * FROM products WHERE product_id=?', (order['product_id'],))
            entitlement = product['entitlement_key'] if product else ''
            if entitlement.startswith('creator_plan:'):
                plan_id = entitlement.split(':', 1)[1]
                cp = creator_profile(user['id'])
                if not cp:
                    fail('creator_required', 'Creator account required for this plan', 409)
                if cp.get('billing_exempt'):
                    fail('billing_exempt', 'Billing-exempt account cannot be changed by payment', 403)
                db.execute('UPDATE creator_profiles SET plan_id=? WHERE user_id=?', (plan_id, user['id']))
            if entitlement:
                db.execute('INSERT OR REPLACE INTO entitlements(user_id,entitlement_key,source,granted_at) VALUES(?,?,?,?)', (user['id'], entitlement, order_id, now()))
            purchase_id = 'pur_' + uuid.uuid4().hex
            db.execute('INSERT OR IGNORE INTO purchase_history(purchase_id,user_id,order_id,product_id,amount,asset,network,transaction_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                       (purchase_id, user['id'], order_id, order['product_id'], order['expected_amount'], method.asset, method.network, txid, now()))
            db.execute("UPDATE orders SET status='FULFILLED',confirmed_at=?,fulfilled_at=? WHERE order_id=?", (now(), now(), order_id))
            audit(user['id'], 'payment_fulfilled', 'order', order_id, {'transaction_hash': txid})
        return db.one('SELECT * FROM orders WHERE order_id=?', (order_id,))

    @app.get('/api/v1/purchases')
    def purchases(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all('SELECT purchase_id,order_id,product_id,amount,asset,network,transaction_hash,created_at FROM purchase_history WHERE user_id=? ORDER BY created_at DESC', (user['id'],))
        return {'purchases': rows}
