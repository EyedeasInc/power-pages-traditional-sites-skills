---
name: pp-webrole
description: "Create, edit, and delete web roles (mspp_webrole) on a traditional (enhanced-data-model, mspp_*) Power Pages site — the access groups that table permissions, web page access rules, and cloud-flow/Web API access bind to. Covers the two special auto-managed roles (Anonymous Users, Authenticated Users — exactly one each) and custom roles, plus assigning a role to a contact. WHEN: create a web role, add a portal role, set up user roles, manage mspp_webrole, make a members-only or admin role, assign a contact to a web role, why is my table permission not applying (no role bound), anonymous vs authenticated role, delete a web role."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Web roles on a Power Pages site — create, assign, manage

Manage **web roles** (`mspp_webrole`) on a traditional (enhanced-data-model, `mspp_*`) Power
Pages site through the Dataverse Web API. A web role is the **access group** that everything
else binds to — table permissions (`pp-tablepermission`), web page access control rules,
cloud-flow access, Web API reads. Without a role, a permission grants nothing.

> Read `references/traditional-site-editing-model.md` first. This skill creates and manages the
> roles; **binding** a role to a table permission is `pp-tablepermission` (the
> `mspp_entitypermission_webrole` intersect).

## The model: three kinds of role

| Role | Flag | Notes |
|---|---|---|
| **Anonymous Users** | `mspp_anonymoususersrole = true` | Applies to signed-**out** visitors. **Exactly one** per site, auto-created — never create a second. |
| **Authenticated Users** | `mspp_authenticatedusersrole = true` | Applies to every signed-**in** user. **Exactly one** per site, auto-created. |
| **Custom role** | both flags `false` | The ones you make: "Members", "Managers", "Partner", etc. A signed-in user gets Authenticated Users **plus** every custom role assigned to their contact. |

> ⚠️ **The one-each rule.** There must be exactly one Anonymous and one Authenticated role per
> site — the platform relies on it. Reuse the existing ones; only ever create **custom** roles.

## Step 1 — List existing roles (scope by site)

```
GET /api/data/v9.2/mspp_webroles?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_anonymoususersrole,mspp_authenticatedusersrole,mspp_webroleid
```

Confirm the Anonymous/Authenticated roles already exist (they will) before adding anything.

## Step 2 — Create a custom role

```jsonc
POST /api/data/v9.2/mspp_webroles
{
  "mspp_name": "Members",
  "mspp_description": "Signed-in members with access to member content",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)",
  "mspp_anonymoususersrole": false,
  "mspp_authenticatedusersrole": false
}
```

Leave both special flags `false` — a custom role must not claim to be the anonymous or
authenticated role.

## Step 3 — Assign a role to a contact

A custom role does nothing until it's on a **contact**. The link is the
`mspp_contact_webrole` (contact ↔ web role) many-to-many. Associate a contact:

```
POST /api/data/v9.2/mspp_webroles(<ROLEID>)/mspp_contact_webrole/$ref
{ "@odata.id": "https://<org>/api/data/v9.2/contacts(<CONTACTID>)" }
```

(Anonymous/Authenticated are applied automatically by sign-in state and are **not** assigned to
contacts.) To list a role's members, read the same relationship; to remove one, `DELETE` the
`$ref`.

## Step 4 — Edit / delete

```
PATCH  /api/data/v9.2/mspp_webroles(<ROLEID>)   { "mspp_name": "Gold Members" }
DELETE /api/data/v9.2/mspp_webroles(<ROLEID>)
```

> Before deleting a role, check nothing depends on it — table permissions bound via the
> `mspp_entitypermission_webrole` intersect, and web page access control rules. Deleting a bound
> role silently drops the access it granted. Never delete the Anonymous or Authenticated role.

## Step 5 — Flush cache & verify

Role and binding changes are cached. Flush (`pp-cache`), then test **as that user**: sign in as
a contact with the role and confirm the gated pages/data are reachable; sign out and confirm
they are not.

## Field & option reference

- Table: `mspp_webrole`; entity set `mspp_webroles`. Key columns: `mspp_name`,
  `mspp_description`, `mspp_anonymoususersrole`, `mspp_authenticatedusersrole`, `mspp_websiteid`.
- Relationships: `mspp_contact_webrole` (members), `mspp_entitypermission_webrole` (table
  permissions — see `pp-tablepermission`).
- Scope every query by `_mspp_websiteid_value`.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
- Related security review: over-broad bindings and Anonymous-role leaks are checks in
  `pp-securityreview`.
