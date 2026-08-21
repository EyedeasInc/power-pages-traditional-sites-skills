# Traditional (enhanced-data-model) Power Pages — editing model

Shared backbone for every skill in this plugin. Read this first; individual skills assume it.

## What "traditional site" means here

A **traditional Power Pages site** is a Studio/Liquid site built on the **enhanced data model**
(`mspp_*` Dataverse tables) — web pages, web templates, web files, content snippets, site
settings, web roles, table permissions, and Liquid. This is **not** a code site (React/Vite SPA);
those are covered by Microsoft's `power-pages` code-site plugin. This plugin fills the gap for the
classic, Dataverse-backed sites.

> Legacy sites use the **standard data model** (`adx_*` tables). The techniques transfer, but the
> table/column names differ (`adx_webtemplate.adx_source` etc.). These skills target `mspp_*`.

## Two surfaces onto the same components

Enhanced-model components can be touched two ways. Know which a skill uses:

1. **Dedicated `mspp_*` tables** — `mspp_webpage`, `mspp_webrole`, `mspp_entitypermission`,
   `mspp_sitesetting`, `mspp_weblinkset`… Use these for records that have first-class tables
   (pages, roles, permissions, settings, nav).
2. **The unified `powerpagecomponent` table** — the surface the Studio and the Power Pages
   management API use for *content* components. Rows are distinguished by
   `powerpagecomponenttype` and carry a `content` JSON string (and/or a `filecontent` File
   column). This is what you PATCH for **web templates, web files, and server logic**.

### `powerpagecomponent` types you will edit

| Type | Component | Where the payload lives |
|---|---|---|
| **8** | Web template | `content` = JSON **`{"source": "<liquid/html>", "mimetype": ...}`** |
| **3** | Web file (CSS/JS/image/binary) | bytes in the **`filecontent`** File column (base64 on the wire) |
| **15** | Server logic — **code** | `content` = JSON **`{"source": "<js>", "webroles": [...]}`** |
| **35** | Server logic — **metadata** | `content` = JSON (web roles, display name, description) |

Always scope by website — `_powerpagesiteid_value` on components, `_mspp_websiteid_value` on
`mspp_*` rows. One tenant/env can host several sites.

## Golden rules (learned the hard way)

1. **Read live before you edit — every time.** A local `src-control` / pac-download folder is a
   **stale snapshot**. GET the live component from Dataverse, apply your change onto *that*, then
   PATCH it back. Never patch on top of a local copy without refreshing first.
2. **Patch components individually via the Dataverse Web API. Never batch-upload.** Do not
   `pac pages upload` a whole site to push one change — it can clobber live edits made in Studio.
   Each skill PATCHes the single component it owns.
3. **Parse the component `content` robustly.** It is a JSON string. `json.loads(raw)` it
   **directly**. Do **not** `html.unescape()` it first — for most components that corrupts
   legitimate `&`/`"`/`<` inside the source and throws `JSONDecodeError`. Only fall back to
   `html.unescape` if the direct parse fails.
4. **PowerShell payload trap.** If you must push a component `source` from PowerShell, read the
   file with `[IO.File]::ReadAllText(...)` and serialize with
   `System.Web.Script.Serialization.JavaScriptSerializer`. `ConvertTo-Json (Get-Content -Raw)`
   **corrupts** the payload (double-encoding / newline mangling). In Python, `json.dumps` is fine.
5. **Apply edits with a match-once guard.** When you string/regex-replace inside a live `source`,
   assert the old fragment matches **exactly once** before writing; abort otherwise. This makes a
   drifted-live-copy fail safely instead of silently mis-patching.
6. **Cache-flush after content/template changes.** The portal serves components from cache; your
   PATCH won't show until the cache is invalidated. See the `flush-cache` skill.

## Auth pattern (shared by every bundled script)

Each script acquires a token the same way — reuse a workspace `scripts/auth.py` if present, else a
bearer token from the environment:

```python
def get_token():
    # 1) a workspace scripts/auth.py exposing get_token() (the dv-connect pattern)
    for p in (os.getcwd(), os.path.join(os.getcwd(), "scripts")):
        if os.path.exists(os.path.join(p, "auth.py")):
            sys.path.insert(0, p)
            try:
                from auth import get_token as _gt, load_env
                load_env(); return _gt()
            except Exception:
                pass
    # 2) env var DATAVERSE_TOKEN (a bearer token)
    t = os.environ.get("DATAVERSE_TOKEN")
    if t: return t
    sys.exit("No auth: provide a workspace scripts/auth.py (get_token) or set DATAVERSE_TOKEN.")
```

`DATAVERSE_URL` comes from a CLI arg or the env var of the same name. If a **Dataverse MCP** is
connected, prefer it for reads (it respects the caller's security role); use the Web API for the
File-column and bulk writes.

## Never commit secrets

These skills are generic tooling. Never hardcode a tenant id, site id, service-principal secret,
portal URL, or any customer specifics into a skill or script — take them as arguments/env vars.
