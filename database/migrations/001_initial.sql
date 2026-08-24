-- Canonical schema lives in backend/app/db.py for the SQLite V0.1 prototype.
-- This file marks migration 001. Production PostgreSQL migration tooling is a V0.2 deployment step.
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL);
INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(1,strftime('%s','now'));
