---
name: pp-serverlogic
description: "Create, edit, deploy, and remove server logic — server-side JavaScript that runs securely on the Power Pages runtime — on a traditional (enhanced-data-model, mspp_*) site through the powerpagecomponent storage model. A server logic is TWO powerpagecomponent rows: a type-35 METADATA record and a type-15 CODE record whose content is JSON {\"source\": \"<js>\", \"webroles\": [...]}. WHEN: add, create, edit, or update server logic, deploy server-side JavaScript, create or change a Power Pages server script, add an API endpoint on the portal, push server logic, change the web roles on a server script, delete server logic, move browser code to the server, run code securely on the runtime, create a server-side handler."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Server logic on a Power Pages site — create, edit, deploy, remove

Create and deploy **server logic** — server-side JavaScript that runs on the Power Pages
runtime — on a traditional **enhanced-data-model** site by writing the `powerpagecomponent`
records directly. Server logic executes **server-side** (secrets, privileged Dataverse calls,
validation the browser can't be trusted to do), and is invoked from the site. It is the
traditional-site analog of a code-site's server-side handler / API endpoint.

Read `references/traditional-site-editing-model.md` first — this skill assumes the shared
`powerpagecomponent` model, the read-live-first rule, and the auth pattern described there.

## The model: server logic is TWO components

Unlike a web page (two `mspp_webpage` rows), server logic lives entirely in the unified
`powerpagecomponent` table as **two rows sharing the same `name`**, distinguished by
`powerpagecomponenttype`:

| Type | Role | `content` (a JSON string) |
|---|---|---|
| **35** | **Metadata** — display name, description, web-role bindings | JSON metadata |
| **15** | **Code** — the actual server-side JavaScript | **`{"source": "<raw JS>", "webroles": [...]}`** |

The runtime executes the JS in the **type-15** `content.source`. The **type-35** row is the
Studio-facing metadata; when you push code *through* it (via `filecontent`), Power Pages
generates or refreshes the matching type-15 for you. Both rows are scoped to one site by
`_powerpagesiteid_value`.

> The `webroles` array on the type-15 `content` controls **who can invoke** the logic. Preserve
> it on every update — clobbering it to `[]` silently makes the endpoint unreachable for those
> roles. The deploy strategy below reads it back and re-sends it.

## Step 1 — Write the server-side JavaScript

Author the logic as a plain `.js` file. It runs on the server, so it can do things browser code
must not — read a secret, call Dataverse with elevated scope, enforce a rule authoritatively.
Keep it a self-contained handler; don't reference browser globals (`window`, `document`).

```js
// hello-endpoint.js — invoked server-side from the portal
module.exports = async function (context) {
  const name = (context.request && context.request.query.name) || "world";
  context.response.json({ message: "Hello, " + name });
};
```

(Match whatever handler shape your site's existing server logic uses — read a working one's
type-15 `content.source` to copy the signature. The point of this skill is the **storage +
deploy model**, not the handler API.)

## Step 2 — Resolve the site id (read live)

Every component write needs `_powerpagesiteid_value`. Don't hardcode it — read it back from an
existing server-logic component so you're always targeting the right site:

```
GET /api/data/v9.2/powerpagecomponents?$filter=powerpagecomponenttype eq 35
    &$select=_powerpagesiteid_value&$top=1
```

Fallback if the site has no server logic yet: `GET /api/data/v9.2/powerpagesites?$select=powerpagesiteid&$top=1`.

## Step 3 — Deploy: check for an existing type-15, then branch

**Read live first.** Look for a type-15 code record with the same `name`:

```
GET /api/data/v9.2/powerpagecomponents?$filter=powerpagecomponenttype eq 15 and name eq '<NAME>'
    &$select=powerpagecomponentid,content
```

Parse its `content` as JSON directly (do **not** `html.unescape` it first) and keep the
`webroles` array. Then branch:

**A. Type-15 EXISTS → PATCH the code record directly.** This is the normal update path. Send the
new source and re-send the web roles you just read:

```jsonc
PATCH /api/data/v9.2/powerpagecomponents(<TYPE15_ID>)     // If-Match: *
{
  "content": "{\"source\":\"<raw JS>\",\"webroles\":[<existing roles>]}"
}
```

`content` is itself a **JSON string** — serialize `{"source": js, "webroles": existing}` and put
the resulting string in the `content` field. In Python, `json.dumps` twice (once for the inner
object, once for the outer PATCH body) is correct; don't hand-escape.

**B. No type-15 yet → PATCH the type-35 with `filecontent`.** On a first deploy the code record
may not exist. PATCH the **type-35** metadata record, handing Power Pages the JS as base64 in a
`filecontent` key inside `content`. The platform detects it and **auto-creates/updates the
type-15** for you:

```jsonc
PATCH /api/data/v9.2/powerpagecomponents(<TYPE35_ID>)     // If-Match: *
{
  "powerpagecomponentid":       "<TYPE35_ID>",
  "name":                       "<NAME>",
  "powerpagecomponenttype":     35,
  "content":                    "{\"filecontent\":\"<base64(js)>\"}",
  "powerpagesiteid@odata.bind": "/powerpagesites(<SITEID>)"
}
```

> Why two branches: once the type-15 exists, patching it directly is precise and preserves the
> web roles. Before it exists, the `filecontent` route on the type-35 is how you get Power Pages
> to materialize the code record in the first place.

## Step 4 — Publish & verify

1. **Clear the portal cache** (`/_services/about` → **Clear cache**). The runtime serves logic
   from cache; your PATCH won't take effect until it's flushed.
2. **Invoke it** from the site the way the logic is wired (its route/endpoint) and confirm the
   response. If it 401/403s, check the `webroles` on the type-15 `content` — an empty array locks
   everyone out.
3. If nothing changed, re-GET the type-15 and confirm `content.source` is your new code (catches
   a create-path PATCH that landed but hasn't regenerated the type-15 yet).

## Bundled helper

`scripts/deploy_server_logic.py` does Steps 2–3 end to end: resolves the site id, finds the
type-15 by name, and PATCHes the right record — the type-15 directly (preserving its web roles)
if it exists, otherwise the type-35 with `filecontent`.

```
# Update an existing server logic (type-15 already exists):
python scripts/deploy_server_logic.py --name hello-endpoint --js-file hello-endpoint.js

# First deploy (no type-15 yet) — supply the type-35 component id:
python scripts/deploy_server_logic.py --name hello-endpoint --js-file hello-endpoint.js \
  --record-id <TYPE35_COMPONENT_ID>

# Explicit env + site, dry run:
python scripts/deploy_server_logic.py --name hello-endpoint --js-file hello-endpoint.js \
  --url https://contoso.crm.dynamics.com --site <SITEID> --dry-run
```

Auth: imports `get_token` from a workspace `scripts/auth.py` if present (the dv-connect pattern),
otherwise reads a bearer token from `DATAVERSE_TOKEN`. `DATAVERSE_URL` comes from `--url` or the
env var. `--dry-run` prints the target and payload without writing.

## Field & option reference

- Table: `powerpagecomponent` (unified content surface — **not** an `mspp_*` or `adx_*` row).
- Discriminator: `powerpagecomponenttype` — **35** = server-logic metadata, **15** = server-logic code.
- Key columns: `name` (shared across the pair), `content` (JSON string), `filecontent` (File
  column, base64 on the wire), `_powerpagesiteid_value` (owning site).
- The code lives in the type-15 `content.source`; access control lives in `content.webroles`.
- Always operate per **site** (`_powerpagesiteid_value`) — one env can host several sites.
- Quirks to remember: (1) parse `content` as JSON directly, never `html.unescape` first;
  (2) preserve `webroles` on every update; (3) no type-15 yet → push via the type-35 `filecontent`
  and let Power Pages create it; (4) clear the cache before verifying.
