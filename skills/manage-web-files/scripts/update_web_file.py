#!/usr/bin/env python3
"""
update_web_file.py — update the bytes of a Power Pages WEB FILE (enhanced data
model, powerpagecomponent type 3) live via the Dataverse Web API, and optionally
bump a `?v=` cache-buster where the file is referenced in a web template.

A web file's payload is the raw bytes in the `filecontent` File column — NOT the
`content` {"source"} JSON that web templates (type 8) use. This tool:
  1. resolves the web file (by --id, or by --name + --site),
  2. reads the local file bytes,
  3. PATCHes the filecontent File column (octet-stream, base64 on the wire),
  4. optionally increments the `?v=N` next to the file reference in a named
     web template's source (match-once guarded).

Auth: reuses a workspace scripts/auth.py get_token() if present (the dv-connect
pattern), else a bearer token from DATAVERSE_TOKEN. DATAVERSE_URL from --url or env.

Examples
--------
  # Replace bytes by component id:
  python update_web_file.py --url https://org.crm.dynamics.com \
    --id 00000000-0000-0000-0000-000000000000 --file ./theme.css \
    --content-type text/css

  # Resolve by name within a site, and bump the cache-buster in the "Theme" template:
  python update_web_file.py --url https://org.crm.dynamics.com \
    --site 11111111-1111-1111-1111-111111111111 --name theme.css \
    --file ./theme.css --content-type text/css --bump-template "Theme"

  # Preview only:
  python update_web_file.py --url ... --id ... --file ./app.js \
    --content-type application/javascript --dry-run
"""
import argparse
import mimetypes
import os
import re
import sys
import json
from pathlib import Path

import requests

API_VERSION = "v9.2"


# --------------------------------------------------------------------------- #
# Auth (shared pattern — see references/traditional-site-editing-model.md)
# --------------------------------------------------------------------------- #
def get_token():
    # 1) a workspace scripts/auth.py exposing get_token() (the dv-connect pattern)
    for p in (os.getcwd(), os.path.join(os.getcwd(), "scripts")):
        if os.path.exists(os.path.join(p, "auth.py")):
            sys.path.insert(0, p)
            try:
                from auth import get_token as _gt  # type: ignore
                try:
                    from auth import load_env  # type: ignore
                    load_env()
                except Exception:
                    pass
                return _gt()
            except Exception:
                pass
    # 2) env var DATAVERSE_TOKEN (a bearer token)
    t = os.environ.get("DATAVERSE_TOKEN")
    if t:
        return t
    sys.exit("No auth: provide a workspace scripts/auth.py (get_token) or set DATAVERSE_TOKEN.")


def resolve_url(cli_url):
    url = cli_url or os.environ.get("DATAVERSE_URL")
    if not url:
        sys.exit("No Dataverse URL: pass --url or set DATAVERSE_URL.")
    return url.rstrip("/")


def _headers(token, write=False):
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    if write:
        h["Content-Type"] = "application/json"
    return h


# --------------------------------------------------------------------------- #
# Locate the web file (powerpagecomponenttype eq 3)
# --------------------------------------------------------------------------- #
def find_web_file(api, token, name, site_id):
    filt = f"powerpagecomponenttype eq 3 and name eq '{name}'"
    if site_id:
        filt += f" and _powerpagesiteid_value eq {site_id}"
    r = requests.get(
        f"{api}/powerpagecomponents",
        headers=_headers(token),
        params={"$filter": filt,
                "$select": "powerpagecomponentid,name,_powerpagesiteid_value"},
    )
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        sys.exit(f"No web file (type 3) named '{name}'"
                 + (f" in site {site_id}" if site_id else "") + ".")
    if len(rows) > 1:
        ids = ", ".join(x["powerpagecomponentid"] for x in rows)
        sys.exit(f"Ambiguous: {len(rows)} web files named '{name}' ({ids}). "
                 f"Pass --site to scope, or --id to target one.")
    return rows[0]["powerpagecomponentid"]


# --------------------------------------------------------------------------- #
# PATCH the filecontent File column with the raw bytes
# --------------------------------------------------------------------------- #
def patch_bytes(api, token, comp_id, file_name, content_type, data, dry_run):
    if dry_run:
        print(f"  [dry-run] would PATCH filecontent of {comp_id}: "
              f"{len(data)} bytes, name={file_name}, content-type={content_type}")
        return
    # (a) file-name metadata
    r = requests.patch(f"{api}/powerpagecomponents({comp_id})",
                       headers=_headers(token, write=True),
                       json={"filecontent_name": file_name})
    r.raise_for_status()
    # (b) the bytes (octet-stream; runtime base64-encodes for storage)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "x-ms-file-name": file_name,
        "x-ms-file-content-type": content_type,
    }
    r = requests.patch(f"{api}/powerpagecomponents({comp_id})/filecontent",
                       headers=headers, data=data)
    if r.status_code in (200, 204):
        print(f"  [ok] uploaded {len(data)} bytes to filecontent of {comp_id}")
    else:
        sys.exit(f"  [FAIL] {r.status_code} {r.text[:300]}")


