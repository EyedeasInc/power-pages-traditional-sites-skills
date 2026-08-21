---
name: manage-web-files
description: "Update the BYTES of a web file (CSS, JS, image, or any binary) on an enhanced-data-model Power Pages site by PATCHing the powerpagecomponent File column directly — then bump a cache-buster so browsers refetch. A web file is a powerpagecomponent type 3; its bytes live in the filecontent File column, NOT in the content {\"source\"} JSON that web templates (type 8) use. WHEN: update portal CSS, change a web file, replace a JS file, update a stylesheet, upload an image to the portal, bump CSS cache, fix web file, swap a favicon, refresh a theme asset, patch filecontent."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Manage web files (CSS / JS / images / binaries) on a Power Pages site

Update the actual **bytes** of a web file on an **enhanced-data-model** Power Pages site by
PATCHing the file through the Dataverse Web API — no whole-site upload, no Studio round-trip.
Then bump a cache-buster so clients refetch the new version.

Read the shared backbone first: `references/traditional-site-editing-model.md`. This skill
assumes its golden rules (read live first, patch one component, never batch-upload).

## Web file vs. web template — where the payload lives (don't confuse them)

Both are rows in the unified `powerpagecomponent` table, but the payload lives in **different
columns**:

| Type | Component | Payload column | Shape |
|---|---|---|---|
| **8** | Web template | `content` | JSON string **`{"source": "<liquid/html>", ...}`** |
| **3** | **Web file** (CSS/JS/image/binary) | **`filecontent`** | raw **bytes** (base64 on the wire) |

> ⚠️ A web file's bytes are **NOT** in the `content` `{"source"}` JSON. That JSON shape is only
> for web templates (type 8) and server logic (types 15/35). For a web file you PATCH the
> **`filecontent` File column** with the raw bytes. Editing `content` on a type-3 row does
> nothing to what the browser downloads.

## Step 1 — Locate the web file (scoped by site)

Find the type-3 component by name, scoped to your site. Never operate tenant-wide — one
environment can host several sites.

```
GET /api/data/v9.2/powerpagecomponents
    ?$filter=powerpagecomponenttype eq 3
             and name eq '<name.css>'
             and _powerpagesiteid_value eq <SITEID>
    &$select=powerpagecomponentid,name,_powerpagesiteid_value
```

- `powerpagecomponenttype eq 3` = web file.
- `name` is the file's component name (e.g. `theme.css`, `app.js`, `logo.png`).
- Capture `powerpagecomponentid` — that is the id you PATCH.

> Tip: if a **Dataverse MCP** is connected, use it for this read (it respects the caller's
> security role). Use the Web API for the File-column write.

## Step 2 — Read the live bytes FIRST (never patch a stale local copy)

If you are modifying (not wholesale replacing) the file — e.g. appending CSS rules — GET the
current bytes and apply your change onto **that**. A local `src-control` / `pac pages download`
folder is a stale snapshot; the live file may carry edits made in Studio.

```
GET /api/data/v9.2/powerpagecomponents(<COMPID>)/filecontent
```

This returns the raw bytes (the runtime decodes the stored base64 for you on a direct File-column
GET). Decode as text for CSS/JS; keep as bytes for images. Make your edit **idempotent** — if you
are appending a block, check it isn't already present before appending again.

## Step 3 — PATCH the bytes onto the `filecontent` File column

Two calls, exactly as in the reference implementation:

**(a) Set the file-name metadata** (a normal JSON PATCH to the `filecontent_name` virtual column):

```
PATCH /api/data/v9.2/powerpagecomponents(<COMPID>)
Content-Type: application/json
{ "filecontent_name": "<name.css>" }
```

**(b) Upload the bytes to the File column** with an octet-stream PATCH to the
`.../filecontent` path. The runtime base64-encodes for storage; you send raw bytes with the
file-name / content-type headers:

```
PATCH /api/data/v9.2/powerpagecomponents(<COMPID>)/filecontent
Authorization: Bearer <token>
Content-Type: application/octet-stream
x-ms-file-name: <name.css>
x-ms-file-content-type: text/css        # image/png, application/javascript, etc.
OData-MaxVersion: 4.0
OData-Version: 4.0

<raw file bytes>
```

