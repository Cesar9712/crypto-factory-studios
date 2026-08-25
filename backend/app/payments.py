from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Any
import hashlib
import re
import httpx

_B58='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def _b58decode(value: str) -> bytes:
    num=0
    for ch in value:
        if ch not in _B58: raise ValueError('invalid_base58')
        num=num*58+_B58.index(ch)
    raw=num.to_bytes((num.bit_length()+7)//8,'big') if num else b''
    pad=len(value)-len(value.lstrip('1'))
    return b'\x00'*pad+raw

def validate_tron_address(value: str) -> bool:
    try:
        raw=_b58decode(value)
        if len(raw)!=25 or raw[0]!=0x41: return False
        checksum=hashlib.sha256(hashlib.sha256(raw[:21]).digest()).digest()[:4]
        return checksum==raw[21:]
    except Exception: return False

def validate_evm_address(value: str) -> bool:
    return bool(re.fullmatch(r'0x[0-9a-fA-F]{40}',value))

def validate_solana_address(value: str) -> bool:
    try: return len(_b58decode(value))==32
    except Exception: return False

TRON_USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
BSC_USDT_CONTRACT = '0x55d398326f99059ff775485246999027b3197955'

@dataclass(frozen=True)
class PaymentMethod:
    method_id: str
    asset: str
    network: str
    standard: str
    address: str
    token_contract: str | None
    decimals: int
    enabled: bool
    production_allowed: bool
    display_name: str
    warning: str

class PaymentMethodRegistry:
    def __init__(self, settings: Any):
        self.settings = settings
        if not validate_tron_address(settings.tron_usdt_address): raise RuntimeError('Invalid TRON treasury address')
        if not validate_evm_address(settings.bsc_usdt_address): raise RuntimeError('Invalid BSC treasury address')
        if not validate_solana_address(settings.sol_address): raise RuntimeError('Invalid Solana treasury address')
        self._methods = {
            'usdt_tron': PaymentMethod('usdt_tron','USDT','TRON','TRC-20',settings.tron_usdt_address,TRON_USDT_CONTRACT,6,True,True,'USDT · TRON (TRC-20)','Send only USDT on TRON (TRC-20).'),
            'usdt_bsc': PaymentMethod('usdt_bsc','BSC-USD','BNB Smart Chain','BEP-20',settings.bsc_usdt_address,BSC_USDT_CONTRACT,18,True,True,'USDT-compatible · BNB Smart Chain (BEP-20)','Send only Binance-Peg BSC-USD on BNB Smart Chain (BEP-20).'),
            'sol': PaymentMethod('sol','SOL','Solana','Native',settings.sol_address,None,9,True,True,'SOL · Solana','Send only native SOL on Solana.'),
        }
    def get(self, method_id: str) -> PaymentMethod | None: return self._methods.get(method_id)
    def values(self): return tuple(self._methods.values())
    def public(self) -> list[dict[str,Any]]:
        out=[]
        for m in self._methods.values():
            if not m.enabled: continue
            out.append({'method_id':m.method_id,'asset':m.asset,'network':m.network,'standard':m.standard,'display_name':m.display_name,'warning':m.warning,'production_allowed':m.production_allowed})
        return out

class PriceService:
    def __init__(self, settings: Any): self.settings=settings
    def _live_sol_usd(self) -> Decimal:
        try:
            r=httpx.get(self.settings.sol_price_url,params={'ids':'solana','vs_currencies':'usd'},timeout=self.settings.blockchain_timeout_seconds)
            r.raise_for_status()
            value=r.json()['solana']['usd']
            rate=Decimal(str(value))
            if rate <= 0: raise ValueError('invalid_rate')
            return rate
        except Exception as exc:
            raise RuntimeError('SOL price provider unavailable') from exc
    def quote_amount(self, usd_price: Decimal, method: PaymentMethod) -> tuple[Decimal, Decimal, str]:
        if method.method_id in {'usdt_tron','usdt_bsc'}:
            return usd_price.quantize(Decimal('0.000001'), rounding=ROUND_DOWN), Decimal('1'), 'stable_reference'
        if self.settings.payments_mode == 'PRODUCTION':
            sol_usd=self._live_sol_usd(); source='coingecko_live'
        else:
            sol_usd=Decimal(str(self.settings.mock_sol_usd_rate)); source='mock_fixed_rate'
        amount=(usd_price/sol_usd).quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
        return amount, sol_usd, source

class MockBlockchainVerifier:
    def verify(self, method: PaymentMethod, txid: str, expected_amount: Decimal) -> dict[str,Any]:
        tx=txid.strip()
        base={'txid':tx,'network':method.network,'recipient':method.address,'asset':method.asset,'token_contract':method.token_contract,'confirmations_ok':True,'success':True,'provider':'mock'}
        if not tx.startswith('mock_'): return {**base,'status':'NOT_FOUND','success':False,'reason':'mock_requires_fixture'}
        if tx.startswith('mock_wrong_network'): return {**base,'status':'WRONG_NETWORK','network':'Wrong Network','success':False}
        if tx.startswith('mock_wrong_recipient'): return {**base,'status':'WRONG_RECIPIENT','recipient':'wrong','success':False}
        if tx.startswith('mock_wrong_asset'): return {**base,'status':'WRONG_ASSET','asset':'FAKE','success':False}
        if tx.startswith('mock_wrong_contract'): return {**base,'status':'WRONG_ASSET','token_contract':'fake','success':False}
        if tx.startswith('mock_failed'): return {**base,'status':'FAILED','success':False}
        if tx.startswith('mock_unconfirmed'): return {**base,'status':'CONFIRMING','confirmations_ok':False}
        if tx.startswith('mock_under'): return {**base,'status':'UNDERPAID','received_amount':str(max(Decimal('0'),expected_amount-Decimal('0.5')))}
        if tx.startswith('mock_over'): return {**base,'status':'OVERPAID','received_amount':str(expected_amount+Decimal('0.5'))}
        return {**base,'status':'CONFIRMED','received_amount':str(expected_amount)}
    def status(self): return {'usdt_tron':True,'usdt_bsc':True,'sol':True}

def canonical_txid(method: PaymentMethod, txid: str) -> str:
    tx=txid.strip()
    if method.method_id in {'usdt_tron','usdt_bsc'}:
        return tx.lower()
    return tx

def payment_fingerprint(network: str, txid: str) -> str:
    return hashlib.sha256(f'{network.lower()}:{txid.strip()}'.encode()).hexdigest()