# --------------------------------------------------------------------------- #
# Optionally bump a ?v=N cache-buster next to the file ref in a web template
# --------------------------------------------------------------------------- #
def bump_cachebuster(api, token, template_name, site_id, file_name, dry_run):
    filt = f"powerpagecomponenttype eq 8 and name eq '{template_name}'"
    if site_id:
        filt += f" and _powerpagesiteid_value eq {site_id}"
    r = requests.get(f"{api}/powerpagecomponents",
                     headers=_headers(token),
                     params={"$filter": filt,
                             "$select": "powerpagecomponentid,name,content"})
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        sys.exit(f"No web template (type 8) named '{template_name}'"
                 + (f" in site {site_id}" if site_id else "") + " to bump.")
    if len(rows) > 1:
        sys.exit(f"Ambiguous: {len(rows)} web templates named '{template_name}'. "
                 f"Pass --site to scope.")
    comp = rows[0]
    comp_id = comp["powerpagecomponentid"]

    # Parse content directly as JSON (do NOT html.unescape first — see backbone rule 3)
    raw = comp.get("content") or ""
    try:
        payload = json.loads(raw)
    except Exception:
        import html
        payload = json.loads(html.unescape(raw))
    source = payload.get("source", "")

    # Match "<file_name>?v=<digits>" exactly once, then increment the number.
    esc = re.escape(file_name)
    pat = re.compile(rf"({esc}\?v=)(\d+)")
    matches = pat.findall(source)
    if len(matches) == 0:
        sys.exit(f"  [abort] no '{file_name}?v=N' cache-buster found in template "
                 f"'{template_name}'. Add a ?v= token, or bump it by hand.")
    if len(matches) > 1:
        sys.exit(f"  [abort] '{file_name}?v=N' appears {len(matches)}x in template "
                 f"'{template_name}'; refusing to guess. Bump it by hand.")
    old_n = int(matches[0][1])
    new_n = old_n + 1
    new_source = pat.sub(rf"\g<1>{new_n}", source, count=1)

    if dry_run:
        print(f"  [dry-run] would bump {file_name}?v={old_n} -> ?v={new_n} "
              f"in template '{template_name}' ({comp_id})")
        return

    payload["source"] = new_source
    r = requests.patch(f"{api}/powerpagecomponents({comp_id})",
                       headers=_headers(token, write=True),
                       json={"content": json.dumps(payload)})
    if r.status_code in (200, 204):
        print(f"  [ok] bumped {file_name}?v={old_n} -> ?v={new_n} in '{template_name}'")
    else:
        sys.exit(f"  [FAIL] template bump {r.status_code} {r.text[:300]}")


def main():
    ap = argparse.ArgumentParser(description="Update a Power Pages web file's bytes live.")
    ap.add_argument("--url", help="Dataverse URL (or set DATAVERSE_URL).")
    ap.add_argument("--id", help="powerpagecomponentid of the web file (type 3).")
    ap.add_argument("--name", help="Web file component name, e.g. theme.css (with --site).")
    ap.add_argument("--site", help="_powerpagesiteid_value to scope --name / --bump-template.")
    ap.add_argument("--file", required=True, help="Local file whose bytes to upload.")
    ap.add_argument("--content-type", help="MIME type (default: guessed from --file).")
    ap.add_argument("--file-name", help="filecontent_name to store (default: local basename).")
    ap.add_argument("--bump-template", help="Name of a web template whose ?v= to increment.")
    ap.add_argument("--dry-run", action="store_true", help="Print actions; PATCH nothing.")
    args = ap.parse_args()

    if not args.id and not args.name:
        ap.error("provide --id, or --name (optionally with --site).")

    local = Path(args.file)
    if not local.exists():
        sys.exit(f"Local file not found: {local}")
    data = local.read_bytes()
    file_name = args.file_name or local.name
    content_type = (args.content_type
                    or mimetypes.guess_type(file_name)[0]
                    or "application/octet-stream")

    url = resolve_url(args.url)
    api = f"{url}/api/data/{API_VERSION}"
    token = get_token()
    print(f"Connected to {url}\n")

    comp_id = args.id or find_web_file(api, token, args.name, args.site)
    print(f"Web file: {comp_id}")

    patch_bytes(api, token, comp_id, file_name, content_type, data, args.dry_run)

    if args.bump_template:
        bump_cachebuster(api, token, args.bump_template, args.site, file_name, args.dry_run)
    else:
        print("  [note] no --bump-template: bump the ?v= cache-buster via the "
              "edit-web-template skill, then flush the portal cache (flush-cache skill).")

    print("\nDone." + (" (dry-run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
