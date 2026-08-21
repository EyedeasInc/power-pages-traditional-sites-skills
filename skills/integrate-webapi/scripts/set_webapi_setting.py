#!/usr/bin/env python
"""Enable the Power Pages Web API for one Dataverse table on a traditional (mspp_*) site.

Idempotently creates/updates the two site settings that expose <table> to /_api/*:
  Webapi/<table>/enabled  = true
  Webapi/<table>/fields   = <comma-separated column LogicalNames | *>
and, with --innererror, the optional:
  Webapi/<table>/errors/innererror = true

For each setting it reads live (by name, scoped to the website): PATCH if a row exists,
POST otherwise. It never batch-uploads and never touches other settings.

Enabling the Web API does NOT bypass security — the caller's web role still needs a matching
table permission on <table> for a call to return data / accept a write.

<table> is the entity LogicalName (singular, e.g. nnn_project); the endpoint URL uses the
entity set (plural, /_api/nnn_projects). --fields values are CASE-SENSITIVE column
LogicalNames; verify them against table metadata rather than guessing. Prefer an explicit
least-field list over "*".

Auth (in order):
  1. a workspace scripts/auth.py exposing get_token()  (the dv-connect pattern), or
  2. env var DATAVERSE_TOKEN (a bearer token).
DATAVERSE_URL comes from --url or the env var of the same name.

Usage:
  python set_webapi_setting.py --url https://org.crm.dynamics.com --site <SITEID> \
    --table nnn_project --fields nnn_projectid,nnn_name,nnn_status,createdon \
    [--innererror] [--dry-run]
"""
import argparse, os, sys, requests, urllib3
urllib3.disable_warnings()


def get_token():
    # 1) workspace scripts/auth.py
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("DATAVERSE_URL", ""))
    ap.add_argument("--site", required=True, help="Website id (_mspp_websiteid_value)")
    ap.add_argument("--table", required=True, help="Entity LogicalName, e.g. nnn_project")
    ap.add_argument("--fields", default="*",
                    help="Comma-separated column LogicalNames (case-sensitive) or *. Prefer a least-field list.")
    ap.add_argument("--innererror", action="store_true",
                    help="Also set Webapi/<table>/errors/innererror = true (dev aid).")
    ap.add_argument("--dry-run", action="store_true", help="Print planned actions; write nothing.")
    a = ap.parse_args()
    if not a.url:
        sys.exit("Missing --url or DATAVERSE_URL")

    BASE = a.url.rstrip("/") + "/api/data/v9.2"
    H = {"Authorization": "Bearer " + get_token(), "OData-MaxVersion": "4.0",
         "OData-Version": "4.0", "Accept": "application/json", "Content-Type": "application/json"}

    # desired settings (name -> value)
    desired = {
        f"Webapi/{a.table}/enabled": "true",
        f"Webapi/{a.table}/fields":  a.fields,
    }
    if a.innererror:
        desired[f"Webapi/{a.table}/errors/innererror"] = "true"

    if a.fields.strip() == "*":
        print("! --fields is '*': exposing ALL columns of", a.table,
              "to any web role with a table permission. Prefer a least-field list.\n")

    def find(name):
        # OData string literals escape ' by doubling it
        f = name.replace("'", "''")
        r = requests.get(BASE + "/mspp_sitesettings", headers=H, verify=False, params={
            "$select": "mspp_sitesettingid,mspp_value",
            "$filter": f"mspp_name eq '{f}' and _mspp_websiteid_value eq {a.site}",
        })
        r.raise_for_status()
        return r.json().get("value", [])

    for name, value in desired.items():
        rows = find(name)
        if rows:
            sid = rows[0]["mspp_sitesettingid"]
            if rows[0].get("mspp_value") == value:
                print(f"[same] {name} = {value}")
                continue
            if a.dry_run:
                print(f"[would PATCH] {name}: {rows[0].get('mspp_value')!r} -> {value!r}")
                continue
            r = requests.patch(f"{BASE}/mspp_sitesettings({sid})", headers=H, verify=False,
                               json={"mspp_value": value})
            ok = r.status_code < 300
            print(f"[{'ok ' if ok else 'FAIL'}] PATCH {name} = {value}"
                  + ("" if ok else f"  {r.status_code} {r.text[:200]}"))
        else:
            if a.dry_run:
                print(f"[would POST] {name} = {value}")
                continue
            body = {"mspp_name": name, "mspp_value": value,
                    "mspp_websiteid@odata.bind": f"/mspp_websites({a.site})"}
            r = requests.post(BASE + "/mspp_sitesettings", headers=H, verify=False, json=body)
            ok = r.status_code < 300
            print(f"[{'ok ' if ok else 'FAIL'}] POST  {name} = {value}"
                  + ("" if ok else f"  {r.status_code} {r.text[:200]}"))

    print("\nDone." + ("  (dry run — nothing written)" if a.dry_run else
          "  Next: /_services/about -> Clear cache, then verify /_api/<entityset>."))
    print("Reminder: also bind a TABLE PERMISSION for", a.table,
          "to the caller's web role, or the API returns nothing / 403.")


if __name__ == "__main__":
    main()
