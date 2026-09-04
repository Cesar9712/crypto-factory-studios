-- Prompt Factory advanced systems: seller economy, promotions, moderation, referrals, payouts and analytics.
-- Additive-only migration. No existing tables or data are removed.

CREATE TABLE IF NOT EXISTS prompt_dynamic_categories(
  category_id TEXT PRIMARY KEY,label TEXT NOT NULL UNIQUE,slug TEXT NOT NULL UNIQUE,active INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_seller_profiles(
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,username TEXT NOT NULL UNIQUE,avatar_url TEXT NOT NULL DEFAULT '',
  bio TEXT NOT NULL DEFAULT '',badges_json TEXT NOT NULL DEFAULT '[]',blocked INTEGER NOT NULL DEFAULT 0,joined_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_creator_follows(
  follower_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,creator_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,PRIMARY KEY(follower_id,creator_id)
);
CREATE TABLE IF NOT EXISTS prompt_saved_searches(
  search_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,label TEXT NOT NULL,query_json TEXT NOT NULL,
  created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_notifications(
  notification_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,type TEXT NOT NULL,title TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '',target_url TEXT NOT NULL DEFAULT '',source_key TEXT NOT NULL UNIQUE,read_at INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_assets(
  asset_id TEXT PRIMARY KEY,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,label TEXT NOT NULL DEFAULT '',url TEXT NOT NULL,media_type TEXT NOT NULL DEFAULT '',position INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_listing_license_options(
  option_id TEXT PRIMARY KEY,listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,license_type TEXT NOT NULL,
  price_usd TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,UNIQUE(listing_id,license_type)
);
CREATE TABLE IF NOT EXISTS prompt_promotions(
  promotion_id TEXT PRIMARY KEY,listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label TEXT NOT NULL,sale_price_usd TEXT NOT NULL,starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_coupons(
  coupon_id TEXT PRIMARY KEY,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,listing_id TEXT REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
  code TEXT NOT NULL UNIQUE,discount_type TEXT NOT NULL,discount_value TEXT NOT NULL,max_uses INTEGER,uses_count INTEGER NOT NULL DEFAULT 0,
  starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_checkout_intents(
  product_id TEXT PRIMARY KEY,buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,listing_id TEXT NOT NULL REFERENCES prompt_listings(listing_id) ON DELETE CASCADE,
  coupon_id TEXT REFERENCES prompt_coupons(coupon_id) ON DELETE SET NULL,license_type TEXT NOT NULL,amount_usd TEXT NOT NULL,created_at INTEGER NOT NULL,redeemed_order_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS prompt_collection_offers(
  offer_id TEXT PRIMARY KEY,collection_id TEXT NOT NULL REFERENCES prompt_collections(collection_id) ON DELETE CASCADE,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_id TEXT NOT NULL UNIQUE REFERENCES products(product_id),pricing_model TEXT NOT NULL,price_usd TEXT NOT NULL,license_type TEXT NOT NULL DEFAULT 'PERSONAL',
  duration_days INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'PUBLISHED',sales_count INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_collection_access(
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,offer_id TEXT NOT NULL REFERENCES prompt_collection_offers(offer_id) ON DELETE CASCADE,
  collection_id TEXT NOT NULL REFERENCES prompt_collections(collection_id) ON DELETE CASCADE,order_id TEXT UNIQUE,license_type TEXT NOT NULL,
  expires_at INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,PRIMARY KEY(user_id,offer_id)
);
CREATE TABLE IF NOT EXISTS prompt_collection_sales(
  sale_id TEXT PRIMARY KEY,offer_id TEXT NOT NULL REFERENCES prompt_collection_offers(offer_id) ON DELETE CASCADE,buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,order_id TEXT NOT NULL UNIQUE,gross_usd NUMERIC NOT NULL,platform_fee_usd NUMERIC NOT NULL,
  seller_amount_usd NUMERIC NOT NULL,status TEXT NOT NULL DEFAULT 'CONFIRMED',created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_moderation_reports(
  report_id TEXT PRIMARY KEY,reporter_id TEXT REFERENCES users(id) ON DELETE SET NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,category TEXT NOT NULL,
  details TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',resolution TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_duplicate_flags(
  flag_id TEXT PRIMARY KEY,prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,matched_prompt_id TEXT NOT NULL REFERENCES prompts(prompt_id) ON DELETE CASCADE,
  similarity REAL NOT NULL,exact_match INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'OPEN',created_at INTEGER NOT NULL,UNIQUE(prompt_id,matched_prompt_id)
);
CREATE TABLE IF NOT EXISTS prompt_disputes(
  dispute_id TEXT PRIMARY KEY,purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seller_id TEXT REFERENCES users(id) ON DELETE SET NULL,reason TEXT NOT NULL,details TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',frozen_usd NUMERIC NOT NULL DEFAULT 0,
  resolution TEXT NOT NULL DEFAULT '',refund_tx TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_payouts(
  payout_id TEXT PRIMARY KEY,seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,amount_usd NUMERIC NOT NULL,fee_usd NUMERIC NOT NULL,
  net_usd NUMERIC NOT NULL,method TEXT NOT NULL,destination TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',payout_tx TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_referral_codes(
  code TEXT PRIMARY KEY,user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_referral_attributions(
  referred_user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,affiliate_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code TEXT NOT NULL REFERENCES prompt_referral_codes(code),created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_referral_earnings(
  earning_id TEXT PRIMARY KEY,purchase_id TEXT NOT NULL UNIQUE REFERENCES prompt_purchases(purchase_id) ON DELETE CASCADE,
  affiliate_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,amount_usd NUMERIC NOT NULL,created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_analytics_events(
  event_id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id) ON DELETE SET NULL,event_type TEXT NOT NULL,prompt_id TEXT REFERENCES prompts(prompt_id) ON DELETE SET NULL,
  listing_id TEXT REFERENCES prompt_listings(listing_id) ON DELETE SET NULL,creator_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_advanced_entitlement_events(
  order_id TEXT PRIMARY KEY REFERENCES orders(order_id) ON DELETE CASCADE,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entitlement_key TEXT NOT NULL,applied_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pf_notify_user ON prompt_notifications(user_id,created_at);
CREATE INDEX IF NOT EXISTS idx_pf_analytics_creator ON prompt_analytics_events(creator_id,created_at);
CREATE INDEX IF NOT EXISTS idx_pf_reports_status ON prompt_moderation_reports(status,created_at);
CREATE INDEX IF NOT EXISTS idx_pf_payouts_status ON prompt_payouts(status,created_at);
CREATE INDEX IF NOT EXISTS idx_pf_collection_access_user ON prompt_collection_access(user_id,expires_at);
