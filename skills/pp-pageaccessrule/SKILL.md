---
name: pp-pageaccessrule
description: "Create, edit, and delete web page access control rules (mspp_webpageaccesscontrolrule) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — page-level authorization that grants or restricts access to a web page (and its child pages) for specific web roles, independent of table permissions. WHEN: restrict a page to a web role, make a page members-only, page-level security, mspp_webpageaccesscontrolrule, grant change/edit rights on a page, hide a page from anonymous users, control who can see a page, page access control rule, bind a page rule to a role."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Web page access control rules — create, edit, delete

Manage **web page access control rules** (`mspp_webpageaccesscontrolrule`) on a traditional
(enhanced-data-model, `mspp_*`) Power Pages site through the Dataverse Web API. A page access rule
is **page-level authorization** — it grants or restricts access to a web page (and, by scope, its
descendants) for specific **web roles**. This is distinct from table permissions
(`pp-tablepermission`), which gate *data*; this gates *pages*.

> Read `references/traditional-site-editing-model.md` first. A rule targets a **root** web page,
> declares a **right** (restrict read / grant change) and a **scope**, and is **bound to web
> roles** via an intersect. `pp-securityreview` check #4 (anonymous access) inspects exactly
> these rules; `pp-webrole` creates the roles they bind.

## The model

| Column | Holds |
|---|---|
| `mspp_name` | Rule name. |
| `mspp_webpageid` | Lookup → the **root** `mspp_webpage` the rule protects. |
| `mspp_right` | **Restrict Read** (only bound roles may view) or **Grant Change** (bound roles may edit). |
| `mspp_scope` | How far it reaches — the page only, or the page **and** its descendants (option values vary by version). |
| `_mspp_websiteid_value` | Site. |
| **binding** | `mspp_webpageaccesscontrolrule_webrole` intersect → the web roles the rule applies to. |

> ℹ️ **Confirm option values** for `mspp_right` and `mspp_scope` against your environment (they
> mirror legacy `adx_webpageaccesscontrolrule`). Read an existing rule first and copy them.

## Step 1 — List existing rules (scope by site)

```
GET /api/data/v9.2/mspp_webpageaccesscontrolrules?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_right,mspp_scope,_mspp_webpageid_value,mspp_webpageaccesscontrolruleid
```

## Step 2 — Create a rule

Point it at the **root** page and set the right/scope:

```jsonc
POST /api/data/v9.2/mspp_webpageaccesscontrolrules
{
  "mspp_name": "Members area — restrict read",
  "mspp_right":  <Restrict Read option>,
  "mspp_scope":  <page + descendants option>,
  "mspp_webpageid@odata.bind":  "/mspp_webpages(<ROOT_WEBPAGEID>)",
  "mspp_websiteid@odata.bind":  "/mspp_websites(<SITEID>)"
}
```

## Step 3 — Bind the web role(s)

A **Restrict Read** rule does nothing until you bind the roles allowed to view. Associate via the
intersect:

```
POST /api/data/v9.2/mspp_webpageaccesscontrolrules(<RULEID>)/mspp_webpageaccesscontrolrule_webrole/$ref
{ "@odata.id": "https://<org>/api/data/v9.2/mspp_webroles(<ROLEID>)" }
```

> **Verify bindings by reading the intersect directly** (an `$expand` reads blind under an
> app-only service principal — same gotcha as table permissions):
> `GET .../mspp_webpageaccesscontrolrule_webroleset?$filter=...`. Bind to a **custom** or
> **Authenticated Users** role to make a page members-only; leaving Anonymous able to read a
> sensitive page is a `pp-securityreview` finding.

## Step 4 — Edit / unbind / delete

```
PATCH  /api/data/v9.2/mspp_webpageaccesscontrolrules(<RULEID>)   { "mspp_name": "Members only" }
DELETE /api/data/v9.2/mspp_webpageaccesscontrolrules(<RULEID>)/mspp_webpageaccesscontrolrule_webrole(<ROLEID>)/$ref
DELETE /api/data/v9.2/mspp_webpageaccesscontrolrules(<RULEID>)
```

## Step 5 — Flush cache, then test as each user

Flush (`pp-cache`), then verify **both directions**: sign in as a bound-role user and confirm the
page loads; sign out (or use an unbound role) and confirm it challenges/hides. Restrict-Read rules
are how you make a members area — test the negative case, not just the positive.

## Field & option reference

- Table: `mspp_webpageaccesscontrolrule`; intersect `mspp_webpageaccesscontrolrule_webrole`.
  Scope by `_mspp_websiteid_value`. Confirm `mspp_right` / `mspp_scope` option values in your env.
- Gates **pages**, not data — pair with `pp-tablepermission` (data) and `pp-webrole` (roles) for
  full access control. Reviewed by `pp-securityreview`.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.

## Microsoft docs & shared references

- Page access rules gate **pages** by web role; table permissions gate **data**. Both are deny-by-default.
- Full detail: `references/security-model.md`.
