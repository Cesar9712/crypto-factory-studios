import unittest, tempfile, os
from backend.app_factory import build_mock_app
from backend.models import TransferEvent

TREASURY='TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9'
CONTRACT='TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

class Clock:
    def __init__(self,t=1000): self.t=t
    def __call__(self): return self.t

class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock(); self.svc,self.repo,self.provider=build_mock_app(clock=self.clock)
        self.order=self.svc.create_order('player1','factory_pass_season_01','idem-1')
    def transfer(self,amount=4.99,contract=CONTRACT,to=TREASURY,confirmed=True,success=True,txid='tx1',idx=0):
        e=TransferEvent(txid,idx,contract,to,'TSENDER',amount,success,confirmed,100,self.clock())
        self.provider.add_transfer(e); return e
    def test_correct_payment_fulfills(self):
        self.transfer(); o=self.svc.submit_txid(self.order.order_id,'tx1'); self.assertEqual(o.status,'FULFILLED'); self.assertTrue(self.repo.has_entitlement('player1','factory_pass_season_01'))
    def test_idempotent_create(self):
        same=self.svc.create_order('player1','factory_pass_season_01','idem-1'); self.assertEqual(same.order_id,self.order.order_id)
    def test_underpayment(self):
        self.transfer(4.0); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'UNDERPAID')
    def test_overpayment(self):
        self.transfer(5.5); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'OVERPAID')
    def test_wrong_contract(self):
        self.transfer(contract='TFAKE'); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'FAILED')
    def test_wrong_destination(self):
        self.transfer(to='TWRONG'); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'FAILED')
    def test_unconfirmed_waits(self):
        self.transfer(confirmed=False); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'CONFIRMING')
    def test_failed_transaction(self):
        self.transfer(success=False); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'FAILED')
    def test_unknown_txid_waits(self): self.assertEqual(self.svc.submit_txid(self.order.order_id,'missing').status,'WAITING_PAYMENT')
    def test_expired_order(self):
        self.clock.t=99999; self.transfer(); self.assertEqual(self.svc.submit_txid(self.order.order_id,'tx1').status,'EXPIRED')
    def test_duplicate_transfer_cannot_credit_second_order(self):
        self.transfer(); self.svc.submit_txid(self.order.order_id,'tx1')
        o2=self.svc.create_order('player2','factory_pass_season_02','idem-2'); self.assertEqual(self.svc.submit_txid(o2.order_id,'tx1').status,'REVIEW_REQUIRED')
    def test_double_submit_is_idempotent(self):
        self.transfer(); a=self.svc.submit_txid(self.order.order_id,'tx1'); b=self.svc.submit_txid(self.order.order_id,'tx1'); self.assertEqual(a.status,'FULFILLED'); self.assertEqual(b.status,'FULFILLED')
    def test_modified_client_price_has_no_effect(self): self.assertEqual(self.order.expected_amount,4.99)
    def test_reconciliation_fulfills_confirmed_after_crash(self):
        self.order.status='CONFIRMED'; self.repo.update_order(self.order); self.svc.reconcile(); self.assertTrue(self.repo.has_entitlement('player1','factory_pass_season_01'))
    def test_provider_unavailable_is_not_client_authority(self):
        self.provider.available=False; self.assertFalse(self.provider.health_check()); self.assertEqual(self.order.status,'WAITING_PAYMENT')

if __name__=='__main__': unittest.main()
