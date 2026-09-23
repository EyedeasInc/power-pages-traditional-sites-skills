---
name: pp-webapi
description: "Enable, consume, audit, and disable the Power Pages Web API (/_api/*) for a Dataverse table on a traditional (enhanced-data-model, mspp_*) site. Teaches the two Web API site settings (Webapi/<table>/enabled, Webapi/<table>/fields), least-field exposure with case-sensitive column LogicalNames, the mandatory webapi.safeAjax client wrapper (CSRF token), and that table permissions + web roles still gate every call. WHEN: enable the Power Pages Web API, expose a table to the portal /_api, add or edit web api site settings, audit or reduce Web API exposure, disable the Web API for a table, call Dataverse from a portal page, set Webapi fields, portal ajax to Dataverse, portal CRUD from a page, /_api file upload, safeAjax, __RequestVerificationToken, why does /_api return nothing or 403."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# The Power Pages Web API for a table — enable, consume, audit, disable

The **Power Pages Web API** lets front-end JavaScript on a page read and write Dataverse
records through same-origin `/_api/*` endpoints — no custom back end. On a **traditional
(enhanced-data-model, `mspp_*`)** site you turn it on **per table** with two site-setting
records, then call it from the page with the platform's `webapi.safeAjax` wrapper.

Two things are load-bearing and easy to get wrong: which **columns** you expose (case-sensitive
LogicalNames, least-field), and **how** the browser calls it (you must use `safeAjax`, never a
hand-rolled `fetch`). Both are covered below.

> Enabling the Web API does **not** bypass security. Every call is still filtered by **table
> permissions bound to the caller's web role** (see Step 4). Turning on the Web API only makes
> the endpoint *reachable*; a matching table permission is what makes it *return data*.

## The model: two site settings per table

The Web API is configured through **`mspp_sitesetting`** records — name/value rows scoped to one
website (`_mspp_websiteid_value`). To expose table `<table>` (its **entity LogicalName**, e.g.
`account`, `contact`, `nnn_project`) you create:

| Site setting name | Value | Purpose |
|---|---|---|
| `Webapi/<table>/enabled` | `true` | Switches the `/_api/<entityset>` endpoint on for this table |
| `Webapi/<table>/fields` | `col1,col2,col3` (or `*`) | The exact columns the API may read/write |
| `Webapi/<table>/errors/innererror` | `true` *(optional)* | Returns full inner-error text — handy while developing, drop it in prod |

Notes that matter:

- `<table>` is the **entity LogicalName** (singular, e.g. `nnn_project`), **not** the entity-set
  (plural) name you put in the URL. The endpoint URL uses the entity-set: `/_api/nnn_projects`.
- **`fields` is a comma-separated list of column LogicalNames — case-sensitive.** `Name` and
  `name` are different; a wrong case silently drops the column. Verify each name against table
  metadata (below); don't guess.
- **Prefer least-field over `*`.** `*` exposes every column of the table to any web role that has
  a table permission — including columns the page never touches. List only what the page reads or
  writes. Widen later if needed; you can't un-leak.
- These are ordinary `mspp_sitesetting` rows — read them live, then PATCH the existing one or POST
  a new one. **Never batch-upload the whole site to push one setting.**

### Get the exact column LogicalNames (don't guess)

Case matters, so read them from metadata rather than the form UI:

```
GET /api/data/v9.2/EntityDefinitions(LogicalName='nnn_project')/Attributes
    ?$select=LogicalName,AttributeType&$filter=IsValidODataAttribute eq true
```

Pick the columns the page needs (plus the primary key `nnn_projectid` and typically
`statecode`/`statuscode` if you show status). That set becomes your `fields` value.

## Step 1 — Read live: does the setting already exist?

Scope by **website** — a tenant can host several sites, each with its own settings.

```
GET /api/data/v9.2/mspp_sitesettings
    ?$select=mspp_sitesettingid,mspp_name,mspp_value
    &$filter=_mspp_websiteid_value eq <SITEID> and startswith(mspp_name,'Webapi/nnn_project/')
```

If a setting exists, you **PATCH** it (don't create a duplicate — two rows with the same name is
ambiguous and the runtime may pick either). If not, you **POST** it.

## Step 2 — Create or update the two settings

**Create (POST)** — bind the website with `@odata.bind`:

