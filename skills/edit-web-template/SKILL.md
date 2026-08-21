---
name: edit-web-template
description: "Safely edit a web template (powerpagecomponent type 8) on a traditional Power Pages site by patching its live Liquid/HTML source through the Dataverse Web API — GET the live component, parse its content JSON robustly, apply a match-once string/regex edit to the source, and PATCH just that one component (never a batch upload). WHEN: edit a web template, change portal HTML/Liquid, update a Power Pages template, patch web template source, fix portal markup, modify a liquid template, tweak a template's rendered output, apply a code fix to a mspp_ web template."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Edit a web template on a Power Pages site

Change the Liquid/HTML **source** of a web template on an **enhanced-data-model**
Power Pages site by patching the single `powerpagecomponent` record directly through the
Dataverse Web API. No batch upload, no `pac pages upload` — you touch exactly one row.

> Read `references/traditional-site-editing-model.md` first. This skill assumes its golden
> rules: **read live before you edit**, **patch components individually**, **parse `content`
> robustly**, **match-once guard**, and **flush cache after**.

## The model: a web template is one component row with a JSON payload

A web template is a `powerpagecomponent` with `powerpagecomponenttype = 8`. The Liquid/HTML
lives inside the `content` column, which is **a JSON string**, not raw markup:

```json
{"source": "<div class=\"card\">{{ page.title }}</div>", "mimetype": "text/html"}
```

So editing a template is: GET the component → `json.loads(content)` → edit `content["source"]`
→ `json.dumps(content)` → PATCH the component. The `source` is what the site renders (inside
whatever page template references it); `mimetype` and any other keys must be preserved untouched.

## Step 1 — Locate the web template (by id, or by name + site)

If you already have the `powerpagecomponentid`, skip to Step 2. Otherwise find it by name,
scoped to the site so you don't match a same-named template on another site in the same env:

```
GET /api/data/v9.2/powerpagecomponents?$select=powerpagecomponentid,name,_powerpagesiteid_value
    &$filter=powerpagecomponenttype eq 8 and name eq '<Template Name>'
```

Add ` and _powerpagesiteid_value eq <SITEID>` to the `$filter` when the env hosts several sites.
To resolve the site id from a template you already have, read `_powerpagesiteid_value` on the
component. To list a site's templates, filter on `powerpagecomponenttype eq 8 and
_powerpagesiteid_value eq <SITEID>` and `$select=powerpagecomponentid,name`.

## Step 2 — GET the LIVE component and parse `content` robustly

The live Dataverse row is the source of truth. A local `src-control` / pac-download copy is a
**stale snapshot** — never patch on top of it. GET the live `content`:

```
GET /api/data/v9.2/powerpagecomponents(<COMPONENTID>)?$select=name,content
```

Parse the `content` string **directly** — do **not** `html.unescape()` it first:

```python
raw = record["content"] or "{}"
try:
    content = json.loads(raw)                 # correct path: parse the JSON string directly
except json.JSONDecodeError:
    content = json.loads(html.unescape(raw))  # fallback ONLY if the direct parse fails
source = content["source"]
```

Unescaping first corrupts legitimate `&`, `"`, and `<` inside the Liquid/HTML and throws
`JSONDecodeError` on templates that are perfectly valid — so try the direct parse first and
fall back to `html.unescape` only when it fails. Save `source` to a file if you want to eyeball
or hand-edit it before patching.

## Step 3 — Edit the source with a match-once guard

Apply your change to `source` as a string or regex replace, and **require the old fragment to
match exactly once** before writing. Abort the whole run if it matches zero times (drift — the
live copy isn't what you expected) or more than once (ambiguous — you'd patch the wrong spot):

```python
old = '<div class="card">{{ page.title }}</div>'
new = '<div class="card">{{ page.title | escape }}</div>'

n = source.count(old)
if n != 1:
    sys.exit(f"ABORT: old fragment matched {n} time(s) (expected 1). No PATCH sent.")
source = source.replace(old, new)
```

This is what makes a drifted live template **fail safely** instead of silently mis-patching.
For a multi-hunk change, guard each hunk independently and abort before *any* write if any hunk
fails its count. Anchor short fragments with a couple of surrounding lines so they match uniquely.

## Step 4 — PATCH the single component back

Put the edited `source` back into `content`, re-serialize the whole JSON object (preserving
`mimetype` and any other keys), and PATCH only this component:

```
PATCH /api/data/v9.2/powerpagecomponents(<COMPONENTID>)
Content-Type: application/json

{ "content": "{\"source\":\"<div class=\\\"card\\\">{{ page.title | escape }}</div>\",\"mimetype\":\"text/html\"}" }
```

In Python: `body = {"content": json.dumps(content)}`. A 204 (or 200) means success.

> **Never** `pac pages upload` the site to push one template change — it can clobber live edits
> made in Studio or by another patch. PATCH the one component you own.

## Step 5 — Flush the cache, then verify

The portal serves web templates from cache; your PATCH will not show until the cache is
invalidated. Flush it (see the `flush-cache` skill — e.g. open `/_services/about` and click
**Clear cache**), then load a page that renders this template and confirm your change is live and
the template still renders (a broken Liquid tag surfaces as a render error on the page).

## PowerShell caveat

If you must patch from PowerShell instead of Python, read the source with
`[IO.File]::ReadAllText(...)` and serialize the `content` object with
`System.Web.Script.Serialization.JavaScriptSerializer`. `ConvertTo-Json (Get-Content -Raw ...)`
**corrupts** the payload (double-encoding and newline mangling). In Python, `json.dumps` is fine.

## Bundled helper

`scripts/edit_web_template.py` does the whole loop with a `--dry-run` and the match-once guard.
It resolves the template by id or by name+site, does the robust parse, and either **pulls** the
live source to a file for editing or **applies** a new source / an old→new replacement and PATCHes.

Pull the live source to a file, edit it locally, then push it back:

```
# 1) fetch live source to a file
python scripts/edit_web_template.py --url https://org.crm.dynamics.com \
  --name "My Template" --site <SITEID> --pull-to source.html

# 2) edit source.html, then push it back (preview first)
python scripts/edit_web_template.py --url https://org.crm.dynamics.com \
  --id <COMPONENTID> --source-file source.html --dry-run
python scripts/edit_web_template.py --url https://org.crm.dynamics.com \
  --id <COMPONENTID> --source-file source.html
```

Or apply a single guarded old→new replacement without a round-trip through a file:

```
python scripts/edit_web_template.py --url https://org.crm.dynamics.com --id <COMPONENTID> \
  --replace-old-file old.txt --replace-new-file new.txt --dry-run
```

Auth: it imports `get_token` from a workspace `scripts/auth.py` if present (the dv-connect
pattern), otherwise reads a bearer token from the `DATAVERSE_TOKEN` env var. `DATAVERSE_URL`
comes from `--url` or the env var of the same name.

## Field & option reference

- Table: `powerpagecomponent`; entity set `powerpagecomponents`; this skill edits
  `powerpagecomponenttype = 8` (web template) rows only.
- Payload: `content` is a JSON string `{"source": "<liquid/html>", "mimetype": ...}`. Edit
  `source`; preserve every other key. PATCH body is `{"content": json.dumps(content)}`.
- Scope by site: `_powerpagesiteid_value` on the component — one env can host several sites.
- Parse rule: `json.loads(raw)` **directly**; `html.unescape` only as a fallback on failure.
- Safety rules: GET live first (local copies are stale); match-once guard before PATCH; patch the
  single component (never batch-upload); flush cache after (see `flush-cache`).
