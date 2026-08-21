#!/usr/bin/env python
"""Create a Power Pages web page (root + content) and optionally a nav web link.

Enhanced data model: a page = a ROOT mspp_webpage (mspp_isroot=true; partialurl/parent/
template/publishing) + a CONTENT mspp_webpage (mspp_isroot=false; links to root, language,
mspp_copy). Creating the root can auto-create an empty content page — this reuses it and
repairs its lookups rather than creating a duplicate.

Auth (in order):
  1. a workspace scripts/auth.py exposing get_token()  (the dv-connect pattern), or
  2. env var DATAVERSE_TOKEN (a bearer token).
DATAVERSE_URL comes from --url or the env var of the same name.

Usage:
  python add_webpage.py --url https://org.crm.dynamics.com --site <SITEID> \
    --name "Test" --partialurl test \
    --template <TEMPLATEID> --parent <PARENTID> --publishing <PUBLISHEDID> --lang <LANGID> \
    [--copy-file body.html | --copy "<h1>Hi</h1>"] [--displayorder 5] \
    [--weblinkset <SETID>] [--weblink-order 5]
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
    ap.add_argument("--site", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--partialurl", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--parent", required=True)
    ap.add_argument("--publishing", required=True)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--displayorder", type=int, default=5)
    ap.add_argument("--copy")
    ap.add_argument("--copy-file")
    ap.add_argument("--weblinkset")
    ap.add_argument("--weblink-order", type=int, default=None)
    a = ap.parse_args()
    if not a.url:
        sys.exit("Missing --url or DATAVERSE_URL")

    BASE = a.url.rstrip("/") + "/api/data/v9.2"
    H = {"Authorization": "Bearer " + get_token(), "OData-MaxVersion": "4.0",
         "OData-Version": "4.0", "Accept": "application/json", "Content-Type": "application/json"}
    HREP = {**H, "Prefer": "return=representation"}
    copy = a.copy or ""
    if a.copy_file:
        with open(a.copy_file, encoding="utf-8") as f:
            copy = f.read()

    def get(u):
        return requests.get(BASE + u, headers=H, verify=False).json().get("value", [])

    def ref(cid, nav, eset, gid):
        r = requests.put(f"{BASE}/mspp_webpages({cid})/{nav}/$ref", headers=H,
                         json={"@odata.id": f"{BASE}/{eset}({gid})"}, verify=False)
        if r.status_code >= 300:
            print(f"  ! {nav}: {r.status_code} {r.text[:120]}")
        return r.status_code

    # ---- ROOT (reuse if a page with this partial url already exists) ----
    existing = get(f"/mspp_webpages?$select=mspp_webpageid,mspp_isroot&$filter="
                   f"_mspp_websiteid_value eq {a.site} and mspp_partialurl eq '{a.partialurl}'")
    root = next((x for x in existing if x.get("mspp_isroot")), None)
    if root:
        root_id = root["mspp_webpageid"]; print("reuse root:", root_id)
    else:
        body = {"mspp_name": a.name, "mspp_title": a.name, "mspp_partialurl": a.partialurl,
                "mspp_isroot": True, "mspp_displayorder": a.displayorder,
                "mspp_pagetemplateid@odata.bind": f"/mspp_pagetemplates({a.template})",
                "mspp_parentpageid@odata.bind": f"/mspp_webpages({a.parent})",
                "mspp_publishingstateid@odata.bind": f"/mspp_publishingstates({a.publishing})",
                "mspp_websiteid@odata.bind": f"/mspp_websites({a.site})"}
        r = requests.post(BASE + "/mspp_webpages", headers=HREP, json=body, verify=False)
        if r.status_code >= 300:
            sys.exit(f"ROOT create failed {r.status_code}: {r.text[:400]}")
        root_id = r.json()["mspp_webpageid"]; print("created root:", root_id)

    # ---- CONTENT (reuse the auto-created one if present) ----
    content = get(f"/mspp_webpages?$select=mspp_webpageid&$filter=_mspp_rootwebpageid_value eq {root_id}")
    if content:
        content_id = content[0]["mspp_webpageid"]; print("reuse content:", content_id)
    else:
        body = {"mspp_name": a.name, "mspp_title": a.name, "mspp_partialurl": a.partialurl,
                "mspp_isroot": False, "mspp_displayorder": a.displayorder,
                "mspp_rootwebpageid@odata.bind": f"/mspp_webpages({root_id})",
                "mspp_websiteid@odata.bind": f"/mspp_websites({a.site})"}
        r = requests.post(BASE + "/mspp_webpages", headers=HREP, json=body, verify=False)
        if r.status_code >= 300:
            sys.exit(f"CONTENT create failed {r.status_code}: {r.text[:400]}")
        content_id = r.json()["mspp_webpageid"]; print("created content:", content_id)

    # repair/ensure the content page's lookups (idempotent)
    ref(content_id, "mspp_pagetemplateid", "mspp_pagetemplates", a.template)
    ref(content_id, "mspp_publishingstateid", "mspp_publishingstates", a.publishing)
    ref(content_id, "mspp_webpagelanguageid", "mspp_websitelanguages", a.lang)
    ref(content_id, "mspp_parentpageid", "mspp_webpages", a.parent)

    # page body via single-property PUT
    if copy:
        r = requests.put(f"{BASE}/mspp_webpages({content_id})/mspp_copy", headers=H,
                         json={"value": copy}, verify=False)
        print("PUT copy:", r.status_code)

    # ---- optional nav web link ----
    if a.weblinkset:
        body = {"mspp_name": a.name,
                "mspp_displayorder": a.weblink_order if a.weblink_order is not None else a.displayorder,
                "mspp_weblinksetid@odata.bind": f"/mspp_weblinksets({a.weblinkset})",
                "mspp_pageid@odata.bind": f"/mspp_webpages({root_id})"}
        r = requests.post(BASE + "/mspp_weblinks", headers=HREP, json=body, verify=False)
        print("web link:", r.status_code, "" if r.status_code < 300 else r.text[:200])

    print(f"\nDONE  root={root_id}  content={content_id}  url=/{a.partialurl}")
    print("Next: /_services/about -> Clear cache, then load the page to verify.")


if __name__ == "__main__":
    main()
