# Power Pages traditional-site security review — runnable checklist

Work top to bottom. Each item gives **what to query/inspect**, a **severity**, and the
**fix**. Everything is scoped to one website — set `<SITEID>` = the `mspp_websiteid` you are
auditing and `<PPSITEID>` = the matching `powerpagesiteid` for `powerpagecomponent` rows.
All GETs are read-only. Read the shared backbone (`references/traditional-site-editing-model.md`)
first: read live before you conclude anything — a local `src-control` snapshot can be stale.

Endpoint note: portal/browser calls hit `/_api/<entityset>` (Web API for Pages); admin/audit
reads use the Dataverse Web API `/api/data/v9.2/…`. Prefer the **Dataverse MCP** for reads
where available (it respects your security role); the queries below are written as Dataverse
Web API for portability.

---

## 0. Inventory (fill before you start)

- [ ] Website confirmed:
      `GET /api/data/v9.2/mspp_websites?$select=mspp_name,mspp_primarydomainname`
- [ ] Web templates:
      `GET /api/data/v9.2/powerpagecomponents?$filter=_powerpagesiteid_value eq <PPSITEID> and powerpagecomponenttype eq 8&$select=name,powerpagecomponentid`
- [ ] Web files (JS/CSS/binary, type 3):
      `…and powerpagecomponenttype eq 3&$select=name,powerpagecomponentid`
- [ ] Site settings:
      `GET /api/data/v9.2/mspp_sitesettings?$filter=_mspp_websiteid_value eq <SITEID>&$select=mspp_name,mspp_value`
- [ ] Web roles:
      `GET /api/data/v9.2/mspp_webroles?$filter=_mspp_websiteid_value eq <SITEID>&$select=mspp_webroleid,mspp_name,mspp_authenticatedusersrole,mspp_anonymoususersrole`
- [ ] Table permissions:
      `GET /api/data/v9.2/mspp_entitypermissions?$filter=_mspp_websiteid_value eq <SITEID>&$select=mspp_entitypermissionid,mspp_name,mspp_entityname,mspp_scope,mspp_read,mspp_write,mspp_create,mspp_delete,mspp_append,mspp_appendto,_mspp_parententitypermission_value`

---

## 1. Stored XSS in web templates / page JS  — Severity: CRITICAL when visitor-reachable

