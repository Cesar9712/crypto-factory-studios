from pathlib import Path

from backend.app.db import DB


def test_low_introductory_creator_plan_prices(tmp_path: Path):
    db = DB(tmp_path / "pricing.db")
    products = {row["product_id"]: row for row in db.all("SELECT * FROM products")}
    assert products["creator_plus_monthly"]["price_usd"] == "1.99"
    assert products["creator_pro_monthly"]["price_usd"] == "3.99"


def test_owner_plan_is_not_a_billable_product(tmp_path: Path):
    db = DB(tmp_path / "pricing.db")
    products = {row["product_id"] for row in db.all("SELECT * FROM products")}
    assert "internal_unlimited" not in products
