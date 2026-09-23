# Web templates as reusable components + Liquid patterns

Shared reference for building reusable web-template components and writing solid Liquid. Used by
`pp-webtemplate`, `pp-webpage`, `pp-pagetemplate`, `pp-liquid`, and the `web-template-architect` agent.

> **Authority:** Microsoft Learn for the component/manifest model; community notes labelled.
> **Sources:** [Web templates as components](https://learn.microsoft.com/en-us/power-pages/configure/web-templates-as-components) ·
> [Liquid filters](https://learn.microsoft.com/en-us/power-pages/configure/liquid/liquid-filters) ·
> [Store content in templates](https://learn.microsoft.com/en-us/power-pages/templates/).

## Reusable components with `{% manifest %}` (the official mechanism)

Build a parameterized web template **once** and let makers reconfigure it in the design studio,
instead of duplicating markup. Add a `{% manifest %}` tag declaring the component:

```liquid
{% manifest %}
{
  "type": "Functional",
  "displayName": "Data Cards",
  "description": "Displays records as a cards layout",
  "tables": ["cards"],
  "params": [
    { "id": "title", "displayName": "Title",  "description": "Heading for this component" },
    { "id": "count", "displayName": "Count",  "description": "Number of items to display" }
  ]
}
{% endmanifest %}
<!-- component markup using {{ title }} and the count param below -->
```

Consume it on a page or in another template:

```liquid
{% include 'Data Cards' title: 'Topics' count: '4' %}
```

Rules that matter:

- `type` must be **`Functional`** to appear in the design studio's **Add component** flow.
- **All params arrive as strings** — convert in code: `{% assign n = count | integer %}`.
- **Nesting components is not supported** (a component can't `{% include %}` another component).
- To customize an out-of-the-box web template, **copy it and extend the copy** (don't edit the OOB
  source — it can be overwritten).
- `tables` lets makers jump to the Data workspace for the listed tables (use logical names).

## Page-template render modes (Rewrite vs Web Template)

A page template can render via a **Web Template** (Liquid) or in **Rewrite** mode. Some controls —
notably the **entity list Calendar and Map views** — do **not** render when the page template is
bound to a web template; use a **Rewrite-mode** page template for those pages. *(Nick Doelman)*

## Liquid vs Web API — draw the boundary deliberately

- **Liquid / FetchXML renders server-side at page build** — fast first paint, and table permissions
  are enforced at render. Use it for read-heavy display and anything permission-sensitive.
- **The Web API is for client-side interactivity/CRUD.** Use it only when the page needs to
  read/write after load.
- Keep queries, secrets, and permission logic **server-side** — don't ship them to the browser.
  *(Nicholas Hayduk; Tino Rabe)*

For server-side logic callable from a template, see the **`{% serverlogic %}`** tag in
`references/server-logic-objects.md`.

## Liquid patterns & gotchas

- **`| liquid` filter for nested content.** Liquid stored inside a content snippet or site-marker
  copy renders as **raw text** unless you pipe it through `| liquid`. *(Nick Doelman)*
- **Site markers over hard-coded links** — `{{ sitemarkers["Name"].url }}` survives page moves
  (`pp-sitemarker`). *(Nick Doelman)*
- **`forloop.index` (1-based) vs `forloop.index0` (0-based)** — pick the right one to avoid
  off-by-one bugs. *(Michel Mendes)*
- **Normalize dates before comparing** — don't string-compare date values; convert to a common
  format first. *(Franco Musso)*
- **Escape record-sourced output** — pipe Dataverse values through `| escape` before emitting into
  HTML/JS to prevent stored XSS (see `pp-securityreview`).

## Client-side JavaScript in templates

- **Put JS in the narrowest scope** — an entity list's Custom JavaScript beats the web page, which
  beats the global header: fewer executions, easier maintenance, correct load timing. *(Nicholas
  Hayduk)*
- **jQuery timing** — jQuery loads from a bundle **after** `<head>` and (on the legacy editor) only
  auto-loads for signed-in admins, so head-placed or anonymous-user code can break. Put
  jQuery-dependent code in page content or a site-wide tracking snippet, and **always test signed
  out**. Verify availability on your enhanced-model site. *(Nicholas Hayduk)*
- **Per-page / per-section CSS via data attributes** on the page/section wrapper keeps theme
  overrides contained instead of leaking through a global stylesheet. *(Franco Musso)*

## Advanced: web templates as data endpoints

A web template can render **JSON** (a template whose page template outputs JSON) to feed a JS library
such as FullCalendar — use Liquid/FetchXML to shape and filter the payload server-side. *(Franco
Musso)* Web templates + content snippets can also emit dynamic **Open Graph** meta tags so shared
links preview correctly. *(Tino Rabe)*
