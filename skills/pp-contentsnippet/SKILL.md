---
name: pp-contentsnippet
description: "Create, edit, and delete content snippets (mspp_contentsnippet) on a traditional (enhanced-data-model, mspp_*) Power Pages site — the named, reusable, localizable text/HTML blocks that templates and pages pull in via Liquid ({{ snippets[\"Name\"] }} / {% editable snippets %}) — through the Dataverse Web API. WHEN: add a content snippet, edit portal text, change a reusable text block, update the homepage hero copy, create an HTML snippet, localize a snippet, edit mspp_contentsnippet, change footer/banner text without touching a template, manage editable content blocks."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Content snippets on a Power Pages site — create, edit, delete

Manage **content snippets** (`mspp_contentsnippet`) on a traditional (enhanced-data-model,
`mspp_*`) Power Pages site through the Dataverse Web API. A snippet is a **named, reusable,
localizable** block of text or HTML that templates and pages pull in with Liquid — so editors
change copy (hero text, banners, footers, CTAs) **without touching a web template**.

> Read `references/traditional-site-editing-model.md` first. A snippet's value is edited on the
> `mspp_contentsnippet` record directly (not inside a `powerpagecomponent` JSON payload), then
> the cache is flushed.

## The model

A content snippet is one `mspp_contentsnippet` row per **name + language**:

| Column | Holds |
|---|---|
| `mspp_name` | The snippet key referenced in Liquid (e.g. `Home/Hero/Heading`). Slash-namespacing is conventional. |
| `mspp_value` | The text or HTML rendered. |
| `mspp_contentsnippetlanguageid` | The language (localized variants share the `mspp_name`). |
| `_mspp_websiteid_value` | The site it belongs to. |
| `mspp_type` | Text vs HTML (option set). |

**How it's consumed in Liquid** (already in a web template / page — for reference):

```liquid
{{ snippets["Home/Hero/Heading"] }}                     {# render #}
{% editable snippets "Home/Hero/Heading" type: 'html' %} {# render + inline-editable for editors #}
```

## Step 1 — Find the snippet (by name + site)

```
GET /api/data/v9.2/mspp_contentsnippets
    ?$filter=_mspp_websiteid_value eq <SITEID> and mspp_name eq 'Home/Hero/Heading'
    &$select=mspp_name,mspp_value,_mspp_contentsnippetlanguageid_value,mspp_contentsnippetid
```

A localized site has **one row per language** for the same `mspp_name` — match the language you
intend to edit.

## Step 2 — Create a snippet

Resolve the site's language first (`mspp_websitelanguages`), then:

```jsonc
POST /api/data/v9.2/mspp_contentsnippets
{
  "mspp_name": "Home/Hero/Heading",
  "mspp_value": "<h1>AI-first Power Pages</h1>",
  "mspp_websiteid@odata.bind":                 "/mspp_websites(<SITEID>)",
  "mspp_contentsnippetlanguageid@odata.bind":  "/mspp_websitelanguages(<LANGID>)"
}
```

## Step 3 — Edit a snippet's value

```
PATCH /api/data/v9.2/mspp_contentsnippets(<SNIPPETID>)   { "mspp_value": "<h1>New heading</h1>" }
```

Editing a snippet is the safe way to change on-page copy that lives in a snippet — no template
edit, no code review. If the text is currently **hard-coded in a web template** instead, moving
it into a snippet (create snippet + replace the literal with `{{ snippets[...] }}` via
`pp-webtemplate`) makes it editor-manageable.

## Step 4 — Delete

```
DELETE /api/data/v9.2/mspp_contentsnippets(<SNIPPETID>)
```

Before deleting, grep the site's templates/pages for `snippets["<name>"]` — a snippet still
referenced in Liquid renders empty once deleted (and `{% editable %}` may error).

## Step 5 — Flush cache & verify

Snippets are cached — flush (`pp-cache`), then load a page that renders the snippet and confirm
the new value shows (and, for HTML snippets, renders correctly).

## Security note (HTML snippets)

An **HTML** snippet's `mspp_value` is rendered **raw**. Anyone who can edit the snippet can
inject markup/script that runs for every visitor. Treat snippet-edit rights as content-injection
rights: restrict who can edit them, and don't build an HTML snippet from untrusted input. This is
part of the XSS surface `pp-securityreview` checks.

## Field & option reference

- Table: `mspp_contentsnippet`; entity set `mspp_contentsnippets`. Key columns: `mspp_name`,
  `mspp_value`, `mspp_type`, `mspp_contentsnippetlanguageid`, `mspp_websiteid`.
- One row per **name + language**; scope every query by `_mspp_websiteid_value`.
- Naming convention: slash-namespaced keys (`Area/Section/Element`) keep snippets organized.
- Auth: Dataverse MCP or a Web API bearer token (`DATAVERSE_TOKEN`), per the shared backbone.
