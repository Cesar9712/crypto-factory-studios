import time
import uuid

from fastapi.testclient import TestClient

from backend.app.main import app, db


PASSWORD = "VeryStrongPromptFactoryPassword123!"


def register_user(client: TestClient, prefix: str):
    suffix = uuid.uuid4().hex[:10]
    email = f"{prefix}-{suffix}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": PASSWORD,
        "display_name": f"{prefix.title()} User",
    })
    assert r.status_code == 200, r.text
    me = client.get("/api/v1/me")
    assert me.status_code == 200
    return email, me.json()["user"], {"X-CSRF-Token": client.cookies.get("cfs_csrf")}


def login_user(client: TestClient, email: str):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": client.cookies.get("cfs_csrf")}


def logout(client: TestClient, headers: dict):
    r = client.post("/api/v1/auth/logout", headers=headers)
    assert r.status_code == 200, r.text


def create_prompt(client: TestClient, headers: dict, title: str, text: str | None = None):
    r = client.post("/api/v1/prompt-factory/prompts", headers=headers, json={
        "title": title,
        "description": "Advanced marketplace test prompt",
        "prompt_text": text or "Build a complete {{PRODUCT_NAME}} launch plan with measurable outcomes.",
        "system_instructions": "Be precise.",
        "category": "MARKETING",
        "tags": ["advanced", "marketplace"],
        "ai_models": ["ChatGPT"],
        "variables": [{"name": "PRODUCT_NAME", "label": "Product name"}],
    })
    assert r.status_code == 200, r.text
    return r.json()["prompt"]


def create_seller_profile(client: TestClient, headers: dict, username: str):
    r = client.put("/api/v1/prompt-factory/creator/profile", headers=headers, json={
        "username": username,
        "bio": "Prompt Factory seller",
        "avatar_url": "https://example.com/avatar.png",
    })
    assert r.status_code == 200, r.text
    return r.json()["profile"]


def pay_product(client: TestClient, headers: dict, product_id: str):
    q = client.post("/api/v1/payments/quotes", headers=headers, json={"product_id": product_id, "method_id": "usdt_tron"})
    assert q.status_code == 200, q.text
    order = client.post("/api/v1/payments/orders", headers=headers, json={
        "quote_id": q.json()["quote_id"],
        "idempotency_key": "pf-advanced-" + uuid.uuid4().hex,
    })
    assert order.status_code == 200, order.text
    order_id = order.json()["order_id"]
    paid = client.post(f"/api/v1/payments/orders/{order_id}/submit-tx", headers=headers, json={
        "transaction_hash": "mock_prompt_factory_advanced_" + uuid.uuid4().hex,
    })
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "FULFILLED"
    return order_id


def test_advanced_creator_profile_follow_assets_saved_search_export_import():
    with TestClient(app) as client:
        seller_email, seller, seller_headers = register_user(client, "adv-profile")
        username = "seller_" + uuid.uuid4().hex[:8]
        profile = create_seller_profile(client, seller_headers, username)
        assert profile["username"] == username

        prompt = create_prompt(client, seller_headers, "Asset Prompt " + uuid.uuid4().hex[:6])
        asset = client.post(f"/api/v1/prompt-factory/prompts/{prompt['prompt_id']}/assets", headers=seller_headers, json={
            "kind": "COVER",
            "label": "Cover",
            "url": "https://example.com/prompt-cover.webp",
            "media_type": "image/webp",
        })
        assert asset.status_code == 200, asset.text

        saved = client.post("/api/v1/prompt-factory/saved-searches", headers=seller_headers, json={
            "label": "Marketing prompts",
            "query": {"category": "MARKETING", "sort": "rating"},
        })
        assert saved.status_code == 200
        searches = client.get("/api/v1/prompt-factory/saved-searches")
        assert searches.status_code == 200
        assert any(x["label"] == "Marketing prompts" for x in searches.json()["searches"])

        exported = client.get("/api/v1/prompt-factory/export")
        assert exported.status_code == 200
        assert exported.json()["format"] == "cfs-prompt-vault-v1"
        exported_prompt = next(p for p in exported.json()["prompts"] if p["prompt_id"] == prompt["prompt_id"])
        assert exported_prompt["assets"][0]["kind"] == "COVER"

        public_creator = client.get(f"/api/v1/prompt-factory/creators/{username}")
        assert public_creator.status_code == 200
        assert public_creator.json()["creator"]["user_id"] == seller["id"]

        logout(client, seller_headers)
        _, follower, follower_headers = register_user(client, "adv-follower")
        followed = client.post(f"/api/v1/prompt-factory/creators/{seller['id']}/follow", headers=follower_headers)
        assert followed.status_code == 200 and followed.json()["following"] is True
        following = client.get("/api/v1/prompt-factory/following")
        assert any(x["user_id"] == seller["id"] for x in following.json()["following"])

        imported = client.post("/api/v1/prompt-factory/import", headers=follower_headers, json={"prompts": [exported_prompt]})
        assert imported.status_code == 200, imported.text
        assert imported.json()["imported"] == 1

        logout(client, follower_headers)
        login_user(client, seller_email)
        creator = client.get(f"/api/v1/prompt-factory/creators/{username}")
        assert creator.json()["stats"]["followers"] >= 1


