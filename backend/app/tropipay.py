from __future__ import annotations

import json
import time
from typing import Any

import httpx


class TropiPayError(RuntimeError):
    pass


class TropiPayClient:
    """Minimal server-to-server TropiPay API v3 client.

    Credentials never leave the backend. Incoming webhooks are treated only as
    hints; fulfillment is authorized exclusively after an authenticated
    movement lookup returns an exact completed movement.
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.base_url = settings.tropipay_api_base_url.rstrip("/")
        self._access_token = ""
        self._token_expires_at = 0.0

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.tropipay_enabled
            and self.settings.tropipay_client_id
            and self.settings.tropipay_client_secret
        )

    def _token(self) -> str:
        if not self.enabled:
            raise TropiPayError("TropiPay is not configured")
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        try:
            response = httpx.post(
                f"{self.base_url}/access/token",
                json={
                    "client_id": self.settings.tropipay_client_id,
                    "client_secret": self.settings.tropipay_client_secret,
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=self.settings.tropipay_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            token = str(payload.get("access_token") or "")
            if not token:
                raise ValueError("missing_access_token")
            expires_in = int(payload.get("expires_in") or 3600)
            self._access_token = token
            self._token_expires_at = time.time() + max(300, expires_in)
            return token
        except Exception as exc:
            raise TropiPayError("TropiPay authentication failed") from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_paylink(
        self,
        *,
        reference: str,
        concept: str,
        description: str,
        amount_cents: int,
        currency: str,
        success_url: str,
        failed_url: str,
        notification_url: str,
    ) -> dict[str, Any]:
        if amount_cents < 100:
            raise TropiPayError("TropiPay PayLinks require at least 100 cents")
        body = {
            "concept": concept[:254],
            "description": description[:500],
            "amount": int(amount_cents),
            "currency": currency,
            # singleUse=true requires full customer address/phone/country data.
            # CFS instead uses a unique internal reference and idempotent
            # fulfillment, then independently verifies the movement.
            "singleUse": False,
            "favorite": False,
            "reasonId": 4,
            "reference": reference,
            "expirationDays": 1,
            "lang": "es",
            "payment3DS": "default",
            "urlSuccess": success_url,
            "urlFailed": failed_url,
            "urlNotification": notification_url,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/paymentcards",
                json=body,
                headers=self._headers(),
                timeout=self.settings.tropipay_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("id") or not payload.get("shortUrl"):
                raise ValueError("invalid_paylink_response")
            return payload
        except TropiPayError:
            raise
        except Exception as exc:
            raise TropiPayError("Could not create TropiPay PayLink") from exc

    def find_movement(
        self, *, reference: str, amount_cents: int, currency: str
    ) -> dict[str, Any] | None:
        query = {
            "state": ["completed", "pending", "failed", "cancelled"],
            "currency": currency,
            "amountGte": int(amount_cents),
            "amountLte": int(amount_cents),
            "reference": reference,
        }
        try:
            response = httpx.get(
                f"{self.base_url}/movements/",
                params={"limit": 20, "offset": 0, "query": json.dumps(query, separators=(",", ":"))},
                headers=self._headers(),
                timeout=self.settings.tropipay_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", payload if isinstance(payload, list) else [])
            for item in items or []:
                if (
                    str(item.get("reference") or "") == reference
                    and str(item.get("currency") or "").upper() == currency.upper()
                    and int(item.get("amount") or 0) == int(amount_cents)
                ):
                    return item
            return None
        except TropiPayError:
            raise
        except Exception as exc:
            raise TropiPayError("Could not verify TropiPay movement") from exc
