#!/usr/bin/env python
"""Flush a Power Pages portal cache by hitting <domain>/_services/about.

Resolves the portal domain from the site record (or takes it directly), then issues
an authenticated GET to /_services/about to nudge the portal to re-read components
from Dataverse. Use after PATCHing web templates, web files, site settings, table
permissions, or web pages.

Auth (in order):
  1. a workspace scripts/auth.py exposing get_token()  (the dv-connect pattern), or
  2. env var DATAVERSE_TOKEN (a bearer token).
DATAVERSE_URL comes from --url or the env var of the same name.

Usage:
  python flush_cache.py --url https://org.crm.dynamics.com --site <SITEID>
  python flush_cache.py --url https://org.crm.dynamics.com --domain contoso.powerappsportals.com
"""
import argparse
import os
import sys

import requests
import urllib3

urllib3.disable_warnings()


def get_token():
    for p in (os.getcwd(), os.path.join(os.getcwd(), "scripts")):
        if os.path.exists(os.path.join(p, "auth.py")):
            sys.path.insert(0, p)
            try:
                from auth import get_token as _gt, load_env  # type: ignore
                load_env()
                return _gt()
            except Exception:
                pass
    t = os.environ.get("DATAVERSE_TOKEN")
    if t:
        return t
    sys.exit("No auth: provide a workspace scripts/auth.py (get_token) or set DATAVERSE_TOKEN.")


def resolve_domain(api, headers, site_id):
    """Return the primarydomainname for a powerpagesite (or the first site if site_id is None)."""
    params = {"$select": "name,primarydomainname"}
    if site_id:
        params["$filter"] = f"powerpagesiteid eq {site_id}"
    r = requests.get(f"{api}/powerpagesites", headers=headers, params=params, verify=False)
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        sys.exit("Could not resolve a portal domain — pass --domain explicitly.")
    dom = rows[0].get("primarydomainname")
    if not dom:
        sys.exit("Site has no primarydomainname — pass --domain explicitly.")
    print(f"Resolved domain: {dom}  (site: {rows[0].get('name')})")
    return dom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("DATAVERSE_URL"),
                    help="Dataverse env URL (or DATAVERSE_URL env var)")
    ap.add_argument("--site", help="powerpagesiteid (to resolve the domain)")
    ap.add_argument("--domain", help="portal domain, e.g. contoso.powerappsportals.com "
                                     "(skips Dataverse lookup)")
    args = ap.parse_args()
    if not args.url and not args.domain:
        sys.exit("Provide --url (to resolve the domain) or --domain directly.")

    domain = args.domain
    if not domain:
        token = get_token()
        api = args.url.rstrip("/") + "/api/data/v9.2"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json",
                   "OData-MaxVersion": "4.0", "OData-Version": "4.0"}
        domain = resolve_domain(api, headers, args.site)

    about = f"https://{domain}/_services/about"
    print(f"Flushing via {about} ...")
    try:
        r = requests.get(about, timeout=30, verify=False)
        print(f"  HTTP {r.status_code}")
        if r.status_code >= 400:
            print("  Non-2xx — the portal may still have flushed; verify by reloading the page.")
    except requests.exceptions.RequestException as e:
        sys.exit(f"Could not reach {about}: {e}\n"
                 f"If the host doesn't resolve from this machine, use Power Pages Studio -> "
                 f"Sync / Clear cache instead.")
    print("Done. Reload a real page (not the API) to confirm; hard-refresh for CSS/JS changes.")


if __name__ == "__main__":
    main()
