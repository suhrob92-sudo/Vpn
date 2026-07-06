"""Async HTTP client for the 3X-UI panel API (MHSanaei/3x-ui, v2.x endpoints).

Endpoint paths are documented in the official Postman collection
(https://documenter.getpostman.com/view/16802678/2s9YkgD5jm) and verified against
client libraries. All panel responses share the shape {"success", "msg", "obj"}.

Every path lives in this module only — a panel running the newer v3 API
("panel/api/clients/*") requires changes here and nowhere else.
"""
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class XuiError(Exception):
    """Raised when the panel is unreachable or returns success=false."""


class XuiClient:
    def __init__(self, panel_url: str, username: str, password: str, timeout: float = 15.0):
        self._base = panel_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout
        self._cookies: httpx.Cookies | None = None

    # ── session ──────────────────────────────────────────────────────────

    async def login(self) -> None:
        """POST /login with username/password; the panel sets a session cookie
        (name varies by version: '3x-ui' or 'session') — we keep whatever we get."""
        async with self._client() as client:
            resp = await client.post(
                f"{self._base}/login",
                data={"username": self._username, "password": self._password},
            )
        body = self._parse(resp)
        if not body.get("success"):
            raise XuiError(f"panel login failed: {body.get('msg', 'unknown error')}")
        if not resp.cookies:
            raise XuiError("panel login returned no session cookie")
        self._cookies = resp.cookies
        logger.info("3x-ui login ok: %s", self._base)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            cookies=self._cookies,
            headers={"Accept": "application/json"},
            verify=True,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Request with one automatic re-login on auth failure/expired session."""
        if self._cookies is None:
            await self.login()
        for attempt in (1, 2):
            async with self._client() as client:
                resp = await client.request(method, f"{self._base}{path}", **kwargs)
            if resp.status_code in (401, 403) or self._looks_like_login_page(resp):
                if attempt == 1:
                    self._cookies = None
                    await self.login()
                    continue
                raise XuiError("panel authentication failed after re-login")
            body = self._parse(resp)
            if not body.get("success"):
                raise XuiError(f"panel error on {path}: {body.get('msg', resp.text[:200])}")
            return body.get("obj")
        raise XuiError("unreachable")  # pragma: no cover

    @staticmethod
    def _looks_like_login_page(resp: httpx.Response) -> bool:
        ctype = resp.headers.get("content-type", "")
        return resp.status_code == 200 and "text/html" in ctype

    @staticmethod
    def _parse(resp: httpx.Response) -> dict:
        try:
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise XuiError(f"panel HTTP {exc.response.status_code}") from exc
        except json.JSONDecodeError as exc:
            raise XuiError("panel returned non-JSON response") from exc

    # ── inbounds / clients ───────────────────────────────────────────────

    async def list_inbounds(self) -> list[dict]:
        return await self._request("GET", "/panel/api/inbounds/list") or []

    async def get_inbound(self, inbound_id: int) -> dict:
        return await self._request("GET", f"/panel/api/inbounds/get/{inbound_id}")

    async def add_client(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        *,
        total_bytes: int = 0,
        expiry_time_ms: int = 0,
        flow: str = "xtls-rprx-vision",
        limit_ip: int = 0,
        sub_id: str = "",
    ) -> None:
        """Add a client to an inbound.

        Panel contract: totalGB is a byte count despite the name; expiryTime is
        Unix epoch in milliseconds; 0 means unlimited for both.
        """
        settings = {
            "clients": [
                {
                    "id": client_uuid,
                    "email": email,
                    "enable": True,
                    "flow": flow,
                    "limitIp": limit_ip,
                    "totalGB": total_bytes,
                    "expiryTime": expiry_time_ms,
                    "tgId": "",
                    "subId": sub_id,
                }
            ]
        }
        await self._request(
            "POST",
            "/panel/api/inbounds/addClient",
            json={"id": inbound_id, "settings": json.dumps(settings)},
        )

    async def update_client(
        self,
        inbound_id: int,
        client_uuid: str,
        email: str,
        *,
        enable: bool,
        total_bytes: int = 0,
        expiry_time_ms: int = 0,
        flow: str = "xtls-rprx-vision",
        limit_ip: int = 0,
        sub_id: str = "",
    ) -> None:
        settings = {
            "clients": [
                {
                    "id": client_uuid,
                    "email": email,
                    "enable": enable,
                    "flow": flow,
                    "limitIp": limit_ip,
                    "totalGB": total_bytes,
                    "expiryTime": expiry_time_ms,
                    "tgId": "",
                    "subId": sub_id,
                }
            ]
        }
        await self._request(
            "POST",
            f"/panel/api/inbounds/updateClient/{client_uuid}",
            json={"id": inbound_id, "settings": json.dumps(settings)},
        )

    async def delete_client(self, inbound_id: int, client_uuid: str) -> None:
        await self._request(
            "POST", f"/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}"
        )

    async def get_client_traffic(self, email: str) -> dict | None:
        """Returns {'up': bytes, 'down': bytes, 'total': bytes, 'expiryTime': ms, ...} or None."""
        return await self._request(
            "GET", f"/panel/api/inbounds/getClientTraffics/{email}"
        )
