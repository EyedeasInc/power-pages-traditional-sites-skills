---
name: pp-security-review
description: "Run a security review of a traditional (enhanced-data-model, mspp_*) Power Pages site, focused on the failure modes specific to this platform rather than generic web scanning — stored XSS in web templates and page JS that interpolates Dataverse fields raw, Web API column over-exposure, missing or over-broad table permissions, accidental anonymous access, weak security headers/CSP, Liquid data leaks, and secrets served to the browser. Produces a fill-in findings report. WHEN: security review a Power Pages site, audit portal security, check for portal XSS, review table permissions, find data exposure, portal security checklist, portal security audit, harden a Power Pages site, review web templates for XSS, check Web API exposure, review anonymous access, check CSP/security headers on a portal, run the platform security scan, start a quick or deep scan, get the security scan report or score, check or enable the Web Application Firewall (WAF)."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Security review — traditional Power Pages site

Audit an **enhanced-data-model** (`mspp_*`) Power Pages site for the vulnerabilities that
are *specific to this platform*: Dataverse data flowing into the browser through web
templates and page JS, and the Dataverse-side access controls (Web API settings, table
permissions, web roles) that gate it. This is not a generic web scanner — it targets the
seams where portal content, Liquid, the Web API, and the security model meet.

Read `references/traditional-site-editing-model.md` first (the shared backbone: the
component tables, "read live before you edit", cache flush). Then work the checklist in
`references/review-checklist.md`, which has the exact query/inspection for each item, a
severity, and a fix. Record findings in the report format at the end of this file.

> **Read live, change nothing (by default).** A review is read-only. GET the live
> components from Dataverse — a local `src-control` / `pac pages download` folder is a
> **stale snapshot** and will hide a vulnerability that was introduced in Studio. Only
> remediate after the finding is confirmed and the owner approves; remediation follows the
> `pp-web-template` / `pp-webapi` skills (patch the single live component, then
> flush cache).

## Scope the review (do this first)

Pin the **website** you are auditing — a tenant/env can host several. Everything below is
scoped by `_mspp_websiteid_value` on `mspp_*` rows and `_powerpagesiteid_value` on
`powerpagecomponent` rows.

```
GET /api/data/v9.2/mspp_websites?$select=mspp_name,mspp_primarydomainname
```

Then enumerate the surfaces you'll inspect: web templates (`powerpagecomponent`
`powerpagecomponenttype = 8`), web files with JS (type 3), site settings
(`mspp_sitesetting`), web pages (`mspp_webpage`), web roles (`mspp_webrole`), table
permissions (`mspp_entitypermission`), and content snippets (`mspp_contentsnippet`).

## Step 0 — Run the platform's own scan first (`pac power-pages`)

Before the manual checks, let the platform scan itself — it's free signal and it costs one
command. The `pac power-pages` command group (Preview) runs Microsoft's built-in Power Pages
security scanner and returns a score plus a report. Authenticate once with `pac auth create`
(or reuse the active profile), then, scoped by the **website id** (`get-websites` lists them):

```
pac power-pages get-websites                              # find the site --id (website GUID)
pac power-pages start-quick-scan   --id <SITEID>          # fast checks
pac power-pages start-deep-scan    --id <SITEID>          # thorough, slower — run and come back
pac power-pages get-security-scan-score  --id <SITEID>    # single number to track over time
pac power-pages get-security-scan-report --id <SITEID>    # the detailed findings
```

Treat the scan as **complementary, not a substitute**: it catches configuration/header/WAF
issues the platform knows about, but it does **not** see the platform-specific application
flaws below — stored XSS from raw Dataverse interpolation, Web API `*` over-exposure, blind
table-permission gaps, or Liquid `nil != blank` leaks. Fold the scan's findings into the
same report, then work the seven checks for everything the scanner can't reach.

> **Web Application Firewall (WAF) & IP allow-list** are remediation levers in the same
> command group: `get-waf-status` / `get-waf-rules` / `enable-waf` / `update-waf-policy-settings`
> (Prevention vs Detection mode), and `get-allowed-ip-addresses` / `add-allowed-ip-addresses`
> to restrict who can reach the site. These are defense-in-depth on top of fixing the app
> itself — a WAF in front of an unescaped sink is not a substitute for escaping it.

## The seven checks

