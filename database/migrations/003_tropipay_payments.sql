-- TropiPay hosted card checkout integration.
-- Runtime schema is also declared in backend/app/db.py for SQLite/Postgres parity.
CREATE TABLE IF NOT EXISTS tropipay_payment_links(
 order_id TEXT PRIMARY KEY REFERENCES orders(order_id) ON DELETE CASCADE,
 reference TEXT NOT NULL UNIQUE,
 provider_payment_id TEXT,
 pay_url TEXT NOT NULL,
 amount_cents INTEGER NOT NULL,
 currency TEXT NOT NULL,
 provider_movement_id TEXT UNIQUE,
 provider_state TEXT NOT NULL DEFAULT '',
 raw_json TEXT NOT NULL DEFAULT '{}',
 updated_at INTEGER NOT NULL
);
