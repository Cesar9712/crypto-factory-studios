from __future__ import annotations
import sqlite3, json
from pathlib import Path
from .models import Order

SCHEMA='''
CREATE TABLE IF NOT EXISTS orders(
 order_id TEXT PRIMARY KEY, player_id TEXT NOT NULL, product_id TEXT NOT NULL,
 expected_amount REAL NOT NULL, network TEXT NOT NULL, token TEXT NOT NULL,
 token_contract TEXT NOT NULL, receiving_address TEXT NOT NULL,
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
 idempotency_key TEXT UNIQUE NOT NULL, status TEXT NOT NULL,
 received_amount REAL NOT NULL DEFAULT 0, sender_address TEXT NOT NULL DEFAULT '',
 txid TEXT NOT NULL DEFAULT '', event_index INTEGER NOT NULL DEFAULT -1,
 block_number INTEGER NOT NULL DEFAULT 0, detected_at INTEGER NOT NULL DEFAULT 0,
 confirmed_at INTEGER NOT NULL DEFAULT 0, fulfilled_at INTEGER NOT NULL DEFAULT 0,
 confirmation_state TEXT NOT NULL DEFAULT 'UNCONFIRMED'
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_consumed_transfer ON orders(txid,event_index) WHERE txid <> '';
CREATE TABLE IF NOT EXISTS entitlements(
 entitlement_key TEXT PRIMARY KEY, player_id TEXT NOT NULL, product_id TEXT NOT NULL,
 order_id TEXT UNIQUE NOT NULL, granted_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, payload TEXT NOT NULL, created_at INTEGER NOT NULL);
'''

class PaymentRepository:
    def __init__(self, db_path=':memory:'):
        self.db=sqlite3.connect(db_path)
        self.db.row_factory=sqlite3.Row
        self.db.executescript(SCHEMA); self.db.commit()
    def insert_order(self, order:Order):
        d=order.to_dict(); keys=list(d); vals=[d[k] for k in keys]
        self.db.execute(f"INSERT INTO orders({','.join(keys)}) VALUES({','.join('?' for _ in keys)})",vals); self.db.commit()
    def update_order(self, order:Order):
        d=order.to_dict(); keys=[k for k in d if k!='order_id']
        self.db.execute('UPDATE orders SET '+','.join(f'{k}=?' for k in keys)+' WHERE order_id=?',[d[k] for k in keys]+[order.order_id]); self.db.commit()
    def get_order(self, order_id:str):
        r=self.db.execute('SELECT * FROM orders WHERE order_id=?',(order_id,)).fetchone(); return Order(**dict(r)) if r else None
    def get_order_by_idempotency(self,key:str):
        r=self.db.execute('SELECT * FROM orders WHERE idempotency_key=?',(key,)).fetchone(); return Order(**dict(r)) if r else None
    def transfer_consumed(self,txid:str,event_index:int):
        return self.db.execute('SELECT 1 FROM orders WHERE txid=? AND event_index=?',(txid,event_index)).fetchone() is not None
    def list_reconcilable(self):
        rows=self.db.execute("SELECT * FROM orders WHERE status IN ('PAYMENT_DETECTED','CONFIRMING','CONFIRMED')").fetchall(); return [Order(**dict(r)) for r in rows]
    def grant_entitlement_once(self,player_id,product_id,order_id,now):
        key=f'{player_id}:{product_id}'
        try:
            self.db.execute('INSERT INTO entitlements VALUES(?,?,?,?,?)',(key,player_id,product_id,order_id,now)); self.db.commit(); return True
        except sqlite3.IntegrityError: return False
    def has_entitlement(self,player_id,product_id):
        return self.db.execute('SELECT 1 FROM entitlements WHERE player_id=? AND product_id=?',(player_id,product_id)).fetchone() is not None
    def list_entitlements(self,player_id):
        return [dict(r) for r in self.db.execute('SELECT * FROM entitlements WHERE player_id=?',(player_id,)).fetchall()]
    def audit(self,event,payload,now):
        self.db.execute('INSERT INTO audit_log(event,payload,created_at) VALUES(?,?,?)',(event,json.dumps(payload,sort_keys=True),now)); self.db.commit()
