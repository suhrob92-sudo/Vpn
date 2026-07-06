# VPN Platform — System Architecture (MVP)

Production-grade paid VPN service delivered through a Telegram Bot + Telegram Mini App.
VPN servers are managed exclusively through the **3X-UI panel HTTP API** (MHSanaei/3x-ui);
payments through **CryptoBot (Crypto Pay API)** with Telegram Stars as the alternative provider.

---

## 1. System architecture

```
                ┌──────────────────────────────────────────────────────┐
                │                     Telegram                         │
                │   Bot (aiogram 3, long polling)   Mini App (WebApp)  │
                └───────────────┬──────────────────────┬───────────────┘
                                │                      │ initData (HMAC-validated)
                                ▼                      ▼
┌──────────┐  JWT   ┌─────────────────────────────────────────────────┐
│  Admin   │───────▶│                 Backend API (FastAPI)           │
│  Panel   │        │                                                 │
└──────────┘        │  ┌───────────────┐  ┌──────────────────────┐    │
                    │  │ Payment Svc   │  │ VPN Management Svc   │    │
                    │  │ (provider-    │  │ (3X-UI API wrapper)  │────┼──▶ 3X-UI panels
                    │  │  agnostic)    │  └──────────────────────┘    │    on VPN servers
                    │  │  • CryptoBot  │  ┌──────────────────────┐    │    (VLESS+Reality)
                    │  │  • Stars      │  │ Subscription Svc     │    │
                    │  └───────────────┘  │ (universal URL/QR)   │    │
                    │                     └──────────────────────┘    │
                    └───────┬─────────────────────────┬───────────────┘
                            ▼                         ▼
                      PostgreSQL                 Redis ◀── ARQ worker
                                                          (expiry cron, notifications)
```

Key decisions (fixed, per master prompt §0):

| Decision | Choice | Rationale |
|---|---|---|
| VPN control plane | 3X-UI panel HTTP API only | Panel already solves client CRUD, traffic accounting, inbound management. No raw Xray config editing. |
| Subscription delivery | Standard base64 subscription URL | Readable by Happ, v2rayNG, sing-box, Streisand. Happ is one option, not a dependency. |
| Payments | CryptoBot (USDT/TON) primary, Telegram Stars secondary | Provider-agnostic `PaymentProvider` interface; adding a provider = one adapter. |
| Device limit | Informational only in MVP | Strict device enforcement needs IP tracking; `device_hint` is shown as a recommendation (e.g. "up to 3 devices"), never promised as enforcement. |
| Services layout | `apps/backend/app/services/*` packages | Single deployable API for MVP; each service is an isolated package with its own interface so it can be split into a separate process later without rewrites. |

## 2. Final technology stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic v2
- **DB / cache**: PostgreSQL 16, Redis 7
- **Background tasks**: ARQ (Redis-native)
- **Bot**: aiogram 3.x (long polling in MVP)
- **Mini App**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Telegram WebApp JS API
- **Admin panel**: Next.js 14, JWT auth against `/admin/*` API
- **VPN infra**: 3X-UI panel per VPN server, Xray backend, VLESS + Reality inbound
- **Payments**: Crypto Pay API (@CryptoBot), Telegram Stars (aiogram `send_invoice`, XTR)
- **Deploy**: Ubuntu, Docker Compose, Caddy (auto TLS), GitHub Actions

## 3. 3X-UI API compatibility (verified endpoint list)

Verified against the MHSanaei/3x-ui **v2.x API** (the officially documented Postman
collection and client libraries). All endpoints return `{"success": bool, "msg": str, "obj": ...}`.
Paths are centralized in `app/services/vpn_manager/xui_client.py` — if a panel runs the
new v3 API (`panel/api/clients/*`), only that module changes.

| Purpose | Method + path |
|---|---|
| Login (form/JSON `username`, `password`) → session cookie | `POST {panel}/login` |
| List inbounds | `GET {panel}/panel/api/inbounds/list` |
| Get inbound | `GET {panel}/panel/api/inbounds/get/{inboundId}` |
| Add client | `POST {panel}/panel/api/inbounds/addClient` |
| Update client (enable/expiry/limit) | `POST {panel}/panel/api/inbounds/updateClient/{clientUuid}` |
| Delete client | `POST {panel}/panel/api/inbounds/{inboundId}/delClient/{clientUuid}` |
| Client traffic by email | `GET {panel}/panel/api/inbounds/getClientTraffics/{email}` |
| Online clients | `POST {panel}/panel/api/inbounds/onlines` |

