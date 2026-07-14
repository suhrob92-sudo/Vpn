"""Telegram initData validation — the front door of the platform."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

BOT_TOKEN = "12345:TEST-BOT-TOKEN-abcdefghijklmnopqrstuvwx"


def make_init_data(user_id: int = 777, auth_age: int = 0, tamper: bool = False) -> str:
    user = {"id": user_id, "first_name": "Test", "username": "tester", "language_code": "uz"}
    pairs = {
        "auth_date": str(int(time.time()) - auth_age),
        "query_id": "AAF-test",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if tamper:
        signature = "0" * 64
    return urlencode({**pairs, "hash": signature})


async def test_valid_init_data_creates_user(client):
    resp = await client.post("/auth/telegram", json={"init_data": make_init_data()})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["access_token"]
    assert body["data"]["user"]["telegram_id"] == 777

    # JWT works against a protected endpoint
    token = body["data"]["access_token"]
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["telegram_id"] == 777


async def test_tampered_hash_rejected(client):
    resp = await client.post("/auth/telegram", json={"init_data": make_init_data(tamper=True)})
    assert resp.status_code == 401


async def test_stale_init_data_rejected(client):
    resp = await client.post(
        "/auth/telegram", json={"init_data": make_init_data(auth_age=7200)}
    )
    assert resp.status_code == 401


async def test_repeat_auth_updates_not_duplicates(client):
    for _ in range(2):
        resp = await client.post("/auth/telegram", json={"init_data": make_init_data()})
        assert resp.status_code == 200
    from sqlalchemy import func, select

    from app.core.db import get_session_factory
    from app.models import User

    async with get_session_factory()() as db:
        count = await db.scalar(select(func.count(User.id)))
    assert count == 1
