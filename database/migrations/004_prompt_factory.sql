-- Prompt Factory marketplace and private vault.
-- Production uses Neon PostgreSQL through the FastAPI service; database access is not exposed directly to browsers.

CREATE TABLE IF NOT EXISTS prompt_plans(
  plan_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  price_usd TEXT NOT NULL,
  max_prompts INTEGER,
  commission_bps INTEGER NOT NULL,
  features_json TEXT NOT NULL DEFAULT '[]',
  active INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompt_user_plans(
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES prompt_plans(plan_id),
  starts_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_user_storage(
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  extra_slots INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_storage_addons(
  addon_id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  price_usd TEXT NOT NULL,
  extra_slots INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompt_platform_settings(
  setting_key TEXT PRIMARY KEY,
  setting_value TEXT NOT NULL,
  updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompts(
  prompt_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  prompt_text TEXT NOT NULL,
  system_instructions TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT 'OTHER',
  subcategory TEXT NOT NULL DEFAULT '',
  tags_json TEXT NOT NULL DEFAULT '[]',
  ai_models_json TEXT NOT NULL DEFAULT '[]',
  difficulty TEXT NOT NULL DEFAULT 'INTERMEDIATE',
  language TEXT NOT NULL DEFAULT 'en',
  variables_json TEXT NOT NULL DEFAULT '[]',
  visibility TEXT NOT NULL DEFAULT 'PRIVATE',
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  content_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  archived_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompt_versions(
  version_id TEXT PRIMARY KEY,
  prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  prompt_text TEXT NOT NULL,
  system_instructions TEXT NOT NULL DEFAULT '',
  variables_json TEXT NOT NULL DEFAULT '[]',
  changelog TEXT NOT NULL DEFAULT '',
  content_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  UNIQUE(prompt_id, version_number)
);

CREATE TABLE IF NOT EXISTS prompt_listings(
  listing_id TEXT PRIMARY KEY,
  prompt_id TEXT NOT NULL UNIQUE REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_id TEXT NOT NULL UNIQUE REFERENCES products(product_id),
  price_usd TEXT NOT NULL,
  pricing_model TEXT NOT NULL DEFAULT 'FIXED',
  license_type TEXT NOT NULL DEFAULT 'PERSONAL',
  preview_text TEXT NOT NULL DEFAULT '',
  examples_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  commission_bps INTEGER NOT NULL,
  featured INTEGER NOT NULL DEFAULT 0,
  sales_count INTEGER NOT NULL DEFAULT 0,
  rating_avg REAL NOT NULL DEFAULT 0,
  rating_count INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_purchases(
  purchase_id TEXT PRIMARY KEY,
  buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seller_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
  order_id TEXT UNIQUE,
  license_type TEXT NOT NULL,
  gross_usd NUMERIC NOT NULL DEFAULT 0,
  platform_fee_usd NUMERIC NOT NULL DEFAULT 0,
  seller_amount_usd NUMERIC NOT NULL DEFAULT 0,
  payment_asset TEXT NOT NULL DEFAULT 'FREE',
  payment_network TEXT NOT NULL DEFAULT 'FREE',
  status TEXT NOT NULL DEFAULT 'CONFIRMED',
  created_at INTEGER NOT NULL,
  UNIQUE(buyer_id, listing_id)
);

CREATE TABLE IF NOT EXISTS prompt_reviews(
  review_id TEXT PRIMARY KEY,
  purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
  buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  rating INTEGER NOT NULL,
  comment TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_favorites(
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  PRIMARY KEY(user_id, prompt_id)
);

CREATE TABLE IF NOT EXISTS prompt_collections(
  collection_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  visibility TEXT NOT NULL DEFAULT 'PRIVATE',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_collection_items(
  collection_id TEXT NOT NULL REFERENCES prompt_collections(collection_id) ON DELETE CASCADE,
  prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(collection_id, prompt_id)
);

CREATE TABLE IF NOT EXISTS seller_balances(
  seller_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  available_usd NUMERIC NOT NULL DEFAULT 0,
  pending_usd NUMERIC NOT NULL DEFAULT 0,
  lifetime_earnings_usd NUMERIC NOT NULL DEFAULT 0,
  platform_fees_usd NUMERIC NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS seller_ledger(
  ledger_id TEXT PRIMARY KEY,
  seller_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
  gross_usd NUMERIC NOT NULL,
  platform_fee_usd NUMERIC NOT NULL,
  seller_amount_usd NUMERIC NOT NULL,
  event_type TEXT NOT NULL DEFAULT 'SALE',
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_entitlement_events(
  order_id TEXT PRIMARY KEY REFERENCES orders(order_id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entitlement_key TEXT NOT NULL,
  applied_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompts_owner ON prompts(owner_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category, status);
CREATE INDEX IF NOT EXISTS idx_prompt_listings_status ON prompt_listings(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_prompt_purchases_buyer ON prompt_purchases(buyer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_purchases_seller ON prompt_purchases(seller_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_entitlement_user ON prompt_entitlement_events(user_id, applied_at);
