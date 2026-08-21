# Power Pages Traditional-site toolkit

Skills for building, editing, integrating, and **securing** traditional **Power Pages** sites —
the Dataverse-backed Studio/Liquid sites on the **enhanced data model** (`mspp_*` tables +
`powerpagecomponent`). This is the traditional-site counterpart to Microsoft's
[code-site plugin](https://github.com/microsoft/power-platform-skills/blob/main/plugins/power-pages/README.md):
it covers the classic, non-code portals that plugin doesn't.

> Every skill assumes the shared backbone in
> [`references/traditional-site-editing-model.md`](references/traditional-site-editing-model.md) —
> the component storage model, the read-live-first rule, the robust-parse / PATCH technique, the
> shared auth pattern, and the cache-flush rule. Read it first.

## Skills

| Skill | What it does |
|---|---|
| **`/add-webpage`** | Create a web page (root + localized content `mspp_webpage` records) modeled on an existing page — template/parent/publishing/language, page body, and navigation. Handles the auto-created content page and validation-plugin quirks. |
| **`/edit-web-template`** | Safely edit a web template (`powerpagecomponent` type 8, `content` = `{"source"}`): read live → robust-parse → match-once-guarded edit → PATCH → flush. |
| **`/manage-web-files`** | Update web files (type 3 — CSS/JS/images) whose bytes live in the `filecontent` File column, plus the `?v=` URL cache-buster clients need. |
| **`/add-server-logic`** | Create/deploy server-side JavaScript via the type-35 (metadata) / type-15 (code) storage model. |
| **`/write-liquid`** | Write correct, safe Liquid — including the `nil != blank` trap, FetchXML guards, output escaping, and the `webapi.safeAjax` rule. |
| **`/integrate-webapi`** | Enable and safely consume the Power Pages Web API (`/_api/*`) for a table — the `Webapi/<table>/*` site settings and the mandatory `safeAjax` wrapper. |
| **`/table-permissions`** | Configure `mspp_entitypermission` and bind it to web roles — and **verify** bindings via the `mspp_entitypermission_webroleset` intersect (an `$expand` reads blind under a service principal). |
| **`/security-review`** | Audit a traditional site for the platform's real failure modes: stored XSS in templates/page JS, Web API over-exposure, table-permission gaps, anonymous access, CSP/headers, Liquid data leaks, and leaked secrets. |
| **`/flush-cache`** | Invalidate the portal cache so component changes actually show (`/_services/about`, Studio clear-cache, and the browser cache-buster). |

## Install (local)

```text
/plugin marketplace add D:\AI\powerpages-traditional-site
/plugin install powerpages-traditional-site@powerpages-traditional-site
```

Then invoke a skill by name (e.g. `/edit-web-template`) or just describe the task
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

## Layout

```
powerpages-traditional-site/
├─ plugin.json                         # plugin manifest
├─ .claude-plugin/marketplace.json     # local marketplace entry
├─ references/
│  └─ traditional-site-editing-model.md   # shared backbone (read first)
└─ skills/
   ├─ add-webpage/         add-server-logic/     integrate-webapi/
   ├─ edit-web-template/   write-liquid/         table-permissions/
   ├─ manage-web-files/    security-review/      flush-cache/
```