Each is detailed in `references/review-checklist.md`. In priority order:

### 1. Stored XSS in web templates / page JS  ⚠️ highest value

The signature failure on this platform: portal JavaScript fetches Dataverse rows from the
Web API (`/_api/<table>s?...`) and builds `innerHTML` by **interpolating field values raw**
— search results, cards, nav menus, "most used" tiles. A Dataverse text field that contains
markup (`<img src=x onerror=...>`, `"><script>…`) then **executes in every visitor's
browser**. The attacker only needs write access to that field via any intake path (a portal
form, an internal app, an integration) — the payload is *stored* and fires for everyone.

**How to check.** Pull each web template's `source` and each JS web file live. Search for
sinks fed by API data with no escaping:

- `innerHTML =`, `insertAdjacentHTML(`, `.html(` (jQuery), template strings assembled into
  markup, and string concatenation like `'<div>' + row.fieldname + '</div>'`.
- Trace each one back: does the interpolated value come from a Web API response, a Liquid
  `fetchxml`/`entityview` result, or a URL parameter? If yes and it isn't escaped → finding.
- In Liquid, look for `{{ … }}` emitting record fields into an HTML/JS context **without**
  the `| escape` filter (or building an `onclick`/`href` from a field).

**How to fix.** Define one `escapeHtml()` helper and apply it to **every** interpolation —
element **bodies and attribute values alike**:

```js
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
// body:      el.innerHTML = '<div class="card-title">' + escapeHtml(row.aeso_name) + '</div>';
// attribute: '<i class="' + escapeHtml(row.aeso_icon) + '"></i>'   // classic attribute breakout
// href:      '<a href="' + escapeHtml(row.aeso_url) + '">'          // + validate scheme
```

A `"`-only replace is **not enough** — you must escape `& < > " '`. Escaping only `"`
still lets a value break out of an unquoted/`'`-quoted attribute or inject a raw `<`. In
Liquid, pipe every record-sourced output through `| escape` (and `| escape` again if it
lands inside a JS string). This mirrors a real remediation: an `escapeHtml` helper added to
a landing page whose search results, quick-links, and card titles all interpolated
Dataverse fields raw — every sink wrapped, with a guard asserting the raw sinks were gone
before the fix shipped. See the checklist for the drift-safe patch procedure.

### 2. Web API over-exposure

The Web API is gated per table/column by **site settings**. `Webapi/<table>/fields = *`
exposes *every* column — including ones your UI never uses — to anyone who can read the
table under portal permissions. Combined with a table permission, `*` can leak PII, internal
notes, or audit columns.

**How to check.** List every Web API site setting and flag `= *` or any sensitive column:

```
GET /api/data/v9.2/mspp_sitesettings?$filter=_mspp_websiteid_value eq <SITEID>
    and startswith(mspp_name,'Webapi/')&$select=mspp_name,mspp_value
```

**How to fix.** Replace `*` with the explicit least-field list the front-end actually reads.
Cross-ref the `pp-webapi` skill for the correct `Webapi/<table>/enabled` +
`Webapi/<table>/fields` shape.

### 3. Table-permission gaps / over-broad scope

