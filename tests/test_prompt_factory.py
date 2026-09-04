import uuid

from fastapi.testclient import TestClient

from backend.app.main import app


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
    return email, {"X-CSRF-Token": client.cookies.get("cfs_csrf")}


def login_user(client: TestClient, email: str):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": client.cookies.get("cfs_csrf")}


def create_prompt(client: TestClient, headers: dict, title: str = "Marketplace Prompt"):
    r = client.post("/api/v1/prompt-factory/prompts", headers=headers, json={
        "title": title,
        "description": "A useful protected prompt",
        "prompt_text": "SECRET BODY: Build a {{PRODUCT_NAME}} launch plan.",
        "system_instructions": "Return concise steps.",
        "category": "MARKETING",
        "tags": ["launch", "marketing"],
        "ai_models": ["ChatGPT", "Claude"],
        "variables": [{"name": "PRODUCT_NAME", "label": "Product name"}],
    })
    assert r.status_code == 200, r.text
    return r.json()["prompt"]


def pay_product(client: TestClient, headers: dict, product_id: str):
    q = client.post("/api/v1/payments/quotes", headers=headers, json={"product_id": product_id, "method_id": "usdt_tron"})
    assert q.status_code == 200, q.text
    order = client.post("/api/v1/payments/orders", headers=headers, json={
        "quote_id": q.json()["quote_id"],
        "idempotency_key": "pf-test-" + uuid.uuid4().hex,
    })
    assert order.status_code == 200, order.text
    order_id = order.json()["order_id"]
    paid = client.post(f"/api/v1/payments/orders/{order_id}/submit-tx", headers=headers, json={
        "transaction_hash": "mock_prompt_factory_" + uuid.uuid4().hex,
    })
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "FULFILLED"
    return order_id


