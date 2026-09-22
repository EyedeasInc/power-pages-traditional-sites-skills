---
name: pp-multistepform
description: "Create, edit, and delete multistep forms (mspp_webform + mspp_webformstep + mspp_webformmetadata) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — a multi-page wizard that builds a record across steps, with the full surface: form-level properties (auth, session persistence, edit-expiry), progress indicator, step types (Load Form / Load Tab / Condition / Redirect) and branching, per-step metadata (control styles, prepopulate, set-value-on-save, validation), notes/file attachments, custom JavaScript, and AI form-fill. WHEN: add a multistep form, create a wizard, multi-page portal form, web form, mspp_webform, add/branch a form step, conditional navigation, progress bar, edit-expiry, prefill or validate a step field, file upload in a wizard, custom validation, render with Liquid webform."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.2.0"
---

# Multistep forms (wizards) on a Power Pages site — full configuration

Manage **multistep forms** (`mspp_webform`, its `mspp_webformstep` steps, and per-field
`mspp_webformmetadata`) on a traditional (enhanced-data-model, `mspp_*`) Power Pages site through
the Dataverse Web API. A multistep form is a **wizard** that builds a record across steps with
**conditional branching** — for applications, registrations, and long intake flows.

> Read `references/traditional-site-editing-model.md` first. Structure: one **`mspp_webform`**
> (form-level properties + progress bar) → an ordered chain of **`mspp_webformstep`** rows (Load
> Form / Load Tab / Condition / Redirect) → optional **`mspp_webformmetadata`** per-field
> overrides on a step. Use a multistep form only when you truly need multiple steps — a single
> page is `pp-basicform`. Column logical names mirror legacy `adx_webform*`; **read an existing
> wizard first** and copy names/option values.

## Step 1 — Create the webform (form-level properties)