def test_pay_what_you_want_coupon_license_referral_and_payout():
    with TestClient(app) as client:
        affiliate_email, affiliate, affiliate_headers = register_user(client, "adv-affiliate")
        referral = client.get("/api/v1/prompt-factory/referrals/me")
        assert referral.status_code == 200
        code = referral.json()["referral"]["code"]
        logout(client, affiliate_headers)

        seller_email, seller, seller_headers = register_user(client, "adv-seller")
        create_seller_profile(client, seller_headers, "seller_" + uuid.uuid4().hex[:8])
        prompt = create_prompt(client, seller_headers, "PWYW Prompt " + uuid.uuid4().hex[:6])
        listed = client.post(f"/api/v1/prompt-factory/prompts/{prompt['prompt_id']}/publish-advanced", headers=seller_headers, json={
            "price_usd": "10.00",
            "pricing_model": "PAY_WHAT_YOU_WANT",
            "license_type": "PERSONAL",
            "preview_text": "Premium protected prompt",
            "examples": ["Example"],
        })
        assert listed.status_code == 200, listed.text
        listing = listed.json()["listing"]
        assert listing["status"] == "PUBLISHED"
        listing_id = listing["listing_id"]

        licenses = client.put(f"/api/v1/prompt-factory/listings/{listing_id}/licenses", headers=seller_headers, json=[
            {"license_type": "PERSONAL", "price_usd": "10.00", "active": True},
            {"license_type": "EXTENDED", "price_usd": "10.00", "active": True},
        ])
        assert licenses.status_code == 200, licenses.text

        t = int(time.time())
        coupon = client.post("/api/v1/prompt-factory/coupons", headers=seller_headers, json={
            "listing_id": listing_id,
            "code": "SAVE10" + uuid.uuid4().hex[:5].upper(),
            "discount_type": "PERCENT",
            "discount_value": "10",
            "max_uses": 5,
            "starts_at": t - 60,
            "ends_at": t + 3600,
        })
        assert coupon.status_code == 200, coupon.text
        coupon_code = coupon.json()["coupon"]["code"]
        logout(client, seller_headers)

        buyer_email, buyer, buyer_headers = register_user(client, "adv-buyer")
        attributed = client.post("/api/v1/prompt-factory/referrals/attribute", headers=buyer_headers, json={"code": code})
        assert attributed.status_code == 200

        checkout = client.post(f"/api/v1/prompt-factory/listings/{listing_id}/checkout-advanced", headers=buyer_headers, json={
            "amount_usd": "20.00",
            "coupon_code": coupon_code,
            "license_type": "EXTENDED",
        })
        assert checkout.status_code == 200, checkout.text
        assert checkout.json()["price_usd"] == "18.00"
        order_id = pay_product(client, buyer_headers, checkout.json()["product_id"])

        base_reconcile = client.post("/api/v1/prompt-factory/reconcile", headers=buyer_headers)
        assert base_reconcile.status_code == 200
        advanced = client.post("/api/v1/prompt-factory/reconcile-advanced", headers=buyer_headers)
        assert advanced.status_code == 200, advanced.text
        finishing = client.post("/api/v1/prompt-factory/reconcile-finishing", headers=buyer_headers)
        assert finishing.status_code == 200, finishing.text

        vault = client.get("/api/v1/prompt-factory/vault")
        bought = next(x for x in vault.json()["purchased"] if x["prompt_id"] == prompt["prompt_id"])
        assert bought["purchased_license"] == "EXTENDED"
        assert bought["order_id"] == order_id

        logout(client, buyer_headers)
        seller_headers = login_user(client, seller_email)
        dashboard = client.get("/api/v1/prompt-factory/creator/dashboard")
        assert dashboard.status_code == 200
        available = float(dashboard.json()["balance"]["available_usd"])
        assert abs(available - 14.40) < 0.001

        payout = client.post("/api/v1/prompt-factory/payouts", headers=seller_headers, json={
            "amount_usd": "10.00",
            "method": "USDT_TRON",
            "destination": "TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9",
        })
        assert payout.status_code == 200, payout.text
        assert payout.json()["payout"]["status"] == "PENDING"
        logout(client, seller_headers)

        affiliate_headers = login_user(client, affiliate_email)
        referral_state = client.get("/api/v1/prompt-factory/referrals/me")
        assert referral_state.status_code == 200
        assert abs(float(referral_state.json()["earnings"]["n"]) - 0.54) < 0.001
        pf_me = client.get("/api/v1/prompt-factory/me")
        assert abs(float(pf_me.json()["seller_balance"]["available_usd"]) - 0.54) < 0.001


