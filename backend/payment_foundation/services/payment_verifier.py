from __future__ import annotations
from dataclasses import dataclass
from ..models import TransferEvent

@dataclass
class VerificationResult:
    valid: bool
    status: str
    reason: str=''

class PaymentVerifier:
    EPSILON=0.000001
    def __init__(self, config): self.config=config
    def verify(self,event:TransferEvent,expected_amount:float):
        if not event.success: return VerificationResult(False,'FAILED','transaction_failed')
        if event.token_contract != self.config['token_contract']: return VerificationResult(False,'FAILED','wrong_token_contract')
        if event.to_address != self.config['treasury_address']: return VerificationResult(False,'FAILED','wrong_destination')
        if event.amount < expected_amount-self.EPSILON: return VerificationResult(False,'UNDERPAID','underpayment')
        if event.amount > expected_amount+self.EPSILON: return VerificationResult(False,'OVERPAID','overpayment_review')
        if not event.confirmed: return VerificationResult(True,'CONFIRMING','awaiting_confirmation')
        return VerificationResult(True,'CONFIRMED','confirmed')
