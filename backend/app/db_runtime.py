from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from threading import Lock

from .db import SCHEMA


class DB:
    def __init__(self, path: Path, database_url: str = ""):
        self.path = path
        self.database_url = database_url.strip()
        self.lock = Lock()
        self.backend = "postgres" if self.database_url else "sqlite"

        if self.backend == "postgres":
            import psycopg
            from psycopg.rows import dict_row

            self._psycopg = psycopg
            self.conn = psycopg.connect(self.database_url, autocommit=True, row_factory=dict_row)
            pg_schema = (
                SCHEMA.replace("PRAGMA foreign_keys=ON;", "")
                .replace(" COLLATE NOCASE", "")
                .replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
                .replace("max_storage_bytes INTEGER", "max_storage_bytes BIGINT")
                .replace("max_upload_bytes INTEGER", "max_upload_bytes BIGINT")
                .replace("compressed_bytes INTEGER", "compressed_bytes BIGINT")
                .replace("uncompressed_bytes INTEGER", "uncompressed_bytes BIGINT")
            )
            with self.lock:
                with self.conn.cursor() as cur:
                    for statement in pg_schema.split(";"):
                        statement = statement.strip()
                        if statement:
                            cur.execute(statement)
                    # Existing Neon databases may already have been initialized with
                    # PostgreSQL INTEGER columns before the BIGINT fix. Widening these
                    # columns is safe and idempotent and prevents plan limits such as
                    # 5 GiB / 25 GiB from overflowing a signed 32-bit integer.
                    for statement in (
                        "ALTER TABLE creator_plans ALTER COLUMN max_storage_bytes TYPE BIGINT",
                        "ALTER TABLE creator_plans ALTER COLUMN max_upload_bytes TYPE BIGINT",
                        "ALTER TABLE game_builds ALTER COLUMN compressed_bytes TYPE BIGINT",
                        "ALTER TABLE game_builds ALTER COLUMN uncompressed_bytes TYPE BIGINT",
                    ):
                        cur.execute(statement)
        else:
            self.conn = sqlite3.connect(path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            with self.lock:
                self.conn.executescript(SCHEMA)
                self.conn.commit()

        self.seed_plans()
        self.seed_products()

    @property
    def persistent(self) -> bool:
        return self.backend == "postgres"

    def _sql(self, sql: str) -> str:
        if self.backend != "postgres":
            return sql

        sql = sql.replace(" COLLATE NOCASE", "")
        sql = sql.replace("?", "%s")
        upper = sql.lstrip().upper()

        if upper.startswith("INSERT OR IGNORE INTO"):
            sql = re.sub(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.I)
            if "ON CONFLICT" not in sql.upper():
                sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

        if upper.startswith("INSERT OR REPLACE INTO PAYMENT_METHODS"):
            sql = re.sub(r"^\s*INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", sql, flags=re.I)
            sql = sql.rstrip().rstrip(";") + (
                " ON CONFLICT(method_id) DO UPDATE SET "
                "asset=excluded.asset,network=excluded.network,standard=excluded.standard,"
                "address=excluded.address,token_contract=excluded.token_contract,enabled=excluded.enabled,"
                "production_allowed=excluded.production_allowed,updated_at=excluded.updated_at"
            )

        if upper.startswith("INSERT OR REPLACE INTO ENTITLEMENTS"):
            sql = re.sub(r"^\s*INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", sql, flags=re.I)
            sql = sql.rstrip().rstrip(";") + (
                " ON CONFLICT(user_id,entitlement_key) DO UPDATE SET "
                "source=excluded.source,granted_at=excluded.granted_at"
            )

        return sql

    def _raise_portable_integrity(self, exc: Exception):
        if self.backend == "postgres" and isinstance(exc, self._psycopg.IntegrityError):
            raise sqlite3.IntegrityError(str(exc)) from exc
        raise exc

    def seed_plans(self):
        plans = [
            ("free", "Creator Free", 2, 512 * 1024 * 1024, 3, 64 * 1024 * 1024, 0, 0, 0, 1),
            ("plus", "Creator Plus", 10, 5 * 1024 * 1024 * 1024, 10, 256 * 1024 * 1024, 1, 1, 1, 3),
            ("pro", "Creator Pro", 50, 25 * 1024 * 1024 * 1024, 30, 512 * 1024 * 1024, 1, 1, 1, 10),
            ("internal_unlimited", "Internal Unlimited", None, None, None, None, 1, 1, 1, 100),
        ]
        sql = """INSERT INTO creator_plans(plan_id,label,max_games,max_storage_bytes,max_builds_per_game,max_upload_bytes,advanced_analytics,private_builds,priority_processing,team_members)
                 VALUES(?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(plan_id) DO UPDATE SET
                 label=excluded.label,max_games=excluded.max_games,max_storage_bytes=excluded.max_storage_bytes,
                 max_builds_per_game=excluded.max_builds_per_game,max_upload_bytes=excluded.max_upload_bytes,
                 advanced_analytics=excluded.advanced_analytics,private_builds=excluded.private_builds,
                 priority_processing=excluded.priority_processing,team_members=excluded.team_members"""
        with self.lock:
            try:
                if self.backend == "postgres":
                    with self.conn.cursor() as cur:
                        cur.executemany(self._sql(sql), plans)
                else:
                    self.conn.executemany(sql, plans)
                    self.conn.commit()
            except Exception as exc:
                self._raise_portable_integrity(exc)

    def seed_products(self):
        products = [
            ("creator_plus_monthly", "Creator Plus", "More games, storage and creator tools", "1.99", "creator_plan:plus", 1, 0),
            ("creator_pro_monthly", "Creator Pro", "Higher limits and professional creator tools", "3.99", "creator_plan:pro", 1, 0),
        ]
        sql = """INSERT INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at)
                 VALUES(?,?,?,?,?,?,?)
                 ON CONFLICT(product_id) DO UPDATE SET
                 label=excluded.label,description=excluded.description,price_usd=excluded.price_usd,
                 entitlement_key=excluded.entitlement_key,active=excluded.active"""
        with self.lock:
            try:
                if self.backend == "postgres":
                    with self.conn.cursor() as cur:
                        cur.executemany(self._sql(sql), products)
                else:
                    self.conn.executemany(sql, products)
                    self.conn.commit()
            except Exception as exc:
                self._raise_portable_integrity(exc)

    def execute(self, sql, args=()):
        with self.lock:
            try:
                if self.backend == "postgres":
                    cur = self.conn.cursor()
                    cur.execute(self._sql(sql), args)
                    return cur
                cur = self.conn.execute(sql, args)
                self.conn.commit()
                return cur
            except Exception as exc:
                self._raise_portable_integrity(exc)

    def one(self, sql, args=()):
        with self.lock:
            if self.backend == "postgres":
                with self.conn.cursor() as cur:
                    cur.execute(self._sql(sql), args)
                    row = cur.fetchone()
                    return dict(row) if row else None
            row = self.conn.execute(sql, args).fetchone()
            return dict(row) if row else None

    def all(self, sql, args=()):
        with self.lock:
            if self.backend == "postgres":
                with self.conn.cursor() as cur:
                    cur.execute(self._sql(sql), args)
                    return [dict(r) for r in cur.fetchall()]
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def ping(self) -> bool:
        try:
            row = self.one("SELECT 1 AS ok")
            return bool(row and row.get("ok") == 1)
        except Exception:
            return False
