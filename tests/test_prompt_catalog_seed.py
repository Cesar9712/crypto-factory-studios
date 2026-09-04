from pathlib import Path

from backend.app.db_runtime import DB
from backend.app.prompt_catalog_seed import (
    CATALOG_CATEGORIES,
    CATALOG_COUNT,
    CATALOG_PRICES,
    ensure_official_prompt_catalog,
)
from backend.app.routes_prompt_factory import ensure_prompt_factory_schema


def test_official_catalog_covers_every_category_and_price_tier_idempotently(tmp_path: Path):
    clock = lambda: 1_788_540_000
    db = DB(tmp_path / "catalog.sqlite")
    ensure_prompt_factory_schema(db, clock)
    db.execute(
        """INSERT INTO users(id,email,password_hash,display_name,role,disabled,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        ("usr_catalog_owner", "catalog-owner@example.com", "not-used", "Official Catalog", "platform_owner", 0, clock(), clock()),
    )

    seeded = ensure_official_prompt_catalog(db, clock)
    assert seeded == CATALOG_COUNT == 72
    assert CATALOG_CATEGORIES == 24
    assert CATALOG_PRICES == ("0.00", "1.99", "4.99", "9.99", "19.99")

    prompts = db.all("SELECT * FROM prompts WHERE slug LIKE 'cfs-%'")
    listings = db.all("SELECT * FROM prompt_listings WHERE listing_id LIKE 'lst_seed_%'")
    assert len(prompts) == 72
    assert len(listings) == 72
    assert len({row["category"] for row in prompts}) == 24
    assert {row["price_usd"] for row in listings} == set(CATALOG_PRICES)
    assert all(row["status"] == "PUBLISHED" for row in listings)
    assert all(row["visibility"] == "FOR_SALE" for row in prompts)
    assert all(len(row["prompt_text"]) > 900 for row in prompts)
    assert all("{{contexto}}" in row["prompt_text"] for row in prompts)

    free_listing = next(row for row in listings if row["price_usd"] == "0.00")
    paid_listing = next(row for row in listings if row["price_usd"] != "0.00")
    assert db.one("SELECT active FROM products WHERE product_id=?", (free_listing["product_id"],))["active"] == 0
    assert db.one("SELECT active FROM products WHERE product_id=?", (paid_listing["product_id"],))["active"] == 1

    # Re-seeding can refresh catalog metadata/prices but must never wipe marketplace history.
    db.execute(
        "UPDATE prompt_listings SET sales_count=7,rating_avg=4.8,rating_count=5 WHERE listing_id=?",
        (paid_listing["listing_id"],),
    )
    assert ensure_official_prompt_catalog(db, clock) == 0
    preserved = db.one(
        "SELECT sales_count,rating_avg,rating_count FROM prompt_listings WHERE listing_id=?",
        (paid_listing["listing_id"],),
    )
    assert preserved["sales_count"] == 7
    assert float(preserved["rating_avg"]) == 4.8
    assert preserved["rating_count"] == 5


def test_catalog_seed_refuses_to_create_privileged_seller_implicitly(tmp_path: Path):
    clock = lambda: 1_788_540_000
    db = DB(tmp_path / "catalog-no-owner.sqlite")
    ensure_prompt_factory_schema(db, clock)
    assert ensure_official_prompt_catalog(db, clock) == 0
    assert db.one("SELECT COUNT(*) AS n FROM prompts WHERE slug LIKE 'cfs-%'")["n"] == 0
    assert db.one("SELECT COUNT(*) AS n FROM users WHERE role='platform_owner'")["n"] == 0
