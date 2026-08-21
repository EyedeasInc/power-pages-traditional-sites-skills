---
name: add-webpage
description: "Create a new web page on a Power Pages site and add it to the site navigation, through the Dataverse (mspp_*) data model — no custom code. A Power Pages web page is TWO records: a root web page + one localized content web page per language. WHEN: add a page, create a web page, new web page, add a page to a Power Pages site, add a navigation/menu item, add a nav link, scaffold a page, add a sub page, create webpage records, add page to sitemap."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Add a web page (+ navigation) to a Power Pages site

Create a new web page on an **enhanced-data-model** Power Pages site by writing the
Dataverse records directly, then surface it in navigation. Works without editing any
front-end code on a non-code site.

## The model: a web page is TWO records

In the enhanced data model every visible page is **two `mspp_webpage` rows**:

| Record | `mspp_isroot` | Holds |
|---|---|---|
| **Root** | `true` | `mspp_partialurl` (the URL), parent page, page template, publishing state, website, display order, nav/auth settings |
| **Content** (one per language) | `false` | link to the root (`mspp_rootwebpageid`), the language (`mspp_webpagelanguageid`), and the page body (`mspp_copy`) — plus its own page template / publishing state / parent |

The browser path (e.g. `/test`) comes from the **root**'s `mspp_partialurl`. The HTML you
see comes from the matching **content** page's `mspp_copy` (rendered inside the page
template). Both must be in the **Published** state and belong to the same website.

## Step 1 — Model it on an existing page (don't guess the lookups)

