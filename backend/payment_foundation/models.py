from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional

class PaymentStatus(str, Enum):
    CREATED='CREATED'; WAITING_PAYMENT='WAITING_PAYMENT'; PAYMENT_DETECTED='PAYMENT_DETECTED'
    CONFIRMING='CONFIRMING'; CONFIRMED='CONFIRMED'; FULFILLED='FULFILLED'; EXPIRED='EXPIRED'
    UNDERPAID='UNDERPAID'; OVERPAID='OVERPAID'; FAILED='FAILED'; REVIEW_REQUIRED='REVIEW_REQUIRED'; REFUNDED='REFUNDED'

@dataclass
class Order:
    order_id: str
    player_id: str
    product_id: str
    expected_amount: float
    network: str
    token: str
    token_contract: str
    receiving_address: str
    created_at: int
    expires_at: int
    idempotency_key: str
    status: str=PaymentStatus.CREATED.value
    received_amount: float=0.0
    sender_address: str=''
    txid: str=''
    event_index: int=-1
    block_number: int=0
    detected_at: int=0
    confirmed_at: int=0
    fulfilled_at: int=0
    confirmation_state: str='UNCONFIRMED'
    def to_dict(self): return asdict(self)

@dataclass
class TransferEvent:
    txid: str
    event_index: int
    token_contract: str
    to_address: str
    from_address: str
    amount: float
    success: bool
    confirmed: bool
    block_number: int=0
    timestamp: int=0
    def unique_key(self)->str: return f'{self.txid}:{self.event_index}'
