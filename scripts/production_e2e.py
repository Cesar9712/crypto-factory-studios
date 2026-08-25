from __future__ import annotations

import io
import os
import uuid
import zipfile

import httpx


EDGE = os.getenv("CFS_E2E_BASE_URL", "https://crypto-factory-studios.cesargp9712.workers.dev").rstrip("/")
PASSWORD = "CFS-Production-QA-Only-Strong-Password-2026!"
RUN_ID = (os.getenv("GITHUB_SHA", "local")[:12] + "-" + uuid.uuid4().hex[:10]).lower()
EMAIL = f"cfs-production-e2e-{RUN_ID}@example.com"
CREATOR_SLUG = f"e2e-{RUN_ID}"[:40]
GAME_TITLE = f"CFS E2E {RUN_ID}"
MARKER = f"cfs-production-e2e:{RUN_ID}"


def expect(response: httpx.Response, status: int, label: str) -> dict:
    if response.status_code != status:
        body = response.text[:1000]
        raise AssertionError(f"{label}: expected HTTP {status}, got {response.status_code}: {body}")
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: expected JSON response, got {response.text[:500]!r}") from exc


def csrf_headers(client: httpx.Client) -> dict[str, str]:
    token = client.cookies.get("cfs_csrf")
    if not token:
        raise AssertionError("CSRF cookie was not set")
    return {"X-CSRF-Token": token}


def game_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "index.html",
            "<!doctype html><html><head><meta charset='utf-8'><title>CFS E2E</title>"
            "<link rel='stylesheet' href='style.css'></head><body><main id='app'>"
            + MARKER
            + "</main><script src='game.js'></script></body></html>",
        )
        archive.writestr("style.css", "body{font-family:sans-serif}main{padding:2rem}")
        archive.writestr("game.js", f"document.body.dataset.cfsE2E={MARKER!r};")
    return buf.getvalue()


def assert_play_sandbox(response: httpx.Response) -> None:
    csp = response.headers.get("content-security-policy", "")
    if "sandbox" not in csp or "allow-same-origin" in csp:
        raise AssertionError(f"published game CSP is not origin-isolating: {csp!r}")
    if response.headers.get("cross-origin-resource-policy") != "cross-origin":
        raise AssertionError(
            "published game CORP must allow sandboxed opaque-origin assets: "
            f"{response.headers.get('cross-origin-resource-policy')!r}"
        )


