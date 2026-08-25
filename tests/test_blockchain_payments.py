from decimal import Decimal
from types import SimpleNamespace

from backend.app.blockchain import ProductionBlockchainVerifier, TRANSFER_TOPIC, _tron_payload_hex
from backend.app.payments import PaymentMethodRegistry, canonical_txid


def settings():
    return SimpleNamespace(
        tron_usdt_address='TSrSa2iL7a1csWRLTrzhRoW1oUUaDKpDj9',
        bsc_usdt_address='0xb6e727732F845bDb7792C075B147658e84a173d2',
        sol_address='EpiJ5GUjXMhcQpZtErxwGq5VZKwvkxV8kSz8PUKtpsr2',
        tron_rpc_url='https://tron.invalid', tron_api_key='',
        bsc_rpc_url='https://bsc.invalid', solana_rpc_url='https://sol.invalid',
        blockchain_timeout_seconds=1, blockchain_retries=0,
        tron_min_confirmations=20, bsc_min_confirmations=5,
        solana_commitment='finalized',
    )


def test_txid_normalization_preserves_solana_case():
    s=settings(); methods=PaymentMethodRegistry(s)
    assert canonical_txid(methods.get('usdt_tron'), 'ABCD') == 'abcd'
    assert canonical_txid(methods.get('usdt_bsc'), '0xABCD') == '0xabcd'
    assert canonical_txid(methods.get('sol'), 'AbCdEf') == 'AbCdEf'


def test_bsc_verifier_checks_contract_recipient_amount_and_confirmations(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_bsc'); verifier=ProductionBlockchainVerifier(s)
    recipient=method.address.lower().removeprefix('0x').rjust(64, '0')
    sender='1'.rjust(64, '0')
    txid='0x'+'a'*64
    receipt={
        'transactionHash':txid,'status':'0x1','blockNumber':'0x64',
        'logs':[{'address':method.token_contract,'topics':[TRANSFER_TOPIC,'0x'+sender,'0x'+recipient],'data':hex(1_990_000_000_000_000_000)}]
    }
    def rpc(url, name, params):
        return {'eth_chainId':'0x38','eth_getTransactionReceipt':receipt,'eth_blockNumber':'0x70'}[name]
    monkeypatch.setattr(verifier,'_rpc',rpc)
    result=verifier.verify(method,txid,Decimal('1.99'))
    assert result['status']=='CONFIRMED'
    assert result['success'] is True
    assert Decimal(result['received_amount'])==Decimal('1.99')
    assert result['confirmations']>=5


def test_bsc_wrong_recipient_is_rejected(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_bsc'); verifier=ProductionBlockchainVerifier(s)
    wrong='2'.rjust(64,'0'); txid='0x'+'b'*64
    receipt={'transactionHash':txid,'status':'0x1','blockNumber':'0x64','logs':[{'address':method.token_contract,'topics':[TRANSFER_TOPIC,'0x'+'1'.rjust(64,'0'),'0x'+wrong],'data':hex(2*10**18)}]}
    monkeypatch.setattr(verifier,'_rpc',lambda url,name,params:{'eth_chainId':'0x38','eth_getTransactionReceipt':receipt,'eth_blockNumber':'0x70'}[name])
    assert verifier.verify(method,txid,Decimal('1.99'))['status']=='WRONG_RECIPIENT'


def test_tron_verifier_checks_transfer_log(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_tron'); verifier=ProductionBlockchainVerifier(s)
    txid='a'*64
    contract=_tron_payload_hex(method.token_contract)
    recipient_payload=_tron_payload_hex(method.address)
    recipient_topic=recipient_payload[2:].rjust(64,'0')
    transfer_topic=TRANSFER_TOPIC.removeprefix('0x')
    info={'id':txid,'blockNumber':100,'receipt':{'result':'SUCCESS'},'log':[{'address':contract[-40:],'topics':[transfer_topic,'0'*64,recipient_topic],'data':hex(1_990_000)[2:]}]}
    def post(url,payload,headers=None):
        if url.endswith('gettransactionbyid'): return {'txID':txid}
        if url.endswith('gettransactioninfobyid'): return info
        if url.endswith('getnowblock'): return {'blockID':'x','block_header':{'raw_data':{'number':125}}}
        raise AssertionError(url)
    monkeypatch.setattr(verifier,'_post_json',post)
    result=verifier.verify(method,txid,Decimal('1.99'))
    assert result['status']=='CONFIRMED'
    assert result['received_amount']=='1.99'


def test_solana_verifier_requires_exact_treasury_transfer(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('sol'); verifier=ProductionBlockchainVerifier(s)
    txid='2'*88
    transaction={
        'slot':123,'meta':{'err':None,'innerInstructions':[]},
        'transaction':{'message':{'instructions':[{'program':'system','parsed':{'type':'transfer','info':{'destination':method.address,'lamports':19_000_000}}}]}}
    }
    def rpc(url,name,params):
        if name=='getTransaction': return transaction
        if name=='getSignatureStatuses': return {'value':[{'err':None,'confirmationStatus':'finalized'}]}
        raise AssertionError(name)
    monkeypatch.setattr(verifier,'_rpc',rpc)
    verified=verifier.verify(method,txid,Decimal('0.019'))
    assert verified['status']=='CONFIRMED'
    assert verified['success'] is True


def test_provider_failure_is_not_treated_as_payment(monkeypatch):
    s=settings(); method=PaymentMethodRegistry(s).get('usdt_bsc'); verifier=ProductionBlockchainVerifier(s)
    def fail_rpc(*args,**kwargs):
        from backend.app.blockchain import ProviderUnavailable
        raise ProviderUnavailable('down')
    monkeypatch.setattr(verifier,'_rpc',fail_rpc)
    result=verifier.verify(method,'0x'+'c'*64,Decimal('1.99'))
    assert result['status']=='PROVIDER_UNAVAILABLE'
    assert result['success'] is False
