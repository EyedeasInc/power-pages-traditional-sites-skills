# Liquid patterns — copy-paste cheat sheet

Correct, safe snippets for traditional (enhanced-data-model, `mspp_*`) Power Pages sites.
Companion to `../SKILL.md`. Replace `mspp_product` / field names with your table's.

---

## Empty-result guard (the `nil != blank` trap)

`nil != blank` is **TRUE** in Power Pages Liquid. Test collections with `.size`, never `blank`.

```liquid
{% comment %} WRONG — fires even with zero rows {% endcomment %}
{% if results.entities != blank %} ...has rows... {% endif %}

{% comment %} RIGHT {% endcomment %}
{% if results.entities.size > 0 %} ...has rows... {% else %} none {% endif %}

{% comment %} RIGHT — unless variant {% endcomment %}
{% unless results.entities.size > 0 %} none {% endunless %}
```

`== blank` / `!= blank` is acceptable only for a **scalar text** field ("is this string empty?"),
never for a collection / query result.

---

## FetchXML: query, guard, loop, select columns

```liquid
{% fetchxml products %}
<fetch top="20">
  <entity name="mspp_product">
    <attribute name="mspp_productid" />
    <attribute name="mspp_name" />
    <attribute name="mspp_price" />
    <order attribute="mspp_name" descending="false" />
    <filter type="and">
      <condition attribute="statecode" operator="eq" value="0" />
    </filter>
  </entity>
</fetch>
{% endfetchxml %}

{% if products.results.entities.size > 0 %}
  <ul>
  {% for p in products.results.entities %}
    <li>
      <a href="/product?id={{ p.mspp_productid | url_encode }}">{{ p.mspp_name | escape }}</a>
      — {{ p.mspp_price }}
    </li>
  {% endfor %}
  </ul>
{% else %}
  <p>No products found.</p>
{% endif %}
```

### FetchXML paging

```liquid
{% assign pg = request.params.page | default: 1 %}
{% fetchxml products %}
<fetch count="10" page="{{ pg }}" returntotalrecordcount="true">
  <entity name="mspp_product">
    <attribute name="mspp_name" />
    <order attribute="mspp_name" />
  </entity>
</fetch>
{% endfetchxml %}

{% if products.results.entities.size > 0 %}
  {% for p in products.results.entities %}{{ p.mspp_name | escape }}<br>{% endfor %}
  {% if products.results.more_records %}
    <a href="?page={{ pg | plus: 1 }}">Next</a>
  {% endif %}
{% endif %}
```

### Reading a lookup / option / money field

```liquid
{{ p.mspp_categoryid.Name | escape }}   {% comment %} lookup display text {% endcomment %}
{{ p.mspp_categoryid.Id }}              {% comment %} lookup GUID {% endcomment %}
{{ p.statuscode.Value }}                {% comment %} option numeric value {% endcomment %}
{{ p.statuscode.Label | escape }}       {% comment %} option label {% endcomment %}
```

---

## Escaping on output (stop stored XSS)

```liquid
<h2>{{ record.mspp_name | escape }}</h2>            {% comment %} element body {% endcomment %}
<a title="{{ record.mspp_note | escape }}">open</a> {% comment %} attribute value {% endcomment %}
<a href="/d?id={{ record.mspp_id | url_encode }}">  {% comment %} URL / query string {% endcomment %}
```

Never emit a portal-user-writable field without `escape`. Only skip it for a field that is
intentionally maker-authored trusted HTML.

### JavaScript escape helper (for Web API data built into innerHTML)

```html
<script>
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  // el.innerHTML = "<h3>" + escapeHtml(rec.mspp_name) + "</h3>" +
  //   '<span data-x="' + escapeHtml(rec.mspp_code) + '">' + escapeHtml(rec.mspp_note) + "</span>";
  // Prefer el.textContent = rec.mspp_name / el.setAttribute(...) when no HTML is needed.
</script>
```

---

## Web API via `webapi.safeAjax` (never a hand-rolled wrapper)

Include the wrapper template once, then call `safeAjax`. It attaches the CSRF token that writes
require.

```liquid
{% include 'Power Apps Web API Wrapper Function' %}
```

### GET

```html
<script>
  webapi.safeAjax({
    type: "GET",
    url: "/_api/mspp_products?$select=mspp_name,mspp_price&$orderby=mspp_name&$top=10",
    contentType: "application/json",
    success: function (data) {
      (data.value || []).forEach(function (rec) {
        // escapeHtml(rec.mspp_name) before any innerHTML
      });
    },
    error: function (xhr) { console.error(xhr.status, xhr.responseText); }
  });
</script>
```

### POST (create)

```html
<script>
  webapi.safeAjax({
    type: "POST",
    url: "/_api/mspp_products",
    contentType: "application/json",
    data: JSON.stringify({ "mspp_name": "New", "mspp_price": 9.99 }),
    success: function (res, status, xhr) {
      var newId = xhr.getResponseHeader("entityid");
    }
  });
</script>
```

### PATCH (update) / DELETE

```html
<script>
  webapi.safeAjax({ type: "PATCH", url: "/_api/mspp_products(" + id + ")",
    contentType: "application/json", data: JSON.stringify({ "mspp_price": 12.50 }) });

  webapi.safeAjax({ type: "DELETE", url: "/_api/mspp_products(" + id + ")",
    contentType: "application/json" });
</script>
```

Rules: never roll your own `$.ajax`/`fetch` for `/_api/*` (you lose CSRF handling); never
`fetch()` against `/_api/file/*` — use `safeAjax`. Web API access needs the `Webapi/<table>/…`
site settings **and** table permissions for the caller's web role.

---

## Entity list (configured view, no hand-written FetchXML)

```liquid
{% entitylist name: "Active Products" %}
  {% entityview id: page.adx_entityview %}
    {% if entityview.records.size > 0 %}
      <table>
        {% for row in entityview.records %}
          <tr><td>{{ row.mspp_name | escape }}</td><td>{{ row.mspp_price }}</td></tr>
        {% endfor %}
      </table>
      {% comment %} paging exposed by the view {% endcomment %}
      {% if entityview.pages > 1 %}Page {{ entityview.page }} of {{ entityview.pages }}{% endif %}
    {% else %}
      <p>No records.</p>
    {% endif %}
  {% endentityview %}
{% endentitylist %}
```

---

## Common objects — quick reference

```liquid
{% if user %}Hello {{ user.fullname | escape }}{% else %}Sign in{% endif %}
{% if user.roles contains 'Administrators' %} ...admin only... {% endif %}

{{ page.title | escape }}          {% comment %} current page {% endcomment %}
{{ website.id }}                    {% comment %} current site {% endcomment %}
{{ settings['Header/ShowSearch'] }} {% comment %} site setting {% endcomment %}
{{ snippets['Footer Text'] }}       {% comment %} content snippet {% endcomment %}

{% assign p = entities.mspp_product['00000000-0000-0000-0000-000000000000'] %}
{% if p %}{{ p.mspp_name | escape }}{% endif %}   {% comment %} nil if not found/permitted {% endcomment %}
```

Everything sourced from Dataverse (`entities`, entity lists, `user`'s child data) is untrusted on
output — `escape` it — and its collections follow the `.size` rule, never `blank`.
