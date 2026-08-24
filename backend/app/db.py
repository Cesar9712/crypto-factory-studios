from __future__ import annotations
import sqlite3
from pathlib import Path
from threading import Lock

SCHEMA = r'''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
 id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE COLLATE NOCASE,password_hash TEXT NOT NULL,
 display_name TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'player',disabled INTEGER NOT NULL DEFAULT 0,
 created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
 token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,revoked_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS creator_profiles(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,slug TEXT NOT NULL UNIQUE,bio TEXT NOT NULL DEFAULT '',
 trust_level TEXT NOT NULL DEFAULT 'NEW',plan_id TEXT NOT NULL DEFAULT 'free',billing_exempt INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS creator_plans(
 plan_id TEXT PRIMARY KEY,label TEXT NOT NULL,max_games INTEGER,max_storage_bytes INTEGER,max_builds_per_game INTEGER,
 max_upload_bytes INTEGER,advanced_analytics INTEGER NOT NULL DEFAULT 0,private_builds INTEGER NOT NULL DEFAULT 0,
 priority_processing INTEGER NOT NULL DEFAULT 0,team_members INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS games(
 game_id TEXT PRIMARY KEY,creator_id TEXT NOT NULL REFERENCES users(id),slug TEXT NOT NULL UNIQUE,title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',genre TEXT NOT NULL DEFAULT 'Other',tags_json TEXT NOT NULL DEFAULT '[]',
 status TEXT NOT NULL DEFAULT 'DRAFT',visibility TEXT NOT NULL DEFAULT 'PUBLIC',web3_enabled INTEGER NOT NULL DEFAULT 0,
 created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,published_build_id TEXT);
CREATE TABLE IF NOT EXISTS game_builds(
 build_id TEXT PRIMARY KEY,game_id TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,creator_id TEXT NOT NULL REFERENCES users(id),
 version TEXT NOT NULL,status TEXT NOT NULL,archive_path TEXT NOT NULL,manifest_json TEXT NOT NULL DEFAULT '{}',
 compressed_bytes INTEGER NOT NULL DEFAULT 0,uncompressed_bytes INTEGER NOT NULL DEFAULT 0,file_count INTEGER NOT NULL DEFAULT 0,
 sha256 TEXT NOT NULL,scan_status TEXT NOT NULL DEFAULT 'PENDING',created_at INTEGER NOT NULL,published_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS security_scans(
 scan_id TEXT PRIMARY KEY,build_id TEXT NOT NULL REFERENCES game_builds(build_id) ON DELETE CASCADE,engine TEXT NOT NULL,
 status TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS game_saves(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,game_id TEXT NOT NULL,save_version INTEGER NOT NULL DEFAULT 1,
 revision INTEGER NOT NULL DEFAULT 0,save_json TEXT NOT NULL DEFAULT '{}',updated_at INTEGER NOT NULL,
 PRIMARY KEY(user_id,game_id));
CREATE TABLE IF NOT EXISTS analytics_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT,game_id TEXT,event_name TEXT NOT NULL,payload_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS reports(
 report_id TEXT PRIMARY KEY,reporter_id TEXT REFERENCES users(id),game_id TEXT,creator_id TEXT,category TEXT NOT NULL,details TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS audit_logs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,actor_id TEXT,action TEXT NOT NULL,target_type TEXT NOT NULL,target_id TEXT,details_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS subscriptions(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,plan_id TEXT NOT NULL,status TEXT NOT NULL,start_at INTEGER NOT NULL,renewal_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS entitlements(
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,entitlement_key TEXT NOT NULL,source TEXT NOT NULL,granted_at INTEGER NOT NULL,
 PRIMARY KEY(user_id,entitlement_key));

CREATE TABLE IF NOT EXISTS products(
 product_id TEXT PRIMARY KEY,label TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',price_usd TEXT NOT NULL,
 entitlement_key TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS payment_methods(
 method_id TEXT PRIMARY KEY,asset TEXT NOT NULL,network TEXT NOT NULL,standard TEXT NOT NULL,address TEXT NOT NULL,
 token_contract TEXT,enabled INTEGER NOT NULL DEFAULT 1,production_allowed INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS payment_quotes(
 quote_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,product_id TEXT NOT NULL REFERENCES products(product_id),
 method_id TEXT NOT NULL REFERENCES payment_methods(method_id),fiat_price_usd TEXT NOT NULL,crypto_amount TEXT NOT NULL,exchange_rate TEXT NOT NULL,
 rate_source TEXT NOT NULL,created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS orders(
 order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,product_id TEXT NOT NULL REFERENCES products(product_id),
 quote_id TEXT NOT NULL REFERENCES payment_quotes(quote_id),method_id TEXT NOT NULL REFERENCES payment_methods(method_id),expected_amount TEXT NOT NULL,
 received_amount TEXT NOT NULL DEFAULT '0',asset TEXT NOT NULL,network TEXT NOT NULL,receiving_address TEXT NOT NULL,status TEXT NOT NULL,
 transaction_hash TEXT,created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,confirmed_at INTEGER NOT NULL DEFAULT 0,fulfilled_at INTEGER NOT NULL DEFAULT 0,
 idempotency_key TEXT NOT NULL UNIQUE);
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_network_tx ON orders(network,transaction_hash) WHERE transaction_hash IS NOT NULL;
CREATE TABLE IF NOT EXISTS blockchain_transactions(
 fingerprint TEXT PRIMARY KEY,network TEXT NOT NULL,transaction_hash TEXT NOT NULL,order_id TEXT NOT NULL REFERENCES orders(order_id),
 verification_json TEXT NOT NULL,consumed_at INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uq_blockchain_network_tx ON blockchain_transactions(network,transaction_hash);
CREATE TABLE IF NOT EXISTS payment_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,order_id TEXT NOT NULL REFERENCES orders(order_id),event_type TEXT NOT NULL,
 details_json TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS purchase_history(
 purchase_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id),
 product_id TEXT NOT NULL,amount TEXT NOT NULL,asset TEXT NOT NULL,network TEXT NOT NULL,transaction_hash TEXT,created_at INTEGER NOT NULL);
'''

