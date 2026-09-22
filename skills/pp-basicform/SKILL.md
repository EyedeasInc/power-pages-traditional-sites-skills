---
name: pp-basicform
description: "Create, edit, and delete basic forms (mspp_entityform + mspp_entityformmetadata) on a traditional (enhanced-data-model, mspp_*) Power Pages site through the Dataverse Web API — a portal form bound to a Dataverse table that inserts, edits, or read-only-displays a single record from a Dataverse main form, with the full configuration surface: record source, form options (captcha, validation, tabs-as-steps), on-success (message/redirect), Additional Settings (associate portal user, file upload / Attach File, associated table reference, record actions), per-field metadata (control styles, prepopulate, set-value-on-save, validation, notes/timeline), custom JavaScript, and AI form-fill. WHEN: add a basic form, create/edit a portal form, insert/edit/read-only form, file upload on a form, attach file, form captcha, redirect on submit, prefill a field, required field, custom validation, add a delete/workflow action to a form, entityform, mspp_entityform, AI form fill, render a form with Liquid entityform."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.2.0"
---

# Basic forms on a Power Pages site — full configuration

Manage **basic forms** (`mspp_entityform`, with per-field `mspp_entityformmetadata` and related
config) on a traditional (enhanced-data-model, `mspp_*`) Power Pages site through the Dataverse
Web API. A basic form renders **one Dataverse record** for **Insert / Edit / ReadOnly** on the
portal, reusing a **Dataverse main form's** layout — the no-code way to collect or show a record.

> Read `references/traditional-site-editing-model.md` first. The full surface is: the **form**
> (`mspp_entityform`) → **Form Options / On Success / Additional Settings** (columns + related
> config on the form) → **metadata rows** (`mspp_entityformmetadata`, per field/section/tab/notes)
> → **Custom JavaScript** → placed on a page. Most settings below are **columns on
> `mspp_entityform`** (or related rows); their exact logical names mirror the legacy
> `adx_entityform*` set — **read an existing form's columns first** and copy names/option values
> rather than guessing.

## Step 1 — Create the form (table, form, mode, record source)

