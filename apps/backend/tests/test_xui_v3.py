"""XuiClient version auto-detection: v2 form login vs v3 CSRF login + new endpoints."""
import json

import httpx
import pytest
import respx

from app.services.vpn_manager.xui_client import XuiClient

BASE = "https://panel.test:2053/secret"


def _ok(obj=None, **extra):
    return httpx.Response(200, json={"success": True, "msg": "", "obj": obj, **extra})


@respx.mock
async def test_v2_login_and_add_client():
    respx.post(f"{BASE}/login").mock(
        return_value=httpx.Response(
            200, json={"success": True}, headers={"set-cookie": "session=abc; Path=/"}
        )
    )
    add_route = respx.post(f"{BASE}/panel/api/inbounds/addClient").mock(return_value=_ok())

    client = XuiClient(BASE, "admin", "pw")
    await client.add_client(3, "uuid-1", "u1s1", total_bytes=5 * 1024**3, expiry_time_ms=123)

    assert add_route.called
    sent = json.loads(add_route.calls[0].request.content)
    assert sent["id"] == 3
    inner = json.loads(sent["settings"])["clients"][0]
    assert inner["id"] == "uuid-1"
    assert inner["totalGB"] == 5 * 1024**3  # v2: bytes


@respx.mock
async def test_v3_csrf_login_and_add_client():
    # Bare form login is rejected by the v3 CSRF middleware.
    login_route = respx.post(f"{BASE}/login")
    login_route.side_effect = [
        httpx.Response(403),
        httpx.Response(
            200, json={"success": True}, headers={"set-cookie": "3x-ui=s1; Path=/"}
        ),
    ]
    respx.get(f"{BASE}/csrf-token").mock(
        return_value=httpx.Response(
            200,
            json={"success": True, "obj": "csrf-tok"},
            headers={"set-cookie": "3x-ui=s0; Path=/"},
        )
    )
    add_route = respx.post(f"{BASE}/panel/api/clients/add").mock(return_value=_ok())

    client = XuiClient(BASE, "admin", "pw")
    await client.add_client(1, "uuid-9", "u9s1", total_bytes=5 * 1024**3, expiry_time_ms=42)

    # Second login call was JSON with the CSRF header.
    json_login = login_route.calls[1].request
    assert json_login.headers["x-csrf-token"] == "csrf-tok"
    assert json.loads(json_login.content) == {"username": "admin", "password": "pw"}

    sent = json.loads(add_route.calls[0].request.content)
    assert sent["inboundIds"] == [1]
    assert sent["client"]["id"] == "uuid-9"
    assert sent["client"]["totalGB"] == 5  # v3: gigabytes
    assert sent["client"]["expiryTime"] == 42
    # Unsafe API calls replay the CSRF token too.
    assert add_route.calls[0].request.headers["x-csrf-token"] == "csrf-tok"


@respx.mock
async def test_v3_update_client_uses_email_path():
    respx.post(f"{BASE}/login").mock(return_value=httpx.Response(403))
    respx.get(f"{BASE}/csrf-token").mock(
        return_value=httpx.Response(
            200,
            json={"success": True, "obj": "t"},
            headers={"set-cookie": "3x-ui=s; Path=/"},
        )
    )
    # JSON login (second POST /login call) — same route, override after first 403:
    respx.post(f"{BASE}/login").side_effect = [
        httpx.Response(403),
        httpx.Response(200, json={"success": True}, headers={"set-cookie": "3x-ui=s2; Path=/"}),
    ]
    upd = respx.post(f"{BASE}/panel/api/clients/update/u1s1").mock(return_value=_ok())

    client = XuiClient(BASE, "admin", "pw")
    await client.update_client(7, "uuid-1", "u1s1", enable=False, expiry_time_ms=99)

    assert upd.called
    req = upd.calls[0].request
    assert "inboundIds=7" in str(req.url)
    body = json.loads(req.content)
    assert body["enable"] is False and body["id"] == "uuid-1"


@respx.mock
async def test_v2_wrong_password_raises():
    respx.post(f"{BASE}/login").mock(
        return_value=httpx.Response(200, json={"success": False, "msg": "bad creds"})
    )
    client = XuiClient(BASE, "admin", "wrong")
    with pytest.raises(Exception, match="bad creds"):
        await client.login()
