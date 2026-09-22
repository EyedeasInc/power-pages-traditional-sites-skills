---
name: pp-basicform
description: "Create, edit, and delete basic forms (mspp_entityform + mspp_entityformmetadata) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — a portal form bound to a Dataverse table that creates, edits, or read-only-displays a single record, using a Dataverse main form's layout, plus per-field metadata overrides (labels, required, control type, validation). WHEN: add a basic form, create a portal form, build a create/edit form on a page, add a form to submit records, entity form, mspp_entityform, make a contact/registration form, set a form to insert or edit or read-only mode, override a field label or make a field required on a portal form, render a form with Liquid entityform."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Basic forms on a Power Pages site — create, edit, delete

Manage **basic forms** (`mspp_entityform`, with per-field `mspp_entityformmetadata`) on a
traditional (enhanced-data-model, `mspp_*`) Power Pages site through the Dataverse Web API. A
basic form renders **one Dataverse record** for **create / edit / read-only** on the portal,
reusing a **Dataverse main form's** layout — the no-code way to collect or show a single record.

> Read `references/traditional-site-editing-model.md` first. A basic form has two parts: the
> **form** (`mspp_entityform`) — what table, which main form, what mode — and optional
> **metadata rows** (`mspp_entityformmetadata`) that override individual fields. It's then
> **placed on a page** (below).

## The model

| Record | Holds |
|---|---|
| **`mspp_entityform`** | `mspp_name`, target table (`mspp_entityname`), the Dataverse main form to render (`mspp_formname`), mode (Insert / Edit / ReadOnly), success behavior (redirect/message), captcha, and site (`_mspp_websiteid_value`). |
| **`mspp_entityformmetadata`** | One row per overridden field: which attribute, and overrides — label, required, control type, validation, default. Linked back via `_mspp_entityform_value`. |

## Step 1 — Model on an existing form (copy the shape)

```
GET /api/data/v9.2/mspp_entityforms?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_entityname,mspp_formname,mspp_mode,mspp_entityformid
```

Confirm the exact **table logical name** (`mspp_entityname`, e.g. `contact`) and the **main form
name** (`mspp_formname`) exist in Dataverse before you bind them — a typo renders an empty form.

## Step 2 — Create the basic form

```jsonc
POST /api/data/v9.2/mspp_entityforms
{
  "mspp_name": "Contact Us",
  "mspp_entityname": "contact",              // Dataverse table logical name
  "mspp_formname": "Web Contact",            // an existing MAIN form on that table
  "mspp_mode": <Insert|Edit|ReadOnly option>,// Insert = create a new record
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

> ℹ️ **Confirm option values** for `mspp_mode` (Insert / Edit / ReadOnly) and any target/success
> option sets against your environment — they mirror the legacy `adx_entityform` set. Copy them
> from the Step 1 read rather than guessing the integers.

For **Edit / ReadOnly** forms, the form needs a record to load — configure the record source
(query-string primary key or the current portal user) per the target-record settings on the form.

## Step 3 — Override fields (optional metadata)

Add a metadata row per field you want to change (label, required, control):

```jsonc
POST /api/data/v9.2/mspp_entityformmetadatas
{
  "mspp_attributelogicalname": "emailaddress1",
  "mspp_label": "Your email",
  "mspp_fieldisrequired": true,
  "mspp_entityform@odata.bind": "/mspp_entityforms(<ENTITYFORMID>)"
}
```

Only add rows for fields you're actually changing; unlisted fields render as the main form
defines them. (Confirm the metadata column names against your env.)

## Step 4 — Place the form on a page

A basic form does nothing until a page renders it. Two ways:

- **Liquid** in the page's `mspp_copy` or a web template (`pp-webpage` / `pp-webtemplate`):

  ```liquid
  {% entityform name: "Contact Us" %}
  ```

- **Design studio**: add the **Form** component to a page and pick this basic form. (Via API
  the reference is set on the web page / a content row; the Liquid tag is the portable way.)

## Step 5 — Edit / delete

```
PATCH  /api/data/v9.2/mspp_entityforms(<ID>)   { "mspp_name": "Contact form" }
DELETE /api/data/v9.2/mspp_entityformmetadatas(<METAID>)   // drop one field override
DELETE /api/data/v9.2/mspp_entityforms(<ID>)               // delete the form
```

Before deleting a form, grep templates/pages for `entityform name: "<name>"` — a page rendering
a deleted form errors.

## Step 6 — Flush cache, then test end-to-end

Flush (`pp-cache`), load the page, and **submit**: confirm the record is created/updated in
Dataverse, the success behavior fires, and validation works. An Insert form also needs **table
permissions + a web role** (`pp-tablepermission` / `pp-webrole`) granting Create on the table —
without them the submit fails with a permission error.

## Field & option reference

- Tables: `mspp_entityform`, `mspp_entityformmetadata`. Scope by `_mspp_websiteid_value`.
- Key `mspp_entityform` columns: `mspp_name`, `mspp_entityname`, `mspp_formname`, `mspp_mode`,
  success/redirect + captcha settings. Confirm exact logical names/option values in your env.
- A form's writes are still gated by **table permissions** (`pp-tablepermission`) + **web roles**
  (`pp-webrole`); over-exposed forms are a `pp-securityreview` finding.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
