from __future__ import annotations

from typing import Callable

from fastapi import Header


def register_prompt_factory_finishing_routes(app, *, db, session_user: Callable, audit: Callable, fail: Callable, now: Callable):
    def current_user(authorization: str | None):
        user, _ = session_user(authorization)
        return user

    @app.get('/api/v1/prompt-factory/creator/profile')
    def my_seller_profile(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        return {'profile': db.one('SELECT * FROM prompt_seller_profiles WHERE user_id=?', (user['id'],))}

    @app.get('/api/v1/prompt-factory/listings/{listing_id}/checkout-options')
    def checkout_options(listing_id: str):
        listing = db.one("SELECT listing_id,price_usd,pricing_model,license_type FROM prompt_listings WHERE listing_id=? AND status='PUBLISHED'", (listing_id,))
        if not listing:
            fail('listing_not_found', 'Listing not found', 404)
        t = now()
        promotion = db.one(
            "SELECT promotion_id,label,sale_price_usd,starts_at,ends_at FROM prompt_promotions WHERE listing_id=? AND active=1 AND starts_at<=? AND ends_at>=? ORDER BY sale_price_usd ASC LIMIT 1",
            (listing_id, t, t),
        )
        licenses = db.all(
            "SELECT license_type,price_usd FROM prompt_listing_license_options WHERE listing_id=? AND active=1 ORDER BY price_usd",
            (listing_id,),
        )
        if not licenses:
            licenses = [{'license_type': listing['license_type'], 'price_usd': listing['price_usd']}]
        return {'listing': listing, 'promotion': promotion, 'licenses': licenses}

    @app.get('/api/v1/prompt-factory/creator/promotions')
    def my_promotions(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        rows = db.all("""SELECT pr.*,p.title FROM prompt_promotions pr JOIN prompt_listings l ON l.listing_id=pr.listing_id
                         JOIN prompts p ON p.prompt_id=l.prompt_id WHERE pr.seller_id=? ORDER BY pr.created_at DESC""", (user['id'],))
        return {'promotions': rows}

    @app.get('/api/v1/prompt-factory/creator/coupons')
    def my_coupons(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        return {'coupons': db.all('SELECT * FROM prompt_coupons WHERE seller_id=? ORDER BY created_at DESC', (user['id'],))}

    @app.put('/api/v1/prompt-factory/promotions/{promotion_id}/active')
    def promotion_active(promotion_id: str, active: bool, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        row = db.one('SELECT promotion_id FROM prompt_promotions WHERE promotion_id=? AND seller_id=?', (promotion_id, user['id']))
        if not row:
            fail('promotion_not_found', 'Promotion not found', 404)
        db.execute('UPDATE prompt_promotions SET active=?,updated_at=? WHERE promotion_id=? AND seller_id=?', (1 if active else 0, now(), promotion_id, user['id']))
        return {'ok': True, 'active': active}

    @app.put('/api/v1/prompt-factory/coupons/{coupon_id}/active')
    def coupon_active(coupon_id: str, active: bool, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        row = db.one('SELECT coupon_id FROM prompt_coupons WHERE coupon_id=? AND seller_id=?', (coupon_id, user['id']))
        if not row:
            fail('coupon_not_found', 'Coupon not found', 404)
        db.execute('UPDATE prompt_coupons SET active=?,updated_at=? WHERE coupon_id=? AND seller_id=?', (1 if active else 0, now(), coupon_id, user['id']))
        return {'ok': True, 'active': active}

    @app.put('/api/v1/prompt-factory/listings/{listing_id}/seller-status')
    def seller_listing_status(listing_id: str, status: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        listing = db.one('SELECT * FROM prompt_listings WHERE listing_id=? AND seller_id=?', (listing_id, user['id']))
        if not listing:
            fail('listing_not_found', 'Listing not found', 404)
        value = status.strip().upper()
        if value not in {'PUBLISHED', 'PAUSED', 'SOLD_OUT', 'ARCHIVED'}:
            fail('invalid_status', 'Invalid listing status', 400)
        if value == 'PUBLISHED':
            profile = db.one('SELECT blocked FROM prompt_seller_profiles WHERE user_id=?', (user['id'],))
            if profile and int(profile.get('blocked') or 0):
                fail('seller_blocked', 'Seller is blocked', 403)
        db.execute('UPDATE prompt_listings SET status=?,updated_at=? WHERE listing_id=? AND seller_id=?', (value, now(), listing_id, user['id']))
        db.execute('UPDATE products SET active=? WHERE product_id=?', (1 if value == 'PUBLISHED' and float(listing['price_usd']) > 0 and listing['pricing_model'] != 'PAY_WHAT_YOU_WANT' else 0, listing['product_id']))
        audit(user['id'], 'prompt_listing_status_changed', 'prompt_listing', listing_id, {'status': value})
        return {'ok': True, 'status': value}

    @app.get('/api/v1/prompt-factory/creator/collection-offers')
    def my_collection_offers(authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        return {'offers': db.all("""SELECT o.*,c.title,c.description FROM prompt_collection_offers o
                                  JOIN prompt_collections c ON c.collection_id=o.collection_id WHERE o.seller_id=? ORDER BY o.updated_at DESC""", (user['id'],))}

    @app.get('/api/v1/prompt-factory/collections/{collection_id}/items')
    def collection_items(collection_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        collection = db.one('SELECT * FROM prompt_collections WHERE collection_id=?', (collection_id,))
        if not collection:
            fail('collection_not_found', 'Collection not found', 404)
        if collection['owner_id'] != user['id'] and collection['visibility'] not in {'PUBLIC', 'UNLISTED'}:
            fail('collection_not_found', 'Collection not found', 404)
        rows = db.all("""SELECT p.prompt_id,p.title,p.description,p.category,ci.position FROM prompt_collection_items ci
                         JOIN prompts p ON p.prompt_id=ci.prompt_id WHERE ci.collection_id=? ORDER BY ci.position""", (collection_id,))
        return {'collection': collection, 'items': rows}

    @app.delete('/api/v1/prompt-factory/collections/{collection_id}/items/{prompt_id}')
    def remove_collection_item(collection_id: str, prompt_id: str, authorization: str | None = Header(default=None)):
        user = current_user(authorization)
        if not db.one('SELECT collection_id FROM prompt_collections WHERE collection_id=? AND owner_id=?', (collection_id, user['id'])):
            fail('collection_not_found', 'Collection not found', 404)
        db.execute('DELETE FROM prompt_collection_items WHERE collection_id=? AND prompt_id=?', (collection_id, prompt_id))
        db.execute('UPDATE prompt_collections SET updated_at=? WHERE collection_id=?', (now(), collection_id))
        return {'ok': True}

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
