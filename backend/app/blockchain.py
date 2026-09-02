from __future__ import annotations

import hashlib
import re
import time
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


def _b58decode(value: str) -> bytes:
    n = 0
    for ch in value:
        if ch not in _B58:
            raise ValueError('invalid_base58')
        n = n * 58 + _B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    pad = len(value) - len(value.lstrip('1'))
    return b'\0' * pad + raw


def _tron_b58_from_hex20(value: str) -> str:
    h = value.lower().removeprefix('0x')[-40:]
    payload = b'\x41' + bytes.fromhex(h)
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _b58encode(payload + checksum)


def _tron_payload_hex(address: str) -> str:
    raw = _b58decode(address)
    if len(raw) != 25 or raw[0] != 0x41:
        raise ValueError('invalid_tron_address')
    checksum = hashlib.sha256(hashlib.sha256(raw[:21]).digest()).digest()[:4]
    if checksum != raw[21:]:
        raise ValueError('invalid_tron_address')
    return raw[:21].hex()


def _tron_contract_matches(log_address: str, expected_payload_hex: str) -> bool:
    # TRON APIs have historically exposed event-log contract addresses either
    # with or without the leading 0x41 network byte. Accept both encodings, but
    # only after exact hex normalization.
    observed = log_address.lower().removeprefix('0x')
    expected = expected_payload_hex.lower().removeprefix('0x')
    return observed in {expected, expected[-40:]}


def _amount_result(received: Decimal, expected: Decimal) -> tuple[str, bool, str | None]:
    if received < expected:
        return 'UNDERPAID', False, 'underpayment'
    if received > expected:
        # Do not auto-fulfil overpayments on a shared treasury address. Exact
        # amount matching is also an order-binding signal against TX-hash races.
        return 'MANUAL_REVIEW', False, 'overpayment'
    return 'CONFIRMED', True, None


class ProviderUnavailable(RuntimeError):
    pass