Missing permissions cause data leaks (if a broader one covers the table) or silent breakage;
**Global** scope where **Contact**/**Account** scope belongs lets one authenticated user read
*every* row instead of only their own.

**How to check.** Read `mspp_entitypermission` for the site and inspect `mspp_scope`
(Global / Contact / Account / Self) and the CRUD privilege flags per table. **Verify the
web-role bindings via the `mspp_entitypermission_webroleset` intersect directly** — an
`$expand` from the permission or role reads *blind* under an app-only service principal and
will make an over-broad grant look empty. See the checklist for the exact intersect query.

**How to fix.** Tighten scope to the narrowest that still works (Contact/Account over
Global), remove CRUD rights the role doesn't need, add the missing parent-scope permissions
that a Contact/Account scope depends on. Cross-ref the pp-table-permissions guidance.

### 4. Anonymous access

Authenticated content leaks when a page or a table permission is bound to the **Anonymous
Users** web role, or when a page's authentication settings are left open.

**How to check.** Find the Anonymous web role and list what it's bound to — table
permissions (via the intersect), web pages, and page access control rules. Inspect each
sensitive `mspp_webpage`'s authentication settings (published state + any
`mspp_webpageaccesscontrolrule`). Any authenticated-only page or PII table reachable by
Anonymous → finding.

**How to fix.** Remove the Anonymous binding; bind to **Authenticated Users** (or a specific
role) instead. Re-test the page logged out to confirm it now challenges.

### 5. Security headers / CSP

A missing/weak **Content-Security-Policy** turns a single XSS into full script execution;
missing `X-Content-Type-Options`, `X-Frame-Options`, and HSTS leave MIME-sniffing,
clickjacking, and downgrade exposure.

**How to check.** Inspect the site settings that drive headers
(`HTTP/Content-Security-Policy`, `HTTP/X-Content-Type-Options`, `HTTP/X-Frame-Options`,
`HTTP/Strict-Transport-Security` — names vary by version) and confirm the live responses
carry them. Flag a CSP that allows `unsafe-inline`/`unsafe-eval` scripts (an XSS payload
runs unimpeded) or no CSP at all.

**How to fix.** Set a restrictive CSP (avoid `unsafe-inline` for `script-src`; use nonces/
hashes if the site has inline scripts), `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`/`SAMEORIGIN`, and HSTS. Cross-ref the `manage-headers` guidance.

### 6. Liquid data leaks

Liquid runs server-side and can read Dataverse directly — a template that queries data and
renders it **without a permission gate** bypasses table permissions. And the classic
platform quirk: **`nil != blank` is TRUE in Liquid**, so `{% if x != blank %}` on a FetchXML
result is *always true* and can render a block (and its data) that should have been hidden.

**How to check.** In each web template, find `{% fetchxml %}` / `{% entityview %}` /
`{% assign … = entities… %}` blocks; confirm the surrounding page/section is permission-
gated and that emptiness tests use `.size` or `{% unless %}` — **never** `== blank` /
`!= blank` — for entity results.

**How to fix.** Gate the query behind the right web role/table permission; replace
`!= blank` / `== blank` with `.size > 0` / `{% unless result.size > 0 %}`. Cross-ref the
pp-liquid guidance.

### 7. Secrets served to the browser

API keys, bearer tokens, connection strings, or function keys hardcoded in a **web template**
or a **JS web file** are downloaded by every visitor — fully public.

**How to check.** Grep every web template `source` and JS/web-file body (live copies) for
`apikey`, `api_key`, `Bearer `, `AccountKey=`, `client_secret`, `?code=`, `sig=`, AWS-style
keys, GU();-looking function keys in URLs, etc.

**How to fix.** Remove the secret from client-served content; move the call server-side
(Power Pages **server logic** / a cloud flow) so the secret stays out of the browser, and
**rotate** the exposed credential — assume it is compromised.

## Findings report format

Produce one table (highest severity first). Fill a row per confirmed finding:

```
| # | Severity | Check | Location (component + id) | Issue | Fix | Status |
|---|----------|-------|---------------------------|-------|-----|--------|
| 1 | Critical | XSS   | Web template "…" (powerpagecomponent <guid>), search-results render | row.aeso_name interpolated raw into innerHTML | Wrap every interpolation in escapeHtml(); re-check raw sinks gone | Open |
| 2 | High     | WebAPI| Site setting Webapi/aeso_contact/fields | value is `*` (exposes all columns) | Replace with explicit least-field list | Open |
```

Severity guide: **Critical** = stored XSS reachable by visitors, or PII reachable by
Anonymous. **High** = Web API `*` on a sensitive table, Global scope where Contact belongs,
secret in client content. **Medium** = missing CSP/headers, unescaped-but-low-impact output.
**Low** = defense-in-depth hardening. For each finding record: severity, exact location
(component name **and** id), the concrete issue, the fix, and a status you update as it's
remediated.

## Remediating (only after approval)

Fixes are single-component live patches, not a site re-upload:

- **XSS / Liquid / secret in a web template** → `pp-web-template` (GET live `source`,
  apply the escape/gate/removal with a match-once guard, PATCH, flush cache).
- **Web API fields / anonymous / table permissions / headers** → the corresponding config
  skill (`pp-webapi`, pp-table-permissions, `manage-headers`) — never batch-upload the
  whole site to push one setting.
- Re-run the relevant checklist item after each fix to confirm the finding is closed, then
  flush the portal cache and re-test as an anonymous and as an authenticated user.