**Inspect.** For each web template pull the live `source` (it's JSON in `content`); for each
JS web file pull its body. Parse `content` with `json.loads` directly — do **not**
`html.unescape` first (that corrupts legitimate `& " <` in the source; only fall back to
unescape if the direct parse throws).

```
GET /api/data/v9.2/powerpagecomponents(<COMPID>)?$select=name,content
```

Search each source for **HTML sinks fed by data**:

- [ ] `innerHTML =`, `outerHTML =`, `insertAdjacentHTML(`, jQuery `.html(`, `.append('<…'+…)`
- [ ] Template literals / string concatenation building markup from a variable:
      `` `<div>${row.field}</div>` `` or `'<div>' + row.field + '</div>'`
- [ ] Attribute construction from data: `'class="' + val`, `'href="' + val`, `'style="' + val`,
      `'onclick="' + val` — the **attribute-breakout** class; an unescaped value can close the
      attribute and add `onerror=`/`onmouseover=` or a `javascript:` href.
- [ ] Liquid `{{ record.field }}` emitted into HTML or into a `<script>` string **without**
      `| escape`.

**Trace each sink to its source.** It's a finding when the interpolated value comes from:
Web API response data, a Liquid `fetchxml`/`entityview` row, `document.location`/URL params,
or any Dataverse text/multiline field an attacker could write through *any* intake path. The
value being "internal data" is not a defense — stored XSS fires from stored data.

**Grep helper (against live-downloaded sources):**
```
rg -n "innerHTML|insertAdjacentHTML|\.html\(|\$\{[^}]*\}|' *\+|\+ *'" <dir-of-live-sources>
rg -n "\{\{[^}]*\}\}" <dir> | rg -v "\| *escape"   # Liquid outputs missing | escape
```

**Fix.** One `escapeHtml` helper, applied to **every** interpolation — bodies *and*
attributes. Escape all five: `& < > " '` (a `"`-only replace is insufficient):

```js
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
```

- Body:      `'<h3 class="card-title">' + escapeHtml(item.aeso_name || '') + '</h3>'`
- Attribute: `'<i class="' + escapeHtml(item.aeso_icon) + '"></i>'`
- href:      `'<a href="' + escapeHtml(item.aeso_url) + '">'` — plus validate the scheme
  (reject `javascript:`), since escaping alone still allows a `javascript:` URL.
- Liquid:    `{{ record.aeso_name | escape }}` (and pipe `| escape` again when the value is
  written into a JS string literal inside a `<script>`).

**Drift-safe remediation procedure** (mirrors a real landing-page XSS fix — search results,
quick-links, and card titles all interpolated Dataverse fields raw):

1. GET the **live** template `source` (not the local copy).
2. If `function escapeHtml` is already present, it's likely already fixed — verify and stop.
3. Insert the helper; wrap each sink. Derive each edit as an old→new hunk and require it to
   match the live source **exactly once** before applying — abort on 0 or >1 matches so a
   drifted live copy fails safely instead of mis-patching.
4. **Post-conditions before PATCH:** assert `escapeHtml` is present *and* each known raw sink
   string is gone. Only then PATCH `content` back and flush the portal cache.

---

## 2. Web API over-exposure — Severity: HIGH (sensitive table) / MEDIUM

**Inspect.** List the Web API site settings and read each `fields` value:

```
GET /api/data/v9.2/mspp_sitesettings?$filter=_mspp_websiteid_value eq <SITEID>
    and startswith(mspp_name,'Webapi/')&$select=mspp_name,mspp_value
```

- [ ] `Webapi/<table>/fields = *`  → exposes **every** column. Finding.
- [ ] `fields` list containing sensitive columns the UI never renders (email, phone, SSN-like,
      internal notes, approval/audit columns, `*_value` lookups to sensitive parents).
- [ ] `Webapi/<table>/enabled = true` for a table with **no** legitimate portal use.

**Fix.** Replace `*` with the explicit least-field list the front-end actually consumes;
remove sensitive columns; disable the endpoint for tables not used by the portal. Follow the
`integrate-webapi` skill's `Webapi/<table>/enabled` + `Webapi/<table>/fields` shape. After
narrowing, re-test the portal feature that reads the table to confirm nothing broke.

---

## 3. Table-permission gaps / over-broad scope — Severity: HIGH (Global-where-Contact) / MEDIUM

**Inspect.** Read every `mspp_entitypermission` for the site (query in §0). For each:

- [ ] **Scope.** `mspp_scope` = Global exposes *all rows* of the table to any bound role.
      Where the intent is "the user's own records", scope should be **Contact** or **Account**
      (with a parent permission), or **Self**. Global-where-Contact-belongs → HIGH finding.
- [ ] **CRUD breadth.** Flag `mspp_write/create/delete = true` on roles that should be
      read-only, and `mspp_delete` granted broadly.
- [ ] **Missing parent.** A Contact/Account-scoped permission needs a `_mspp_parententitypermission_value`
      chain up to a Global/Contact anchor; a broken chain either leaks (falls back to a broader
      grant) or breaks the page. Verify the chain resolves.

**Verify the web-role bindings via the intersect DIRECTLY.** Under an app-only service
principal, `$expand` from a permission or role to its roles often reads **blind** (returns
empty) and hides an over-broad grant. Query the intersect table itself:

```
GET /api/data/v9.2/mspp_entitypermission_webroleset?$select=mspp_entitypermissionid,mspp_webroleid
```

Join each `mspp_entitypermissionid` to its permission (name/scope) and each `mspp_webroleid`
to its role name — that is the authoritative "who can do what to which table" map. Cross-check
that no sensitive permission resolves to the Anonymous role (feeds §4).

**Fix.** Narrow `mspp_scope` to the least that works (Contact/Account over Global); strip
unneeded CRUD flags; repair or add the parent permission; unbind roles that shouldn't have
the grant. Apply via the table-permissions config path — do not batch-upload the site.

---

## 4. Anonymous access — Severity: CRITICAL (PII) / HIGH

**Inspect.**

- [ ] Identify the Anonymous role: from §0, the row with `mspp_anonymoususersrole = true`.
- [ ] **Table permissions bound to Anonymous:** filter the §3 intersect results to that
      `mspp_webroleid`. Any permission on a table with authenticated-only or PII data → finding
      (CRITICAL if PII/personal records).
- [ ] **Pages reachable anonymously:** for sensitive `mspp_webpage` rows, inspect the page's
      authentication/access-control settings and any `mspp_webpageaccesscontrolrule` +
      `mspp_webpageaccesscontrolrule_webrole` bindings. A page meant to be authenticated that
      has no rule (or an Anonymous rule) is exposed.
- [ ] **Web files / content snippets** with sensitive content served without a gate.

**Fix.** Remove the Anonymous binding; bind the permission/page to **Authenticated Users** or
a specific role. Add the missing web-page access-control rule. Re-test **logged out** — the
page must challenge for sign-in and the `/_api` read must 403.

---

## 5. Security headers / CSP — Severity: MEDIUM (HIGH if XSS also present)

**Inspect.** Header behavior is driven by `HTTP/…` site settings (names vary by portal
version) and by the site's uploaded headers. Check both the settings and the **live response
headers**:

```
GET /api/data/v9.2/mspp_sitesettings?$filter=_mspp_websiteid_value eq <SITEID>
    and startswith(mspp_name,'HTTP/')&$select=mspp_name,mspp_value
```

- [ ] **Content-Security-Policy** present? A missing CSP means any XSS (see §1) runs
      unrestricted. A CSP with `script-src … 'unsafe-inline'` / `'unsafe-eval'` barely
      constrains an injected script → finding, and it directly amplifies §1.
- [ ] **X-Content-Type-Options: nosniff** — missing → MIME-sniffing risk.
- [ ] **X-Frame-Options** `DENY`/`SAMEORIGIN` (or CSP `frame-ancestors`) — missing →
      clickjacking.
- [ ] **Strict-Transport-Security** — missing → downgrade exposure.

**Fix.** Set a restrictive CSP: avoid `unsafe-inline`/`unsafe-eval` for `script-src`; move
inline scripts to web files or gate them with nonces/hashes; set `frame-ancestors`. Add
`X-Content-Type-Options: nosniff`, `X-Frame-Options`, and HSTS. Use the `manage-headers`
config path. Re-fetch the live headers to confirm they're applied (flush cache first).

---

## 6. Liquid data leaks — Severity: HIGH (ungated data) / MEDIUM

**Inspect.** In each web template `source`:

- [ ] `{% fetchxml %}`, `{% entityview %}`, `{% assign x = entities['…'] %}`, `{% aggregatequery %}`
      — is the rendered result gated by web role / table permission for the current user? An
      ungated query in Liquid runs server-side and can bypass table permissions entirely.
- [ ] **`nil != blank` quirk:** `{% if result != blank %}` / `{% if result == blank %}` on a
      FetchXML/entity result is **wrong** — in Liquid `nil != blank` evaluates **TRUE**, so a
      `!= blank` test is always true and can render a data block that should have been hidden.

```
rg -n "!= *blank|== *blank" <dir-of-live-templates>          # the mislogic
rg -n "\{% *(fetchxml|entityview|aggregatequery|assign)" <dir>  # ungated queries to review
```

**Fix.** Gate the query/section behind the correct role or table permission. Replace
emptiness tests on entity results with `.size`: use `{% if result.size > 0 %}` /
`{% unless result.size > 0 %}` — never `== blank` / `!= blank` for FetchXML results. Follow
the write-liquid guidance.

---

## 7. Secrets served to the browser — Severity: HIGH

**Inspect.** Grep every **live** web template `source` and every JS/web-file body:

```
rg -ni "api[_-]?key|secret|bearer |authorization:|AccountKey=|client_secret|\?code=|&sig=|x-functions-key|AKIA[0-9A-Z]{16}" <dir-of-live-sources>
```

- [ ] Hardcoded API keys, function keys (`?code=…`, `x-functions-key`), SAS tokens
      (`sig=…`), connection strings (`AccountKey=…`), OAuth `client_secret`, bearer tokens.
- [ ] Endpoints that only "work" because a key is embedded — anything a visitor's browser
      downloads is public.

**Fix.** Remove the secret from client-served content. Move the privileged call **server-side**
— Power Pages **server logic** (see `add-server-logic`) or a cloud flow behind the Web API —
so the secret never reaches the browser. **Rotate** the exposed credential immediately; treat
any secret that shipped to the browser as compromised.

---

## Findings report (fill in)

```
| # | Severity | Check | Location (component name + id) | Issue | Fix | Status |
|---|----------|-------|--------------------------------|-------|-----|--------|
|   |          |       |                                |       |     | Open   |
```

- **Severity:** Critical / High / Medium / Low (per the guidance in SKILL.md).
- **Check:** XSS / WebAPI / TablePerm / Anonymous / Headers / Liquid / Secret.
- **Location:** component *name and id* (or site-setting name), plus the line/function.
- **Issue / Fix:** concrete, one line each. **Status:** Open → Fixed → Verified.

After each remediation, re-run that check's inspection, flush the portal cache, and re-test as
both an anonymous and an authenticated user before marking **Verified**.
