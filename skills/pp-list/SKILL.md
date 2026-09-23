---
name: pp-list
description: "Create, edit, and delete lists (mspp_entitylist) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — a no-code grid of Dataverse records from one or more saved views, with the full surface: attributes (views, page size, details page), Grid Configuration Options (view + item actions Create/Download/Details/Edit/Delete/Workflow, override columns, dialogs, messages, CSS), filters (my/account, search), alternate views (map, calendar, modern list), custom scripting via the list web template, the deprecated OData feed vs the Web API, and AI features (natural-language search, AI list summary). WHEN: add a list, portal list/grid, entity list, mspp_entitylist, show Dataverse records on a page, list actions create/edit/delete/download, map view, calendar view, modern list, filter a list, search a list, natural language search, AI list summary, OData feed, wire a list to a details/create form."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.2.0"
---

# Lists on a Power Pages site — full configuration

Manage **lists** (`mspp_entitylist`) on a traditional (enhanced-data-model, `mspp_*`) Power Pages
site through the Dataverse Web API. A list is a **no-code grid** of Dataverse records built from
one or more **Dataverse saved views** (`savedquery`), with sorting, paging, search, filters,
row/toolbar actions, and alternate renderings (map, calendar, modern list).

> Read `references/traditional-site-editing-model.md` first. Core columns live on
> `mspp_entitylist`; actions/dialogs/overrides live in the **Options / Grid Configuration** JSON
> on the list; map & calendar views are their own config tabs. Column logical names mirror legacy
> `adx_entitylist`; **read an existing list first** and copy names/shapes.

## Step 1 — Create the list (attributes)

```jsonc
POST /api/data/v9.2/mspp_entitylists
{
  "mspp_name": "Accounts",
  "mspp_entityname": "account",       // Table Name (logical)
  "mspp_pagesize": 10,                 // Page Size (default 10)
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
  // + View reference (one or more savedquery ids) — see the note
}
```

| Attribute | Notes |
|---|---|
| Table Name (`mspp_entityname`) | The table the views load from. Required. |
| View | One or more **saved views** to render. **Multiple views → the page shows a view switcher.** Required. |
| Page Size | Records per page (default 10). |
| Web Page for Details View (+ Details Button Label) | Row link to a details page; the record id + *ID Query String Parameter Name* are appended. |

> ℹ️ The **view reference** (a list of `savedquery` ids) and search flags are stored on the list;
> read an existing list to see the exact column/shape and reproduce it.

## Step 2 — Grid Configuration → Options (actions, columns, messages)

The **Options** tab (Basic + Advanced) drives actions and presentation:

**View Actions** (toolbar, above the grid): **Create**, **Download** (exports to `.xlsx` via
FetchXML). **Item Actions** (per row, each gated by table permissions): **Details**, **Edit**,
**Delete**, **Workflow** (on-demand), **Activate**, **Deactivate**, plus per-table specials
(Resolve/Cancel Case on `incident`, Win/Lose on `opportunity`, etc.).

- **Create / Details / Edit** actions point at a **basic form** (`pp-basicform`) of the list's
  table (opened in a dialog or a target page) — *Record ID Parameter Name* must match the form's
  (default `id`). If the table has no basic form, the button won't render.
- **Delete** action permanently deletes the row (Delete privilege required); configure its
  confirmation dialog.
- **Override Column Attributes:** per-column *Display Name* and *Width* (with *Grid Column Width
  Style* = Pixels/Percent).
- **Messages / dialogs:** Loading / Error / Access Denied / Empty message overrides, and
  Create/Edit/Details/Delete/Error **dialog** settings (title, size, CSS).
- **CSS:** *CSS Class* (whole grid area) and *Grid CSS Class* (the `<table>`).

Each action supports *Confirmation Required?*, button label/tooltip/CSS, and *Redirect to
Webpage/URL* on completion (recommended for Delete).

## Step 3 — Filters & search

- **My / Account filter:** set **Portal User Attribute** and/or **Account Attribute** to scope
  rows to the signed-in user and/or their parent Customer account. If both are set, the page shows
  a *My / account* switcher. Also filterable by current website.
- **Search:** enable search (with placeholder text). Exclude large text columns from search — they
  hurt performance (query anti-pattern).

## Step 4 — Alternate views

- **Map view** (`Map View` tab): render records as **Bing-maps** pushpins from latitude/longitude
  columns; set Default Center Lat/Long, Distance Values + Units. Records without coordinates are
  excluded; the saved view's rows are replaced by a distance query. (Bing only; not in the German
  Sovereign Cloud.)
- **Calendar view** (`Calendar View` tab): render records as events — map **Start/End Date**,
  **Summary**, **Description**, **Organizer**, **Location**, **Is All Day** columns; set **Initial
  View** (year/month/week/day), **Initial Date**, **Time Zone Display Mode**, and **Style** (Full
  Calendar / Event List). Needs at least one date column.
- **Modern list (preview):** an updated rendering — shimmer loading, infinite scroll, inline
  column filters, and styling (colors, alternating rows, spacing). Enabled/styled in the design
  studio; styles are copyable across lists.

## Step 5 — Data access: Web API, not the OData feed

The legacy **list OData feed** is **deprecated** (no new sites since Oct 2022; removal by June
2026). For programmatic/AJAX access to list data, use the **Power Pages Web API** (`/_api/*`) —
see `pp-webapi`. Don't build new integrations on the OData feed.

## Step 6 — Custom scripting

A list is rendered by a **list web template**; custom behavior goes in the template's Liquid/JS
(edit via `pp-webtemplate`) or in page JS on the hosting page — there's no per-list "Custom
JavaScript" column like forms have. Read list data client-side via the **Web API** (`pp-webapi`),
and always escape record values before injecting them into the DOM (a `pp-securityreview` XSS
check).

## Step 7 — AI features (preview)

- **Natural-language / Copilot search:** design studio → *Edit List → More options → Enable
  search in this list* + **Search with natural language** On. Queries of >2 words are interpreted
  by Copilot (`Orders from last week over 500 dollars`); ≤2 words (or quoted) do a text search.
  Requires site version **9.7.4.x+**.
- **AI list summary:** an AI-generated summary of the list's records. Limits: no virtual tables,
  ≥5 rows for a meaningful summary, first 5,000 records only (Dataverse page cap), TDS-endpoint
  column-type limits. Governed by the admin Copilot governance controls.

These are design-studio/site features, not `mspp_entitylist` columns.

## Step 8 — Place on a page & test

```liquid
{% include 'entity_list' key: 'Accounts' %}
```

Or add the **List** component in the design studio; a page can also reference the list via its
lookup. Flush (`pp-cache`), then confirm the grid renders, search/sort/paging/filters work,
row/toolbar actions open the right forms/pages, and alternate views display. A list shows only
records the user can **Read** — an empty list is usually a missing **table permission + web role**
(`pp-tablepermission` / `pp-webrole`), not a broken view.

## Field & option reference

- Table: `mspp_entitylist` (+ `savedquery` views). Scope by `_mspp_websiteid_value`. Confirm exact
  columns/JSON shapes against your env.
- Reads gated by table permissions (`pp-tablepermission`) + web roles (`pp-webrole`); a broad list
  over a sensitive table is a `pp-securityreview` finding. Create/Edit actions rely on
  `pp-basicform`.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.

## Microsoft docs & shared references

- From **June 2026**, lists enforce table permissions regardless of the legacy flag; **list OData feeds are removed by June 2026** — use the Web API. Modern lists support custom JavaScript (v9.8.8.x+).
- Full detail: `references/security-model.md`, `references/webapi-field-configuration.md`.
