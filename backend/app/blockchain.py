from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any

import httpx

TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
_B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, 'big')
    out = ''
    while n:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    pad = len(raw) - len(raw.lstrip(b'\0'))
    return ('1' * pad) + (out or '')


def _tron_b58_from_hex20(value: str) -> str:
    h = value.lower().removeprefix('0x')[-40:]
    payload = b'\x41' + bytes.fromhex(h)
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _b58encode(payload + checksum)


def _tron_payload_hex(address: str) -> str:
    n = 0
    for ch in address:
        if ch not in _B58:
            raise ValueError('invalid_tron_address')
        n = n * 58 + _B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    raw = b'\0' * (len(address) - len(address.lstrip('1'))) + raw
    if len(raw) != 25:
        raise ValueError('invalid_tron_address')
    return raw[:21].hex()


def _amount_status(received: Decimal, expected: Decimal) -> str:
    if received < expected:
        return 'UNDERPAID'
    if received > expected:
        return 'OVERPAID'
    return 'CONFIRMED'


class ProviderUnavailable(RuntimeError):
    pass


class ProductionBlockchainVerifier:
    def __init__(self, settings: Any):
        self.settings = settings

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=self.settings.blockchain_timeout_seconds)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(str(exc)) from exc

    def _rpc(self, url: str, method: str, params: list[Any]) -> Any:
        body = self._post_json(url, {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        if body.get('error'):
            raise ProviderUnavailable(str(body['error']))
        return body.get('result')

    def verify(self, method, txid: str, expected_amount: Decimal) -> dict[str, Any]:
        txid = txid.strip()
        try:
            if method.method_id == 'usdt_tron':
                return self._verify_tron(method, txid, expected_amount)
            if method.method_id == 'usdt_bsc':
                return self._verify_bsc(method, txid, expected_amount)
            if method.method_id == 'sol':
                return self._verify_solana(method, txid, expected_amount)
            return {'status': 'FAILED', 'success': False, 'reason': 'unsupported_method', 'txid': txid}
        except ProviderUnavailable:
            return {'status': 'PROVIDER_UNAVAILABLE', 'success': False, 'reason': 'provider_unavailable', 'txid': txid, 'network': method.network}
        except Exception:
            return {'status': 'FAILED', 'success': False, 'reason': 'verification_error', 'txid': txid, 'network': method.network}

    def _tron_headers(self) -> dict[str, str]:
        return {'TRON-PRO-API-KEY': self.settings.tron_api_key} if self.settings.tron_api_key else {}

    def _verify_tron(self, method, txid: str, expected: Decimal) -> dict[str, Any]:
        if len(txid) != 64 or any(c not in '0123456789abcdefABCDEF' for c in txid):
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_tx_hash', 'txid': txid, 'network': method.network}
        base = self.settings.tron_rpc_url.rstrip('/')
        headers = self._tron_headers()
        tx = self._post_json(base + '/wallet/gettransactionbyid', {'value': txid}, headers)
        info = self._post_json(base + '/wallet/gettransactioninfobyid', {'value': txid}, headers)
        if not tx or not tx.get('txID') or not info or not info.get('id'):
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        receipt_result = ((info.get('receipt') or {}).get('result') or info.get('result') or '').upper()
        if receipt_result and receipt_result != 'SUCCESS':
            return {'status': 'FAILED', 'success': False, 'txid': txid, 'network': method.network}
        latest = self._post_json(base + '/wallet/getnowblock', {}, headers)
        latest_num = int((((latest.get('block_header') or {}).get('raw_data') or {}).get('number') or 0))
        block_num = int(info.get('blockNumber') or 0)
        confirmations = max(0, latest_num - block_num + 1) if block_num else 0
        expected_contract = _tron_payload_hex(method.token_contract).lower()
        received_units = 0
        found_contract = False
        found_recipient = False
        for log in info.get('log') or []:
            contract = str(log.get('address') or '').lower().removeprefix('0x')
            topics = [str(x).lower().removeprefix('0x') for x in (log.get('topics') or [])]
            if contract != expected_contract:
                continue
            found_contract = True
            if len(topics) < 3 or ('0x' + topics[0]) != TRANSFER_TOPIC:
                continue
            recipient = _tron_b58_from_hex20(topics[2])
            if recipient != method.address:
                continue
            found_recipient = True
            received_units += int(str(log.get('data') or '0'), 16)
        if not found_contract:
            return {'status': 'WRONG_ASSET', 'success': False, 'txid': txid, 'network': method.network, 'token_contract': method.token_contract}
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_units) / (Decimal(10) ** method.decimals)
        if confirmations < self.settings.tron_min_confirmations:
            return {'status': 'CONFIRMING', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': False}
        status = _amount_status(received, expected)
        return {'status': status, 'success': status in {'CONFIRMED', 'OVERPAID'}, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': True, 'block_number': block_num, 'provider': 'tron-fullnode-http'}

    def _verify_bsc(self, method, txid: str, expected: Decimal) -> dict[str, Any]:
        if not txid.startswith('0x') or len(txid) != 66:
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_tx_hash', 'txid': txid, 'network': method.network}
        chain_id = int(self._rpc(self.settings.bsc_rpc_url, 'eth_chainId', []), 16)
        if chain_id != 56:
            return {'status': 'WRONG_NETWORK', 'success': False, 'txid': txid, 'network': method.network}
        receipt = self._rpc(self.settings.bsc_rpc_url, 'eth_getTransactionReceipt', [txid])
        if not receipt:
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        if int(receipt.get('status', '0x0'), 16) != 1:
            return {'status': 'FAILED', 'success': False, 'txid': txid, 'network': method.network}
        latest = int(self._rpc(self.settings.bsc_rpc_url, 'eth_blockNumber', []), 16)
        block_num = int(receipt['blockNumber'], 16)
        confirmations = max(0, latest - block_num + 1)
        contract = method.token_contract.lower()
        recipient_topic = method.address.lower().removeprefix('0x').rjust(64, '0')
        received_units = 0
        found_contract = False
        found_recipient = False
        for log in receipt.get('logs') or []:
            if str(log.get('address') or '').lower() != contract:
                continue
            found_contract = True
            topics = [str(x).lower() for x in (log.get('topics') or [])]
            if len(topics) < 3 or topics[0] != TRANSFER_TOPIC:
                continue
            if topics[2].removeprefix('0x') != recipient_topic:
                continue
            found_recipient = True
            received_units += int(log.get('data') or '0x0', 16)
        if not found_contract:
            return {'status': 'WRONG_ASSET', 'success': False, 'txid': txid, 'network': method.network, 'token_contract': method.token_contract}
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_units) / (Decimal(10) ** method.decimals)
        if confirmations < self.settings.bsc_min_confirmations:
            return {'status': 'CONFIRMING', 'success': False, 'txid': txid, 'network': method.network, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': False}
        status = _amount_status(received, expected)
        return {'status': status, 'success': status in {'CONFIRMED', 'OVERPAID'}, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': True, 'block_number': block_num, 'provider': 'bsc-json-rpc'}

    def _verify_solana(self, method, txid: str, expected: Decimal) -> dict[str, Any]:
        if len(txid) < 80 or len(txid) > 100:
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_signature', 'txid': txid, 'network': method.network}
        result = self._rpc(self.settings.solana_rpc_url, 'getTransaction', [txid, {'encoding': 'jsonParsed', 'commitment': self.settings.solana_commitment, 'maxSupportedTransactionVersion': 0}])
        if not result:
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        meta = result.get('meta') or {}
        if meta.get('err') is not None:
            return {'status': 'FAILED', 'success': False, 'txid': txid, 'network': method.network}
        received_lamports = 0
        found_recipient = False
        instructions = (((result.get('transaction') or {}).get('message') or {}).get('instructions') or [])
        for instruction in instructions:
            parsed = instruction.get('parsed') if isinstance(instruction, dict) else None
            if not isinstance(parsed, dict) or parsed.get('type') not in {'transfer', 'transferWithSeed'}:
                continue
            info = parsed.get('info') or {}
            if info.get('destination') != method.address:
                continue
            found_recipient = True
            if 'lamports' in info:
                received_lamports += int(info['lamports'])
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_lamports) / Decimal(1_000_000_000)
        status = _amount_status(received, expected)
        return {'status': status, 'success': status in {'CONFIRMED', 'OVERPAID'}, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'received_amount': str(received), 'confirmations_ok': True, 'commitment': self.settings.solana_commitment, 'slot': result.get('slot'), 'provider': 'solana-json-rpc'}

    def status(self) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        try:
            base = self.settings.tron_rpc_url.rstrip('/')
            checks['usdt_tron'] = bool(self._post_json(base + '/wallet/getnowblock', {}, self._tron_headers()).get('blockID'))
        except Exception:
            checks['usdt_tron'] = False
        try:
            checks['usdt_bsc'] = int(self._rpc(self.settings.bsc_rpc_url, 'eth_chainId', []), 16) == 56
        except Exception:
            checks['usdt_bsc'] = False
        try:
            checks['sol'] = self._rpc(self.settings.solana_rpc_url, 'getHealth', []) == 'ok'
        except Exception:
            checks['sol'] = False
        return checks
