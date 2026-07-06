# 3X-UI VPN Server Setup Guide

Step-by-step guide for preparing a VPN server and registering it in the platform.
Repeat for every location (Germany, Netherlands, Finland, ...).

## 1. Provision the server

- Ubuntu 22.04+ VPS, 1+ vCPU, 1+ GB RAM, public IPv4.
- Open ports: `443` (VLESS Reality), panel port (keep non-standard, e.g. `2053`), `22`.

```bash
apt update && apt upgrade -y
```

## 2. Install 3X-UI (MHSanaei)

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

During install, set:
- a **strong random** panel username and password (they go into the platform admin panel later),
- a random **web base path** (e.g. `/Xk3jP9qL/`) — the panel URL becomes
  `https://SERVER:2053/Xk3jP9qL`,
- panel port (e.g. `2053`).

Enable HTTPS for the panel itself (panel settings → SSL certificate, or put it behind a
domain + certbot). The platform refuses plain-HTTP panel URLs in production.

## 3. Create the VLESS + Reality inbound

Panel → **Inbounds → Add Inbound**:

| Field | Value |
|---|---|
| Remark | `main` (any) |
| Protocol | `vless` |
| Listen port | `443` |
| Security | `reality` |
| SNI / Dest | a popular TLS host, e.g. `yahoo.com:443`, SNI `yahoo.com` |
| Flow (clients) | `xtls-rprx-vision` |

Press **Get New Cert** (Reality key pair) — the panel generates `privateKey`/`publicKey`
and a `shortId`. Save:

- **Inbound ID** — shown in the inbound list (usually `1` for the first one)
- **Public key** (`pbk`)
- **Short ID** (`sid`)
- **SNI** (e.g. `yahoo.com`)

Delete any default test clients from the inbound — the platform manages clients itself.

## 4. Register the server in the platform admin panel

Admin panel → **Servers → Add server**:

| Platform field | Value from this guide |
|---|---|
| `name` | e.g. `DE-1 Frankfurt` |
| `country` / `city` | `DE` / `Frankfurt` |
| `panel_url` | `https://SERVER:2053/Xk3jP9qL` (base path, no trailing `/login`) |
| `panel_user` / `panel_pass` | panel credentials (stored encrypted) |
| `inbound_id` | inbound ID from step 3 |
| `host` | public IP or domain clients connect to |
| `port` | `443` |
| `public_key` | Reality public key |
| `short_id` | Reality short id |
| `sni` | Reality SNI |
| `status` | `ONLINE` |

## 5. Verify

Admin panel → Servers → the new server row → **Check** runs a live login against the
panel API and reports success/failure. After that, any new paid subscription will
provision clients on this server automatically.

## Troubleshooting

- **Login fails**: check panel URL includes the web base path; check credentials;
  check the panel port is reachable from the platform host (firewall).
- **Clients created but cannot connect**: verify Reality `dest/SNI` host is reachable,
  `publicKey`/`shortId` in the platform match the inbound, port 443 open.
- **Panel version differences**: endpoint paths are centralized in
  `apps/backend/app/services/vpn_manager/xui_client.py`; 3x-ui v3 (`panel/api/clients/*`)
  requires updating only that module.
