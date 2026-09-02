from types import SimpleNamespace

from backend.app.payments import BASE_USDC_CONTRACT, PaymentMethodRegistry, PriceService
from backend.app.routes_bitshelf import CATALOG, _zip_bytes


def settings():
    return SimpleNamespace(
        tron_usdt_address="TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9",
        bsc_usdt_address="0xb6e727732F845bDb7792C075B147658e84a173d2",
        base_usdc_address="0xb6e727732F845bDb7792C075B147658e84a173d2",
        sol_address="EpiJ5GUjXMhcQpZtErxwGq5VZKwvkxV8kSz8PUKtpsr2",
        tron_deposit_addresses=(),
        bsc_deposit_addresses=(),
        base_deposit_addresses=(),
        sol_deposit_addresses=(),
        payments_mode="TEST",
        deposit_address_mode="SHARED_MARKER",
        mock_sol_usd_rate="150.00",
        blockchain_timeout_seconds=2,
    )


def test_base_usdc_method_is_exact_and_non_custodial_destination():
    methods=PaymentMethodRegistry(settings())
    base=methods.get("usdc_base")
    assert base is not None
    assert base.asset=="USDC"
    assert base.network=="Base"
    assert base.decimals==6
    assert base.address=="0xb6e727732F845bDb7792C075B147658e84a173d2"
    assert base.token_contract.lower()==BASE_USDC_CONTRACT.lower()


def test_base_usdc_quote_tracks_usd_one_to_one_in_test_mode():
    methods=PaymentMethodRegistry(settings())
    amount,rate,source=PriceService(settings()).quote_amount(__import__("decimal").Decimal("3.00"),methods.get("usdc_base"))
    assert str(amount)=="3.000000"
    assert str(rate)=="1"
    assert source=="stable_reference"


def test_bitshelf_catalog_has_required_mvp_and_bundles():
    paid=[p for p in CATALOG.values() if not p.get("free")]
    assert len(paid)>=14
    assert any(p["category"]=="Bundle" for p in paid)
    assert any(p["category"]=="Premium" for p in paid)


def test_bitshelf_downloads_are_real_zip_files():
    payload=_zip_bytes("bitshelf_ai_prompt_starter")
    assert payload.startswith(b"PK")
    assert len(payload)>500
