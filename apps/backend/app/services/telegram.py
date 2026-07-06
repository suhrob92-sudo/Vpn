"""Minimal Bot API sender used by the backend/worker (no aiogram dependency)."""
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_message(chat_id: int, text: str) -> bool:
    token = get_settings().bot_token
    if not token or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
        return bool(resp.json().get("ok"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram send failed to %s: %s", chat_id, exc)
        return False


async def notify_admin(text: str) -> None:
    await send_message(get_settings().admin_chat_id, f"⚠️ <b>VPN Platform</b>\n{text}")