def test_collection_bundle_purchase_is_idempotent_and_unlocks_library():
    with TestClient(app) as client:
        seller_email, seller, seller_headers = register_user(client, "adv-bundle-seller")
        create_seller_profile(client, seller_headers, "bundle_" + uuid.uuid4().hex[:8])
        p1 = create_prompt(client, seller_headers, "Bundle One " + uuid.uuid4().hex[:6])
        p2 = create_prompt(client, seller_headers, "Bundle Two " + uuid.uuid4().hex[:6], "Second protected prompt body")
        collection = client.post("/api/v1/prompt-factory/collections", headers=seller_headers, json={
            "title": "Premium Bundle " + uuid.uuid4().hex[:6],
            "description": "Two prompt bundle",
            "visibility": "PUBLIC",
        })
        assert collection.status_code == 200
        cid = collection.json()["collection"]["collection_id"]
        for prompt in (p1, p2):
            added = client.post(f"/api/v1/prompt-factory/collections/{cid}/items", headers=seller_headers, json={"prompt_id": prompt["prompt_id"]})
            assert added.status_code == 200, added.text

        offer = client.post(f"/api/v1/prompt-factory/collections/{cid}/offer", headers=seller_headers, json={
            "pricing_model": "BUNDLE",
            "price_usd": "12.00",
            "license_type": "COMMERCIAL",
            "duration_days": 0,
        })
        assert offer.status_code == 200, offer.text
        offer_id = offer.json()["offer"]["offer_id"]
        logout(client, seller_headers)

        _, buyer, buyer_headers = register_user(client, "adv-bundle-buyer")
        checkout = client.post(f"/api/v1/prompt-factory/collection-offers/{offer_id}/prepare-checkout", headers=buyer_headers)
        assert checkout.status_code == 200, checkout.text
        pay_product(client, buyer_headers, checkout.json()["product_id"])
        standard = client.post("/api/v1/prompt-factory/reconcile", headers=buyer_headers)
        assert standard.status_code == 200
        first = client.post("/api/v1/prompt-factory/reconcile-advanced", headers=buyer_headers)
        assert first.status_code == 200, first.text
        assert first.json()["advanced_applied"] == 1
        second = client.post("/api/v1/prompt-factory/reconcile-advanced", headers=buyer_headers)
        assert second.status_code == 200
        assert second.json()["advanced_applied"] == 0

        library = client.get("/api/v1/prompt-factory/collection-library")
        ids = {x["prompt_id"] for x in library.json()["prompts"]}
        assert {p1["prompt_id"], p2["prompt_id"]}.issubset(ids)
        access = client.get(f"/api/v1/prompt-factory/collection-library/{p1['prompt_id']}")
        assert access.status_code == 200
        assert access.json()["prompt"]["license_type"] == "COMMERCIAL"

        logout(client, buyer_headers)
        seller_headers = login_user(client, seller_email)
        dashboard = client.get("/api/v1/prompt-factory/creator/dashboard")
        assert float(dashboard.json()["balance"]["available_usd"]) >= 9.60


