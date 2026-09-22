---
name: pp-headers
description: "Inspect and configure the security response headers a traditional (enhanced-data-model, mspp_*) Power Pages site sends to browsers — Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, HSTS, referrer/permissions policy, and cookie/CORS behavior — through the mspp_sitesetting records that drive them, then verify the live responses. WHEN: configure security headers, add or fix a Content Security Policy, set CSP on a portal, add X-Frame-Options / HSTS / nosniff, fix CSP errors, harden browser headers, clickjacking protection, cookie SameSite, manage-headers, why is my portal missing security headers."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Security headers & CSP on a Power Pages site

Configure the **security response headers** a traditional (enhanced-data-model, `mspp_*`) Power
Pages site sends to browsers — driven by **`mspp_sitesetting`** records — then verify the live
responses carry them. This is the header/CSP layer referenced by `pp-securityreview` (check #5).

> Read `references/traditional-site-editing-model.md` first. Headers are **site settings**, so
> the loop is: read the current settings → set/patch the `mspp_value` → flush cache → confirm
> the header on a live response.

> ℹ️ **Setting names vary by platform version.** The header site settings have used both
> `HTTP/<Header>` and `Header/<name>` naming across versions, and some are managed in the Power
> Pages **Set up → Site settings / security** UI. Always **list the site's current settings
> first** (below) and match the names already in use; confirm against Microsoft's Power Pages
> security-header docs before inventing a new one.

## Step 1 — List the current header settings (scope by site)

```
GET /api/data/v9.2/mspp_sitesettings?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_value,mspp_sitesettingid
```

Scan for the header-related names in use, typically among:

| Concern | Setting name (confirm live) | Good value |
|---|---|---|
| Content-Security-Policy | `HTTP/Content-Security-Policy` (or `Header/Content-Security-Policy`) | restrictive policy; avoid `unsafe-inline`/`unsafe-eval` in `script-src` |
| Clickjacking | `HTTP/X-Frame-Options` | `SAMEORIGIN` or `DENY` |
| MIME sniffing | `HTTP/X-Content-Type-Options` | `nosniff` |
| Transport security | `HTTP/Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| Referrer | `HTTP/Referrer-Policy` | `strict-origin-when-cross-origin` |
| Permissions | `HTTP/Permissions-Policy` | least-privilege feature list |

## Step 2 — Create or update a header setting

Update an existing setting's value:

```
PATCH /api/data/v9.2/mspp_sitesettings(<SETTINGID>)   { "mspp_value": "nosniff" }
```

Create one that's missing (bind the website):

```jsonc
POST /api/data/v9.2/mspp_sitesettings
{
  "mspp_name": "HTTP/X-Content-Type-Options",
  "mspp_value": "nosniff",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

## Content-Security-Policy — the high-value one

A missing or `unsafe-inline` CSP turns a single XSS into full script execution. Build a policy
that reflects what the site actually loads, then tighten:

```
default-src 'self';
script-src 'self' https://<cdns-you-use>;         /* no 'unsafe-inline' / 'unsafe-eval' */
style-src  'self' 'unsafe-inline';                /* portals often need inline styles */
img-src    'self' data: https:;
connect-src 'self';
frame-ancestors 'self';
```

If the site has inline scripts you can't remove, prefer **nonces/hashes** over
`unsafe-inline`. Roll a strict CSP out carefully — a too-tight policy blanks pages; watch the
browser console for `Refused to …` violations and widen only what's genuinely needed.

## Step 3 — Cookies & CORS (related settings)

Cookie `SameSite`/secure behavior and cross-origin sharing are governed by their own site
settings (names vary by version — list them as in Step 1). Prefer `SameSite=Lax`/`Strict` and a
narrowly-scoped CORS allow-list; never reflect an arbitrary `Origin`.

## Step 4 — Flush cache & verify on the wire

Header settings are cached — flush (`pp-cache`), then confirm the **live response** carries the
header (not just that the setting exists):

```
curl -sI https://<site-domain>/ | findstr /I "content-security-policy x-frame-options x-content-type-options strict-transport-security"
```

Fix until every intended header is present with the intended value, and the CSP shows no console
violations on a normal page load.

## Notes

- **List first, match existing names** — don't create a duplicate under a different naming
  scheme; that leaves two half-configured settings.
- Set the header, flush, then **verify on the wire** — an `mspp_sitesetting` row present but not
  reflected in the response usually means the cache wasn't flushed or the name is wrong.
- Headers are defense-in-depth; they reduce XSS blast radius but don't replace escaping — see
  `pp-securityreview` and `pp-liquid`.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
