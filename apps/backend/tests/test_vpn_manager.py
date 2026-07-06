"""3X-UI wrapper: exact panel API contract (paths, payloads, session handling)."""
import json

import httpx
import pytest
import respx

from app.services.vpn_manager.xui_client import XuiClient, XuiError

PANEL = "https://panel.test:2053/base"


def login_route(respx_mock, success: bool = True):
    return respx_mock.post(f"{PANEL}/login").mock(
        return_value=httpx.Response(
            200,
            json={"success": success, "msg": "" if success else "bad creds", "obj": None},
            headers={"set-cookie": "3x-ui=session-token; Path=/"} if success else {},
        )
    )


@respx.mock
async def test_login_stores_session_cookie(respx_mock):
    login_route(respx_mock)
    client = XuiClient(PANEL, "admin", "pass")
    await client.login()
    assert client._cookies is not None


@respx.mock
async def test_login_failure_raises(respx_mock):
    login_route(respx_mock, success=False)
    client = XuiClient(PANEL, "admin", "wrong")
    with pytest.raises(XuiError):
        await client.login()


@respx.mock
async def test_add_client_sends_panel_contract(respx_mock):
    login_route(respx_mock)
    add = respx_mock.post(f"{PANEL}/panel/api/inbounds/addClient").mock(
        return_value=httpx.Response(200, json={"success": True, "msg": "", "obj": None})
    )
    client = XuiClient(PANEL, "admin", "pass")
    await client.add_client(
        inbound_id=3,
        client_uuid="uuid-1",
        email="u1s1-xy",
        total_bytes=50 * 1024**3,
        expiry_time_ms=1_800_000_000_000,
    )
    assert add.called
    sent = json.loads(add.calls[0].request.content)
    assert sent["id"] == 3
    settings = json.loads(sent["settings"])
    c = settings["clients"][0]
    assert c["id"] == "uuid-1"
    assert c["email"] == "u1s1-xy"
    assert c["enable"] is True
    assert c["totalGB"] == 50 * 1024**3      # bytes, despite the field name
    assert c["expiryTime"] == 1_800_000_000_000  # unix ms
    assert c["flow"] == "xtls-rprx-vision"


@respx.mock
async def test_relogin_on_auth_failure(respx_mock):
    login_route(respx_mock)
    traffic = respx_mock.get(f"{PANEL}/panel/api/inbounds/getClientTraffics/u1").mock(
        side_effect=[
            httpx.Response(401),
            httpx.Response(
                200, json={"success": True, "msg": "", "obj": {"up": 10, "down": 20}}
            ),
        ]
    )
    client = XuiClient(PANEL, "admin", "pass")
    stats = await client.get_client_traffic("u1")
    assert stats == {"up": 10, "down": 20}
    assert traffic.call_count == 2  # first 401, then success after re-login


@respx.mock
async def test_panel_error_raises(respx_mock):
    login_route(respx_mock)
    respx_mock.post(f"{PANEL}/panel/api/inbounds/addClient").mock(
        return_value=httpx.Response(
            200, json={"success": False, "msg": "client exists", "obj": None}
        )
    )
    client = XuiClient(PANEL, "admin", "pass")
    with pytest.raises(XuiError, match="client exists"):
        await client.add_client(1, "uuid", "email")


def test_vless_link_format():
    from app.models import VpnAccess, VpnServer
    from app.services.vpn_manager.manager import build_vless_link

    server = VpnServer(
        name="DE-1", country="DE", panel_url="x", panel_user="x",
        panel_pass_encrypted="x", inbound_id=1, host="1.2.3.4", port=443,
        public_key="PBK", short_id="SID", sni="yahoo.com",
    )
    access = VpnAccess(
        user_id=1, subscription_id=1, server_id=1,
        external_user_id="e", uuid="UUID-1",
    )
    link = build_vless_link(access, server)
    assert link.startswith("vless://UUID-1@1.2.3.4:443?")
    assert "security=reality" in link
    assert "pbk=PBK" in link
    assert "sid=SID" in link
    assert "sni=yahoo.com" in link
    assert "flow=xtls-rprx-vision" in link
