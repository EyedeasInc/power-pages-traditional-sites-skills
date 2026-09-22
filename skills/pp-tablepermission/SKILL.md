---
name: pp-table-permissions
description: "Configure table permissions (mspp_entitypermission) on a traditional (enhanced-data-model, mspp_*) Power Pages site and bind them to web roles so portal users can read/write Dataverse records. A permission grants CRUD scope on a table; it does NOTHING until it is bound to a web role via the mspp_entitypermission_webrole many-to-many intersect. WHEN: set up table permissions, grant portal CRUD access, bind a permission to a web role, fix portal 403/empty data, configure entity permission, verify web role bindings, give a web role read/create/write/delete on a table, scope records to the signed-in contact."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Table permissions (+ web-role binding) on a Power Pages site

On an **enhanced-data-model** site, portal access to Dataverse records is governed by
**table permissions** (`mspp_entitypermission`). Configure them by writing Dataverse records
directly — no front-end code. Read the shared
[`references/traditional-site-editing-model.md`](../../references/traditional-site-editing-model.md)
first; this skill assumes it.

> Table permissions are a **first-class `mspp_*` table** (per the backbone's rule: dedicated
> tables for pages, roles, permissions, settings, nav). Don't route them through the
> `powerpagecomponent` surface — write `mspp_entitypermission` directly.

## The model: a permission + a binding are TWO things

A permission alone does **nothing**. Access exists only when a permission is **bound to a web
role** that the user holds:

| Piece | Table | Holds |
|---|---|---|
| **Table permission** | `mspp_entitypermission` | the target table, the **scope**, the CRUD flags, the website |
| **Binding** | `mspp_entitypermission_webrole` (M:N intersect) | one (permission, web role) pair — repeated per bound role |

A signed-in user gets a privilege on a record only if **some web role they hold** is bound to a
permission whose **scope** includes that record. No binding ⇒ no access, no matter how the flags
are set. This is the #1 cause of "portal shows empty data / 403 on my table."

## Scopes — which records the permission covers

`mspp_scope` (Access Type) picks the record set the permission applies to:

| Scope | Option value | Covers | Needs |
|---|---|---|---|
| **Global** | `756150000` | every row of the table | — |
| **Contact** | `756150001` | rows related to the signed-in **contact** | `mspp_contactrelationship` = the contact→table relationship schema name |
| **Account** | `756150002` | rows related to the contact's parent **account** | `mspp_accountrelationship` |
| **Parent** | `756150003` | rows reachable from a **parent permission** via a relationship | `mspp_parententitypermission` + `mspp_parentrelationship` |
| **Self** | `756150004` | the user's **own contact record** only | — |

