from decimal import Decimal
from types import SimpleNamespace

from backend.app.blockchain import ProductionBlockchainVerifier, TRANSFER_TOPIC
from backend.app.payments import PaymentMethodRegistry, PriceService


def settings():
    return SimpleNamespace(
        tron_usdt_address='TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9',
        bsc_usdt_address='0xb6e727732F845bDb7792C075B147658e84a173d2',
        sol_address='EpiJ5GUjXMhcQpZtErxwGq5VZKwvkxV8kSz8PUKtpsr2',
        tron_rpc_url='https://tron.invalid', tron_api_key='',
        bsc_rpc_url='https://bsc.invalid', solana_rpc_url='https://sol.invalid',
        sol_price_url='https://price.invalid', blockchain_timeout_seconds=1,
        tron_min_confirmations=20, bsc_min_confirmations=5,
        solana_commitment='finalized', payments_mode='PRODUCTION',
        mock_sol_usd_rate='150.00',
    )


def test_bsc_rejects_malformed_hash_before_provider_call(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_bsc'); verifier=ProductionBlockchainVerifier(s)
    monkeypatch.setattr(verifier, '_rpc', lambda *a, **k: (_ for _ in ()).throw(AssertionError('provider should not be called')))
    result=verifier.verify(method, '0x' + 'z'*64, Decimal('1.99'))
    assert result['status']=='NOT_FOUND'
    assert result['reason']=='invalid_tx_hash'


def test_solana_rejects_non_base58_signature_before_provider_call(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('sol'); verifier=ProductionBlockchainVerifier(s)
    monkeypatch.setattr(verifier, '_rpc', lambda *a, **k: (_ for _ in ()).throw(AssertionError('provider should not be called')))
    result=verifier.verify(method, '0'*88, Decimal('0.01'))
    assert result['status']=='NOT_FOUND'
    assert result['reason']=='invalid_signature'


def test_solana_only_accepts_system_program_native_transfer(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('sol'); verifier=ProductionBlockchainVerifier(s)
    txid='2'*88
    malicious={
        'slot':123,'meta':{'err':None,'innerInstructions':[]},
        'transaction':{'message':{'instructions':[{
            'program':'spl-token',
            'parsed':{'type':'transfer','info':{'destination':method.address,'lamports':20_000_000}}
        }]}}
    }
    def rpc(url,name,params):
        if name=='getTransaction': return malicious
        if name=='getSignatureStatuses': return {'value':[{'err':None,'confirmationStatus':'finalized'}]}
        raise AssertionError(name)
    monkeypatch.setattr(verifier,'_rpc',rpc)
    result=verifier.verify(method,txid,Decimal('0.02'))
    assert result['status']=='WRONG_RECIPIENT'


def test_production_overpayment_requires_manual_review(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_bsc'); verifier=ProductionBlockchainVerifier(s)
    recipient=method.address.lower().removeprefix('0x').rjust(64,'0')
    receipt={'transactionHash':'0x'+'a'*64,'status':'0x1','blockNumber':'0x64','logs':[{
        'address':method.token_contract,
        'topics':[TRANSFER_TOPIC,'0x'+'1'.rjust(64,'0'),'0x'+recipient],
        'data':hex(2*10**18),
    }]}
    monkeypatch.setattr(verifier,'_rpc',lambda url,name,params:{'eth_chainId':'0x38','eth_getTransactionReceipt':receipt,'eth_blockNumber':'0x70'}[name])
    result=verifier.verify(method,'0x'+'a'*64,Decimal('1.99'))
    assert result['status']=='MANUAL_REVIEW'
    assert result['reason']=='overpayment'
    assert result['success'] is False


def test_production_stablecoin_quote_uses_small_unique_payment_marker(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_tron'); service=PriceService(s)
    monkeypatch.setattr('backend.app.payments.secrets.randbelow', lambda n: 4321)
    amount, rate, source=service.quote_amount(Decimal('1.99'),method)
    assert amount==Decimal('1.994322')
    assert rate==Decimal('1')
    assert source=='stable_reference_unique_amount'