def test_prompt_vault_versions_render_and_archive():
    with TestClient(app) as client:
        _, headers = register_user(client, "vault")
        prompt = create_prompt(client, headers, "Versioned Prompt " + uuid.uuid4().hex[:6])
        pid = prompt["prompt_id"]
        assert "SECRET BODY" in prompt["prompt_text"]

        updated = client.put(f"/api/v1/prompt-factory/prompts/{pid}", headers=headers, json={
            "prompt_text": "VERSION TWO for {{PRODUCT_NAME}}",
            "changelog": "Improve output",
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["version"] == 2

        versions = client.get(f"/api/v1/prompt-factory/prompts/{pid}/versions")
        assert versions.status_code == 200
        assert [v["version_number"] for v in versions.json()["versions"]][:2] == [2, 1]

        rendered = client.post(f"/api/v1/prompt-factory/prompts/{pid}/render", headers=headers, json={"values": {"PRODUCT_NAME": "Nova"}})
        assert rendered.status_code == 200
        assert rendered.json()["rendered_prompt"] == "VERSION TWO for Nova"

        restored = client.post(f"/api/v1/prompt-factory/prompts/{pid}/versions/1/restore", headers=headers)
        assert restored.status_code == 200
        assert restored.json()["version"] == 3
        assert "SECRET BODY" in restored.json()["prompt"]["prompt_text"]

        archived = client.delete(f"/api/v1/prompt-factory/prompts/{pid}", headers=headers)
        assert archived.status_code == 200
        vault = client.get("/api/v1/prompt-factory/vault")
        assert all(p["prompt_id"] != pid for p in vault.json()["owned"])


def test_free_plan_enforces_ten_prompt_limit():
    with TestClient(app) as client:
        _, headers = register_user(client, "limit")
        base = uuid.uuid4().hex[:6]
        for i in range(10):
            r = client.post("/api/v1/prompt-factory/prompts", headers=headers, json={
                "title": f"Limit {base} {i}",
                "prompt_text": f"Prompt {i}",
            })
            assert r.status_code == 200, r.text
        blocked = client.post("/api/v1/prompt-factory/prompts", headers=headers, json={
            "title": f"Limit {base} blocked",
            "prompt_text": "Should not be stored",
        })
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["error_code"] == "prompt_limit"


def test_marketplace_paid_purchase_is_server_authoritative_and_commission_is_idempotent():
    with TestClient(app) as client:
        seller_email, seller_headers = register_user(client, "seller")
        prompt = create_prompt(client, seller_headers, "Paid Prompt " + uuid.uuid4().hex[:6])
        pid = prompt["prompt_id"]
        listed = client.post(f"/api/v1/prompt-factory/prompts/{pid}/sell", headers=seller_headers, json={
            "price_usd": "10.00",
            "pricing_model": "FIXED",
            "license_type": "COMMERCIAL",
            "preview_text": "Protected commercial prompt",
            "examples": ["Example result"],
        })
        assert listed.status_code == 200, listed.text
        listing = listed.json()["listing"]
        listing_id = listing["listing_id"]
        assert int(listing["commission_bps"]) == 2000

        self_buy = client.post(f"/api/v1/prompt-factory/listings/{listing_id}/prepare-checkout", headers=seller_headers)
        assert self_buy.status_code == 409

        public = client.get(f"/api/v1/prompt-factory/listings/{prompt['slug']}")
        assert public.status_code == 200
        assert "SECRET BODY" not in public.text

        client.post("/api/v1/auth/logout", headers=seller_headers)
        buyer_email, buyer_headers = register_user(client, "buyer")
        checkout = client.post(f"/api/v1/prompt-factory/listings/{listing_id}/prepare-checkout", headers=buyer_headers)
        assert checkout.status_code == 200, checkout.text
        assert checkout.json()["price_usd"] == "10.00"

        order_id = pay_product(client, buyer_headers, checkout.json()["product_id"])
        reconciled = client.post("/api/v1/prompt-factory/reconcile", headers=buyer_headers)
        assert reconciled.status_code == 200, reconciled.text
        assert reconciled.json()["applied"] == 1

        repeated = client.post("/api/v1/prompt-factory/reconcile", headers=buyer_headers)
        assert repeated.status_code == 200
        assert repeated.json()["applied"] == 0

        vault = client.get("/api/v1/prompt-factory/vault")
        bought = next(p for p in vault.json()["purchased"] if p["prompt_id"] == pid)
        assert "SECRET BODY" in bought["prompt_text"]
        assert bought["purchased_license"] == "COMMERCIAL"
        purchase_id = bought["purchase_id"]

        review = client.post(f"/api/v1/prompt-factory/purchases/{purchase_id}/review", headers=buyer_headers, json={
            "rating": 5,
            "comment": "Verified purchase",
        })
        assert review.status_code == 200

        history = client.get("/api/v1/purchases")
        assert any(p["order_id"] == order_id for p in history.json()["purchases"])

        client.post("/api/v1/auth/logout", headers=buyer_headers)
        seller_headers = login_user(client, seller_email)
        dashboard = client.get("/api/v1/prompt-factory/creator/dashboard")
        assert dashboard.status_code == 200
        data = dashboard.json()
        assert str(data["sales"]["gross"]) in {"10", "10.0", "10.00"}
        assert str(data["sales"]["fees"]) in {"2", "2.0", "2.00"}
        assert str(data["sales"]["net"]) in {"8", "8.0", "8.00"}
        assert str(data["balance"]["available_usd"]) in {"8", "8.0", "8.00"}


def test_free_listing_acquisition_and_verified_review_only():
    with TestClient(app) as client:
        _, seller_headers = register_user(client, "free-seller")
        prompt = create_prompt(client, seller_headers, "Free Prompt " + uuid.uuid4().hex[:6])
        listed = client.post(f"/api/v1/prompt-factory/prompts/{prompt['prompt_id']}/sell", headers=seller_headers, json={
            "price_usd": "999.00",
            "pricing_model": "FREE",
            "license_type": "PERSONAL",
            "preview_text": "Free sample",
        })
        assert listed.status_code == 200
        listing = listed.json()["listing"]
        assert str(listing["price_usd"]) == "0.00"

        client.post("/api/v1/auth/logout", headers=seller_headers)
        _, buyer_headers = register_user(client, "free-buyer")
        acquired = client.post(f"/api/v1/prompt-factory/listings/{listing['listing_id']}/acquire-free", headers=buyer_headers)
        assert acquired.status_code == 200
        purchase_id = acquired.json()["purchase"]["purchase_id"]

        review = client.post(f"/api/v1/prompt-factory/purchases/{purchase_id}/review", headers=buyer_headers, json={"rating": 4, "comment": "Useful"})
        assert review.status_code == 200

        fake = client.post("/api/v1/prompt-factory/purchases/not-real/review", headers=buyer_headers, json={"rating": 5})
        assert fake.status_code == 403


def test_paid_plan_reconciliation_expands_capacity_once():
    with TestClient(app) as client:
        _, headers = register_user(client, "plan")
        checkout = client.post("/api/v1/prompt-factory/plans/starter/prepare-checkout", headers=headers)
        assert checkout.status_code == 200
        pay_product(client, headers, checkout.json()["product_id"])
        first = client.post("/api/v1/prompt-factory/reconcile", headers=headers)
        assert first.status_code == 200
        assert first.json()["applied"] == 1
        state = client.get("/api/v1/prompt-factory/me")
        assert state.status_code == 200
        assert state.json()["plan"]["plan_id"] == "starter"
        assert state.json()["storage"]["limit"] == 50
        second = client.post("/api/v1/prompt-factory/reconcile", headers=headers)
        assert second.json()["applied"] == 0
