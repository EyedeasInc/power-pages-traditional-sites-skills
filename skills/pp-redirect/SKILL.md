---
name: pp-redirect
description: "Create, edit, and delete URL redirects (mspp_redirect) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — map an old/inbound URL to a target (a web page, a site marker, or an external URL) with a 301/302 status, so renamed or moved pages and vanity URLs keep resolving. WHEN: add a redirect, redirect an old URL, mspp_redirect, 301 redirect on the portal, vanity URL, forward a moved page, set up URL forwarding, fix broken inbound links after a page rename, redirect to an external site."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# URL redirects on a Power Pages site — create, edit, delete

Manage **URL redirects** (`mspp_redirect`) on a traditional (enhanced-data-model, `mspp_*`) Power
Pages site through the Dataverse Web API. A redirect maps an **inbound URL** to a **target** — a
web page, a site marker, or an external URL — with a **301/302** status, so renamed/moved pages
and vanity URLs keep resolving instead of 404ing.

> Read `references/traditional-site-editing-model.md` first. A redirect targets exactly one of:
> a web page, a `pp-sitemarker`, or an external URL. Prefer marker/page targets so the redirect
> survives later URL changes.

## The model

| Column | Holds |
|---|---|
| `mspp_name` | Redirect name. |
| `mspp_inboundurl` | The incoming path to catch (e.g. `/old-pricing`). |
| `mspp_redirectwebpageid` | Target **web page** (root) — one of the three targets. |
| `mspp_sitemarkerid` | Target **site marker** — one of the three targets. |
| `mspp_redirecturl` | Target **external / absolute URL** — one of the three targets. |
| `mspp_statuscode` | **301** (permanent) or **302** (temporary). |
| `_mspp_websiteid_value` | Site. |

> ℹ️ **Set exactly one target** (page **or** marker **or** URL). **Confirm the exact column and
> `mspp_statuscode` option values** against your environment (they mirror legacy `adx_redirect`);
> read an existing redirect first.

## Step 1 — List existing redirects (scope by site)

```
GET /api/data/v9.2/mspp_redirects?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_inboundurl,mspp_redirecturl,mspp_statuscode,_mspp_redirectwebpageid_value,_mspp_sitemarkerid_value,mspp_redirectid
```

## Step 2 — Create a redirect

**To a page** (survives URL changes — preferred):

```jsonc
POST /api/data/v9.2/mspp_redirects
{
  "mspp_name": "Old pricing → Pricing",
  "mspp_inboundurl": "/old-pricing",
  "mspp_statuscode": <301 option>,
  "mspp_redirectwebpageid@odata.bind": "/mspp_webpages(<ROOT_WEBPAGEID>)",
  "mspp_websiteid@odata.bind":         "/mspp_websites(<SITEID>)"
}
```

**To an external URL:**

```jsonc
POST /api/data/v9.2/mspp_redirects
{
  "mspp_name": "Docs → Learn",
  "mspp_inboundurl": "/docs",
  "mspp_redirecturl": "https://learn.microsoft.com/power-pages",
  "mspp_statuscode": <301 option>,
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

Use **301** for a permanent move (search engines transfer ranking) and **302** for a temporary
one.

## Step 3 — Edit / delete

```
PATCH  /api/data/v9.2/mspp_redirects(<ID>)   { "mspp_statuscode": <302 option> }
DELETE /api/data/v9.2/mspp_redirects(<ID>)
```

## Step 4 — Flush cache & verify

Flush (`pp-cache`), then request the inbound URL and confirm it returns the redirect (301/302) to
the right target — test with redirects **not** followed so you see the status and `Location`:

```
curl -sI https://<site-domain>/old-pricing | findstr /I "HTTP location"
```

## Field & option reference

- Table: `mspp_redirect`; entity set `mspp_redirects`. Key columns: `mspp_name`,
  `mspp_inboundurl`, the three target columns (set exactly one), `mspp_statuscode`,
  `mspp_websiteid`. Scope by `_mspp_websiteid_value`. Confirm exact names/option values in your env.
- Prefer page/marker targets over hard-coded URLs; pair with `pp-sitemarker` and `pp-webpage`.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
