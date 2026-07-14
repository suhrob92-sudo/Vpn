"""Async HTTP client for the 3X-UI panel API (MHSanaei/3x-ui).

Supports both panel generations transparently:

* **v2.x** — form-encoded ``POST /login`` (no CSRF), client operations under
  ``/panel/api/inbounds/*`` (addClient/updateClient/getClientTraffics), and
  ``totalGB`` measured in **bytes** despite the name.
* **v3.x** — the rewritten panel protects every unsafe request with a CSRF
  token: ``GET /csrf-token`` mints a session token which must be replayed in
  the ``X-CSRF-Token`` header (a bare POST /login returns HTTP 403 — that is
  how v3 is detected). Client operations moved to ``/panel/api/clients/*``
  and ``totalGB`` is measured in **gigabytes**.

Every path lives in this module only; the rest of the platform talks to the
manager, never to the panel directly. Panel responses share the shape
{"success", "msg", "obj"} in both generations.
"""
import json
import logging
import math
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GB = 1024**3

CSRF_HEADER = "X-CSRF-Token"


class XuiError(Exception):
    """Raised when the panel is unreachable or returns success=false."""


class XuiClient:
    def __init__(self, panel_url: str, username: str, password: str, timeout: float = 15.0):
        self._base = panel_url.rstrip("/")
        self._username = username
        self._password = password
        self._timeout = timeout
        self._cookies: httpx.Cookies | None = None
        self._csrf: str | None = None
        self._v3: bool | None = None  # None = version not detected yet

    # ── session ──────────────────────────────────────────────────────────

    async def login(self) -> None:
        """Authenticate against the panel, auto-detecting the API generation.

        v2 accepts a plain form POST; v3 rejects it with HTTP 403 (CSRF), in
        which case we fetch a CSRF token and retry the login the v3 way.
        """
        async with self._client() as client:
            resp = await client.post(
                f"{self._base}/login",
                data={"username": self._username, "password": self._password},
            )
            if resp.status_code == 403:
                await self._login_v3(client)
                return
            body = self._parse(resp)
            if not body.get("success"):
                raise XuiError(f"panel login failed: {body.get('msg', 'unknown error')}")
            if not client.cookies:
                raise XuiError("panel login returned no session cookie")
            self._cookies = httpx.Cookies(client.cookies)
            self._csrf = None
            self._v3 = False
            logger.info("3x-ui v2 login ok: %s", self._base)

    async def _login_v3(self, client: httpx.AsyncClient) -> None:
        """v3 login: GET /csrf-token (sets the session cookie + returns the
        token), then POST /login as JSON with the X-CSRF-Token header."""
        tok_resp = await client.get(f"{self._base}/csrf-token")
        tok_body = self._parse(tok_resp)
        token = tok_body.get("obj") or ""
        if not tok_body.get("success") or not token:
            raise XuiError("panel csrf-token request failed")

        resp = await client.post(
            f"{self._base}/login",
            json={"username": self._username, "password": self._password},
            headers={CSRF_HEADER: token},
        )
        body = self._parse(resp)
        if not body.get("success"):
            raise XuiError(f"panel login failed: {body.get('msg', 'unknown error')}")
        if not client.cookies:
            raise XuiError("panel login returned no session cookie")
        self._cookies = httpx.Cookies(client.cookies)
        self._csrf = token
        self._v3 = True
        logger.info("3x-ui v3 login ok: %s", self._base)

    def _client(self) -> httpx.AsyncClient:
        headers = {"Accept": "application/json"}
        if self._csrf:
            headers[CSRF_HEADER] = self._csrf
        return httpx.AsyncClient(
            timeout=self._timeout,
            cookies=self._cookies,
            headers=headers,
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
                    self._csrf = None
                    await self.login()
                    continue
                raise XuiError("panel authentication failed after re-login")
            body = self._parse(resp)
            if not body.get("success"):
                raise XuiError(f"panel error on {path}: {body.get('msg', resp.text[:200])}")
            return body.get("obj")
        raise XuiError("unreachable")  # pragma: no cover

    async def _ensure_version(self) -> bool:
        if self._v3 is None:
            await self.login()
        return bool(self._v3)

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

    @staticmethod
    def _client_obj(
        client_uuid: str,
        email: str,
        *,
        enable: bool,
        total_bytes: int,
        expiry_time_ms: int,
        flow: str,
        limit_ip: int,
        sub_id: str,
        v3: bool,
    ) -> dict:
        """Panel client object. v2 wants totalGB in bytes, v3 in gigabytes."""
        total = math.ceil(total_bytes / GB) if (v3 and total_bytes) else total_bytes
        obj = {
            "id": client_uuid,
            "email": email,
            "enable": enable,
            "flow": flow,
            "limitIp": limit_ip,
            "totalGB": total,
            "expiryTime": expiry_time_ms,
            "subId": sub_id,
        }
        if v3:
            obj.update({"tgId": 0, "comment": "", "reset": 0, "security": ""})
        else:
            obj["tgId"] = ""
        return obj

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

        Panel contract: expiryTime is Unix epoch in milliseconds; 0 means
        unlimited for both traffic and expiry.
        """
        v3 = await self._ensure_version()
        client = self._client_obj(
            client_uuid, email, enable=True, total_bytes=total_bytes,
            expiry_time_ms=expiry_time_ms, flow=flow, limit_ip=limit_ip,
            sub_id=sub_id, v3=v3,
        )
        if v3:
            await self._request(
                "POST",
                "/panel/api/clients/add",
                json={"client": client, "inboundIds": [inbound_id]},
            )
        else:
            await self._request(
                "POST",
                "/panel/api/inbounds/addClient",
                json={"id": inbound_id, "settings": json.dumps({"clients": [client]})},
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
        v3 = await self._ensure_version()
        client = self._client_obj(
            client_uuid, email, enable=enable, total_bytes=total_bytes,
            expiry_time_ms=expiry_time_ms, flow=flow, limit_ip=limit_ip,
            sub_id=sub_id, v3=v3,
        )
        if v3:
            await self._request(
                "POST",
                f"/panel/api/clients/update/{email}",
                params={"inboundIds": str(inbound_id)},
                json=client,
            )
        else:
            await self._request(
                "POST",
                f"/panel/api/inbounds/updateClient/{client_uuid}",
                json={"id": inbound_id, "settings": json.dumps({"clients": [client]})},
            )

    async def delete_client(self, inbound_id: int, client_uuid: str, email: str = "") -> None:
        if await self._ensure_version():
            await self._request("POST", f"/panel/api/clients/del/{email or client_uuid}")
        else:
            await self._request(
                "POST", f"/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}"
            )

    async def get_client_traffic(self, email: str) -> dict | None:
        """Returns {'up': bytes, 'down': bytes, 'total': bytes, 'expiryTime': ms, ...} or None."""
        if await self._ensure_version():
            return await self._request("GET", f"/panel/api/clients/traffic/{email}")
        return await self._request(
            "GET", f"/panel/api/inbounds/getClientTraffics/{email}"
        )