```jsonc
POST /api/data/v9.2/mspp_entityforms
{
  "mspp_name": "Contact Us",
  "mspp_entityname": "contact",       // target table logical name
  "mspp_formname": "Web Contact",     // an existing MAIN form on that table
  "mspp_mode": <Insert|Edit|ReadOnly>,
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

- **Mode** — *Insert* creates a new record; *Edit* / *ReadOnly* need an existing record, selected
  via **Record Source Type**: `Query String` (with **Record ID Parameter Name**, default `id`),
  `Current Portal User`, or `Record Associated to Current Portal User` (needs **Relationship
  Name**; optional **Allow Create If Null**).
- **Tab Name** renders only one tab of the form.

## Step 2 — Form Options

Columns on the form controlling render/validation behavior:

| Setting | Effect |
|---|---|
| Add Captcha / Show Captcha for Authenticated users | CAPTCHA on the form. |
| Auto Generate Steps From Tabs | Render each form **tab as a sequential step** (submit on the last). |
| Set Recommended Fields as Required / Make All Fields Required | Bulk-require fields. |
| ToolTips Enabled | Use the attribute description as a tooltip (accessibility). |
| Render Web Resources Inline | Drop the iframe around web resources. |
| Validation Group / Validation Summary CSS Class / Enable Validation Summary Links / …Link Text / …Header Text | Validation summary styling + behavior. |
| Instructions / Record Not Found Message / Show Unsupported Fields | Copy + display toggles. |

## Step 3 — On Success (after submit)

`On Success` = **Display Success Message** (with *Success Message* + *Hide Form on Success*) **or
Redirect**. Redirect adds: *External URL* **or** *Web Page*, plus append options — *Append
Existing Query String*, *Append Record ID To Query String* (+ *Record ID Parameter Name*),
*Append Custom Query String*, and *Append Attribute Value to Query String* (parameter name +
attribute logical name).

## Step 4 — Additional Settings (Advanced Settings reveals more)

**Associate portal user:** *Associate Current Portal User* + *Portal User Lookup Column*
(+ *Is Activity Party*) stamps the signed-in user onto the record.

**File upload — Attach File** (a file control at the bottom of the form):

| Setting | Notes |
|---|---|
| Attach File | Turn on the upload control. |
| Attach File Storage Location | `Note Attachment` or `Azure Blob Storage` (Azure requires storage configured). |
| Allow Multiple Files | Multiple uploads. |
| Accept | MIME types (e.g. `image/*,application/pdf`). |
| Restrict Files to Accepted Types (+ File Type Error Message) | Enforce `Accept` (else it's only a hint). |
| Maximum File Size (in kilobytes) (+ File Size Error Message) | Size cap. |
| Attach File Required (+ Required Error Message) | Make attachment mandatory. |
| Label | Control label. |

> **File upload needs permissions**, not `Enable Table Permissions` on the form (deprecated):
> the **annotation** table needs **Create + Append**, the parent table the matching **AppendTo**
> (and Create/Read/Write for the record itself). To also *view* uploaded files, add the
> **timeline** control and configure a `Notes`/`Timeline` metadata row (Step 6). See `pp-webrole`
> / `pp-tablepermission`.

**Associated Table Reference** (relate the saved record to another): *Set Table Reference On
Save*, *Relationship Name*, *Table Logical Name*, *Target Lookup Attribute Logical Name*,
*Source Type* (Query String / Current Portal User / a previous step), plus the query-string keys.

**Record actions** (Advanced Settings) — buttons on Edit/ReadOnly forms, each gated by table
permissions: **Delete, Workflow, Create Related Record, Activate, Deactivate**, plus per-table
specials (e.g. Resolve/Cancel Case on `incident`, Win/Lose on `opportunity`). Prefer a
**Workflow** over Activate/Deactivate for OOB tables with defined state/status transitions.

## Step 5 — Per-field metadata (`mspp_entityformmetadata`)

Add one metadata row per element you override. **Type** = `Attribute` / `Section` / `Tab` /
`Subgrid` / `Notes` / `Timeline`.

```jsonc
POST /api/data/v9.2/mspp_entityformmetadatas
{
  "mspp_type": <Attribute>,
  "mspp_attributelogicalname": "emailaddress1",
  "mspp_label": "Your email",
  "mspp_entityform@odata.bind": "/mspp_entityforms(<ENTITYFORMID>)"
}
```

For **Attribute** rows the surface is rich (mirror of multistep metadata):
- **Control style:** radio-button option sets (vertical/horizontal), *Render Lookup as Dropdown*,
  *Code component* (PCF), constant-sum / rank-order / multiple-choice / matrix controls (need a
  *Group Name*), *Randomize Option Set Values*, *CSS Class*. **Choice columns don't appear in the
  picker — type the logical name into `Attribute Logical Name`.**
- **Prepopulate field:** *Ignore Default Value*; set a default from `Value` / `Today's Date` /
  `Current User's Contact` (+ *From Attribute*).
- **Set Value On Save:** force a value on save (`Value` / Today's Date / Current User's Contact) —
  Two-Option = `true/false`, Option Set = integer, Lookup = GUID.
- **Validation:** *Field is Required*, *Regular Expression* (+ messages), range/geolocation/etc.
  error-message overrides.
- **Description & instructions:** custom text Above/Below the field or Above the label.

`Section` / `Tab` rows just relabel a section/tab. `Notes` / `Timeline` configure attachments
(Step 6). `Subgrid` configures an embedded child grid.

## Step 6 — Notes / Timeline (viewing & managing attachments)

To let users **view/add/edit/delete** attachments (not just upload), add a `Notes` (or
`Timeline`) metadata row: *Create/Edit/Delete Enabled* + dialog options, *File Attachment
Location* (Note attachment / Azure Blob), *Accept MIME Type(s)*, *Restrict MIME Types*, *Maximum
File Size (KB)*, list ordering, labels. Requires the **timeline** control on the Dataverse form,
the annotation **child table permission** (Read/Create/Append/Write/Delete per action), and each
web-visible note's description prefixed `*WEB*` (auto-added for notes created via the portal; the
prefix is set by `KnowledgeManagement/NotesFilter`). A rich-text editor is enabled with the
`Timeline/RTEEnabled` site setting.

## Step 7 — Custom JavaScript

The form has a **Custom JavaScript** column, injected just before the closing `</form>`. Field
input IDs = the attribute logical name, so jQuery is the tool:

```javascript
$(document).ready(function () { $("#address1_stateorprovince").val("Saskatchewan"); });
```

Add custom validators by pushing onto `Page_Validators`, or wrap **`entityFormClientValidate`**
(runs on Next/Submit; return `false` to block submit). Note: adding option-set values in JS
triggers an "Invalid postback" error; client-side validation isn't supported inside a subgrid.

## Step 8 — AI form fill (preview)

**Intelligent forms** let visitors extract field values from an uploaded attachment/email and
auto-fill, plus AI draft assistance for multi-line text. Enabled in the **design studio**
(Edit form → *Enable AI form fill assistance*), governed centrally (see the admin *copilot
governance* controls). It's a rendering feature layered on the form — not an `mspp_entityform`
column you set via the API.

## Step 9 — Place on a page & secure

```liquid
{% entityform name: "Contact Us" %}
```

Or add the **Form** component to a page in the design studio. An **Insert** form needs **table
permissions + a web role** granting Create on the target table (`pp-tablepermission` /
`pp-webrole`); without them the submit fails. Don't rely on the deprecated *Enable Table
Permissions* form flag — use real table permissions.

## Step 10 — Flush cache & test end-to-end

Flush (`pp-cache`), load the page, and **submit**: confirm the record writes, success/redirect
fires, validation and file upload work, and actions respect permissions.

## Field & option reference

- Tables: `mspp_entityform`, `mspp_entityformmetadata` (+ notes on `annotation`). Scope by
  `_mspp_websiteid_value`. Confirm exact logical names/option values against your env.
- Considerations: no connection-table subgrids, duplicate/party-list fields, or business rules in
  basic forms; request validation blocks raw HTML input (`Site/DisableFormDataSafeHtmlValidation`).
- Writes gated by table permissions (`pp-tablepermission`) + web roles (`pp-webrole`);
  over-exposed forms are a `pp-securityreview` finding.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
