---
name: pp-columnpermission
description: "Create, edit, and delete column-level security (mspp_columnpermissionprofile + mspp_columnpermission) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — restrict read/update/create on specific COLUMNS of a table within a table permission, bound to web roles, so a role can see/edit a table but not sensitive fields on it. Extends pp-tablepermission. WHEN: restrict a column on the portal, column-level security, hide a field from a web role, mspp_columnpermission, column permission profile, allow read but not edit on a field, protect sensitive columns, field-level portal security, extend a table permission to specific columns."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Column-level security on a Power Pages site — create, edit, delete

Manage **column permissions** (`mspp_columnpermissionprofile` + `mspp_columnpermission`) on a
traditional (enhanced-data-model, `mspp_*`) Power Pages site through the Dataverse Web API.
Column permissions restrict **read / update / create on specific columns** of a table *within* a
table permission — so a web role can access a table but **not** its sensitive fields.

> Read `references/traditional-site-editing-model.md` first. This **extends `pp-tablepermission`**:
> a column-permission **profile** hangs off a table permission (`mspp_entitypermission`) and is
> bound to **web roles**; each **column permission** in the profile sets per-column rights.
> Without a profile, a table permission exposes **every** readable column.

## The model

| Record | Holds |
|---|---|
| **`mspp_columnpermissionprofile`** | A named profile for one table permission: `mspp_name`, the parent table permission (`_mspp_entitypermissionid_value`), site. Bound to web roles via `mspp_columnpermissionprofile_webrole`. |
| **`mspp_columnpermission`** | One row per column: the profile (`_mspp_columnpermissionprofileid_value`), the column (`mspp_attributelogicalname`), and per-column **Read / Update / Create** rights. |

> ℹ️ **Confirm the rights columns/option values** (Read / Update / Create — booleans or an option
> set) and the exact lookup names against your environment; they mirror legacy
> `adx_columnpermission*`. Read an existing profile first and copy the shape.

## Step 1 — Find the table permission to extend

Column permissions attach to an existing `mspp_entitypermission` (see `pp-tablepermission`):

```
GET /api/data/v9.2/mspp_entitypermissions?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_entityname,mspp_entitypermissionid
```

## Step 2 — Create the profile (bound to the table permission)

```jsonc
POST /api/data/v9.2/mspp_columnpermissionprofiles
{
  "mspp_name": "Contact — hide SSN",
  "mspp_entitypermissionid@odata.bind": "/mspp_entitypermissions(<ENTITYPERMISSIONID>)",
  "mspp_websiteid@odata.bind":          "/mspp_websites(<SITEID>)"
}
```

## Step 3 — Add per-column rights

Add a `mspp_columnpermission` for each column you're restricting. Only list the columns you're
constraining; how unlisted columns behave (default allow vs deny) depends on the profile
model — **verify on your site** with a test role:

```jsonc
POST /api/data/v9.2/mspp_columnpermissions
{
  "mspp_attributelogicalname": "adx_ssn",
  "mspp_read":   false,
  "mspp_update": false,
  "mspp_create": false,
  "mspp_columnpermissionprofileid@odata.bind": "/mspp_columnpermissionprofiles(<PROFILEID>)"
}
```

## Step 4 — Bind the profile to web role(s)

```
POST /api/data/v9.2/mspp_columnpermissionprofiles(<PROFILEID>)/mspp_columnpermissionprofile_webrole/$ref
{ "@odata.id": "https://<org>/api/data/v9.2/mspp_webroles(<ROLEID>)" }
```

> **Verify the binding via the intersect directly** — an `$expand` reads blind under an app-only
> service principal (same gotcha as table permissions and page access rules). A profile bound to
> no role has no effect.

## Step 5 — Edit / delete

```
PATCH  /api/data/v9.2/mspp_columnpermissions(<COLID>)   { "mspp_read": true }
DELETE /api/data/v9.2/mspp_columnpermissions(<COLID>)          // stop restricting one column
DELETE /api/data/v9.2/mspp_columnpermissionprofiles(<PROFILEID>)  // remove the whole profile
```

## Step 6 — Flush cache, then test as the restricted role

Flush (`pp-cache`), then sign in **as a user in the bound role** and confirm the restricted
columns are hidden/read-only on the relevant forms, lists, and Web API responses — and that an
**unbound** role still sees them as intended. Column security is only proven by the negative test.

## Field & option reference

- Tables: `mspp_columnpermissionprofile`, `mspp_columnpermission`; intersect
  `mspp_columnpermissionprofile_webrole`. Scope by `_mspp_websiteid_value`.
- Extends `pp-tablepermission` (the table permission is the parent). Reviewed by
  `pp-securityreview` (over-exposure via `*` fields or missing column security).
- Also enforce least-field exposure on the **Web API** (`pp-webapi`) — column security and
  `Webapi/<table>/fields` are complementary controls.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
