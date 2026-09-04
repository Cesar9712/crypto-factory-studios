CREATE TABLE IF NOT EXISTS platform_feature_flags (
    feature_key TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at BIGINT NOT NULL,
    updated_by TEXT
);

INSERT OR IGNORE INTO platform_feature_flags(feature_key, enabled, updated_at, updated_by)
VALUES ('cryptoquest_enabled', 0, 0, 'migration');

INSERT OR IGNORE INTO platform_feature_flags(feature_key, enabled, updated_at, updated_by)
VALUES ('crypto_factory_game_enabled', 0, 0, 'migration');
