#!/usr/bin/env python
"""Safely edit a web template (powerpagecomponent type 8) on a traditional Power Pages site.

The Liquid/HTML lives in the component's `content` column, which is a JSON string
{"source": "<liquid/html>", "mimetype": ...}. This tool GETs the LIVE component, parses that
JSON robustly (json.loads directly; html.unescape only as a fallback), then either:

  * --pull-to FILE            : writes the live source to FILE and stops (edit it, push later), or
  * --source-file FILE        : replaces the whole source with FILE's contents, or
  * --replace-old-file OLD
    --replace-new-file NEW     : a single guarded old->new replacement inside the source
                                 (asserts OLD matches EXACTLY ONCE before writing).

...and PATCHes only that one component back (never a batch upload). Use --dry-run to preview.

Auth (in order):
  1. a workspace scripts/auth.py exposing get_token()  (the dv-connect pattern), or
  2. env var DATAVERSE_TOKEN (a bearer token).
DATAVERSE_URL comes from --url or the env var of the same name.

Usage:
  # fetch the live source to a file
  python edit_web_template.py --url https://org.crm.dynamics.com \
    --name "My Template" --site <SITEID> --pull-to source.html

  # push an edited source file back (preview, then apply)
  python edit_web_template.py --url https://org.crm.dynamics.com --id <COMPONENTID> \
    --source-file source.html --dry-run
  python edit_web_template.py --url https://org.crm.dynamics.com --id <COMPONENTID> \
    --source-file source.html

  # apply one guarded old->new replacement
  python edit_web_template.py --url https://org.crm.dynamics.com --id <COMPONENTID> \
    --replace-old-file old.txt --replace-new-file new.txt --dry-run
"""
import argparse
import html
import json
import os
import sys

import requests
import urllib3

urllib3.disable_warnings()

WEBTEMPLATE_TYPE = 8


def get_token():
    # 1) workspace scripts/auth.py (the dv-connect pattern)
    for p in (os.getcwd(), os.path.join(os.getcwd(), "scripts")):
        if os.path.exists(os.path.join(p, "auth.py")):
            sys.path.insert(0, p)
            try:
                from auth import get_token as _gt, load_env  # type: ignore
                load_env()
                return _gt()
            except Exception:
                pass
    # 2) env token
    t = os.environ.get("DATAVERSE_TOKEN")
    if t:
        return t
    sys.exit("No auth: provide a workspace scripts/auth.py (get_token) or set DATAVERSE_TOKEN.")


def headers(token, write=False):
    h = {"Authorization": "Bearer " + token, "Accept": "application/json",
         "OData-MaxVersion": "4.0", "OData-Version": "4.0"}
    if write:
        h["Content-Type"] = "application/json"
    return h


def parse_content(raw):
    """Parse the component content JSON robustly.

    Parse directly first — html.unescape'ing first corrupts legitimate &/"/< in the source
    and throws on valid templates. Only unescape as a fallback if the direct parse fails.
    """
    raw = raw or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(html.unescape(raw))


def resolve_id(base, h, args):
    if args.id:
        return args.id
    if not args.name:
        sys.exit("Provide --id, or --name (optionally with --site) to locate the template.")
    flt = f"powerpagecomponenttype eq {WEBTEMPLATE_TYPE} and name eq '{args.name}'"
    if args.site:
        flt += f" and _powerpagesiteid_value eq {args.site}"
    r = requests.get(base + "/powerpagecomponents", headers=h, verify=False, params={
        "$select": "powerpagecomponentid,name,_powerpagesiteid_value", "$filter": flt})
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        sys.exit(f"No web template named '{args.name}'"
                 + (f" on site {args.site}." if args.site else " (try passing --site)."))
    if len(rows) > 1:
        sys.exit(f"'{args.name}' is ambiguous ({len(rows)} matches) — pass --site or --id. "
                 + ", ".join(x["powerpagecomponentid"] for x in rows))
    return rows[0]["powerpagecomponentid"]


def main():
    ap = argparse.ArgumentParser(description="Edit a Power Pages web template (component type 8).")
    ap.add_argument("--url", default=os.environ.get("DATAVERSE_URL", ""))
    ap.add_argument("--id", help="powerpagecomponentid of the web template")
    ap.add_argument("--name", help="web template name (with --site to disambiguate)")
    ap.add_argument("--site", help="_powerpagesiteid_value to scope a --name lookup")
    ap.add_argument("--pull-to", metavar="FILE", help="write the live source to FILE and stop")
    ap.add_argument("--source-file", metavar="FILE", help="replace the whole source with FILE")
    ap.add_argument("--replace-old-file", metavar="FILE", help="fragment to replace (match once)")
    ap.add_argument("--replace-new-file", metavar="FILE", help="replacement for the fragment")
    ap.add_argument("--dry-run", action="store_true", help="show what would change; do not PATCH")
    a = ap.parse_args()
    if not a.url:
        sys.exit("Missing --url or DATAVERSE_URL")

    base = a.url.rstrip("/") + "/api/data/v9.2"
    token = get_token()
    h = headers(token)

    comp_id = resolve_id(base, h, a)

    # --- GET the LIVE component ---
    r = requests.get(f"{base}/powerpagecomponents({comp_id})", headers=h, verify=False,
                     params={"$select": "name,content"})
    r.raise_for_status()
    rec = r.json()
    content = parse_content(rec.get("content"))
    source = content.get("source")
    if source is None:
        sys.exit("ERROR: component has no 'source' in its content JSON — is this a type-8 web template?")
    print(f"Web template: {rec.get('name')}  ({comp_id})")
    print(f"Live source: {len(source)} chars")

    # --- pull mode: dump live source and stop ---
    if a.pull_to:
        with open(a.pull_to, "w", encoding="utf-8", newline="") as f:
            f.write(source)
        print(f"Wrote live source to {a.pull_to} — edit it, then push with --source-file.")
        return

    # --- build the new source ---
    if a.source_file:
        with open(a.source_file, encoding="utf-8") as f:
            new_source = f.read()
        if new_source == source:
            print("No change: --source-file is identical to live source. Nothing to do.")
            return
    elif a.replace_old_file and a.replace_new_file:
        with open(a.replace_old_file, encoding="utf-8") as f:
            old = f.read()
        with open(a.replace_new_file, encoding="utf-8") as f:
            new = f.read()
        n = source.count(old)
        if n != 1:  # match-once guard: 0 = drift, >1 = ambiguous
            sys.exit(f"ABORT: old fragment matched {n} time(s) in live source (expected 1). "
                     f"No PATCH sent.\n  fragment head: {old[:90]!r}")
        new_source = source.replace(old, new)
        print("Match-once guard OK (fragment found exactly once).")
    else:
        sys.exit("Choose an action: --pull-to, --source-file, or "
                 "--replace-old-file + --replace-new-file.")

    delta = len(new_source) - len(source)
    print(f"New source: {len(new_source)} chars ({delta:+d}).")

    if a.dry_run:
        print("DRY RUN — not patching. Re-run without --dry-run to apply.")
        return

    # --- PATCH the single component back ---
    content["source"] = new_source
    body = {"content": json.dumps(content)}
    rp = requests.patch(f"{base}/powerpagecomponents({comp_id})",
                        headers=headers(token, write=True), json=body, verify=False)
    if rp.status_code in (200, 204):
        print(f"PATCH {rp.status_code} — web template updated.")
        print("Next: flush the portal cache (see the flush-cache skill), then verify the page.")
    else:
        sys.exit(f"PATCH failed: {rp.status_code} {rp.text[:600]}")


if __name__ == "__main__":
    main()