A `200` or `204` means the bytes are stored. Set `x-ms-file-content-type` to match the asset
(`text/css`, `application/javascript`, `image/png`, `image/svg+xml`, `application/font-woff2`…);
the wrong MIME type can make the browser refuse the file.

> Small-file note: for files under the File-column single-request limit (~16 MB, tunable per
> environment) this single PATCH is enough. Larger files need the Dataverse chunked upload
> protocol — out of scope here; most theme CSS/JS/images are well under the limit.

## Step 4 — Bust the cache so browsers refetch

Two caches sit in front of a web file. Updating the bytes invalidates neither automatically.

1. **The browser cache** keys on the **URL**. If the file is referenced with a version
   querystring — `href="/theme.css?v=7"` — the browser keeps serving the old bytes from the same
   URL forever. **Bump the version** so the URL changes and clients refetch.
   - Find where the file is referenced: it's a `<link>` / `<script>` tag inside a **web template**
     (the theme/layout, or the header partial). Search the site's web templates for the file
     name:
     ```
     GET /api/data/v9.2/powerpagecomponents
         ?$filter=powerpagecomponenttype eq 8 and _powerpagesiteid_value eq <SITEID>
         &$select=powerpagecomponentid,name
     ```
     then read each template's `content` `{"source"}` and grep for `<name.css>`.
   - Bump the `?v=` token (e.g. `?v=7` → `?v=8`) and PATCH that web template's `source` back.
     Editing a web template is the **edit-web-template** skill — use it for the source-JSON
     mechanics (parse `content` directly, match-once guard, `{"source"}` shape).
   - No `?v=` present? Add one, or reference the file's `modifiedon` as the token, so future
     updates are bustable.
2. **The portal server cache.** Even with a fresh URL, the portal serves components from its own
   cache. Flush it after the write — the **flush-cache** skill (open `/_services/about` →
   **Clear cache**). Do this last, after both the bytes and any web-template bump are saved.

## Step 5 — Verify

- Load the file URL directly (`/<partialurl-or-path>/theme.css?v=<new>`) and confirm the new
  bytes are served (view source / DevTools Network, check the response and `Content-Type`).
- Load a page that uses it and confirm the change renders (styles applied, script runs, image
  shown). A hard refresh (Ctrl+F5) rules out a purely local browser cache.
- If you still see the old asset: re-check the `?v=` actually changed in the rendered HTML, and
  that you flushed the portal cache.

## Bundled helper

`scripts/update_web_file.py` does Steps 1–4: resolve the web file (by id, or by `--name` +
`--site`), read the local file, base64/octet-stream PATCH the `filecontent` column, and
optionally bump a `?v=` cache-buster inside a named web template.

```
# By component id, replace the bytes:
python scripts/update_web_file.py --url <DATAVERSE_URL> \
  --id <COMPID> --file ./theme.css --content-type text/css

# By name within a site, and bump the cache-buster in the theme web template:
python scripts/update_web_file.py --url <DATAVERSE_URL> \
  --site <SITEID> --name theme.css --file ./theme.css --content-type text/css \
  --bump-template "Theme" --dry-run
```

- `--dry-run` prints what it would write (bytes, target column, cache-buster bump) without
  PATCHing.
- `--bump-template <name>` finds the named type-8 web template, increments the `?v=N` next to the
  file reference in its `source`, and PATCHes the template (match-once guarded). Omit it to bump
  the cache-buster by hand via the edit-web-template skill.
- Auth: imports `get_token` from a workspace `scripts/auth.py` if present (the dv-connect
  pattern), else reads a bearer token from `DATAVERSE_TOKEN`. `DATAVERSE_URL` from `--url` or the
  env var.

## Field & option reference

- Table: `powerpagecomponent`; web file = `powerpagecomponenttype eq 3`; scope by
  `_powerpagesiteid_value`.
- Bytes column: **`filecontent`** (File). File name: `filecontent_name`. Do **not** use `content`
  for a web file — that column is for template/server-logic `{"source"}` JSON.
- Upload headers: `Content-Type: application/octet-stream`, `x-ms-file-name`,
  `x-ms-file-content-type`. Byte PATCH target is `.../powerpagecomponents(<id>)/filecontent`.
- One component per PATCH. **Never** `pac pages upload` a whole site to push one file — it can
  clobber live Studio edits.
- Cross-reference: **edit-web-template** (bump the `?v=` reference), **flush-cache** (invalidate
  the portal cache after the write).
