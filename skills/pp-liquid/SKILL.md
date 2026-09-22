---
name: pp-liquid
description: "Write correct, safe Liquid in web templates and page content on a traditional (enhanced-data-model, mspp_*) Power Pages site — FetchXML queries, rendering Dataverse data, calling the Web API, and the common Liquid objects. Covers the nil-vs-blank trap that breaks empty-result checks and the escaping needed to stop stored XSS. WHEN: write Liquid, fix Liquid template logic, fetchxml in Power Pages, check if a query returned rows, nil vs blank, render Dataverse data on a portal page, liquid escaping, loop entity results, call the Web API from a Liquid page, entitylist loop, guard an empty FetchXML result."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Write correct, safe Liquid on a Power Pages site

Liquid runs **server-side** when a traditional Power Pages page renders — inside a web template
(`powerpagecomponent` type 8), a content web page's `mspp_copy`, or a content snippet. It reads
Dataverse through Liquid tags and objects, then emits HTML. This skill covers the non-obvious
parts: an empty-result test that silently lies, escaping that stops stored XSS, and the one
correct way to call the Web API.

> Editing model (where these live, how to PATCH them back, cache-flush): see
> `references/traditional-site-editing-model.md`. This skill is about the **Liquid you write**,
> not how you push it.

Copy-paste snippets for every pattern below live in **`references/liquid-patterns.md`**.

## 1 — The `nil != blank` quirk (read this first)

In Power Pages Liquid, **`nil != blank` evaluates to TRUE.** `blank` is a special empty-ish
object, and an unset/nil value is *not equal* to it. So the intuitive "did my query return
anything?" test is **wrong** and will run your "has rows" branch even when there are zero rows.

```liquid
{% comment %} WRONG — runs the "found" branch even when nothing matched {% endcomment %}
{% if results.entities != blank %}
  ...renders as if rows exist, even for an empty result...
{% endif %}

{% comment %} WRONG — the mirror image; skips the branch when rows DO exist {% endcomment %}
{% if results.entities == blank %}
  No results.
{% endif %}
```

**Test the collection's `.size` instead, or use `unless`:**

```liquid
{% comment %} RIGHT — count the rows {% endcomment %}
{% if results.entities.size > 0 %}
  {% for e in results.entities %} ... {% endfor %}
{% else %}
  No results.
{% endif %}

{% comment %} RIGHT — unless treats an empty collection as falsy correctly {% endcomment %}
{% unless results.entities.size > 0 %}
  No results.
{% endunless %}
```

The same applies to any FetchXML result, entity-list result, or lookup collection. **Never use
`== blank` / `!= blank` to decide whether a query returned rows.** Use `.size`. (`blank` is fine
for genuine "is this string empty?" checks on a scalar text value — just not for collections.)

## 2 — FetchXML in Liquid

Run a query with `{% fetchxml %}` and iterate `results.entities`. The variable after `fetchxml`
holds the result set.

```liquid
{% fetchxml products %}
<fetch top="20">
  <entity name="mspp_product">
    <attribute name="mspp_name" />
    <attribute name="mspp_price" />
    <order attribute="mspp_name" />
    <filter type="and">
      <condition attribute="statecode" operator="eq" value="0" />
    </filter>
  </entity>
</fetch>
{% endfetchxml %}

{% if products.results.entities.size > 0 %}
  <ul>
  {% for p in products.results.entities %}
    <li>{{ p.mspp_name | escape }} — {{ p.mspp_price }}</li>
  {% endfor %}
  </ul>
{% else %}
  <p>No products.</p>
{% endif %}
```

Notes:
- **Guard with `.size`** (rule 1) — an empty query is common, and `!= blank` won't catch it.
- **Select only the columns you render** with `<attribute>` — fewer columns, faster query.
- **Paging:** add `count` and `page` to `<fetch>` (e.g. `<fetch count="10" page="2">`). Read
  `results.more_records` to decide whether to show a "next" control. Build page links off a
  query-string value (see `references/liquid-patterns.md`).
- Field access is by **logical name** (`p.mspp_name`); lookups expose `.Name` and `.Id`
  (e.g. `p.mspp_categoryid.Name`).
- FetchXML in Liquid runs with the **portal's** access — it is still subject to **table
  permissions** and the page's web roles. A query that returns nothing is often a missing table
  permission, not a bad query.

## 3 — Render Dataverse data safely (escape everything)

A Dataverse text field can contain markup. If a user (or an integration) stored
`<img src=x onerror=alert(1)>` in a field and you interpolate it raw, it **executes in every
visitor's browser** — stored XSS. Every Dataverse-sourced value you put into HTML must be
escaped.

**In Liquid output, pipe through `| escape`:**