`addClient` body: `{"id": <inboundId>, "settings": "<json string>"}` where settings is
`{"clients": [{"id": "<uuid>", "email": "<internal id>", "enable": true, "flow": "xtls-rprx-vision", "limitIp": 0, "totalGB": <bytes>, "expiryTime": <ms epoch>, "subId": "<random>", "tgId": ""}]}`.
Note: `totalGB` is despite the name a value in **bytes**; `expiryTime` is Unix **milliseconds**; `0` = unlimited.

Session cookie name varies by panel version (`3x-ui` / `session`) — the wrapper stores
whatever cookie the login response sets and re-logins automatically on auth failure.

Deployment checklist per server (see `docs/3XUI-SETUP.md`): panel reachable over HTTPS,
one VLESS+Reality inbound created, its `inboundId`, Reality `publicKey` and `shortId`
recorded in the admin panel when registering the server.

## 4. CryptoBot (Crypto Pay API) compatibility

- Base URL: `https://pay.crypt.bot/api` (testnet: `https://testpay.crypt.bot/api`)
- Auth: header `Crypto-Pay-API-Token: <token>` (token from @CryptoBot → Crypto Pay → Create App)
- Create invoice: `POST /createInvoice` — `asset` (e.g. `USDT`), `amount` (string),
  `description`, `payload` (we pass our internal payment id), `expires_in` (seconds).
  Response contains `invoice_id`, `status`, `bot_invoice_url`, `mini_app_invoice_url`.
- Webhook: CryptoBot POSTs `{"update_id", "update_type": "invoice_paid", "request_date", "payload": <Invoice>}`
  to our endpoint. **Verification (mandatory)**: header `crypto-pay-api-signature` must equal
  HMAC-SHA256 of the **raw request body**, key = `SHA256(api_token)`. Additionally the webhook
  path contains a secret segment (`/payments/webhook/cryptobot/{secret}`).
- **Idempotency**: `payments.provider_payment_id` is UNIQUE (`cryptobot:<invoice_id>`);
  a webhook retry finds the payment already `SUCCESS` and returns 200 without side effects.
- Flow: user picks plan → backend creates `Payment(PENDING)` + CryptoBot invoice →
  Mini App opens `mini_app_invoice_url` → user pays → webhook verified → payment `SUCCESS` →
  subscription created/extended → VPN access provisioned via 3X-UI → user notified by bot.
  The frontend "success" page is cosmetic only; provisioning happens strictly on webhook.

**Telegram Stars (alternative)**: bot sends `sendInvoice` with currency `XTR`; Telegram
delivers `successful_payment` in the bot update — that update itself is Telegram-authenticated,
`telegram_payment_charge_id` is used as `provider_payment_id` for the same idempotent activation path.

## 5. Universal subscription format

`GET /sub/{token}` returns `text/plain`: **base64 of a newline-separated list of `vless://` URIs**
(one per allowed server) — the de-facto standard subscription format consumed by
**v2rayNG, Happ, Streisand, NekoBox, sing-box (via import)**.

Response headers (supported by Happ/v2rayNG, ignored by others):
- `profile-title: base64:<name>` — display name
- `subscription-userinfo: upload=..; download=..; total=..; expire=..` — usage/expiry meta
- `profile-update-interval: 12`

VLESS link template (Reality):
`vless://{uuid}@{host}:{port}?type=tcp&security=reality&pbk={publicKey}&fid={shortId}&sni={sni}&flow=xtls-rprx-vision&fp=chrome#{name}`

Connect screen options (in priority order):
1. **Copy URL** — universal, always works
2. **QR code** — scan from any client
3. Deep links: **v2rayNG** `v2rayng://install-sub?url={url}&name={name}` (verified, 2dust/v2rayNG),
   **Happ** `happ://add/{subscriptionUrl}` (per happ.su developer docs)

Security: token is 32 bytes of `secrets.token_urlsafe`; DB stores only its SHA-256 hash;
no Telegram ID anywhere in the URL; expired/suspended subscription → 404 with empty body.

## 6. Database ER diagram

