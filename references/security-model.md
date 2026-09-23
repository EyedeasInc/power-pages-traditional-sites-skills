# Power Pages security model (deny-by-default)

Shared reference for the traditional-site (enhanced-data-model) authorization model. Used by
`pp-securityreview`, `pp-tablepermission`, `pp-columnpermission`, `pp-webrole`, `pp-pageaccessrule`,
`pp-webapi`, and the `security-auditor` agent.

> **Authority:** Microsoft Learn + Microsoft's official Power Pages plugin security model. Community
> notes labelled. **Sources:** [Table permissions](https://learn.microsoft.com/en-us/power-pages/security/table-permissions) ·
> [Create web roles](https://learn.microsoft.com/en-us/power-pages/security/create-web-roles) ·
> [Web API overview §security](https://learn.microsoft.com/en-us/power-pages/configure/web-api-overview) ·
> [Important changes & deprecations](https://learn.microsoft.com/en-us/power-pages/important-changes-deprecations).

## The one rule: deny by default

Nothing — a page, a list, a form, a Liquid FetchXML query, or a Web API call — reaches a Dataverse
table unless a **table permission**, assigned to one of the current visitor's **web roles**, grants
it. Unconfigured means unreachable (or, on legacy sites, accidentally public — see the audit below).

## Web roles

- **Anonymous Users** — applied automatically to signed-out visitors. Exactly one per site
  (`mspp_anonymoususersrole = true`).
- **Authenticated Users** — applied to every signed-in user. Exactly one per site
  (`mspp_authenticatedusersrole = true`).
- **Custom roles** — the ones you create; assigned to contacts.

A signed-in user receives the **union** of Authenticated Users + every custom role on their contact.
**Nothing subtracts — the widest grant wins.**

> ⚠️ **The "Authenticated Users role" flag trap.** Setting `mspp_authenticatedusersrole = true` on a
> *custom* role silently grants that role's permissions to **every signed-in user**. Keep exactly one
> role carrying each special flag; custom roles must have both flags `false`. *(Nick Doelman)*

## Table permissions = scope + privileges, bound to roles

A table permission grants CRUD privileges on a table at a **scope**, and does nothing until it is
bound to a web role (the `mspp_entitypermission_webrole` intersect).

| Scope | Value | Use |
|---|---|---|
| **Global** | 756150000 | **Avoid.** All records. Only for truly public, read-only reference data. |
| **Contact** | 756150001 | Safest default — the signed-in user's own records. |
| **Account** | 756150002 | The user's parent account's records. |
| **Parent** | 756150003 | Records related through a defined parent relationship. |
| **Self** | 756150004 | The user's own contact record. |

> ⚠️ **Corrected nuance — Global is not automatically anonymous-reachable.** Global controls *which
> records* (all of them). Whether anonymous visitors can reach them depends on **web-role
> assignment**: a Global permission is anonymous-reachable **only if it is bound to the Anonymous
> Users role**. So the real risk is **Global + Anonymous Users role**. *(Refines a common shorthand;
> the underlying mechanism is scope **and** role binding.)*

**Verify bindings via the intersect directly.** An `$expand` from a permission or role reads *blind*
under an app-only service principal and can make an over-broad grant look empty. Query
`mspp_entitypermission_webroleset` directly.

## Web API and column security

- The Web API is **two-gated**: the `Webapi/<table>/*` site settings **and** a table permission must
  both allow the operation (GET→Read, POST→Create, PATCH→Write, DELETE→Delete). See
  `references/webapi-field-configuration.md`.
- **Column permissions** (`pp-columnpermission`) add field-level restrictions on top of table
  permissions. *(Note: Microsoft's official plugin covers table-level CRUD + scope only, not
  column-level security — this plugin's `pp-columnpermission` fills that gap.)*

## Forms & lists: the legacy flag is going away

From **June 2026**, forms and lists enforce table permissions **regardless of the "Enable Table
Permissions" flag** (already enforced on sites created since release 9.3.7.x). Treat the flag as
legacy — configure real table permissions + web roles for every form and list. Lists that use
**OData feeds** also require table permissions (and OData feeds themselves are removed by June 2026 —
use the Web API).

To allow anonymous access, do it **explicitly** with a table permission bound to the Anonymous Users
role — not by leaving the old flag off. Power Pages sites are **private by default**.

## Page-level authorization

Web page access control rules (`pp-pageaccessrule`) gate *pages* by web role — separate from, and
additive to, table permissions (which gate *data*).

## Security headers / CSP

Newer environments enforce a **stricter Content-Security-Policy** (blocking `unsafe-eval` /
`unsafe-inline`); custom scripts that relied on the old policy can break. Configure site headers via
`references/site-settings-catalog.md` (`pp-headers`). *(Michel Mendes)*

## Audit checklist (what a review looks for)

Modelled on Microsoft's `audit-permissions` checks:

1. Tables reached by code/pages/lists/forms with **no** covering permission (broken or leaking).
2. Permissions with **no web-role binding** (dead) or bound to unexpected roles.
3. **Over-broad scope** — Global (especially with Write/Delete), or Global bound to Anonymous.
4. CRUD privileges that exceed what the code actually does.
5. `Append` / `AppendTo` present where lookups/relationships require them.
6. Parent-scope chains that are incomplete (missing the parent permission).
7. `$expand` coverage — every table in a Web API result needs its own permission.
8. Web API `fields` still using `*`, or exposing sensitive columns.
9. Sensitive pages/tables reachable by the **Anonymous Users** role.
10. Missing/weak security headers and CSP.

## Legacy-site exposure audit

Portals created before mandatory permissions may have lists/forms/`_odata`/`_api` feeds with **no**
table permissions — historically internet-public. Enumerate them and treat any unconfigured surface
as public until a permission is added. *(Nick Doelman — "did you remember to lock the door?")*
