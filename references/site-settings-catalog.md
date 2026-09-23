# Site settings catalog (headers, security, and useful lesser-known settings)

Shared reference of high-value `mspp_sitesetting` records for a traditional site. Used by
`pp-headers`, `pp-website`, `pp-webapi`, `pp-basicform`.

> **Authority:** Microsoft Learn for the header/SameSite/search settings (linked inline). The
> lesser-known formatting/lookup/registration settings are **community-cataloged** (Oleksandr
> Olashyn) — **verify the exact name against your site version** before relying on it.
> **Sources:** [Configure site settings](https://learn.microsoft.com/en-us/power-pages/configure/configure-site-settings) ·
> [CORS / headers](https://learn.microsoft.com/en-us/power-pages/configure/cors-support) ·
> [Important changes (SameSite)](https://learn.microsoft.com/en-us/power-pages/important-changes-deprecations) ·
> Olashyn catalog: https://www.dancingwithcrm.com/portal-settings-list/ ·
> https://github.com/OOlashyn/PowerAppsPortalSiteSettingsAndSnippets

> **Note on naming/storage.** Setting names use `/` (e.g. `HTTP/X-Frame-Options`). When exported via
> `pac`, header settings become `*.sitesetting.yml` files with `/` → `-` in the filename. Confirm
> names in the Portal Management app; some entries below are **content snippets**, not site settings.

## Security response headers (map to `pp-headers`) — Microsoft-documented

| Setting | Effect |
|---|---|
| `HTTP/Content-Security-Policy` | CSP. Avoid `unsafe-inline`/`unsafe-eval` in `script-src`. |
| `HTTP/X-Frame-Options` | Clickjacking: `SAMEORIGIN` / `DENY`. |
| `HTTP/X-Content-Type-Options` | `nosniff`. |
| `HTTP/Referrer-Policy` | e.g. `strict-origin-when-cross-origin`. |
| `HTTP/Permissions-Policy` | Least-privilege browser-feature policy. |
| `HTTP/Access-Control-Allow-Origin` / `-Methods` / `-Headers` / `-Credentials` / `-Max-Age` | CORS set. |
| `HTTP/SameSite/Default` | Cookie SameSite for all cookies: `None` / `Lax` / `Strict`. Default `Lax`. |
| `HTTP/SameSite/{CookieName}` | SameSite for a specific cookie. |

> ⚠️ **Platform-managed — do not try to set these:** `Cache-Control` and
> `HTTP/Strict-Transport-Security` (HSTS) are managed by the platform; a site setting has no effect.

## Search

| Setting | Effect |
|---|---|
| `Search/EnableDataverseSearch` | `true` to use Dataverse search (Lucene.NET search is deprecated). |

## Formatting (community-cataloged — verify per version)

| Setting | Effect |
|---|---|
| `DateTime/DateFormat` | Site-wide display + picker date format (e.g. `dd/MM/yyyy`). |
| `DateTime/TimeFormat` | Site-wide time format (e.g. `HH:mm tt`). |

## Lookup modal (community-cataloged — verify per version)

| Setting / snippet | Effect |
|---|---|
| `Portal/Lookup/Modal/Size` | Lookup modal size (`Small` / `Large`). |
| `Portal/Lookup/Modal/Grid/PageSize` | Rows per page in lookup grids (default 10). |
| `Portal/Lookup/Modal/Title` | Lookup modal heading text. |
| `Portal/Lookup/Modal/Grid/Search/PlaceholderText` *(snippet)* | Lookup search placeholder. |
| `Portal/Lookup/Modal/Grid/Search/TooltipText` *(snippet)* | Lookup search wildcard tooltip. |

## Registration / login paths (community-cataloged — verify per version)

Toggle each auth path independently (`Authentication/Registration/...`): `Enabled`,
`LocalLoginEnabled`, `ExternalLoginEnabled`, `OpenRegistrationEnabled`, `InvitationEnabled`,
`RememberMeEnabled`, `ResetPasswordEnabled`. Review these during a security audit — leaving open
registration on unintentionally is a common finding.

## Head / font injection (content snippets)

| Snippet | Effect |
|---|---|
| `Head/Bottom` | Inject markup/metadata at the end of `<head>`. |
| `Head/Fonts` | Add stylesheets/CSS to `<head>`. |

Auth-page copy snippets (`Account/SignIn/PageCopy`, `Account/Nav/SignIn`,
`Account/PasswordReset/ForgotPasswordFormHeading`, …) customize sign-in/reset text.

*Catalog credit: Oleksandr Olashyn (Dancing with CRM), who documents the obscure Power Pages
settings and snippets. Always confirm a setting still exists and behaves as described on your site
version.*
