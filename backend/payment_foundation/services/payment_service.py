from __future__ import annotations
import time, uuid
from pathlib import Path
import json
from ..models import Order, PaymentStatus

class PaymentService:
    def __init__(self,repo,provider,verifier,config,catalog,clock=None):
        self.repo=repo; self.provider=provider; self.verifier=verifier; self.config=config; self.catalog=catalog; self.clock=clock or (lambda:int(time.time()))
    def create_order(self,player_id,product_id,idempotency_key):
        if not self.config.get('payments_enabled',False): raise ValueError('payments_disabled')
        existing=self.repo.get_order_by_idempotency(idempotency_key)
        if existing: return existing
        product=self.catalog.get(product_id)
        if not product or not product.get('active'): raise ValueError('invalid_product')
        now=self.clock(); order=Order(
            order_id='ord_'+uuid.uuid4().hex[:16], player_id=player_id, product_id=product_id,
            expected_amount=float(product['price_usdt']), network=self.config['network'], token=self.config['token'],
            token_contract=self.config['token_contract'], receiving_address=self.config['treasury_address'],
            created_at=now, expires_at=now+int(self.config.get('order_ttl_seconds',900)), idempotency_key=idempotency_key,
            status=PaymentStatus.WAITING_PAYMENT.value)
        self.repo.insert_order(order); self.repo.audit('order_created',{'order_id':order.order_id,'product_id':product_id},now); return order
    def submit_txid(self,order_id,txid,event_index=0):
        order=self.repo.get_order(order_id)
        if not order: raise ValueError('order_not_found')
        if order.status==PaymentStatus.FULFILLED.value: return order
        now=self.clock()
        if now>order.expires_at: order.status=PaymentStatus.EXPIRED.value; self.repo.update_order(order); return order
        if self.repo.transfer_consumed(txid,event_index): order.status=PaymentStatus.REVIEW_REQUIRED.value; self.repo.update_order(order); return order
        event=self.provider.get_transfer(txid,event_index)
        if not event: order.status=PaymentStatus.WAITING_PAYMENT.value; self.repo.update_order(order); return order
        result=self.verifier.verify(event,order.expected_amount)
        order.txid=event.txid; order.event_index=event.event_index; order.received_amount=event.amount; order.sender_address=event.from_address; order.block_number=event.block_number; order.detected_at=now
        order.status=result.status; order.confirmation_state='SOLIDIFIED' if event.confirmed else 'PENDING'
        if result.status=='CONFIRMED': order.confirmed_at=now
        self.repo.update_order(order); self.repo.audit('payment_checked',{'order_id':order_id,'status':order.status,'reason':result.reason},now)
        if order.status=='CONFIRMED': return self.fulfill(order.order_id)
        return order
    def fulfill(self,order_id):
        order=self.repo.get_order(order_id)
        if not order: raise ValueError('order_not_found')
        if order.status==PaymentStatus.FULFILLED.value: return order
        if order.status!=PaymentStatus.CONFIRMED.value: return order
        now=self.clock(); self.repo.grant_entitlement_once(order.player_id,order.product_id,order.order_id,now)
        order.status=PaymentStatus.FULFILLED.value; order.fulfilled_at=now; self.repo.update_order(order); self.repo.audit('order_fulfilled',{'order_id':order_id},now); return order
    def reconcile(self):
        output=[]
        for order in self.repo.list_reconcilable():
            if order.status=='CONFIRMED': output.append(self.fulfill(order.order_id)); continue
            if order.txid: output.append(self.submit_txid(order.order_id,order.txid,order.event_index))
        return output