def test_duplicate_detection_moderation_analytics_notifications_and_admin_overview():
    shared_text = "Exact duplicate body " + uuid.uuid4().hex + " with a long structured prompt for marketing campaign generation."
    with TestClient(app) as client:
        _, seller_a, headers_a = register_user(client, "adv-dup-a")
        create_seller_profile(client, headers_a, "dupa_" + uuid.uuid4().hex[:8])
        pa = create_prompt(client, headers_a, "Original " + uuid.uuid4().hex[:6], shared_text)
        first = client.post(f"/api/v1/prompt-factory/prompts/{pa['prompt_id']}/publish-advanced", headers=headers_a, json={
            "price_usd": "5.00", "pricing_model": "FIXED", "license_type": "PERSONAL", "preview_text": "Original"
        })
        assert first.status_code == 200 and first.json()["listing"]["status"] == "PUBLISHED"
        logout(client, headers_a)

        _, seller_b, headers_b = register_user(client, "adv-dup-b")
        create_seller_profile(client, headers_b, "dupb_" + uuid.uuid4().hex[:8])
        pb = create_prompt(client, headers_b, "Duplicate " + uuid.uuid4().hex[:6], shared_text)
        second = client.post(f"/api/v1/prompt-factory/prompts/{pb['prompt_id']}/publish-advanced", headers=headers_b, json={
            "price_usd": "5.00", "pricing_model": "FIXED", "license_type": "PERSONAL", "preview_text": "Duplicate"
        })
        assert second.status_code == 200, second.text
        assert second.json()["listing"]["status"] == "PENDING_REVIEW"
        assert second.json()["duplicate_matches"]

        event = client.post("/api/v1/prompt-factory/analytics/events", headers=headers_b, json={
            "event_type": "VIEW",
            "prompt_id": pb["prompt_id"],
            "listing_id": second.json()["listing"]["listing_id"],
            "creator_id": seller_b["id"],
            "metadata": {"surface": "test"},
        })
        assert event.status_code == 200
        analytics = client.get("/api/v1/prompt-factory/creator/analytics")
        assert analytics.status_code == 200
        assert analytics.json()["views"] >= 1

        report = client.post("/api/v1/prompt-factory/moderation/reports", headers=headers_b, json={
            "target_type": "PROMPT",
            "target_id": pa["prompt_id"],
            "category": "IP",
            "details": "Test report for moderation workflow",
        })
        assert report.status_code == 200

        me = client.get("/api/v1/me").json()["user"]
        db.execute("UPDATE users SET role='platform_owner' WHERE id=?", (me["id"],))
        overview = client.get("/api/v1/prompt-factory/admin/advanced-overview")
        assert overview.status_code == 200, overview.text
        reports = client.get("/api/v1/prompt-factory/admin/reports")
        assert reports.status_code == 200
        assert any(r["report_id"] == report.json()["report_id"] for r in reports.json()["reports"])
        assert any(f["prompt_id"] == pb["prompt_id"] for f in reports.json()["duplicate_flags"])
