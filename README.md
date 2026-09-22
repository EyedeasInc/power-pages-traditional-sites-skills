# Power Pages Traditional-site toolkit (Claude Code plugin)

Skills for **provisioning**, building, editing, integrating, and **securing** traditional **Power Pages** sites —
the Dataverse-backed Studio/Liquid sites on the **enhanced data model** (`mspp_*` tables +
`powerpagecomponent`). This is the traditional-site counterpart to Microsoft's
[code-site plugin](https://github.com/microsoft/power-platform-skills/blob/main/plugins/power-pages/README.md):
it covers the classic, non-code portals that plugin doesn't.

> Every skill assumes the shared backbone in
> [`references/traditional-site-editing-model.md`](references/traditional-site-editing-model.md) —
> the component storage model, the read-live-first rule, the robust-parse / PATCH technique, the
> shared auth pattern, and the cache-flush rule. Read it first.

## Skills

Skills are **noun-named** (the object, not a verb) so each covers its whole lifecycle — e.g.
`/pp-webpage` creates, edits, *and* deletes pages, not just "adds" one.

| Skill | What it does |
|---|---|
| **`/pp-website`** | Provision and run the **site itself** via the `pac power-pages` CLI (Preview): create a site from a template, list/inspect, start/stop/restart, convert trial→production, set visibility/security group, delete. The container; content lives in the skills below. |
| **`/pp-webpage`** | Create, edit, navigate, and delete web pages (root + localized content `mspp_webpage` records) — template/parent/publishing/language, page body, and web-link-set navigation. Handles the auto-created content page and validation-plugin quirks. |
| **`/pp-web-template`** | Create, edit, read, and delete web templates (`powerpagecomponent` type 8, `content` = `{"source"}`): read live → robust-parse → match-once-guarded edit → PATCH → flush. |
| **`/pp-web-file`** | Create, update, and delete web files (type 3 — CSS/JS/images) whose bytes live in the `filecontent` File column, plus the `?v=` URL cache-buster clients need. |
| **`/pp-server-logic`** | Create, edit, deploy, and remove server-side JavaScript via the type-35 (metadata) / type-15 (code) storage model. |
| **`/pp-liquid`** | Write correct, safe Liquid — including the `nil != blank` trap, FetchXML guards, output escaping, and the `webapi.safeAjax` rule. |
| **`/pp-webapi`** | Enable, consume, audit, and disable the Power Pages Web API (`/_api/*`) for a table — the `Webapi/<table>/*` site settings and the mandatory `safeAjax` wrapper. |
| **`/pp-table-permissions`** | Configure `mspp_entitypermission` and bind it to web roles — and **verify** bindings via the `mspp_entitypermission_webroleset` intersect (an `$expand` reads blind under a service principal). |
| **`/pp-security-review`** | Audit a traditional site for the platform's real failure modes — stored XSS, Web API over-exposure, table-permission gaps, anonymous access, CSP/headers, Liquid data leaks, secrets — and run the platform's own `pac power-pages` quick/deep scans first. |
| **`/pp-cache`** | Invalidate the portal cache so component changes actually show (`/_services/about`, Studio clear-cache, and the browser cache-buster). |

## Install (local)

```text
/plugin marketplace add D:\AI\powerpages-traditional-site
/plugin install powerpages-traditional-site@powerpages-traditional-site
```

Then invoke a skill by name (e.g. `/pp-web-template`) or just describe the task
("update the portal CSS", "why isn't my template change showing", "review my portal's security").

> Prefer one as a personal skill instead of a plugin? Copy the individual `skills/<name>/`
> folder to `~/.claude/skills/<name>/`.

## Requirements

- A Power Pages **enhanced data model** site and Dataverse access — a **Dataverse MCP** (preferred
  for reads; respects security roles), or a Web API **bearer token**.
- The bundled Python scripts share one auth pattern: they reuse a workspace `scripts/auth.py`
  exposing `get_token()` (the `dv-connect` pattern) if present, otherwise read a bearer token from
  the `DATAVERSE_TOKEN` env var. `DATAVERSE_URL` comes from a `--url` arg or the env var.
- These skills **never** batch-upload (`pac pages upload`) — they read the live component and PATCH
  it individually, which is safe alongside Studio edits.
- **`/pp-website` is the exception:** it drives the `pac power-pages` CLI (Preview), which uses a
  **`pac auth`** profile + `--environment`, not the `DATAVERSE_TOKEN` the content skills use. Run
  `pac auth create` / `pac auth list` first. Requires the Power Platform CLI (`pac`).

## Layout

```
powerpages-traditional-site/
├─ plugin.json                         # plugin manifest
├─ .claude-plugin/marketplace.json     # local marketplace entry
├─ references/
│  └─ traditional-site-editing-model.md   # shared backbone (read first)
└─ skills/
   ├─ pp-website/         pp-server-logic/      pp-table-permissions/
   ├─ pp-webpage/         pp-liquid/            pp-security-review/
   ├─ pp-web-template/    pp-webapi/            pp-cache/
   └─ pp-web-file/
```
