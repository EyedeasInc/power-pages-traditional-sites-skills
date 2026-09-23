---
name: pp-cache
description: "Invalidate the Power Pages portal cache so component changes (web templates, web files, content snippets, site settings, table permissions, web pages) become visible. A PATCH to Dataverse updates the record but the running portal keeps serving the cached version until the cache is flushed. WHEN: my change isn't showing on the portal, clear Power Pages cache, flush portal cache, portal still shows old version, invalidate cache, changes not appearing after edit, /_services/about, force portal to refresh."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Flush the Power Pages portal cache

On a traditional (enhanced-data-model) Power Pages site, the running portal serves components
(web templates, web files, content snippets, site settings, table permissions, web pages) from a
**server-side cache**. When you PATCH a component directly in Dataverse — as every editing skill in
this plugin does — the record changes immediately, but visitors keep seeing the **cached** version
until you invalidate it. This is the single most common "I deployed but nothing changed" cause.

See `references/traditional-site-editing-model.md` for the editing model these changes come from.

## When you need it

After any of: `pp-webtemplate`, `pp-webfile` (also needs a URL cache-buster — see that
skill), `pp-serverlogic`, `pp-webapi` (site settings), `pp-tablepermission`, `pp-webpage`
(`mspp_copy` PUTs do **not** auto-bust), or editing content snippets / site settings.

## How to flush

### 1. `/_services/about` (fastest, no tooling)
Open the portal at **`https://<portal-domain>/_services/about`** while signed in. The page shows
the site/version and exposes a **Clear cache** action. Hitting it forces the portal to re-read
components from Dataverse. A plain authenticated `GET` of that URL is enough to nudge it in most
configurations.

Find the portal domain from the site record:
```
GET /api/data/v9.2/powerpagesites?$select=name,primarydomainname
      # or the enhanced-model website:
GET /api/data/v9.2/mspp_websites?$select=mspp_name
```
Match the site you edited (a tenant can host several). Use its `primarydomainname`
(e.g. `contoso.powerappsportals.com`) or the site's custom domain.

### 2. Power Pages Studio / Maker portal
In **Power Pages Studio** for the site, use **Sync** / **Clear cache** (or restart the site).
This is the reliable fallback when `/_services/about` isn't reachable from your machine.

### 3. Browser hard-refresh (client cache only)
For **web files** (CSS/JS), the *browser* also caches by URL. Even after a server flush, a client
may hold the old file. Bump the `?v=` cache-buster where the file is referenced (see
`pp-webfile`) so clients refetch — a server flush alone won't force that.

## Bundled helper

`scripts/flush_cache.py` resolves the site's domain and issues the `/_services/about` request.

```
python scripts/flush_cache.py --url <DATAVERSE_URL> [--site <SITEID>] [--domain <portal-domain>]
```

Auth follows the shared pattern (workspace `scripts/auth.py` `get_token()`, else `DATAVERSE_TOKEN`).

## Verify

Reload the changed page (a real page load, not just the API). If it still shows the old content:
1. Confirm you flushed the **right site's** domain.
2. For CSS/JS, confirm the **`?v=` cache-buster** was bumped (browser cache), then hard-refresh.
3. Confirm the component was actually **Published** and belongs to the same website.

## Notes / gotchas

- The portal hostname may not resolve from every network (dev boxes, locked-down VNets). If the
  `GET` can't reach it, use Studio's **Clear cache** instead.
- Cache flush is **not** instantaneous everywhere — give it a few seconds and reload.
- Flushing does not fix a component that was saved to the **wrong site** or left **unpublished** —
  check those first if a flush "doesn't work".

## Microsoft docs & shared references

- List/form reads are cached (community reports ~15 min); **portal writes clear the cache, but Dataverse-side changes (flows, plugins, model-driven app edits) do not** — design for that lag rather than cache-busting hacks.