```jsonc
POST /api/data/v9.2/mspp_webforms
{
  "mspp_name": "Membership Application",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

Form-level properties (columns on `mspp_webform`):

| Property | Effect |
|---|---|
| Start Step | The first `mspp_webformstep` (set in Step 3). **Can't be a Condition step.** |
| Authentication Required | Redirect anonymous users to sign-in, then back. |
| Start New Session On Load | `No` (default) persists a session so users resume where they left off; `Yes` always restarts. |
| Multiple Records Per User Permitted | `Yes` (default) allows more than one submission per user. |
| Edit Expired State Code / Status Reason / Message | Lock a record from further editing once it reaches a given state/status (e.g. "complete"). |

## Step 2 — Progress indicator

Optional progress UI (columns on the form): **Enabled**, **Type** (`Title` / `Numeric (Step x of
n)` / `Progress Bar`), **Position** (`Top`/`Bottom`/`Left`/`Right`), **Prepend Step Number to
Step Title**.

## Step 3 — Create the steps, then chain them

**Step Type** = `Load Form` / `Load Tab` (render a Dataverse form/tab), `Condition` (branch), or
`Redirect` (send elsewhere). (`Load User Control` is retired.)

```jsonc
POST /api/data/v9.2/mspp_webformsteps
{
  "mspp_name": "Step 1 - Applicant",
  "mspp_type": <Load Form>,
  "mspp_entityname": "contact",          // Target Table Logical Name
  "mspp_formname": "Web Applicant",
  "mspp_webform@odata.bind": "/mspp_webforms(<WEBFORMID>)"
}
```

Then wire the order (single-valued-nav `$ref` PUTs):

```
PUT /api/data/v9.2/mspp_webforms(<WEBFORMID>)/mspp_startstep/$ref   { "@odata.id": ".../mspp_webformsteps(<STEP1ID>)" }
PUT /api/data/v9.2/mspp_webformsteps(<STEP1ID>)/mspp_nextstep/$ref  { "@odata.id": ".../mspp_webformsteps(<STEP2ID>)" }
```

Common step columns: **Next Step**, **Target Table Logical Name**, **Move Previous Permitted**
(default true). **Load Form** steps carry the same rich config as a basic form (record source, on
success, associated-table reference, file upload). **Condition** steps evaluate an expression and
route to true/false next steps; **Redirect** steps end the flow elsewhere. Keep the chain acyclic
ending in a terminal (no next) or Redirect step.

> **Steps can't be reused** across a form (except Condition's fail-branch / different Yes/No
> branches). When you change a form's steps, **delete the multistep-form session records** —
> stale step history mismatches the new sequence.

## Step 4 — Per-field metadata (`mspp_webformmetadata`)

Attach to a **step** (not the form). **Type** = `Attribute` / `Section` / `Tab`.

```jsonc
POST /api/data/v9.2/mspp_webformmetadatas
{
  "mspp_type": <Attribute>,
  "mspp_attributelogicalname": "birthdate",
  "mspp_webformstep@odata.bind": "/mspp_webformsteps(<STEPID>)"
}
```

`Attribute` rows offer (identical to `pp-basicform` metadata): **control style** (radio option
sets, render-lookup-as-dropdown, code component/PCF, constant-sum / rank-order / multiple-choice
/ matrix with a *Group Name*, randomize options, CSS class — **choice columns: type the logical
name**), **prepopulate** (Value / Today's Date / Current User's Contact + *Ignore Default
Value*), **set value on save** (Two-Option `true/false`, Option Set integer, Lookup GUID),
**validation** (required, regex + messages, range/geolocation errors), and **description/
instructions** (Above/Below field or Above label). `Section` / `Tab` rows relabel.

## Step 5 — Notes / file attachments

Same model as basic forms: add a `Notes` metadata row on the **step** that owns the notes, then
configure Create/Edit/Delete + storage (Note attachment / Azure Blob) + MIME/size limits.
Requires the timeline control + annotation child table permissions (see `configure-notes` model,
`pp-tablepermission`).

## Step 6 — Custom JavaScript

Each **step** has a **Custom JavaScript** column (injected before `</form>`). Field IDs =
attribute logical name; use jQuery, push to `Page_Validators`, or wrap `entityFormClientValidate`
(return `false` to block Next/Submit) — same hooks as `pp-basicform` Step 7.

## Step 7 — AI form fill (preview)

The same **Intelligent forms** AI form-fill assistance applies to multistep forms (extract from
attachments, AI draft for multi-line text), enabled in the **design studio** and governed
centrally — a rendering feature, not an `mspp_webform` column.

## Step 8 — Place on a page & test

```liquid
{% webform name: "Membership Application" %}
```

Or add the **Multistep Form** component in the design studio. Flush (`pp-cache`) and walk **every
step and branch**: each step saves, conditions route correctly, the final record lands, and the
progress indicator behaves. Load-Form steps that create records need table permissions + web
roles (`pp-tablepermission` / `pp-webrole`).

## Edit / delete

```
PATCH  /api/data/v9.2/mspp_webformsteps(<STEPID>)   { "mspp_name": "Applicant details" }
DELETE /api/data/v9.2/mspp_webformsteps(<STEPID>)   // re-point neighbours' mspp_nextstep first
DELETE /api/data/v9.2/mspp_webforms(<WEBFORMID>)    // delete the whole wizard
```

Deleting a mid-chain step breaks navigation — re-point the previous step's `mspp_nextstep` first,
and clear session records after any step change.

## Field & option reference

- Tables: `mspp_webform`, `mspp_webformstep`, `mspp_webformmetadata`. Scope by `_mspp_websiteid_value`.
  Confirm exact logical names/option values against your env.
- Chain: `mspp_webform.mspp_startstep` → `mspp_webformstep.mspp_nextstep` → … ; step type drives
  behavior. Writes gated by table permissions (`pp-tablepermission`) + web roles (`pp-webrole`).
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