Pick a working page to copy settings from (the site's Home, or any normal content page).
Read **both** of its `mspp_webpage` records and capture these lookups — you'll reuse them:

```
GET /api/data/v9.2/mspp_webpages?$filter=_mspp_websiteid_value eq <SITEID> and mspp_partialurl eq '<existing-partialurl>'
    &$select=mspp_name,mspp_isroot,mspp_partialurl,_mspp_pagetemplateid_value,_mspp_parentpageid_value,
             _mspp_publishingstateid_value,_mspp_rootwebpageid_value,_mspp_webpagelanguageid_value
```

Record these IDs:
- **website** `_mspp_websiteid_value`
- **page template** `_mspp_pagetemplateid_value` (entity set `mspp_pagetemplates`)
- **parent page** `_mspp_parentpageid_value` — usually the site **Home** root page (entity set `mspp_webpages`)
- **publishing state** `_mspp_publishingstateid_value` — the **Published** state (entity set `mspp_publishingstates`; confirm with `?$filter=mspp_name eq 'Published'`)
- **language** `_mspp_webpagelanguageid_value` — e.g. en-US (entity set `mspp_websitelanguages`)

> Tip: if you have the **Dataverse MCP**, use it to read these — it respects security roles. Otherwise use the Web API with a bearer token.

## Step 2 — Create the ROOT record

POST one `mspp_webpage` with `mspp_isroot = true`. Bind every lookup with `@odata.bind`:

```jsonc
POST /api/data/v9.2/mspp_webpages           // Prefer: return=representation
{
  "mspp_name": "Test",
  "mspp_title": "Test",
  "mspp_partialurl": "test",                 // the URL segment -> /test
  "mspp_isroot": true,
  "mspp_displayorder": 5,
  "mspp_pagetemplateid@odata.bind":   "/mspp_pagetemplates(<TEMPLATEID>)",
  "mspp_parentpageid@odata.bind":     "/mspp_webpages(<PARENTID>)",
  "mspp_publishingstateid@odata.bind":"/mspp_publishingstates(<PUBLISHEDID>)",
  "mspp_websiteid@odata.bind":        "/mspp_websites(<SITEID>)"
}
```

> ⚠️ **Gotcha — the platform auto-creates a content page.** When you create a root page,
> a Power Pages plugin usually creates an **empty content page** for the site's default
> language automatically. **Do not blindly create a second one** — you'll get a duplicate.
> After creating the root, query for any content page first (Step 3).

## Step 3 — Create or reuse the CONTENT record

Check whether the auto-created content page exists:

```
GET /api/data/v9.2/mspp_webpages?$filter=_mspp_rootwebpageid_value eq <ROOTID>&$select=mspp_webpageid
```

- **If one exists** → reuse it. The auto-created one is often **missing** its page template,
  publishing state, and language — set them (see below).
- **If none exists** → POST a content page (`mspp_isroot:false`) binding `mspp_rootwebpageid`,
  `mspp_pagetemplateid`, `mspp_publishingstateid`, `mspp_webpagelanguageid`, `mspp_parentpageid`, `mspp_websiteid`.

**Set/repair the content page's lookups** (idempotent — safe whether auto-created or new).
Use single-valued-navigation `$ref` PUTs (these avoid a full PATCH, which can trip the
home-page validation plugin with `0x80040224`):

```
PUT  /api/data/v9.2/mspp_webpages(<CONTENTID>)/mspp_pagetemplateid/$ref      { "@odata.id": ".../mspp_pagetemplates(<TEMPLATEID>)" }
PUT  /api/data/v9.2/mspp_webpages(<CONTENTID>)/mspp_publishingstateid/$ref   { "@odata.id": ".../mspp_publishingstates(<PUBLISHEDID>)" }
PUT  /api/data/v9.2/mspp_webpages(<CONTENTID>)/mspp_webpagelanguageid/$ref   { "@odata.id": ".../mspp_websitelanguages(<LANGID>)" }
PUT  /api/data/v9.2/mspp_webpages(<CONTENTID>)/mspp_parentpageid/$ref        { "@odata.id": ".../mspp_webpages(<PARENTID>)" }
```

**Set the page body** with a **single-property PUT** (a full PATCH that includes `mspp_copy`
can fail the validation plugin; the single-property PUT does not):

```
PUT /api/data/v9.2/mspp_webpages(<CONTENTID>)/mspp_copy   { "value": "<h1 class=\"...\">Hello</h1> ..." }
```

The `mspp_copy` is the page body rendered inside the template — Liquid + HTML. Reuse the
site's existing CSS classes; don't inline styles if the site keeps CSS in a theme web file.

## Step 4 — Add it to navigation

**Non-code site (standard navigation = Web Link Set).** The page template's header renders a
**web link set**. Add a `mspp_weblink` pointing at the new page:

1. Find the primary nav set: `GET /api/data/v9.2/mspp_weblinksets?$filter=_mspp_websiteid_value eq <SITEID>` (often named "Default").
2. Create the link:
```jsonc
POST /api/data/v9.2/mspp_weblinks
{
  "mspp_name": "Test",
  "mspp_displayorder": 5,
  "mspp_weblinksetid@odata.bind": "/mspp_weblinksets(<SETID>)",
  "mspp_pageid@odata.bind":       "/mspp_webpages(<ROOTID>)"   // link to the ROOT page
}
```
The link label is `mspp_name`; `mspp_pageid` makes the URL track the page (no hard-coded path).

**Custom-layout / code site.** If the site uses a custom web template that renders a
hard-coded nav (not a web link set), add the link there instead — e.g. an `<a>` in the layout
web template's sidebar/header — and deploy that template. (A web link set link won't appear if
the layout doesn't render the set.)

## Step 5 — Publish & verify

1. **Clear the portal cache:** open `/_services/about` and click **Clear cache** (content and
   template changes won't show until you do). A `mspp_copy` PUT does not auto-bust the cache.
2. **Verify:** load `/<partialurl>` — confirm it returns 200 (not a sign-in/404), the body renders
   inside the template, and the nav item appears (and highlights as active on that page).
3. If the page 404s: check the **content page** has `mspp_publishingstateid = Published`, the right
   `mspp_webpagelanguageid`, and `mspp_rootwebpageid` pointing at the root.

## Bundled helper

`scripts/add_webpage.py` does Steps 2–4 end to end (root → reuse/repair content → set lookups →
PUT copy → optional web link), including the auto-content-page handling. Run:

```
python scripts/add_webpage.py --url <DATAVERSE_URL> --site <SITEID> \
  --name "Test" --partialurl test \
  --template <TEMPLATEID> --parent <PARENTID> --publishing <PUBLISHEDID> --lang <LANGID> \
  --copy-file body.html  [--weblinkset <SETID>]  [--displayorder 5]
```

Auth: it imports `get_token` from a workspace `scripts/auth.py` if present (the dv-connect
pattern), otherwise reads a bearer token from the `DATAVERSE_TOKEN` env var.

## Field & option reference

- Tables: `mspp_webpage`, `mspp_pagetemplate`, `mspp_publishingstate`, `mspp_websitelanguage`,
  `mspp_website`, `mspp_weblinkset`, `mspp_weblink` (enhanced data model — `mspp_*`, **not** `adx_*`).
- Key `mspp_webpage` columns: `mspp_name`, `mspp_title`, `mspp_partialurl`, `mspp_isroot`,
  `mspp_copy`, `mspp_displayorder`, and the lookups in Steps 2–3.
- Always operate per **website** (`_mspp_websiteid_value`) — a tenant can host several sites.
- Don't pluralize the URL; keep `mspp_partialurl` lowercase, no spaces.
- Quirks to remember: (1) root create auto-spawns a content page — reuse it; (2) auto-created
  content pages miss template/publishing/language — set them; (3) use single-property `PUT`
  for `mspp_copy` and `$ref` for lookups to dodge the validation plugin; (4) clear the cache.
