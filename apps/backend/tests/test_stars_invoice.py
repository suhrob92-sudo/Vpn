"""Mini App Stars invoice-link endpoint: builds a Bot API createInvoiceLink."""
import httpx
import respx

from app.core.db import get_session_factory
from app.core.security import create_token
from app.models import Plan, User

BOT_TOKEN = "12345:TEST-BOT-TOKEN-abcdefghijklmnopqrstuvwx"
LINK_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"


async def seed_user_and_plans() -> str:
    async with get_session_factory()() as db:
        user = User(telegram_id=707, referral_code="ref707")
        stars_plan = Plan(
            name="1 oylik", price=149, currency="RUB", price_stars=100, duration_days=30
        )
        no_stars_plan = Plan(
            name="Karta only", price=99, currency="RUB", price_stars=0, duration_days=15
        )
        db.add_all([user, stars_plan, no_stars_plan])
        await db.flush()
        token = create_token(str(user.id), "user", 3600)
        await db.commit()
        return token


@respx.mock
async def test_stars_invoice_link_returned(client, respx_mock):
    token = await seed_user_and_plans()
    route = respx_mock.post(LINK_URL).mock(
        return_value=httpx.Response(200, json={"ok": True, "result": "https://t.me/invoice/abc"})
    )
    resp = await client.post(
        "/payments/stars/create",
        json={"plan_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["invoice_link"] == "https://t.me/invoice/abc"
    # Bot API called with XTR currency and the plan's Stars amount
    sent = route.calls[0].request
    import json as _json

    body = _json.loads(sent.content)
    assert body["currency"] == "XTR"
    assert body["prices"][0]["amount"] == 100
    assert body["payload"] == "plan:1"


async def test_stars_rejected_when_plan_has_no_stars_price(client):
    token = await seed_user_and_plans()
    resp = await client.post(
        "/payments/stars/create",
        json={"plan_id": 2},  # price_stars = 0
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