def main() -> int:
    game_id: str | None = None
    game_slug: str | None = None
    registered = False
    client = httpx.Client(base_url=EDGE, follow_redirects=False, timeout=45.0)

    try:
        health = expect(client.get("/health"), 200, "edge health")
        assert health.get("ok") is True and health.get("api_configured") is True, health
        ready = expect(client.get("/ready"), 200, "edge ready")
        assert ready.get("ok") is True and ready.get("upstream_status") == 200, ready

        payment_status = expect(client.get("/api/v1/payments/status"), 200, "payment status")
        assert payment_status.get("mode") == "PRODUCTION", payment_status
        assert payment_status.get("production_enabled") is True, payment_status
        assert payment_status.get("payments_ready") is True, payment_status
        providers = payment_status.get("providers") or {}
        for method_id in ("usdt_tron", "usdt_bsc", "sol"):
            assert providers.get(method_id) is True, providers

        registered_payload = expect(
            client.post(
                "/api/v1/auth/register",
                json={"email": EMAIL, "password": PASSWORD, "display_name": "Production E2E QA"},
            ),
            200,
            "register",
        )
        registered = True
        assert registered_payload["user"]["email"] == EMAIL
        assert client.cookies.get("cfs_session")
        assert client.cookies.get("cfs_csrf")

        me = expect(client.get("/api/v1/me"), 200, "me after register")
        assert me["user"]["email"] == EMAIL and me["creator"] is None

        creator = expect(
            client.post(
                "/api/v1/creator/activate",
                headers=csrf_headers(client),
                json={"creator_slug": CREATOR_SLUG, "bio": "Automated disposable production E2E account."},
            ),
            200,
            "activate creator",
        )
        assert creator["creator"]["slug"] == CREATOR_SLUG

        products = expect(client.get("/api/v1/products"), 200, "payment product catalog").get("products") or []
        assert products, "production payment product catalog is empty"
        methods = expect(client.get("/api/v1/payments/methods"), 200, "payment methods")
        assert methods.get("mode") == "PRODUCTION", methods
        method_rows = {row.get("method_id"): row for row in (methods.get("methods") or [])}
        assert method_rows.get("usdt_tron", {}).get("production_allowed") is True, method_rows

        quote = expect(
            client.post(
                "/api/v1/payments/quotes",
                headers=csrf_headers(client),
                json={"product_id": products[0]["product_id"], "method_id": "usdt_tron"},
            ),
            200,
            "create production payment quote",
        )
        assert quote["method_id"] == "usdt_tron" and quote.get("crypto_amount"), quote

        order = expect(
            client.post(
                "/api/v1/payments/orders",
                headers=csrf_headers(client),
                json={"quote_id": quote["quote_id"], "idempotency_key": f"e2e-payment-{RUN_ID}"},
            ),
            200,
            "create production payment order",
        )
        order_id = order["order_id"]
        assert order["status"] == "AWAITING_PAYMENT", order

        checkout = expect(client.get(f"/api/v1/payments/orders/{order_id}/checkout"), 200, "production checkout")
        assert checkout["order"]["order_id"] == order_id, checkout
        payment_method = checkout["payment_method"]
        assert payment_method["method_id"] == "usdt_tron", payment_method
        assert payment_method.get("address"), "production checkout did not return a treasury address"
        assert checkout["order"].get("expected_amount") == quote.get("crypto_amount"), checkout

        rejected_tx = expect(
            client.post(
                f"/api/v1/payments/orders/{order_id}/submit-tx",
                headers=csrf_headers(client),
                json={"transaction_hash": "not-a-real-transaction"},
            ),
            200,
            "reject nonexistent production transaction",
        )
        assert rejected_tx["status"] == "FAILED", rejected_tx
        purchases_before_funds = expect(client.get("/api/v1/purchases"), 200, "purchases before real funds")
        assert not any(row.get("order_id") == order_id for row in purchases_before_funds.get("purchases", [])), purchases_before_funds
        print(f"production payment quote/order/checkout verified safely: order={order_id} method=usdt_tron")

        created = expect(
            client.post(
                "/api/v1/creator/games",
                headers=csrf_headers(client),
                json={"title": GAME_TITLE, "description": MARKER, "genre": "QA", "visibility": "PUBLIC"},
            ),
            200,
            "create game",
        )
        game_id = created["game"]["game_id"]
        game_slug = created["game"]["slug"]

        edited = expect(
            client.put(
                f"/api/v1/creator/games/{game_id}",
                headers=csrf_headers(client),
                json={"title": GAME_TITLE, "description": MARKER + ":edited", "genre": "QA", "tags": ["e2e", "production"], "visibility": "PUBLIC", "web3_enabled": False},
            ),
            200,
            "edit game",
        )
        assert edited["game"]["game_id"] == game_id

        upload = expect(
            client.post(
                f"/api/v1/creator/games/{game_id}/builds",
                headers=csrf_headers(client),
                data={"version": "e2e-1.0.0"},
                files={"archive": ("cfs-e2e.zip", game_zip(), "application/zip")},
            ),
            200,
            "upload build",
        )
        assert upload["scan_status"] == "CLEAN", upload
        assert upload["status"] == "READY_FOR_REVIEW", upload
        build_id = upload["build_id"]

        builds = expect(client.get(f"/api/v1/creator/games/{game_id}/builds"), 200, "list builds")
        assert any(row["build_id"] == build_id and row["scan_status"] == "CLEAN" for row in builds["builds"]), builds

        published = expect(
            client.post(f"/api/v1/creator/builds/{build_id}/publish", headers=csrf_headers(client)),
            200,
            "publish build",
        )
        assert published["build_id"] == build_id

        catalog = expect(client.get("/api/v1/games"), 200, "catalog")
        assert any(row["game_id"] == game_id and row["slug"] == game_slug for row in catalog["games"]), catalog

        detail = expect(client.get(f"/api/v1/games/{game_slug}"), 200, "game detail")
        assert detail["game"]["game_id"] == game_id

        play = client.get(f"/play/{game_slug}/")
        if play.status_code != 200 or MARKER not in play.text:
            raise AssertionError(f"play endpoint did not serve published B2 content: {play.status_code} {play.text[:500]!r}")
        assert_play_sandbox(play)
        css = client.get(f"/play/{game_slug}/style.css")
        if css.status_code != 200 or "text/css" not in css.headers.get("content-type", ""):
            raise AssertionError(f"published CSS content type invalid: {css.status_code} {css.headers.get('content-type')}")
        assert_play_sandbox(css)

        initial_save = expect(client.get(f"/api/v1/games/{game_id}/save"), 200, "initial save")
        assert initial_save["revision"] == 0 and initial_save["state"] == {}, initial_save

        saved = expect(
            client.put(
                f"/api/v1/games/{game_id}/save",
                headers=csrf_headers(client),
                json={"save_version": 1, "revision": 0, "state": {"marker": MARKER, "step": 1}},
            ),
            200,
            "save game",
        )
        assert saved["revision"] == 1

        conflict = client.put(
            f"/api/v1/games/{game_id}/save",
            headers=csrf_headers(client),
            json={"save_version": 1, "revision": 0, "state": {"marker": "stale"}},
        )
        expect(conflict, 409, "save revision conflict")

        saved2 = expect(
            client.put(
                f"/api/v1/games/{game_id}/save",
                headers=csrf_headers(client),
                json={"save_version": 1, "revision": 1, "state": {"marker": MARKER, "step": 2}},
            ),
            200,
            "update save",
        )
        assert saved2["revision"] == 2

        expect(client.post("/api/v1/auth/logout", headers=csrf_headers(client)), 200, "logout")
        expect(client.get("/api/v1/me"), 401, "me after logout")

        login = expect(client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}), 200, "login again")
        assert login["user"]["email"] == EMAIL
        me2 = expect(client.get("/api/v1/me"), 200, "me after relogin")
        assert me2["creator"]["slug"] == CREATOR_SLUG

        persisted_save = expect(client.get(f"/api/v1/games/{game_id}/save"), 200, "persisted save")
        assert persisted_save["revision"] == 2 and persisted_save["state"] == {"marker": MARKER, "step": 2}, persisted_save
        persisted_play = client.get(f"/play/{game_slug}/")
        if persisted_play.status_code != 200 or MARKER not in persisted_play.text:
            raise AssertionError("published build did not remain available after session renewal")
        assert_play_sandbox(persisted_play)

        print(f"production E2E verified via Cloudflare: user={EMAIL} game={game_slug} build={build_id}")
        return 0
    finally:
        if registered:
            if client.get("/api/v1/me").status_code != 200:
                expect(client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}), 200, "cleanup login")
            deletion = expect(
                client.request(
                    "DELETE",
                    "/api/v1/account",
                    headers=csrf_headers(client),
                    json={"password": PASSWORD, "confirmation": "DELETE ACCOUNT"},
                ),
                200,
                "cleanup account deletion",
            )
            assert deletion.get("deleted") is True, deletion
            expect(client.get("/api/v1/me"), 401, "cleanup session invalidated")
            if game_slug:
                catalog_after = expect(client.get("/api/v1/games"), 200, "catalog after cleanup")
                assert not any(row.get("slug") == game_slug for row in catalog_after.get("games", [])), catalog_after
                expect(client.get(f"/play/{game_slug}/"), 404, "play after cleanup")
            print("production E2E cleanup verified")
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
