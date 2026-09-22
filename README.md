# Power Pages Traditional-site toolkit

Skills for **provisioning**, building, editing, integrating, and **securing** traditional **Power Pages** sites —
the Dataverse-backed Studio/Liquid sites on the **enhanced data model** (`mspp_*` tables +
`powerpagecomponent`). This is the traditional-site counterpart to Microsoft's
[code-site plugin](https://github.com/microsoft/power-platform-skills/blob/main/plugins/power-pages/README.md):
it covers the classic, non-code portals that plugin doesn't.

> Every content skill assumes the shared backbone in
> [`references/traditional-site-editing-model.md`](references/traditional-site-editing-model.md) —
> the component storage model, the read-live-first rule, the robust-parse / PATCH technique, the
> shared auth pattern, and the cache-flush rule. Read it first.

## Skills

Skills are **noun-named** (the object, not a verb) so each covers its whole lifecycle — e.g.
`/pp-webpage` creates, edits, *and* deletes pages, not just "adds" one. Object skills are one
word (`/pp-webtemplate`); action/CLI skills keep a hyphen (`/pp-datamodel-migrate`).

### Content authoring — `mspp_*` / `powerpagecomponent`

| Skill | What it does |
|---|---|
| **`/pp-webpage`** | Create, edit, navigate, and delete web pages (root + localized content `mspp_webpage` records). Handles the auto-created content page and validation-plugin quirks. |
| **`/pp-webtemplate`** | Create, edit, read, and delete web templates (`powerpagecomponent` type 8): read live → robust-parse → match-once-guarded edit → PATCH → flush. |
| **`/pp-webfile`** | Create, update, and delete web files (type 3 — CSS/JS/images) whose bytes live in the `filecontent` File column, plus the `?v=` cache-buster. |
| **`/pp-contentsnippet`** | Create, edit, and delete content snippets (`mspp_contentsnippet`) — the named, localizable text/HTML blocks templates pull in via Liquid. |
| **`/pp-weblink`** | Manage navigation — web link sets (`mspp_weblinkset`) and links (`mspp_weblink`): menus, reordering, dropdowns, page/external links. |
| **`/pp-serverlogic`** | Create, edit, deploy, and remove server-side JavaScript via the type-35 (metadata) / type-15 (code) storage model. |
| **`/pp-liquid`** | Write correct, safe Liquid — the `nil != blank` trap, FetchXML guards, output escaping, and the `webapi.safeAjax` rule. |

### Data & Web API

| Skill | What it does |
|---|---|
| **`/pp-webapi`** | Enable, consume, audit, and disable the Power Pages Web API (`/_api/*`) for a table — the `Webapi/<table>/*` site settings and the mandatory `safeAjax` wrapper. |

### Access & security

| Skill | What it does |
|---|---|
| **`/pp-webrole`** | Create, assign, and manage web roles (`mspp_webrole`) — the access groups everything else binds to (Anonymous / Authenticated / custom). |
| **`/pp-tablepermission`** | Configure `mspp_entitypermission` and bind it to web roles — and **verify** bindings via the `mspp_entitypermission_webroleset` intersect. |
| **`/pp-headers`** | Configure security response headers / CSP via `mspp_sitesetting`, then verify them on the wire. |
| **`/pp-firewall`** | Inspect and configure the WAF and IP allow-list in front of a production site via `pac power-pages` (Preview). |
| **`/pp-securityreview`** | Audit the platform's real failure modes — XSS, Web API over-exposure, permission gaps, anonymous access, headers, Liquid leaks, secrets — and run the `pac power-pages` quick/deep scans first. |

### Site lifecycle & CLI — `pac`

| Skill | What it does |
|---|---|
| **`/pp-website`** | Provision and run the site itself via `pac power-pages` (Preview): create from a template, list/inspect, start/stop/restart, convert trial→production, visibility, delete. |
| **`/pp-datamodel-migrate`** | Migrate a site Standard(`adx_`)→Enhanced(`mspp_`) via `pac pages migrate-datamodel` — the prerequisite the content skills assume; status/revert too. |
| **`/pp-download`** | Download site content to disk (`pac pages download` / `clone`) for backup, diff, and source control. |
| **`/pp-upload`** | Upload/promote site content across environments (`pac pages upload`) with deployment profiles. |
| **`/pp-bootstrap-migrate`** | Bootstrap 3→5 for Liquid templates via `pac pages bootstrap-migrate`, plus the residual structural fixes. |

### Utility

| Skill | What it does |
|---|---|
| **`/pp-cache`** | Invalidate the portal cache so component changes actually show (`/_services/about`, Studio clear-cache, cache-buster). |

## Install (local)

```text
/plugin marketplace add D:\AI\powerpages-traditional-site
/plugin install powerpages-traditional-site@powerpages-traditional-site
```

Then invoke a skill by name (e.g. `/pp-webtemplate`) or just describe the task
("update the portal CSS", "why isn't my template change showing", "review my portal's security").

> Prefer one as a personal skill instead of a plugin? Copy the individual `skills/<name>/`
> folder to `~/.claude/skills/<name>/`.

## Requirements

- A Power Pages **enhanced data model** site and Dataverse access — a **Dataverse MCP** (preferred
  for reads; respects security roles), or a Web API **bearer token**.
- The bundled Python scripts share one auth pattern: they reuse a workspace `scripts/auth.py`
  exposing `get_token()` (the `dv-connect` pattern) if present, otherwise read a bearer token from
  the `DATAVERSE_TOKEN` env var. `DATAVERSE_URL` comes from a `--url` arg or the env var.
- **Two auth models.** The **content** skills (pages, templates, web files, roles, permissions,
  snippets, headers) use the Dataverse Web API (MCP or `DATAVERSE_TOKEN`) and patch **live**
  components individually — they never batch-upload, so they're safe alongside Studio edits. The
  **CLI** skills (`pp-website`, `pp-datamodel-migrate`, `pp-download`, `pp-upload`,
  `pp-bootstrap-migrate`, `pp-firewall`) drive `pac pages` / `pac power-pages`, which use a
  **`pac auth`** profile + `--environment`. Run `pac auth create` / `pac auth list` first; requires
  the Power Platform CLI (`pac`). Several `pac power-pages` commands are **Preview**.
- `pp-upload` is the **bulk** promotion tool (whole folder) for moving a site between
  environments — distinct from the live single-component patch the content skills do.

## Layout

```
powerpages-traditional-site/
├─ plugin.json                         # plugin manifest
├─ .claude-plugin/marketplace.json     # local marketplace entry
├─ references/
│  └─ traditional-site-editing-model.md   # shared backbone (read first)
└─ skills/
   ├─ pp-webpage/          pp-webtemplate/       pp-webfile/
   ├─ pp-contentsnippet/   pp-weblink/           pp-serverlogic/
   ├─ pp-liquid/           pp-webapi/            pp-webrole/
   ├─ pp-tablepermission/  pp-headers/           pp-firewall/
   ├─ pp-securityreview/   pp-website/           pp-datamodel-migrate/
   ├─ pp-download/         pp-upload/            pp-bootstrap-migrate/
   └─ pp-cache/
```
