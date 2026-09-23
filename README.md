# Power Pages Traditional-site toolkit (Claude Code plugin)

Skills for **provisioning**, building, integrating, and **securing** traditional **Power Pages** sites —
the Dataverse-backed Studio/Liquid sites on the **enhanced data model** (`mspp_*` tables +
`powerpagecomponent`). This is the traditional-site counterpart to Microsoft's
[code-site plugin](https://github.com/microsoft/power-platform-skills/blob/main/plugins/power-pages/README.md):
it covers the classic, non-code portals that plugin doesn't.

> Community-authored, led by [Zero to Hero](https://fromzerotoheroes.com). Not a Microsoft
> product. Built on the documented Dataverse Web API + `pac` CLI surface for enhanced-data-model
> sites.

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
| **`/pp-webpage`** | Create, edit, navigate, and delete web pages (root + localized content `mspp_webpage` records). |
| **`/pp-pagetemplate`** | Create, edit, and delete page templates (`mspp_pagetemplate`) — the required link between a page and its web-template layout. |
| **`/pp-webtemplate`** | Create, edit, read, and delete web templates (`powerpagecomponent` type 8): read live → robust-parse → guarded edit → PATCH → flush. |
| **`/pp-webfile`** | Create, update, and delete web files (type 3 — CSS/JS/images) whose bytes live in the `filecontent` File column. |
| **`/pp-contentsnippet`** | Create, edit, and delete content snippets (`mspp_contentsnippet`) — named, localizable text/HTML blocks. |
| **`/pp-serverlogic`** | Create, edit, deploy, and remove server-side JavaScript via the type-35 / type-15 storage model. |
| **`/pp-liquid`** | Write correct, safe Liquid — the `nil != blank` trap, FetchXML guards, output escaping, `safeAjax`. |

### Navigation & routing

| Skill | What it does |
|---|---|
| **`/pp-weblink`** | Manage navigation — web link sets (`mspp_weblinkset`) and links (`mspp_weblink`): menus, dropdowns, page/external links. |
| **`/pp-sitemarker`** | Manage site markers (`mspp_sitemarker`) — named page references Liquid resolves (`{{ sitemarkers[…] }}`). |
| **`/pp-redirect`** | Manage URL redirects (`mspp_redirect`) — map inbound URLs to a page/marker/external target with 301/302. |

### Forms, lists & data

| Skill | What it does |
|---|---|
| **`/pp-basicform`** | Basic forms (`mspp_entityform`) — insert/edit/read-only record forms: record source, on-success/redirect, file upload, record actions, per-field metadata, custom JS, AI form-fill. |
| **`/pp-list`** | Lists (`mspp_entitylist`) — record grids from saved views: toolbar/row actions, my/account filters, map/calendar/modern views, search, and AI natural-language search + list summary. |
| **`/pp-multistepform`** | Multistep forms (`mspp_webform` + steps) — wizards: step types & branching, progress indicator, per-field metadata, session/edit-expiry, custom JS. |
| **`/pp-webapi`** | Enable, consume, audit, and disable the Power Pages Web API (`/_api/*`) for a table. |

### Access & security

| Skill | What it does |
|---|---|
| **`/pp-webrole`** | Create, assign, and manage web roles (`mspp_webrole`) — the access groups everything binds to. |
| **`/pp-tablepermission`** | Configure `mspp_entitypermission` and bind it to web roles; verify via the intersect. |
| **`/pp-columnpermission`** | Column-level security (`mspp_columnpermissionprofile` + `mspp_columnpermission`) within a table permission. |
| **`/pp-pageaccessrule`** | Page-level authorization (`mspp_webpageaccesscontrolrule`) — restrict/grant a page to web roles. |
| **`/pp-headers`** | Configure security response headers / CSP via `mspp_sitesetting`, then verify them on the wire. |
| **`/pp-firewall`** | Inspect and configure the WAF and IP allow-list in front of a production site via `pac power-pages` (Preview). |
| **`/pp-securityreview`** | Audit the platform's real failure modes and run the `pac power-pages` quick/deep scans first. |

### Site lifecycle & CLI — `pac`

| Skill | What it does |
|---|---|
| **`/pp-website`** | Provision and run the site itself via `pac power-pages` (Preview): create, list, start/stop/restart, visibility, delete. |
| **`/pp-datamodel-migrate`** | Migrate a site Standard(`adx_`)→Enhanced(`mspp_`) via `pac pages migrate-datamodel` — the prerequisite the content skills assume. |
| **`/pp-download`** | Download site content to disk (`pac pages download` / `clone`) for backup, diff, source control. |
| **`/pp-upload`** | Upload/promote site content across environments (`pac pages upload`) with deployment profiles. |
| **`/pp-bootstrap-migrate`** | Bootstrap 3→5 for Liquid templates via `pac pages bootstrap-migrate`, plus residual fixes. |

### Utility

| Skill | What it does |
|---|---|
| **`/pp-cache`** | Invalidate the portal cache so component changes actually show. |

## Install (local)

```text
/plugin marketplace add D:\AI\powerpages-traditional-site
/plugin install powerpages-traditional-site@powerpages-traditional-site
```

Then invoke a skill by name (e.g. `/pp-webtemplate`) or just describe the task
("add a members-only page", "put a contact form on the home page", "why isn't my template change showing").

> Prefer one as a personal skill instead of a plugin? Copy the individual `skills/<name>/`
> folder to `~/.claude/skills/<name>/`.

## Requirements

- A Power Pages **enhanced data model** site and Dataverse access — a **Dataverse MCP** (preferred
  for reads; respects security roles), or a Web API **bearer token**.
- The bundled Python scripts share one auth pattern: they reuse a workspace `scripts/auth.py`
  exposing `get_token()` (the `dv-connect` pattern) if present, otherwise read a bearer token from
  the `DATAVERSE_TOKEN` env var. `DATAVERSE_URL` comes from a `--url` arg or the env var.
- **Two auth models.** The **content** skills use the Dataverse Web API (MCP or `DATAVERSE_TOKEN`)
  and patch **live** components individually — they never batch-upload, so they're safe alongside
  Studio edits. The **CLI** skills (`pp-website`, `pp-datamodel-migrate`, `pp-download`,
  `pp-upload`, `pp-bootstrap-migrate`, `pp-firewall`) drive `pac pages` / `pac power-pages`, which
  use a **`pac auth`** profile + `--environment`. Run `pac auth create` / `pac auth list` first;
  requires the Power Platform CLI (`pac`). Several `pac power-pages` commands are **Preview**.
- `pp-upload` is the **bulk** promotion tool (whole folder) for moving a site between
  environments — distinct from the live single-component patch the content skills do.

## Layout

```
powerpages-traditional-site/
├─ plugin.json                         # plugin manifest
├─ .claude-plugin/marketplace.json     # local marketplace entry
├─ agents/                             # read-only specialists (spawned by skills)
│  ├─ security-auditor.md
│  └─ web-template-architect.md
├─ hooks/                              # automatic reminders
│  ├─ hooks.json                       # PostToolUse(Skill) → cache/permission reminder
│  └─ skill_reminder.py
├─ references/                         # shared knowledge (MS Learn + community, cited)
│  ├─ traditional-site-editing-model.md   # shared backbone (read first)
│  ├─ webapi-field-configuration.md
│  ├─ security-model.md
│  ├─ web-template-components.md
│  ├─ server-logic-objects.md
│  ├─ site-settings-catalog.md
│  └─ community-credits.md
└─ skills/                             # 27 skills
   ├─ Content:     pp-webpage/ pp-pagetemplate/ pp-webtemplate/ pp-webfile/
   │               pp-contentsnippet/ pp-serverlogic/ pp-liquid/
   ├─ Nav/routing: pp-weblink/ pp-sitemarker/ pp-redirect/
   ├─ Forms/data:  pp-basicform/ pp-list/ pp-multistepform/ pp-webapi/
   ├─ Security:    pp-webrole/ pp-tablepermission/ pp-columnpermission/
   │               pp-pageaccessrule/ pp-headers/ pp-firewall/ pp-securityreview/
   ├─ Lifecycle:   pp-website/ pp-datamodel-migrate/ pp-download/ pp-upload/ pp-bootstrap-migrate/
   └─ Utility:     pp-cache/
```

## Agents, hooks & references

- **Agents** (`agents/`) — read-only specialists a skill can spawn for a focused, isolated job:
  `security-auditor` (deep security audit, from `pp-securityreview`) and `web-template-architect`
  (reusable-component / Liquid design, from `pp-webtemplate` / `pp-webpage` / `pp-pagetemplate`).
  Reference them by scoped name, e.g. `@powerpages-traditional-site:security-auditor`.
- **Hooks** (`hooks/`) — a `PostToolUse(Skill)` reminder that, after a content-mutating `pp-*` skill,
  nudges you to flush the portal cache (`/pp-cache`) and confirm table permissions + web roles.
- **References** (`references/`) — shared knowledge grounded in **Microsoft Learn** (authoritative),
  cross-checked against Microsoft's official Power Pages plugin, and enriched with credited community
  best practices. Each skill's *"Microsoft docs & shared references"* section points into these.

## Sources & community credits

Knowledge is grounded first in Microsoft Learn, then enriched with field-tested insight from the
Power Pages community — paraphrased, credited, and (where they conflict with Microsoft) corrected in
Microsoft's favor. Full list in [`references/community-credits.md`](references/community-credits.md):
Nick Doelman, Nicholas Hayduk, Oleksandr Olashyn, Ulrikke Akerbak, Tino Rabe, Michel Mendes, Franco
Musso. Community-led by [Zero to Hero](https://fromzerotoheroes.com); not a Microsoft product.
