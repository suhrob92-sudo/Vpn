"""HMAC-signed client for the backend internal API."""
import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from bot.config import get_settings

logger = logging.getLogger(__name__)


class BackendError(Exception):
    pass


async def _post(path: str, payload: dict) -> Any:
    settings = get_settings()
    raw = json.dumps(payload).encode()
    signature = hmac.new(settings.jwt_secret.encode(), raw, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.internal_api_url}{path}",
            content=raw,
            headers={
                "content-type": "application/json",
                "x-internal-signature": signature,
            },
        )
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        logger.error("backend %s -> HTTP %s: %s", path, resp.status_code, resp.text[:300])
        raise BackendError(f"backend returned {resp.status_code}")
    body = resp.json()
    if not body.get("success"):
        raise BackendError(str(body.get("error")))
    return body.get("data")


async def upsert_user(telegram_user: dict, start_param: str | None) -> dict:
    return await _post(
        "/internal/bot/users",
        {"telegram_user": telegram_user, "start_param": start_param},
    )


async def get_profile(telegram_id: int) -> dict | None:
    return await _post("/internal/bot/profile", {"telegram_id": telegram_id})


async def get_plans() -> list[dict]:
    return await _post("/internal/bot/plans", {}) or []


async def report_stars_payment(
    telegram_id: int, plan_id: int, charge_id: str, amount: int
) -> None:
    settings = get_settings()
    payload = {
        "telegram_id": telegram_id,
        "plan_id": plan_id,
        "charge_id": charge_id,
        "amount": amount,
    }
    raw = json.dumps(payload).encode()
    signature = hmac.new(settings.jwt_secret.encode(), raw, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{settings.internal_api_url}/payments/webhook/stars",
            content=raw,
            headers={
                "content-type": "application/json",
                "x-internal-signature": signature,
            },
        )
    if resp.status_code != 200:
        raise BackendError(f"stars report failed: HTTP {resp.status_code}")


async def get_servers() -> list[dict]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{settings.internal_api_url}/servers")
    if resp.status_code != 200:
        raise BackendError(f"servers failed: HTTP {resp.status_code}")
    return resp.json().get("data") or []
