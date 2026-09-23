# Web API field configuration (least-privilege columns)

Shared reference for exposing Dataverse data through the Power Pages **portal Web API** (`/_api/*`)
on a traditional (enhanced-data-model) site. Used by `pp-webapi`, `pp-securityreview`,
`pp-columnpermission`, and the `security-auditor` agent.

> **Authority:** Microsoft Learn is the source of truth here. Community notes are labelled.
> **Sources:** [Portals Web API overview](https://learn.microsoft.com/en-us/power-pages/configure/web-api-overview) ·
> [Important changes & deprecations](https://learn.microsoft.com/en-us/power-pages/important-changes-deprecations) ·
> [Migrate from the Web API wildcard](https://learn.microsoft.com/en-us/troubleshoot/power-platform/power-pages/migrate-web-api-wildcard).

## The site settings

Set per table. **Use the table logical name** (e.g. `incident`) in the setting name; use the
**EntitySetName** (e.g. `incidents`) in the `/_api/` URL. Web API operations are **case-sensitive**.

| Site setting | Purpose |
|---|---|
| `Webapi/<table>/enabled` | `True`/`False`. Turns the Web API on for the table. Default `False`. |
| `Webapi/<table>/fields` | Comma-separated list of column **logical names** exposed (e.g. `name,emailaddress1,telephone1`). Required unless `UseFieldsFromView` is `True` with a non-empty view. |
| `Webapi/<table>/UseFieldsFromView` | `True`/`False`. Exposes columns from a public system view named **`Power Pages Web API Columns`** on that table. **Site version 9.8.8.x+.** Combinable with `fields` (union, de-duplicated). |
| `Webapi/error/innererror` | `True`/`False`. Adds inner-error detail to error responses (debug only). |

## The wildcard (`*`) is being removed — do not use it

`Webapi/<table>/fields = *` (expose every column) is **deprecated and being removed**:

- **August 2026** — newly created sites can no longer use `*`.
- **September 14, 2026** — `*` stops working on **all** sites; requests fail until migrated.

Applies to standard **and** custom tables, **anonymous and authenticated** users, and to reads,
writes, aggregates, FetchXML, **and file/image columns**. An admin can request a one-time ~90-day
extension (Power Platform admin center → *Manage exemptions*), but it only defers the deadline.

## Build the least-privilege column list

List **only** the columns the site actually uses — never "all columns as a wildcard replacement."
Scan every Web API call and the code that reads its response for logical names in:

- response properties (`result.fullname` → `fullname`),
- create/update payloads (`{ emailaddress1: … }` → `emailaddress1`),
- `$select`, `$filter`, `$orderby`, and `$expand` (include the related-table columns too).

Column-name rules:

- Ordinary columns → the **logical name**.
- Lookup **read/filter** → the OData property `_<logicalname>_value` (e.g. `_primarycontactid_value`).
- Lookup **write** → the **navigation property** (the name used before `@odata.bind`).
- **File / image / rich-text columns → list them explicitly by logical name.** There are **no
  exceptions.** *(Correction: a community post described `msdyn_richtextfile` as a wildcard
  "exception" — Microsoft's guidance is that no column is exempt; verify the exact column name on a
  live site and list it.)*

### Option: `UseFieldsFromView` (v9.8.8.x+)

Instead of (or alongside) a hand-maintained `fields` list, create a public system view named
**`Power Pages Web API Columns`** on the table, add the needed columns, publish it, and set
`Webapi/<table>/UseFieldsFromView = True`. Notes: only **displayed** primary-table columns are
included (not filter/sort-only columns, not related-table columns); lookups still surface as
`_<logical>_value`; changes take **up to 5 minutes** to propagate.

> **Alignment note:** Microsoft's *official* Power Pages plugin does **not** use `UseFieldsFromView`
> yet — it writes explicit `fields` lists. `UseFieldsFromView` is a newer **platform** capability, not
> "what the MS plugin does." Offer both; pick explicit `fields` when the column set is stable and you
> want it in source control, the view when makers should manage columns without editing settings.

## Security still gates everything

The Web API is not a security boundary on its own. Every call is additionally gated by:

- **Table permissions + web roles** (record-level access — see `references/security-model.md`), and
- **Column permissions** (`pp-columnpermission`) for field-level restrictions.

All Web API calls require a **CSRF token** (use the `safeAjax` wrapper). The Web API also benefits
from server-side caching — clearing the portal cache causes brief performance degradation.

## Web API is for data tables only

Configuration tables are **not** accessible through the portal Web API — you cannot read/write
`mspp_*` / `adx_*` config components (web page, web template, site setting, entity form, entity
list, entity permission, page template, content snippet, web role, etc.) through `/_api`. Use the
Dataverse Web API / the `pp-*` content skills for those.

## Known issue — nested permissions on GET

A `GET` on a table with multiple levels of 1:N / N:N table permissions using **Parental / Contact /
Account** scopes can return a CDS error (the scope adds query conditions). Work around it by issuing
the query as **FetchXML** through the Web API.

## Practitioner notes (community, verify per site)

- **FetchXML through the Web API** — once the table's Web API is enabled you can pass `?fetchXml=`
  (URL-encode it); table + column permissions still apply, aggregates work, but you cannot mix OData
  `$` params and you hit the ~2048-char URL limit. *(Nicholas Hayduk — engineeredcode.com)*
- **`#` in an OData `$filter` value can silently truncate the query** — encode/escape `#`. *(Tino
  Rabe — powerportals.de)*
- **A PowerFx formula column can surface a computed value** without exposing the underlying
  restricted columns. Useful, but it is a workaround, not an MS-blessed pattern: the formula still
  **publishes derived data**, so make sure it can't leak a restricted value. *(Michel Mendes —
  michelcarlo.com)*
