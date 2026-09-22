---
name: pp-multistepform
description: "Create, edit, and delete multistep forms (mspp_webform + mspp_webformstep + mspp_webformmetadata) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — a multi-page wizard that collects a record across several steps with conditional navigation, each step loading a Dataverse form, condition, or redirect. WHEN: add a multistep form, create a wizard, build a multi-page portal form, web form, mspp_webform, add a form step, application/registration wizard, conditional step navigation, render a multistep form with Liquid webform, collect a record across multiple pages."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Multistep forms (wizards) on a Power Pages site — create, edit, delete

Manage **multistep forms** (`mspp_webform`, its `mspp_webformstep` steps, and per-field
`mspp_webformmetadata`) on a traditional (enhanced-data-model, `mspp_*`) Power Pages site through
the Dataverse Web API. A multistep form is a **wizard** that builds up a record across several
steps with **conditional navigation** — the no-code pattern for applications, registrations, and
long intake flows.

> Read `references/traditional-site-editing-model.md` first. Structure: one **`mspp_webform`**
> (the wizard) → an ordered chain of **`mspp_webformstep`** rows (each a Load-Form / Condition /
> Redirect step) → optional **`mspp_webformmetadata`** per-field overrides on a step. The wizard
> is then **placed on a page** (below). Compare with `pp-basicform` (a single-record, single-page
> form) — use a multistep form only when you genuinely need multiple steps.

## The model

| Record | Holds |
|---|---|
| **`mspp_webform`** | `mspp_name`, the **start step** (`mspp_startstep` → first `mspp_webformstep`), auth/session settings, and site (`_mspp_websiteid_value`). |
| **`mspp_webformstep`** | `mspp_name`, its webform (`_mspp_webform_value`), **type** (Load Form / Condition / Load Tab / Redirect), the target table + Dataverse form for a Load-Form step, and the **next step** (`mspp_nextstep`) / condition. |
| **`mspp_webformmetadata`** | Per-field overrides on a Load-Form step (label, required, control) — like `pp-basicform`'s metadata. |

## Step 1 — Model on an existing wizard

```
GET /api/data/v9.2/mspp_webforms?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,_mspp_startstep_value,mspp_webformid
GET /api/data/v9.2/mspp_webformsteps?$filter=_mspp_webform_value eq <WEBFORMID>
    &$select=mspp_name,mspp_type,mspp_entityname,mspp_formname,_mspp_nextstep_value
    &$orderby=mspp_name
```

Copy the **type** option values and the target table/form names from a working wizard before you
build one.

## Step 2 — Create the webform (the wizard shell)

```jsonc
POST /api/data/v9.2/mspp_webforms
{
  "mspp_name": "Membership Application",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

## Step 3 — Create the steps, then chain them

Create each step, then set `mspp_startstep` on the webform and `mspp_nextstep` on each step to
form the order. A **Load Form** step renders a Dataverse form for a table:

```jsonc
POST /api/data/v9.2/mspp_webformsteps
{
  "mspp_name": "Step 1 - Applicant",
  "mspp_type": <Load Form option>,
  "mspp_entityname": "contact",
  "mspp_formname": "Web Applicant",
  "mspp_webform@odata.bind": "/mspp_webforms(<WEBFORMID>)"
}
```

Then wire the chain (single-valued-nav `$ref` PUTs):

```
PUT /api/data/v9.2/mspp_webforms(<WEBFORMID>)/mspp_startstep/$ref   { "@odata.id": ".../mspp_webformsteps(<STEP1ID>)" }
PUT /api/data/v9.2/mspp_webformsteps(<STEP1ID>)/mspp_nextstep/$ref  { "@odata.id": ".../mspp_webformsteps(<STEP2ID>)" }
```

> ℹ️ **Confirm `mspp_type` option values** (Load Form / Condition / Load Tab / Redirect) and the
> next-step/condition column names against your environment — they mirror the legacy
> `adx_webformstep` set. Read them from Step 1 rather than guessing.

**Condition steps** branch on a value (set the condition + true/false next steps);
**Redirect steps** send the user elsewhere at the end. Keep the chain acyclic and ending in a
completion/redirect.

## Step 4 — Per-field overrides (optional)

Add `mspp_webformmetadata` rows against a Load-Form step, same idea as `pp-basicform`'s metadata
(attribute logical name + label/required/control overrides).

## Step 5 — Place the wizard on a page

```liquid
{% webform name: "Membership Application" %}
```

Or add the **Multistep Form** component to a page in the design studio. (See `pp-webpage` /
`pp-webtemplate`.)

## Step 6 — Edit / delete

```
PATCH  /api/data/v9.2/mspp_webformsteps(<STEPID>)   { "mspp_name": "Applicant details" }
DELETE /api/data/v9.2/mspp_webformsteps(<STEPID>)   // re-point neighbours' mspp_nextstep first
DELETE /api/data/v9.2/mspp_webforms(<WEBFORMID>)    // delete the whole wizard
```

Deleting a step mid-chain breaks navigation — re-point the previous step's `mspp_nextstep` first.

## Step 7 — Flush cache, then test the whole flow

Flush (`pp-cache`), load the page, and walk **every step and branch**: confirm each step saves,
conditions route correctly, and the final record lands in Dataverse. Load-Form steps that create
records need **table permissions + web roles** (`pp-tablepermission` / `pp-webrole`).

## Field & option reference

- Tables: `mspp_webform`, `mspp_webformstep`, `mspp_webformmetadata`. Scope by `_mspp_websiteid_value`.
- Chain: `mspp_webform.mspp_startstep` → `mspp_webformstep.mspp_nextstep` → … ; step type drives
  behavior. Confirm exact logical names/option values in your env.
- Writes gated by **table permissions** (`pp-tablepermission`) + **web roles** (`pp-webrole`).
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
