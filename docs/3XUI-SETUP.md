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

## 4b. Multiple transports for Russia (Wi-Fi + mobile LTE bypass)

In Russia, plain Reality works great on Wi-Fi/home but mobile carriers (МТС,
Мегафон, Yota, Билайн, Tele2) do deep DPI and often throttle it. The fix is to
offer several transports for the **same physical VPS** and let the client pick a
working one. Create several **inbounds** in 3X-UI on the same server, then add
each as a **separate server row** in the admin panel (same `panel_url`, different
`inbound_id` + transport). The subscription then includes all of them.

Recommended set per VPS:

| Purpose | 3X-UI inbound | Admin `transport` / `security` | Extra admin fields |
|---|---|---|---|
| Wi-Fi / home | VLESS · TCP · Reality · :443 | `tcp` / `reality` | `public_key`, `short_id`, `sni` |
| **Mobile LTE (best)** | VLESS · WS · TLS behind **Cloudflare** | `ws` / `tls` | `host`=CDN domain, `sni`=domain, `network_path`=WS path, `header_host`=domain |
| Mobile LTE (alt) | VLESS · gRPC · Reality | `grpc` / `reality` | `public_key`, `short_id`, `sni`, `network_path`=serviceName |

**Cloudflare WS/TLS (strongest mobile bypass):**
1. Point a domain/subdomain (e.g. `cdn.yourdomain.com`) at the VPS IP in Cloudflare, **proxied** (orange cloud on).
2. In 3X-UI create a **VLESS + WS** inbound (no Reality); set a WS path like `/vpnws`. TLS is terminated by Cloudflare, so port `443` via the proxy.
3. Add a server row: `transport=ws`, `security=tls`, `host=cdn.yourdomain.com`,
   `sni=cdn.yourdomain.com`, `network_path=/vpnws`, `header_host=cdn.yourdomain.com`,
   `inbound_id`=that inbound. Cloudflare IPs are not blocked in Russia, so LTE users
   stay connected.

Name the rows clearly (`FI Wi-Fi`, `FI LTE`) — users see these names in their client.

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