```
users 1──∞ subscriptions ∞──1 plans
users 1──∞ payments      ∞──1 plans
users 1──∞ vpn_access    ∞──1 vpn_servers
subscriptions 1──∞ vpn_access
users 1──∞ subscription_tokens
users 1──∞ referral_events (as inviter / as invited)
admin_users (standalone)

users(id PK, telegram_id UQ, username, first_name, last_name, language_code,
      referral_code UQ, referred_by FK→users, status, created_at, updated_at)
plans(id PK, name, description, price NUMERIC, currency, duration_days,
      traffic_limit_gb, device_hint, is_active, sort_order, created_at, updated_at)
subscriptions(id PK, user_id FK, plan_id FK, status, started_at, expires_at,
      created_at, updated_at)
payments(id PK, user_id FK, plan_id FK, provider, provider_payment_id UQ ← idempotency,
      amount, currency, status, invoice_url, created_at, paid_at)
vpn_servers(id PK, name, country, city, panel_url, panel_user, panel_pass_encrypted,
      inbound_id, public_key, short_id, sni, host, port, status, created_at, updated_at)
vpn_access(id PK, user_id FK, subscription_id FK, server_id FK,
      external_user_id ← 3X-UI client email/id, uuid, status, created_at, revoked_at)
subscription_tokens(id PK, user_id FK, token_hash UQ, status, created_at, last_accessed_at)
admin_users(id PK, username UQ, password_hash, role, status, created_at)
referral_events(id PK, inviter_id FK, invited_user_id FK, status, created_at)
```

`panel_pass_encrypted` is Fernet-encrypted with `ENCRYPTION_KEY` from env — never plaintext.

## 7. Module architecture

- **Backend** (`apps/backend`): FastAPI, layered — `api/` (routers) → `services/` (business logic)
  → `models/` + `repositories-lite` (SQLAlchemy). Standard response envelope, structured logging
  with secret redaction, Redis rate limiting on auth/payment/sub endpoints.
- **Auth**: `POST /auth/telegram` validates raw `initData` server-side
  (HMAC-SHA256, secret = HMAC("WebAppData", bot_token), `auth_date` freshness ≤ 1h),
  upserts the user, returns a short-lived user JWT. Admin: username+password (argon2) →
  access JWT (15 min) + refresh JWT (7 d) with rotation (jti tracked in Redis, reuse = revoke).
- **VPN Management Service** (`services/vpn_manager`): `create_access`, `revoke_access`,
  `renew_access`, `get_traffic`, `get_config` on top of an async 3X-UI client with
  cookie session cache + automatic re-login. Multi-server: one client per server,
  subscription endpoint merges all configs.
- **Payment Service** (`services/payments`): `PaymentProvider` protocol
  (`create_invoice`, `verify_webhook`, `parse_webhook`) + `CryptoBotProvider`;
  activation logic (`activate_payment`) is provider-independent and idempotent.
- **Bot** (`apps/bot`): aiogram 3 routers; `/start` upserts user + stores referral param
  (`referral_events` tracking only in MVP), WebApp menu button; worker sends expiry
  notifications through the bot token via plain Bot API calls.
- **Worker** (`apps/backend/app/worker.py`): ARQ cron — hourly expiry sweep
  (expired → revoke 3X-UI clients → status EXPIRED → Telegram notification), critical
  errors reported to `ADMIN_CHAT_ID`.

## 8. Repository tree

```
Vpn/
  apps/
    backend/            # FastAPI + services + ARQ worker + Alembic + tests
      app/
        api/            # routers: auth, users, plans, payments, servers, sub, admin
        core/           # settings, security, logging, rate limit, crypto
        models/         # SQLAlchemy models
        schemas/        # Pydantic v2 schemas
        services/
          vpn_manager/  # 3X-UI wrapper
          payments/     # provider-agnostic + CryptoBot adapter
          subscription/ # tokens + universal subscription builder
        worker.py       # ARQ tasks
      alembic/
      tests/
    bot/                # aiogram 3
    miniapp/            # Next.js Mini App
    admin/              # Next.js admin panel
  infra/
    caddy/Caddyfile
    docker/             # Dockerfiles
  scripts/              # backup.sh, restore.sh
  docs/                 # ARCHITECTURE.md, 3XUI-SETUP.md
  .github/workflows/ci.yml
  docker-compose.yml
  docker-compose.prod.yml
  .env.example
  README.md
```

## 9. MVP roadmap (matches master prompt §0.4)

1. **Telegram auth** — initData server-side validation, user upsert, user JWT ✅ stage 1
2. **Plans** — model + public listing + admin CRUD ✅ stage 1
3. **Payment** — CryptoBot invoice + signed webhook + idempotent activation ✅ stage 2
4. **VPN provisioning** — 3X-UI wrapper, client per server ✅ stage 2
5. **Universal subscription** — `/sub/{token}` + Mini App Connect screen (URL/QR/deep links) ✅ stage 3
6. **Expiry automation** — ARQ hourly sweep, revoke + notify ✅ stage 3
7. **Minimal admin panel** — dashboard, users, payments, plans, servers ✅ stage 4

Out of MVP scope (deliberately): referral rewards (only tracking table exists), support
tickets, admin 2FA, audit logs, full monitoring dashboard, onboarding animations.
