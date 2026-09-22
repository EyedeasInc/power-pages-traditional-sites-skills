---
name: pp-list
description: "Create, edit, and delete lists (mspp_entitylist) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — a configurable, no-code grid of Dataverse records on a page, built from one or more Dataverse saved views, with search, sorting, paging, filters, and links to detail/create pages. WHEN: add a list, create a portal list view, show a grid of records on a page, entity list, mspp_entitylist, add a data table to a page, wire a list to a details page, enable search/filter on a portal list, render a list with Liquid entitylist, display Dataverse views on the portal."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Lists on a Power Pages site — create, edit, delete

Manage **lists** (`mspp_entitylist`) on a traditional (enhanced-data-model, `mspp_*`) Power Pages
site through the Dataverse Web API. A list is a **no-code grid** of Dataverse records rendered on
a page from one or more **Dataverse saved views**, with search, sorting, paging, filters, and
optional links to detail/create pages.

> Read `references/traditional-site-editing-model.md` first. A list reuses **Dataverse saved
> views** (`savedquery`) for its columns/sort — you pick the table and the view(s); the list
> config adds search, paging, and the actions. Then it's **placed on a page** (below).

## The model

| Concern | Where |
|---|---|
| Table | `mspp_entityname` (logical name, e.g. `account`). |
| Columns / sort | One or more Dataverse **saved views** referenced by the list (view ids). |
| Behavior | Page size, search enabled, filter config, empty-list message. |
| Actions | Links to a **details** page and a **create** page (basic forms) via web-page lookups. |
| Site | `_mspp_websiteid_value`. |

## Step 1 — Model on an existing list

```
GET /api/data/v9.2/mspp_entitylists?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_entityname,mspp_pagesize,mspp_entitylistid
```

Copy the shape (especially how views are referenced and the page/action lookups) from a working
list. Confirm the **table logical name** and the **saved view id(s)** you'll use exist in
Dataverse first.

## Step 2 — Create the list

```jsonc
POST /api/data/v9.2/mspp_entitylists
{
  "mspp_name": "Accounts",
  "mspp_entityname": "account",             // Dataverse table logical name
  "mspp_pagesize": 20,
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
  // + the view reference column(s) and search/filter flags — see the note
}
```

> ℹ️ **Confirm the view + settings columns** against your environment. The saved-view reference
> (a JSON list of view ids), search-enabled flag, and filter config mirror the legacy
> `adx_entitylist` columns — read them from the Step 1 record and reproduce that exact shape
> rather than guessing names.

## Step 3 — Wire the actions (details / create pages)

To make rows clickable and add a "Create" button, point the list at web pages:

- **Details page** — a page hosting a **basic form** in Edit/ReadOnly mode keyed by the row's id
  (`pp-basicform`).
- **Create page** — a page hosting a basic form in Insert mode.

Bind the corresponding web-page lookups on the list (confirm the lookup column names in your
env), so the list renders row links and a create button.

## Step 4 — Place the list on a page

```liquid
{% entitylist name: "Accounts" %}
  {% entityview id: page.adx_entitylist.id %}
    {% comment %} render rows {% endcomment %}
  {% endentityview %}
{% endentitylist %}
```

In practice the modern list web template does this for you — the design studio **List**
component renders `mspp_entitylist`. The Liquid above is the portable way to place/customize it
(see `pp-webtemplate` / `pp-webpage`).

## Step 5 — Edit / delete

```
PATCH  /api/data/v9.2/mspp_entitylists(<ID>)   { "mspp_pagesize": 50 }
DELETE /api/data/v9.2/mspp_entitylists(<ID>)
```

Before deleting, grep templates/pages for `entitylist name: "<name>"`.

## Step 6 — Flush cache, then test

Flush (`pp-cache`), load the page, and confirm the grid renders, search/sort/paging work, and
row/create links go to the right pages. A list only shows records the signed-in user can read —
it needs **table permissions + a web role** (`pp-tablepermission` / `pp-webrole`) granting Read;
an empty list is usually a missing permission, not a broken view.

## Field & option reference

- Table: `mspp_entitylist`. Scope by `_mspp_websiteid_value`.
- Key columns: `mspp_name`, `mspp_entityname`, `mspp_pagesize`, the saved-view reference,
  search/filter settings, and details/create web-page lookups. Confirm exact names in your env.
- Reads are gated by **table permissions** (`pp-tablepermission`) + **web roles** (`pp-webrole`);
  a `*`-scoped list over a sensitive table is a `pp-securityreview` finding.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
