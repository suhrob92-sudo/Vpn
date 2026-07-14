"""YooKassa (ЮKassa) adapter — Russian bank cards (Sberbank, Mir, Visa/MC RU), SBP.

API: https://yookassa.ru/developers/api
- Base URL: https://api.yookassa.ru/v3
- Auth: HTTP Basic (shopId : secretKey)
- Create payment: POST /v3/payments with an `Idempotence-Key` header (UUID v4).
  Body: amount{value,currency}, capture=true, confirmation{type:redirect,return_url},
  description, metadata{payment_id}. Response has confirmation.confirmation_url.
- Webhooks are NOT signed. Genuineness is established two ways, both enforced here:
    1. source IP must be in YooKassa's published allowlist;
    2. we re-fetch the payment via GET /v3/payments/{id} and trust only its status.
"""
import ipaddress
import logging
import uuid
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.services.payments.base import InvoiceResult

logger = logging.getLogger(__name__)

# Published YooKassa notification source ranges (yookassa.ru/developers/using-api/webhooks).
_TRUSTED_NETWORKS = [
    ipaddress.ip_network(n)
    for n in (
        "185.71.76.0/27",
        "185.71.77.0/27",
        "77.75.153.0/25",
        "77.75.156.11/32",
        "77.75.156.35/32",
        "77.75.154.128/25",
        "2a02:5180::/32",
    )
]


class YooKassaError(Exception):
    pass


def is_trusted_ip(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _TRUSTED_NETWORKS)


class YooKassaProvider:
    name = "yookassa"

    def __init__(
        self,
        shop_id: str | None = None,
        secret_key: str | None = None,
        return_url: str | None = None,
    ):
        settings = get_settings()
        self._shop_id = shop_id if shop_id is not None else settings.yookassa_shop_id
        self._secret_key = secret_key if secret_key is not None else settings.yookassa_secret_key
        self._return_url = return_url or settings.yookassa_return_url
        self._base = "https://api.yookassa.ru/v3"

    def _auth(self) -> tuple[str, str]:
        return (self._shop_id, self._secret_key)

    async def create_invoice(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        internal_payment_id: int,
    ) -> InvoiceResult:
        body = {
            "amount": {"value": f"{Decimal(amount):.2f}", "currency": currency or "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": self._return_url},
            "description": description[:128],
            "metadata": {"payment_id": str(internal_payment_id)},
        }
        headers = {"Idempotence-Key": uuid.uuid4().hex}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self._base}/payments", json=body, headers=headers, auth=self._auth()
            )
        data = resp.json() if resp.content else {}
        if resp.status_code not in (200, 201) or "id" not in data:
            logger.error("yookassa createPayment failed: HTTP %s %s", resp.status_code, data)
            raise YooKassaError("failed to create YooKassa payment")
        url = (data.get("confirmation") or {}).get("confirmation_url")
        if not url:
            raise YooKassaError("YooKassa returned no confirmation_url")
        return InvoiceResult(
            provider_payment_id=f"yookassa:{data['id']}",
            invoice_url=url,
        )

    async def get_payment_status(self, yk_payment_id: str) -> str | None:
        """Authoritative status re-check used to validate an incoming webhook."""
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{self._base}/payments/{yk_payment_id}", auth=self._auth()
            )
        if resp.status_code != 200:
            logger.warning("yookassa getPayment %s -> HTTP %s", yk_payment_id, resp.status_code)
            return None
        return resp.json().get("status")

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:  # protocol shim
        """YooKassa has no body signature; genuineness is IP allowlist + GET re-check,
        both enforced in the router/handler. Never called for this provider."""
        return False
