---
name: pp-pagetemplate
description: "Create, edit, and delete page templates (mspp_pagetemplate) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API. A page template is the required link between a web page and the WEB TEMPLATE (Liquid layout) it renders in — every mspp_webpage binds mspp_pagetemplateid, so a page can't exist without one. Covers the Web Template type (modern), header/footer toggle, the default template, and an optional bound table. WHEN: create a page template, add a new layout for pages, why must a page have a page template, link a web template to pages, set the default page template, change which layout a page uses, manage mspp_pagetemplate, make a full-width or landing-page template, page template vs web template."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Page templates on a Power Pages site — create, edit, delete

Manage **page templates** (`mspp_pagetemplate`) on a traditional (enhanced-data-model, `mspp_*`)
Power Pages site through the Dataverse Web API. A page template is the **required link** between
a **web page** and the **web template** (Liquid layout) that renders it — every `mspp_webpage`
binds `mspp_pagetemplateid`, so **you can't create a page without a page template** (that's why
`pp-webpage` reuses an existing one).

> Read `references/traditional-site-editing-model.md` first. Know the three-link chain:
>
> **web page** (`mspp_webpage`) → **page template** (`mspp_pagetemplate`) → **web template**
> (`mspp_webtemplate`, the Liquid layout).
>
> `pp-webtemplate` edits the **layout markup**; **this** skill manages the page template that
> *selects* which layout a page uses; `pp-webpage` is the page that *consumes* it. Reach for
> `pp-pagetemplate` when you need a **new layout choice** for pages (a landing page, a full-width
> template, a sidebar-less template) — not just to edit existing markup.

## The model

A page template is a `powerpagecomponent`-family virtual table (`mspp_pagetemplate`):

| Column | Holds |
|---|---|
| `mspp_name` | The template's name (what makers pick in the page's settings). |
| `mspp_type` | **Web Template** (modern) vs **Rewrite** (legacy ASPX). New traditional sites use Web Template. |
| `mspp_webtemplateid` | Lookup → the `mspp_webtemplate` (Liquid layout) rendered — used when type = Web Template. |
| `mspp_usewebsiteheaderandfooter` | Wrap the layout in the site's shared header/footer (typical `true`), or a standalone shell (`false`). |
| `mspp_isdefault` | Whether this is the site's default page template. Exactly one default per site. |
| `mspp_entityname` | Optional: the Dataverse table this template is intended for (record-detail templates). |
| `_mspp_websiteid_value` | The site it belongs to. |

> ℹ️ **Confirm logical names & option values** for `mspp_type` against your environment (they
> mirror the legacy `adx_pagetemplate` set; "Web Template" is the modern value). List an existing
> template first (Step 1) and copy its shape.

## Step 1 — List existing page templates (scope by site)

```
GET /api/data/v9.2/mspp_pagetemplates?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_type,mspp_isdefault,mspp_usewebsiteheaderandfooter,_mspp_webtemplateid_value,mspp_pagetemplateid
```

Copy the shape of a working template (especially `mspp_type` and the header/footer flag) rather
than guessing.

## Step 2 — Create a page template (Web Template type)

First get the layout `mspp_webtemplate` id (see `pp-webtemplate` to list/create the layout), then:

```jsonc
POST /api/data/v9.2/mspp_pagetemplates
{
  "mspp_name": "Full-width landing",
  "mspp_usewebsiteheaderandfooter": true,
  "mspp_isdefault": false,
  "mspp_webtemplateid@odata.bind": "/mspp_webtemplates(<WEBTEMPLATEID>)",
  "mspp_websiteid@odata.bind":     "/mspp_websites(<SITEID>)"
  // "mspp_type": <Web Template option value>   // set if the env doesn't default it
}
```

The `mspp_webtemplateid` is the layout the page renders in. If you don't have a suitable layout
yet, create the Liquid web template with `pp-webtemplate`, then bind it here.

## Step 3 — Use it on a page

A page template only takes effect when a page points at it. Bind it from the **root** (and
content) `mspp_webpage` — this is exactly the `mspp_pagetemplateid` bind `pp-webpage` uses:

```
PUT /api/data/v9.2/mspp_webpages(<WEBPAGEID>)/mspp_pagetemplateid/$ref
{ "@odata.id": "https://<org>/api/data/v9.2/mspp_pagetemplates(<PAGETEMPLATEID>)" }
```

(`pp-webpage` sets this at page-create time; use the PUT above to re-point an existing page at a
different template.)

## Step 4 — Edit / set default / delete

```
PATCH  /api/data/v9.2/mspp_pagetemplates(<PTID>)  { "mspp_name": "Landing (wide)" }
PATCH  /api/data/v9.2/mspp_pagetemplates(<PTID>)  { "mspp_isdefault": true }   // new default
DELETE /api/data/v9.2/mspp_pagetemplates(<PTID>)
```

> **Before deleting**, check no page binds it: `GET mspp_webpages?$filter=_mspp_pagetemplateid_value eq <PTID>&$select=mspp_name`.
> Pages bound to a deleted template lose their layout. Keep exactly **one** `mspp_isdefault = true`
> per site — setting a new default, clear the old one.

## Step 5 — Flush cache & verify

Templates are cached — flush (`pp-cache`), then load a page that uses this page template and
confirm it renders in the intended layout (header/footer present or not, per the flag).

## Field & option reference

- Table: `mspp_pagetemplate`; entity set `mspp_pagetemplates`. Key columns: `mspp_name`,
  `mspp_type`, `mspp_webtemplateid`, `mspp_usewebsiteheaderandfooter`, `mspp_isdefault`,
  `mspp_entityname`, `mspp_websiteid`.
- Chain: `mspp_webpage.mspp_pagetemplateid` → `mspp_pagetemplate.mspp_webtemplateid` →
  `mspp_webtemplate`. Layout markup is `pp-webtemplate`; the page is `pp-webpage`.
- Scope every query by `_mspp_websiteid_value`; one env can host several sites.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.

## Microsoft docs & shared references

- **Render mode matters:** a Web-Template page template won't render entity-list **Calendar/Map** views — use a **Rewrite-mode** page template for those pages.
- Full detail: `references/web-template-components.md`.