class ProductionBlockchainVerifier:
    def __init__(self, settings: Any):
        self.settings = settings

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        retries = max(0, int(getattr(self.settings, 'blockchain_retries', 2)))
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                r = httpx.post(url, json=payload, headers=headers, timeout=self.settings.blockchain_timeout_seconds)
                if r.status_code == 429 or 500 <= r.status_code < 600:
                    raise httpx.HTTPStatusError('temporary provider response', request=r.request, response=r)
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, dict):
                    raise ValueError('invalid_provider_json')
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                if attempt >= retries:
                    break
                time.sleep(min(0.25 * (2 ** attempt), 1.0))
        raise ProviderUnavailable(str(last_exc or 'provider unavailable')) from last_exc

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
            if method.method_id == 'usdc_base':
                return self._verify_base(method, txid, expected_amount)
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
        if not re.fullmatch(r'[0-9a-fA-F]{64}', txid):
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_tx_hash', 'txid': txid, 'network': method.network}
        base = self.settings.tron_rpc_url.rstrip('/')
        headers = self._tron_headers()
        tx = self._post_json(base + '/wallet/gettransactionbyid', {'value': txid}, headers)
        info = self._post_json(base + '/wallet/gettransactioninfobyid', {'value': txid}, headers)
        if not tx or not tx.get('txID') or not info or not info.get('id'):
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        if str(tx.get('txID')).lower() != txid.lower() or str(info.get('id')).lower() != txid.lower():
            return {'status': 'FAILED', 'success': False, 'reason': 'provider_tx_mismatch', 'txid': txid, 'network': method.network}
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
            if not _tron_contract_matches(str(log.get('address') or ''), expected_contract):
                continue
            found_contract = True
            topics = [str(x).lower().removeprefix('0x') for x in (log.get('topics') or [])]
            if len(topics) < 3 or ('0x' + topics[0]) != TRANSFER_TOPIC:
                continue
            try:
                recipient = _tron_b58_from_hex20(topics[2])
            except Exception:
                continue
            if recipient != method.address:
                continue
            found_recipient = True
            try:
                received_units += int(str(log.get('data') or '0').removeprefix('0x'), 16)
            except ValueError:
                return {'status': 'FAILED', 'success': False, 'reason': 'invalid_transfer_amount', 'txid': txid, 'network': method.network}
        if not found_contract:
            return {'status': 'WRONG_ASSET', 'success': False, 'txid': txid, 'network': method.network, 'token_contract': method.token_contract}
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_units) / (Decimal(10) ** method.decimals)
        if confirmations < self.settings.tron_min_confirmations:
            return {'status': 'CONFIRMING', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': False}
        status, success, reason = _amount_result(received, expected)
        result={'status': status, 'success': success, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': True, 'block_number': block_num, 'provider': 'tron-fullnode-http'}
        if reason: result['reason']=reason
        return result

    def _verify_bsc(self, method, txid: str, expected: Decimal) -> dict[str, Any]:
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', txid):
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_tx_hash', 'txid': txid, 'network': method.network}
        chain_id_raw = self._rpc(self.settings.bsc_rpc_url, 'eth_chainId', [])
        if not isinstance(chain_id_raw, str):
            raise ProviderUnavailable('invalid_chain_id')
        chain_id = int(chain_id_raw, 16)
        if chain_id != 56:
            return {'status': 'WRONG_NETWORK', 'success': False, 'txid': txid, 'network': method.network}
        receipt = self._rpc(self.settings.bsc_rpc_url, 'eth_getTransactionReceipt', [txid])
        if not receipt:
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        if int(receipt.get('status', '0x0'), 16) != 1:
            return {'status': 'FAILED', 'success': False, 'txid': txid, 'network': method.network}
        if str(receipt.get('transactionHash') or txid).lower() != txid.lower():
            return {'status': 'FAILED', 'success': False, 'reason': 'provider_tx_mismatch', 'txid': txid, 'network': method.network}
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
            try:
                received_units += int(log.get('data') or '0x0', 16)
            except (TypeError, ValueError):
                return {'status': 'FAILED', 'success': False, 'reason': 'invalid_transfer_amount', 'txid': txid, 'network': method.network}
        if not found_contract:
            return {'status': 'WRONG_ASSET', 'success': False, 'txid': txid, 'network': method.network, 'token_contract': method.token_contract}
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_units) / (Decimal(10) ** method.decimals)
        if confirmations < self.settings.bsc_min_confirmations:
            return {'status': 'CONFIRMING', 'success': False, 'txid': txid, 'network': method.network, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': False}
        status, success, reason = _amount_result(received, expected)
        result={'status': status, 'success': success, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': True, 'block_number': block_num, 'provider': 'bsc-json-rpc'}
        if reason: result['reason']=reason
        return result

    def _verify_base(self, method, txid: str, expected: Decimal) -> dict[str, Any]:
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', txid):
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_tx_hash', 'txid': txid, 'network': method.network}
        chain_id_raw = self._rpc(self.settings.base_rpc_url, 'eth_chainId', [])
        if not isinstance(chain_id_raw, str):
            raise ProviderUnavailable('invalid_chain_id')
        chain_id = int(chain_id_raw, 16)
        if chain_id != 8453:
            return {'status': 'WRONG_NETWORK', 'success': False, 'txid': txid, 'network': method.network}
        receipt = self._rpc(self.settings.base_rpc_url, 'eth_getTransactionReceipt', [txid])
        if not receipt:
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        if int(receipt.get('status', '0x0'), 16) != 1:
            return {'status': 'FAILED', 'success': False, 'txid': txid, 'network': method.network}
        if str(receipt.get('transactionHash') or txid).lower() != txid.lower():
            return {'status': 'FAILED', 'success': False, 'reason': 'provider_tx_mismatch', 'txid': txid, 'network': method.network}
        latest = int(self._rpc(self.settings.base_rpc_url, 'eth_blockNumber', []), 16)
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
            try:
                received_units += int(log.get('data') or '0x0', 16)
            except (TypeError, ValueError):
                return {'status': 'FAILED', 'success': False, 'reason': 'invalid_transfer_amount', 'txid': txid, 'network': method.network}
        if not found_contract:
            return {'status': 'WRONG_ASSET', 'success': False, 'txid': txid, 'network': method.network, 'token_contract': method.token_contract}
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_units) / (Decimal(10) ** method.decimals)
        if confirmations < self.settings.base_min_confirmations:
            return {'status': 'CONFIRMING', 'success': False, 'txid': txid, 'network': method.network, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': False}
        status, success, reason = _amount_result(received, expected)
        result={'status': status, 'success': success, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'token_contract': method.token_contract, 'received_amount': str(received), 'confirmations': confirmations, 'confirmations_ok': True, 'block_number': block_num, 'provider': 'base-json-rpc'}
        if reason: result['reason']=reason
        return result

    def _verify_solana(self, method, txid: str, expected: Decimal) -> dict[str, Any]:
        try:
            signature = _b58decode(txid)
        except ValueError:
            signature = b''
        if len(signature) != 64:
            return {'status': 'NOT_FOUND', 'success': False, 'reason': 'invalid_signature', 'txid': txid, 'network': method.network}
        result = self._rpc(self.settings.solana_rpc_url, 'getTransaction', [txid, {'encoding': 'jsonParsed', 'commitment': self.settings.solana_commitment, 'maxSupportedTransactionVersion': 0}])
        if not result:
            return {'status': 'NOT_FOUND', 'success': False, 'txid': txid, 'network': method.network}
        meta = result.get('meta') or {}
        if meta.get('err') is not None:
            return {'status': 'FAILED', 'success': False, 'txid': txid, 'network': method.network}
        statuses = self._rpc(self.settings.solana_rpc_url, 'getSignatureStatuses', [[txid], {'searchTransactionHistory': True}]) or {}
        status_rows = statuses.get('value') or []
        signature_status = status_rows[0] if status_rows else None
        if not signature_status or signature_status.get('err') is not None:
            return {'status': 'FAILED', 'success': False, 'reason': 'signature_status_invalid', 'txid': txid, 'network': method.network}
        confirmation_status = str(signature_status.get('confirmationStatus') or '')
        allowed = {'finalized'} if self.settings.solana_commitment == 'finalized' else {'confirmed', 'finalized'}
        if confirmation_status not in allowed:
            return {'status': 'CONFIRMING', 'success': False, 'txid': txid, 'network': method.network, 'confirmations_ok': False, 'commitment': confirmation_status or 'unknown'}
        received_lamports = 0
        found_recipient = False
        instructions = list((((result.get('transaction') or {}).get('message') or {}).get('instructions') or []))
        for group in meta.get('innerInstructions') or []:
            instructions.extend(group.get('instructions') or [])
        for instruction in instructions:
            if not isinstance(instruction, dict) or instruction.get('program') != 'system':
                continue
            parsed = instruction.get('parsed')
            if not isinstance(parsed, dict) or parsed.get('type') not in {'transfer', 'transferWithSeed'}:
                continue
            info = parsed.get('info') or {}
            if info.get('destination') != method.address:
                continue
            try:
                lamports = int(info.get('lamports', 0))
            except (TypeError, ValueError):
                continue
            if lamports <= 0:
                continue
            found_recipient = True
            received_lamports += lamports
        if not found_recipient:
            return {'status': 'WRONG_RECIPIENT', 'success': False, 'txid': txid, 'network': method.network, 'recipient': method.address}
        received = Decimal(received_lamports) / Decimal(1_000_000_000)
        status, success, reason = _amount_result(received, expected)
        result_payload={'status': status, 'success': success, 'txid': txid, 'network': method.network, 'recipient': method.address, 'asset': method.asset, 'received_amount': str(received), 'confirmations_ok': True, 'commitment': confirmation_status, 'slot': result.get('slot'), 'provider': 'solana-json-rpc'}
        if reason: result_payload['reason']=reason
        return result_payload

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
            checks['usdc_base'] = int(self._rpc(self.settings.base_rpc_url, 'eth_chainId', []), 16) == 8453
        except Exception:
            checks['usdc_base'] = False
        try:
            checks['sol'] = self._rpc(self.settings.solana_rpc_url, 'getHealth', []) == 'ok'
        except Exception:
            checks['sol'] = False
        return checks