**Least privilege:** default to the narrowest scope that works. Use **Contact/Self** for
user-owned data (a user's own requests, profile, submissions). Reserve **Global** for genuinely
public/reference tables, and pair a Global permission with **read-only** flags unless writes are
truly meant to be site-wide.

## Privilege flags

Six booleans on `mspp_entitypermission`, granted independently:

| Flag | Column | Meaning |
|---|---|---|
| **read** | `mspp_read` | view records |
| **create** | `mspp_create` | create records |
| **write** | `mspp_write` | update records |
| **delete** | `mspp_delete` | delete records |
| **append** | `mspp_append` | attach this record to another (works with **appendto**) |
| **appendto** | `mspp_appendto` | allow another record to be attached to this one |

`append`/`appendto` come in a pair and are what you need when a portal form sets a **lookup**
(e.g. attaching a child row to its parent). If a create/update fails only when a lookup is
populated, you're usually missing `append` here and `appendto` on the **related** table's
permission.

## Step 1 — Create (or update) the permission

POST one `mspp_entitypermission`, scoped to the website. Bind lookups with `@odata.bind`:

```jsonc
POST /api/data/v9.2/mspp_entitypermissions          // Prefer: return=representation
{
  "mspp_name": "Announcements - Public",
  "mspp_entitylogicalname": "cr123_announcement",   // target table LOGICAL name
  "mspp_scope": 756150000,                           // Global
  "mspp_read": true,
  "mspp_create": false, "mspp_write": false, "mspp_delete": false,
  "mspp_append": false, "mspp_appendto": false,
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

For a **Contact** scope, drop the relationship instead of Global:

```jsonc
{
  "mspp_name": "Access Request - Self",
  "mspp_entitylogicalname": "cr123_accessrequest",
  "mspp_scope": 756150001,                                   // Contact
  "mspp_contactrelationship": "cr123_contact_accessrequest", // contact -> table relationship schema name
  "mspp_read": true, "mspp_create": true,
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

Idempotency: first `GET /api/data/v9.2/mspp_entitypermissions?$filter=_mspp_websiteid_value eq <SITEID> and mspp_name eq '<name>'`;
PATCH if it exists, else POST.

## Step 2 — BIND the permission to web role(s)

Associate the permission with each web role via the M:N **navigation property**
`mspp_entitypermission_webrole` using a `$ref` collection-bind:

```
POST /api/data/v9.2/mspp_entitypermissions(<PERMID>)/mspp_entitypermission_webrole/$ref
{ "@odata.id": "<ORGURL>/api/data/v9.2/mspp_webroles(<WEBROLEID>)" }
```

Repeat once per role. Re-associating an existing pair returns a duplicate error — treat that as
"already bound" and move on (idempotent). Resolve a web-role **name** to its id with
`GET /api/data/v9.2/mspp_webroles?$filter=_mspp_websiteid_value eq <SITEID> and mspp_name eq 'Authenticated Users'`.

Two roles almost every site has: **Authenticated Users** (any signed-in user) and **Anonymous
Users** (not signed in). Public read on a Global table usually binds both; user-owned data binds
only Authenticated Users.

## Step 3 — VERIFY the bindings (the load-bearing gotcha)

**To confirm which web roles a permission is bound to, query the
`mspp_entitypermission_webroleset` intersect DIRECTLY:**

```
GET /api/data/v9.2/mspp_entitypermission_webroleset
    ?$filter=mspp_entitypermissionid eq <PERMID>
    &$select=mspp_entitypermissionid,mspp_webroleid
```

Each returned row is one (permission, web role) pair. Map `mspp_webroleid` back to a name via
`GET /mspp_webroles(<id>)?$select=mspp_name`.

> ⚠️ **Do NOT verify via a nav-property `$expand`.** Under an **app-only service principal**,
> `GET /mspp_entitypermissions(<PERMID>)?$expand=mspp_entitypermission_webrole` reads **blind** —
> it returns an **empty** collection even when bindings exist. It will make you think the binding
> failed and double-create it. The intersect collection query above returns the real rows. (Note
> the EntitySetName ends in **`-set`** — it is `mspp_entitypermission_webroleset`, *not*
> `..._webroles`. Legacy standard-model sites use `adx_entitypermission_webroleset`.)

If the intersect returns rows but the portal still 403s, re-check: the user actually **holds**
that web role, the **scope** covers the record, and the needed **flag** is set.

## Parent–child permission chains (related tables)

Portal pages that show a parent with its children (an order with its lines, a case with its
notes) need a permission on **each** table. Give the child a **Parent** scope pointing at the
parent's permission:

1. Parent permission — e.g. Contact scope on `cr123_order` (read/create), bound to a role.
2. Child permission — **Parent** scope on `cr123_orderline`:
   `mspp_parententitypermission@odata.bind` → the order permission, and
   `mspp_parentrelationship` = the order→orderline relationship schema name. The child **inherits**
   access through the parent, so you don't re-declare Contact scoping on the child.

Also mind append/appendto: creating a child that references its parent needs `append` on the
child permission and `appendto` on the parent permission.

## How this interacts with the Web API

The portal **Web API** (`/_api/...`) enforces exactly these table permissions and web-role
bindings — it is not a separate access system. If `pp-webapi` calls return 403 or empty,
the fix is here: the calling user's web role needs a bound permission with the right scope and
flag (read for GET, create for POST, write for PATCH, delete for DELETE). The `Webapi/<table>/*`
**site settings** only expose the table to the API surface; they do **not** grant access — the
permission does. (Web roles themselves are managed separately; see `create-webroles` / `setup-auth`
if present.)

## Bundled helper

`scripts/grant_table_permission.py` does Steps 1–2 idempotently and Step 3 on demand. Auth
follows the shared pattern (workspace `scripts/auth.py` `get_token()`, else `DATAVERSE_TOKEN`).

```
# Global read, public — bind two roles
python scripts/grant_table_permission.py --url <ORGURL> --site <SITEID> \
  --name "Announcements - Public" --table cr123_announcement \
  --scope global --privileges read \
  --web-role "Anonymous Users" --web-role "Authenticated Users"

# Contact-scope self-service create+read
python scripts/grant_table_permission.py --url <ORGURL> --site <SITEID> \
  --name "Access Request - Self" --table cr123_accessrequest \
  --scope contact --contact-relationship cr123_contact_accessrequest \
  --privileges read,create --web-role "Authenticated Users"

# Verify bindings via the intersect (the reliable read)
python scripts/grant_table_permission.py --url <ORGURL> --site <SITEID> \
  --name "Access Request - Self" --verify

# Preview only
python scripts/grant_table_permission.py ... --dry-run
```

`--web-role` accepts a GUID or a display name (resolved per-site) and repeats. `--scope`
contact/account/parent require the matching relationship args. `--verify` lists the permission's
web-role bindings by querying `mspp_entitypermission_webroleset` — never an `$expand`.

## Field & option reference

- Tables: `mspp_entitypermission`, `mspp_webrole`, `mspp_website`; M:N intersect
  `mspp_entitypermission_webrole` (relationship/nav name), **EntitySetName**
  `mspp_entitypermission_webroleset` (query collection).
- Key `mspp_entitypermission` columns: `mspp_name`, `mspp_entitylogicalname`, `mspp_scope`,
  `mspp_read`/`mspp_write`/`mspp_create`/`mspp_delete`/`mspp_append`/`mspp_appendto`,
  `mspp_contactrelationship`, `mspp_accountrelationship`, `mspp_parententitypermission`,
  `mspp_parentrelationship`, `mspp_websiteid`.
- `mspp_scope` values: Global `756150000`, Contact `756150001`, Account `756150002`,
  Parent `756150003`, Self `756150004`.
- Always scope by **website** (`_mspp_websiteid_value`) — a tenant can host several sites, each
  with its own roles and permissions.
- Quirks to remember: (1) a permission does nothing until **bound to a web role**; (2) **verify
  bindings via the intersect collection, never an `$expand`** — the expand reads blind under an
  app-only SP; (3) the intersect EntitySetName ends in **`-set`**; (4) lookups on portal forms
  need `append`/`appendto`, not just create/write; (5) related tables use **Parent**-scope child
  permissions.
