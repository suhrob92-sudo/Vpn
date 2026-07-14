# VPN Platform

Paid VPN service platform delivered through a **Telegram Bot + Mini App**.
Users buy a plan (CryptoBot USDT/TON or Telegram Stars), the platform provisions a
VLESS+Reality client on every VPN server via the **3X-UI panel API**, and the user
connects any client (Happ, v2rayNG, sing-box, Streisand) through a universal
subscription URL / QR code.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full architecture and
[`docs/3XUI-SETUP.md`](docs/3XUI-SETUP.md) for VPN server onboarding.

## Components

| Path | What |
|---|---|
| `apps/backend` | FastAPI API + services (payments, VPN manager, subscription) + ARQ worker + Alembic |
| `apps/bot` | aiogram 3 Telegram bot |
| `apps/miniapp` | Next.js Telegram Mini App |
| `apps/admin` | Next.js admin panel |
| `infra/` | Caddy config, Dockerfiles |
| `scripts/` | DB backup / restore |

## Requirements

- Docker + Docker Compose
- A Telegram bot (@BotFather) with a configured Mini App (menu button → your domain `/app`)
- A Crypto Pay app token (@CryptoBot → Crypto Pay → Create App), webhook enabled
- One or more VPN servers with 3X-UI installed (`docs/3XUI-SETUP.md`)

## Quick start (development)

```bash
cp .env.example .env         # fill in BOT_TOKEN, JWT_SECRET, ENCRYPTION_KEY, passwords
docker compose up --build
```

Services: API `http://localhost:8000` (docs at `/docs`), Mini App `http://localhost:3000`,
admin `http://localhost:3001`, Postgres `5432`, Redis `6379`.

Database migrations run automatically on backend start (`alembic upgrade head`).
The first admin user is bootstrapped from `ADMIN_BOOTSTRAP_USERNAME/PASSWORD`.

### Running backend tests

```bash
cd apps/backend
pip install -e ".[dev]"
pytest
```

## Production deploy

```bash
cp .env.example .env         # production values, ENVIRONMENT=production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy terminates TLS for `DOMAIN` automatically and routes:

- `/api/*` → backend
- `/sub/*` → backend (subscription endpoint)
- `/app*` → Mini App
- `/admin*` → admin panel

Set the CryptoBot webhook URL to
`https://DOMAIN/api/payments/webhook/cryptobot/<CRYPTOBOT_WEBHOOK_SECRET>`.

## Environment variables

All secrets live in `.env` (never in code). See [`.env.example`](.env.example) —
every variable is documented inline. Highlights:

- `BOT_TOKEN` — bot token; also used to validate Mini App `initData` (HMAC-SHA256)
- `CRYPTOBOT_API_TOKEN` — Crypto Pay token; webhook signatures are HMAC-SHA256 with key `SHA256(token)`
- `ENCRYPTION_KEY` — Fernet key encrypting 3X-UI panel passwords in the DB
- `JWT_SECRET` — admin/user JWT signing

## Backup / restore

```bash
./scripts/backup.sh          # pg_dump → ./backups/vpn_YYYY-mm-dd_HHMM.sql.gz (keeps 30 days)
./scripts/restore.sh backups/vpn_2026-07-06_0300.sql.gz
```

Schedule `backup.sh` in cron on the host and sync `./backups` to object storage
(rclone/S3) — backups must leave the machine.

## Security model (MVP)

- Telegram `initData` validated server-side; users get short-lived JWTs
- Admin JWT access+refresh with rotation; argon2 password hashes
- Payment webhooks: HMAC signature check + secret URL segment + idempotency
  (`provider_payment_id` unique)
- Subscription tokens: crypto-random, stored hashed, no Telegram ID in URLs
- 3X-UI panel passwords encrypted (Fernet) in DB; secrets redacted from logs
- Rate limiting (Redis) on auth, payment and subscription endpoints

## Troubleshooting

- **Webhook 401**: signature mismatch — check `CRYPTOBOT_API_TOKEN` matches the app that
  created the invoice, and that the webhook URL contains the current secret segment.
- **Provisioning failed** (payment SUCCESS, no VPN access): check server rows in admin →
  Servers → Check; the ARQ worker retries provisioning and alerts `ADMIN_CHAT_ID`.
- **Mini App auth fails**: domain must be registered with @BotFather; `initData` older
  than 1 hour is rejected — reopen the Mini App.