```liquid
<h2>{{ product.mspp_name | escape }}</h2>
<p>{{ product.mspp_description | escape }}</p>
<a href="/detail?id={{ product.mspp_productid | url_encode }}">Details</a>
```

- Use `| escape` for values placed in **element bodies and quoted attribute values**.
- Use `| url_encode` for values placed into a **URL / query string**.
- Only skip escaping for a field that is *intentionally* trusted rich HTML authored by a maker
  (e.g. a page-copy field), never for anything a portal user or external system can write.

**In page JavaScript that builds HTML from Web API data, escape every interpolation** — Liquid's
`escape` does not reach values you fetch client-side. Use a helper on **both** attributes and
element bodies:

```html
<script>
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  // container.innerHTML = "<h3>" + escapeHtml(rec.mspp_name) + "</h3>" +
  //   '<a title="' + escapeHtml(rec.mspp_note) + '">open</a>';
</script>
```

Prefer `textContent` / `setAttribute` where you can — they don't parse HTML at all. When you must
build an `innerHTML` string, wrap **every** dynamic piece in `escapeHtml()`. See the
**`pp-security-review`** skill for the full portal XSS checklist, and **`pp-webapi`** for the
data-fetch side.

## 4 — Calling the Web API from a Liquid page

Client-side reads/writes go through the portal Web API (`/_api/*`). **Always** include the
official **"Power Apps Web API Wrapper Function"** template on the page and call
**`webapi.safeAjax(...)`**. That wrapper fetches and attaches the request-verification (CSRF)
token that `/_api/*` writes require; a hand-rolled `$.ajax`/`fetch` omits it and your POST/PATCH/
DELETE fails with a token error.

```liquid
{% comment %} include the shared wrapper once on the page/template {% endcomment %}
{% include 'Power Apps Web API Wrapper Function' %}

<script>
  webapi.safeAjax({
    type: "GET",
    url: "/_api/mspp_products?$select=mspp_name,mspp_price&$top=10",
    contentType: "application/json",
    success: function (data) {
      (data.value || []).forEach(function (rec) {
        // escapeHtml() every field before it touches innerHTML (rule 3)
      });
    }
  });
</script>
```

Hard rules:
- **Never roll your own** `$.ajax`/`fetch` wrapper for `/_api/*` — CSRF handling lives in
  `safeAjax`. Use it for GET too, for consistency.
- **Never use `fetch()` against `/_api/file/*`** (file/binary column endpoints). Those need the
  wrapper's request handling — go through `safeAjax`.
- Web API access must be enabled per table via **site settings** (`Webapi/<table>/enabled`,
  `Webapi/<table>/fields`) and gated by **table permissions**. Enabling the setting without a
  table permission still returns nothing. See **`pp-webapi`**.

## 5 — Common Liquid objects (practical set)

| Object / tag | Use it for |
|---|---|
| `user` | The signed-in contact. `{% if user %}` = authenticated; `user.fullname`, `user.id`, and roles via `{% if user.roles contains 'Admin' %}`. Nil when anonymous — remember rule 1 for its child collections. |
| `page` | The current web page: `page.title`, `page.url`, `page.adx_*`/`mspp_*` fields, breadcrumbs. |
| `website` | The current site: `website.id`, and the primary way to scope things to this site. |
| `settings` | Site settings: `{{ settings['Header/ShowSearch'] }}` — read a maker-configured value. |
| `snippets` | Content snippets: `{{ snippets['Snippet Name'] }}` for reusable editable text. |
| `entities` | Direct record fetch by GUID: `{% assign p = entities.mspp_product['<guid>'] %}`. Returns nil if not found/permitted — guard before use. |
| `{% entitylist %}` / `{% entityview %}` | Render a configured list (view) with paging/filter without hand-writing FetchXML. |
| `{% entityform %}` / `{% webform %}` | Render a configured basic form / multi-step form for create/edit. |

`entities` and entity-list results are Dataverse data — **escape their fields on output**
(rule 3) and **test their collections with `.size`** (rule 1).

## Checklist before you ship a Liquid change

1. Every "did it return rows?" test uses `.size` (or `unless … .size > 0`), **not** `== blank` /
   `!= blank`.
2. Every Dataverse-sourced value in HTML is `| escape`'d (Liquid) or `escapeHtml()`'d (JS) — in
   both element bodies and attributes.
3. Every `/_api/*` call goes through `webapi.safeAjax` with the wrapper template included; no
   raw `fetch` to `/_api/file/*`.
4. FetchXML selects only needed columns and is scoped/permitted correctly (table permissions +
   web roles), not just syntactically valid.
5. You cache-flushed after PATCHing the template/content (see the shared editing-model reference).