```jsonc
POST /api/data/v9.2/mspp_sitesettings
{
  "mspp_name":  "Webapi/nnn_project/enabled",
  "mspp_value": "true",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

```jsonc
POST /api/data/v9.2/mspp_sitesettings
{
  "mspp_name":  "Webapi/nnn_project/fields",
  "mspp_value": "nnn_projectid,nnn_name,nnn_status,createdon",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

**Update (PATCH)** an existing row by id — change only the value:

```
PATCH /api/data/v9.2/mspp_sitesettings(<SETTINGID>)   { "mspp_value": "nnn_projectid,nnn_name,nnn_status" }
```

The bundled script does the read-live → PATCH-else-POST for both settings idempotently.

## Step 3 — Call it from the page (the client-side rule)

**You MUST include the "Power Apps Web API Wrapper Function" template and call
`webapi.safeAjax(...)`. Do not roll your own wrapper.** The wrapper attaches the
`__RequestVerificationToken` (anti-CSRF) header that every non-GET `/_api/*` call requires; a
hand-rolled `fetch`/`$.ajax` will get **403** on writes because it's missing that token.

Add the template to the page (Studio: *Sync* → the page's content, or include it in the web
template) — it defines the global `webapi.safeAjax`:

```html
{% include 'Power Apps Web API Wrapper Function' %}
```

**GET** (list / read) — safeAjax returns a jQuery promise; the payload is in `data.value`:

```html
<script>
  webapi.safeAjax({
    type: "GET",
    url: "/_api/nnn_projects?$select=nnn_projectid,nnn_name,nnn_status&$top=20",
    contentType: "application/json",
    success: function (data) {
      (data.value || []).forEach(function (row) {
        console.log(row.nnn_name, row.nnn_status);
      });
    },
    error: function (xhr) { console.error("Web API GET failed", xhr.status, xhr.responseText); }
  });
</script>
```

**POST** (create) — send only columns that are in your `fields` list:

```html
<script>
  webapi.safeAjax({
    type: "POST",
    url: "/_api/nnn_projects",
    contentType: "application/json",
    data: JSON.stringify({ nnn_name: "New project", nnn_status: 1 }),
    success: function (res, status, xhr) {
      // new record id is in the OData-EntityId response header
      console.log("created", xhr.getResponseHeader("OData-EntityId"));
    },
    error: function (xhr) { console.error("Web API POST failed", xhr.status, xhr.responseText); }
  });
</script>
```

**PATCH / DELETE** follow the same shape (`type: "PATCH"` with a body, or `type: "DELETE"`) against
`/_api/nnn_projects(<recordId>)`.

> ⚠️ **File columns.** For `/_api/file/*` (uploading to a File/Image column) you must **also** go
> through `webapi.safeAjax` — **never** call `fetch()` against `/_api/file/*`. The file endpoint
> needs the same verification token and header handling the wrapper provides; a raw `fetch` will
> fail or 403.

## Step 4 — Security is still enforced (table permissions + web roles)

The Web API respects the site's **table permissions** and **web roles** exactly like server-rendered
Liquid does. Two settings turn the endpoint *on*; they do **not** grant access.

For a call to return data / accept a write, the signed-in user's **web role** must have a
**table permission** on `<table>` with the matching privilege (Read for GET, Create for POST, Write
for PATCH, Delete for DELETE) and a scope (Global / Contact / Account / Self…) that covers the row.

- No matching table permission → the call returns an **empty result set** (GET) or **403** (write),
  even though `Webapi/<table>/enabled` is `true`.
- Anonymous pages need the permission bound to the **Anonymous Users** web role; authenticated pages
  to **Authenticated Users** (or a custom role).

Set these up with the **pp-tablepermission** workflow — enabling the Web API is orthogonal to it, and
you almost always need both. If a page "silently returns nothing," check the table permission and its
web-role binding **before** re-checking the site settings.

## Step 5 — Publish & verify

1. **Clear the portal cache:** site settings are cached — open `/_services/about` and click
   **Clear cache**, or the new `Webapi/*` values won't take effect.
2. **Verify the endpoint** while signed in as a user who has the table permission — load
   `/_api/nnn_projects?$select=nnn_name&$top=1` in the browser. A JSON `{ "value": [ … ] }` means
   enabled + permitted. `{ "value": [] }` on data you expect → a table-permission/web-role gap.
   A `404`/`"resource not found"` on the entity set → the `enabled` setting is missing or the
   `<table>` name is wrong.
3. **Verify a column** you expect is present in the response — a column absent from `fields`
   (or misspelled/wrong-case) simply won't appear.

## Bundled helper

`scripts/set_webapi_setting.py` reads live and idempotently PATCHes-or-POSTs the
`Webapi/<table>/enabled` and `Webapi/<table>/fields` settings for one site + table:

```
python scripts/set_webapi_setting.py --url https://org.crm.dynamics.com --site <SITEID> \
  --table nnn_project --fields nnn_projectid,nnn_name,nnn_status,createdon \
  [--innererror] [--dry-run]
```

- `--fields "*"` exposes all columns (least-field is preferred — pass the explicit list).
- `--innererror` also sets `Webapi/<table>/errors/innererror = true` (dev aid; omit in prod).
- `--dry-run` prints what it would create/update without writing.

Auth: it imports `get_token` from a workspace `scripts/auth.py` if present (the dv-connect
pattern), otherwise reads a bearer token from the `DATAVERSE_TOKEN` env var. `DATAVERSE_URL` comes
from `--url` or the env var of the same name.

## Field & option reference

- Table: `mspp_sitesetting` (columns `mspp_name`, `mspp_value`, lookup `mspp_websiteid`) — enhanced
  data model (`mspp_*`, **not** `adx_*`).
- Setting names (exact): `Webapi/<table>/enabled`, `Webapi/<table>/fields`,
  `Webapi/<table>/errors/innererror` — `<table>` is the entity **LogicalName** (singular).
- Endpoint URL uses the entity **set** (plural): `/_api/<entityset>` and `/_api/<entityset>(<id>)`.
- `fields` = comma-separated **case-sensitive** column LogicalNames, or `*`. Expose least.
- Client rule: include `{% include 'Power Apps Web API Wrapper Function' %}` and call
  `webapi.safeAjax(...)`. Never roll your own wrapper; never `fetch()` `/_api/file/*`.
- Security: still gated by **table permissions + web roles** — enabling the API grants nothing.
- Always scope by **website** (`_mspp_websiteid_value`); read live, PATCH-else-POST, never
  batch-upload; clear the cache after changing settings.

## Microsoft docs & shared references

- **Wildcard `Webapi/<table>/fields = *` is being removed** — no new sites Aug 2026; removed for **all sites Sept 14, 2026**. Use an explicit least-privilege column list, or set `Webapi/<table>/UseFieldsFromView = True` with a public **`Power Pages Web API Columns`** view (site v9.8.8.x+). No column is exempt (list file/image/rich-text explicitly).
- The Web API serves **data tables only** — `mspp_`/`adx_` config tables are unsupported. A `GET` with nested Parental/Contact/Account permissions may need **FetchXML**.
- Full detail: `references/webapi-field-configuration.md`.
