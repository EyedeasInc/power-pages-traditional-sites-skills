"""
deploy_server_logic.py — Deploy one server-logic JavaScript file to a traditional
(enhanced-data-model) Power Pages site via the `powerpagecomponent` storage model.

Server logic is server-side JavaScript that runs securely on the Power Pages runtime.
It is stored as TWO powerpagecomponent rows:

  Type 35 — server logic METADATA (display name, description, web roles).
            content = JSON.
  Type 15 — server logic CODE.
            content = JSON {"source": "<raw JS>", "webroles": [...]}.

Deploy strategy (read live first, patch the single component you own):
  1. Find the type-15 component with the same `name`.
  2. If it EXISTS  -> PATCH the type-15 `content` directly with
                     {"source": <js>, "webroles": <existing webroles>}.
  3. If it does NOT exist -> PATCH the type-35 record with
                     {"filecontent": base64(<js>)}. Power Pages detects the
                     filecontent and creates/updates the type-15 automatically.
                     (This branch needs the type-35 component id: --record-id.)

The site id (`_powerpagesiteid_value`) is resolved at runtime from an existing
component unless you pass --site.

Usage:
    # Update an existing server logic (type-15 already exists) — only --name + --js-file needed:
    python deploy_server_logic.py --name my-endpoint --js-file my-endpoint.js

    # First deploy of a new server logic (no type-15 yet) — provide the type-35 record id:
    python deploy_server_logic.py --name my-endpoint --js-file my-endpoint.js \
        --record-id <TYPE35_COMPONENT_ID>

    # Explicit environment + site, and a dry run:
    python deploy_server_logic.py --name my-endpoint --js-file my-endpoint.js \
        --url https://contoso.crm.dynamics.com --site <SITEID> --dry-run

Auth: reuses a workspace scripts/auth.py get_token() (the dv-connect pattern) if
present, else a bearer token from the DATAVERSE_TOKEN env var. DATAVERSE_URL comes
from --url or the env var of the same name.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "/api/data/v9.2"


# ── Auth (shared fallback: workspace auth.py OR DATAVERSE_TOKEN) ───────────────

def get_token():
    # 1) a workspace scripts/auth.py exposing get_token() (the dv-connect pattern)
    for p in (os.getcwd(), os.path.join(os.getcwd(), "scripts")):
        if os.path.exists(os.path.join(p, "auth.py")):
            sys.path.insert(0, p)
            try:
                from auth import get_token as _gt, load_env
                load_env()
                return _gt()
            except Exception:
                pass
    # 2) env var DATAVERSE_TOKEN (a bearer token)
    t = os.environ.get("DATAVERSE_TOKEN")
    if t:
        return t
    sys.exit("No auth: provide a workspace scripts/auth.py (get_token) or set DATAVERSE_TOKEN.")


# ── Dataverse Web API helpers ─────────────────────────────────────────────────

def dv_get(base, token, path):
    req = urllib.request.Request(base + path, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def dv_patch(base, token, path, payload):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "If-Match": "*",
        },
    )
    with urllib.request.urlopen(req) as r:
        return r.status


def resolve_site_id(base, token):
    """Resolve the powerpagesite id from any existing server-logic component."""
    data = dv_get(base, token, API + "/powerpagecomponents?" + urllib.parse.urlencode({
        "$filter": "powerpagecomponenttype eq 35",
        "$select": "_powerpagesiteid_value",
        "$top": "1",
    }))
    items = data.get("value", [])
    if items:
        return items[0].get("_powerpagesiteid_value")
    # Fallback: first site in the table.
    data2 = dv_get(base, token, API + "/powerpagesites?$select=powerpagesiteid&$top=1")
    sites = data2.get("value", [])
    return sites[0].get("powerpagesiteid") if sites else None


def find_type15(base, token, name):
    """Return (component_id, existing_webroles) for the type-15 code record, or (None, [])."""
    data = dv_get(base, token, API + "/powerpagecomponents?" + urllib.parse.urlencode({
        "$filter": f"powerpagecomponenttype eq 15 and name eq '{name}'",
        "$select": "powerpagecomponentid,content",
    }))
    items = data.get("value", [])
    if not items:
        return None, []
    rec = items[0]
    try:
        # content is a JSON string — parse it directly; do NOT html.unescape first.
        parsed = json.loads(rec.get("content") or "{}")
        webroles = parsed.get("webroles", [])
    except Exception:
        webroles = []
    return rec["powerpagecomponentid"], webroles


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Deploy a Power Pages server-logic JS file.")
    ap.add_argument("--name", required=True,
                    help="Server logic name (the `name` on the powerpagecomponent rows).")
    ap.add_argument("--js-file", required=True, help="Path to the server-side .js file to deploy.")
    ap.add_argument("--url", default=os.environ.get("DATAVERSE_URL"),
                    help="Dataverse environment URL (or set DATAVERSE_URL).")
    ap.add_argument("--site",
                    help="powerpagesite id. Resolved from an existing component if omitted.")
    ap.add_argument("--record-id",
                    help="Type-35 component id. Required ONLY for a first deploy "
                         "(when no type-15 exists yet).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be PATCHed without writing.")
    args = ap.parse_args()

    if not args.url:
        sys.exit("No Dataverse URL: pass --url or set DATAVERSE_URL.")
    base = args.url.rstrip("/")

    if not os.path.exists(args.js_file):
        sys.exit(f"JS file not found: {args.js_file}")
    with open(args.js_file, "rb") as f:
        js_bytes = f.read()
    js_source = js_bytes.decode("utf-8")

    token = get_token()

    print(f"Server logic : {args.name}")
    print(f"JS file      : {args.js_file} ({len(js_bytes)} bytes)")

    # Read live: is there already a type-15 code record?
    type15_id, existing_webroles = find_type15(base, token, args.name)

    if type15_id:
        # ── Update path: PATCH the type-15 code record directly. ──
        content = json.dumps({"source": js_source, "webroles": existing_webroles})
        path = f"{API}/powerpagecomponents({type15_id})"
        payload = {"content": content}
        print(f"Type-15 ID   : {type15_id} (patching code record directly)")
        print(f"Web roles    : preserving {len(existing_webroles)} existing role(s)")
    else:
        # ── Create path: PATCH the type-35 with filecontent; Power Pages spawns the type-15. ──
        if not args.record_id:
            sys.exit("No type-15 exists yet for this name. Pass --record-id "
                     "<TYPE35_COMPONENT_ID> so the code record can be created.")
        site_id = args.site or resolve_site_id(base, token)
        if not site_id:
            sys.exit("Could not resolve powerpagesite id. Pass --site.")
        print(f"Type-15 ID   : none — patching type-35 {args.record_id} with filecontent")
        print(f"Site ID      : {site_id} (Power Pages will create the type-15)")
        js_b64 = base64.b64encode(js_bytes).decode("ascii")
        content = json.dumps({"filecontent": js_b64})
        path = f"{API}/powerpagecomponents({args.record_id})"
        payload = {
            "powerpagecomponentid": args.record_id,
            "name": args.name,
            "powerpagecomponenttype": 35,
            "content": content,
            "powerpagesiteid@odata.bind": f"/powerpagesites({site_id})",
        }

    if args.dry_run:
        print("DRY RUN      : PATCH " + path)
        print(json.dumps(payload, indent=2)[:1200])
        return

    try:
        status = dv_patch(base, token, path, payload)
        print(f"PATCH HTTP   : {status} — OK")
    except urllib.error.HTTPError as e:
        print(f"PATCH HTTP   : {e.code} — ERROR")
        print(e.read().decode()[:800])
        sys.exit(1)

    print("Done. Remember to clear the portal cache so the runtime picks up the new code.")


if __name__ == "__main__":
    main()
