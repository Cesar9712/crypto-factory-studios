from types import SimpleNamespace

import backend.app.tropipay as tp


def settings():
    return SimpleNamespace(
        tropipay_enabled=True,
        tropipay_client_id="client-test",
        tropipay_client_secret="secret-test",
        tropipay_api_base_url="https://sandbox.tropipay.me/api/v3",
        tropipay_timeout_seconds=5.0,
    )


def test_disabled_without_credentials():
    s=settings(); s.tropipay_client_secret=""
    assert tp.TropiPayClient(s).enabled is False


def test_create_paylink_uses_server_token_and_cents(monkeypatch):
    calls=[]
    class Response:
        def __init__(self,payload): self.payload=payload
        def raise_for_status(self): return None
        def json(self): return self.payload
    def post(url, **kwargs):
        calls.append((url,kwargs))
        if url.endswith("/access/token"):
            return Response({"access_token":"token","expires_in":3600})
        return Response({"id":"pc_1","shortUrl":"https://tppay.me/test","reference":"cfs-ord_1"})
    monkeypatch.setattr(tp.httpx,"post",post)
    c=tp.TropiPayClient(settings())
    result=c.create_paylink(
        reference="cfs-ord_1",concept="Creator Plus",description="Plan",
        amount_cents=199,currency="USD",
        success_url="https://example.test/success",failed_url="https://example.test/failed",
        notification_url="https://example.test/webhook",
    )
    assert result["shortUrl"] == "https://tppay.me/test"
    body=calls[-1][1]["json"]
    assert body["amount"] == 199
    assert body["reference"] == "cfs-ord_1"
    assert "client_secret" not in body


def test_find_movement_requires_exact_reference_amount_currency(monkeypatch):
    class Response:
        def raise_for_status(self): return None
        def json(self):
            return {"items":[
                {"id":1,"reference":"other","amount":199,"currency":"USD","state":"completed"},
                {"id":2,"reference":"cfs-ord_1","amount":199,"currency":"USD","state":"completed"},
            ]}
    c=tp.TropiPayClient(settings())
    c._access_token="token"; c._token_expires_at=99999999999
    monkeypatch.setattr(tp.httpx,"get",lambda *a,**k: Response())
    movement=c.find_movement(reference="cfs-ord_1",amount_cents=199,currency="USD")
    assert movement["id"] == 2
