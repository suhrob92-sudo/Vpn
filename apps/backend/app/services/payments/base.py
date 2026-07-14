"""Provider-agnostic payment interfaces.

Adding a new provider = implement PaymentProvider + register it in
`service.get_provider`. Nothing else changes.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass
class InvoiceResult:
    provider_payment_id: str  # globally unique, prefixed with provider name
    invoice_url: str


class PaymentProvider(Protocol):
    name: str

    async def create_invoice(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        internal_payment_id: int,
    ) -> InvoiceResult:
        """Create an invoice at the provider; returns its id and payment URL."""
        ...

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Cryptographically verify that a webhook came from the provider."""
        ...