class DB:
    def __init__(self,path:Path):
        self.path=path; self.lock=Lock(); self.conn=sqlite3.connect(path,check_same_thread=False)
        self.conn.row_factory=sqlite3.Row
        with self.lock: self.conn.executescript(SCHEMA); self.conn.commit()
        self.seed_plans(); self.seed_products()
    def seed_plans(self):
        plans=[
            ('free','Creator Free',2,512*1024*1024,3,64*1024*1024,0,0,0,1),
            ('plus','Creator Plus',10,5*1024*1024*1024,10,256*1024*1024,1,1,1,3),
            ('pro','Creator Pro',50,25*1024*1024*1024,30,512*1024*1024,1,1,1,10),
            ('internal_unlimited','Internal Unlimited',None,None,None,None,1,1,1,100),
        ]
        with self.lock:
            self.conn.executemany('INSERT OR REPLACE INTO creator_plans(plan_id,label,max_games,max_storage_bytes,max_builds_per_game,max_upload_bytes,advanced_analytics,private_builds,priority_processing,team_members) VALUES(?,?,?,?,?,?,?,?,?,?)',plans)
            self.conn.commit()

    def seed_products(self):
        products=[
            ('creator_plus_monthly','Creator Plus','More games, storage and creator tools','4.99','creator_plan:plus',1,0),
            ('creator_pro_monthly','Creator Pro','Higher limits and professional creator tools','9.99','creator_plan:pro',1,0),
        ]
        with self.lock:
            self.conn.executemany('INSERT OR IGNORE INTO products(product_id,label,description,price_usd,entitlement_key,active,created_at) VALUES(?,?,?,?,?,?,?)',products)
            self.conn.commit()

    def execute(self,sql,args=()):
        with self.lock:
            cur=self.conn.execute(sql,args); self.conn.commit(); return cur
    def one(self,sql,args=()):
        with self.lock:
            row=self.conn.execute(sql,args).fetchone(); return dict(row) if row else None
    def all(self,sql,args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql,args).fetchall()]
