"""CryptoBot (Crypto Pay API) adapter.

API: https://help.crypt.bot/crypto-pay-api
- Auth header: Crypto-Pay-API-Token
- POST {base}/createInvoice
- Webhook: update_type == "invoice_paid"; header `crypto-pay-api-signature` is
  HMAC-SHA256 of the raw request body with key = SHA256(api_token).
"""
import hashlib
import hmac
import logging
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.services.payments.base import InvoiceResult

logger = logging.getLogger(__name__)


class CryptoBotError(Exception):
    pass


class CryptoBotProvider:
    name = "cryptobot"

    def __init__(self, api_token: str | None = None, api_url: str | None = None):
        settings = get_settings()
        self._token = api_token if api_token is not None else settings.cryptobot_api_token
        self._api_url = (api_url or settings.cryptobot_api_url).rstrip("/")

    async def create_invoice(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        internal_payment_id: int,
    ) -> InvoiceResult:
        payload = {
            "asset": currency,
            "amount": str(amount),
            "description": description[:1024],
            "payload": str(internal_payment_id),
            "expires_in": 3600,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self._api_url}/createInvoice",
                json=payload,
                headers={"Crypto-Pay-API-Token": self._token},
            )
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200 or not data.get("ok"):
            logger.error("createInvoice failed: HTTP %s %s", resp.status_code, data.get("error"))
            raise CryptoBotError("failed to create CryptoBot invoice")
        invoice = data["result"]
        url = invoice.get("mini_app_invoice_url") or invoice.get("bot_invoice_url")
        return InvoiceResult(
            provider_payment_id=f"cryptobot:{invoice['invoice_id']}",
            invoice_url=url,
        )

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        secret = hashlib.sha256(self._token.encode()).digest()
        expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
