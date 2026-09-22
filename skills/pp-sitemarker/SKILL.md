---
name: pp-sitemarker
description: "Create, edit, and delete site markers (mspp_sitemarker) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — named references to a web page that Liquid and settings resolve by name ({{ sitemarkers[\"Name\"].url }}), so links keep working when a page's URL changes. WHEN: add a site marker, create a named page reference, mspp_sitemarker, link by name instead of URL, make a link survive a URL change, resolve a page URL in Liquid, sitemarkers, point a template at a page by marker."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Site markers on a Power Pages site — create, edit, delete

Manage **site markers** (`mspp_sitemarker`) on a traditional (enhanced-data-model, `mspp_*`)
Power Pages site through the Dataverse Web API. A site marker is a **named pointer to a web page**
that Liquid and configuration resolve by name — so templates link to a page by a **stable marker
name** instead of a hard-coded URL, and the link keeps working when the page's `mspp_partialurl`
changes.

> Read `references/traditional-site-editing-model.md` first. A marker is a name → page mapping;
> templates consume it in Liquid. Pair with `pp-webpage` (the target page) and `pp-webtemplate`
> (where the marker is used).

## The model

| Column | Holds |
|---|---|
| `mspp_name` | The marker name referenced in Liquid (e.g. `Home`, `Contact Us`). |
| `mspp_pageid` | Lookup → the **root** `mspp_webpage` the marker points at. |
| `_mspp_websiteid_value` | The site it belongs to. |

**How it's consumed in Liquid** (in a web template — for reference):

```liquid
<a href="{{ sitemarkers["Contact Us"].url }}">Contact us</a>
```

## Step 1 — List existing markers (scope by site)

```
GET /api/data/v9.2/mspp_sitemarkers?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,_mspp_pageid_value,mspp_sitemarkerid
```

## Step 2 — Create a marker

Resolve the target **root** web page id first (see `pp-webpage`), then:

```jsonc
POST /api/data/v9.2/mspp_sitemarkers
{
  "mspp_name": "Contact Us",
  "mspp_pageid@odata.bind":    "/mspp_webpages(<ROOT_WEBPAGEID>)",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

Bind the **root** page (not the content page) so the marker resolves to the page's URL.

## Step 3 — Re-point / edit / delete

```
PUT    /api/data/v9.2/mspp_sitemarkers(<ID>)/mspp_pageid/$ref   { "@odata.id": ".../mspp_webpages(<NEW_ROOTID>)" }
PATCH  /api/data/v9.2/mspp_sitemarkers(<ID>)                    { "mspp_name": "Contact" }
DELETE /api/data/v9.2/mspp_sitemarkers(<ID>)
```

> **Renaming or deleting a marker breaks every `sitemarkers["<old name>"]` reference.** Grep
> templates/pages for the marker name before you change it; re-pointing `mspp_pageid` is the safe
> way to redirect a marker to a new page without touching any template.

## Step 4 — Flush cache & verify

Flush (`pp-cache`), then load a page that uses the marker and confirm the link resolves to the
right URL (and re-check after you re-point a marker).

## Field & option reference

- Table: `mspp_sitemarker`; entity set `mspp_sitemarkers`. Key columns: `mspp_name`,
  `mspp_pageid`, `mspp_websiteid`. Scope by `_mspp_websiteid_value`.
- Prefer markers over hard-coded paths in templates — the whole point is URL-change resilience.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
