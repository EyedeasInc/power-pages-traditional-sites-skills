#!/usr/bin/env python
"""Refresh a Power Pages portal cache.

Default: restart the site with `pac power-pages restart-website`, which makes every instance
re-read components from Dataverse (about two minutes). It needs pac signed in to the site's
environment, not a portal session.

/_services/about only clears the cache when a contact with the Administrators web role selects
Clear cache in a signed in browser; a script GET of that URL does nothing. --about-only prints
that URL so a portal admin can do it by hand.

--site is the portal id (the `id` column of `pac power-pages get-websites`), not the Dataverse
powerpagesite record id (`websiteRecordId`).

Usage:
  python flush_cache.py --site <SITEID>                      # restart (default)
  python flush_cache.py --site <SITEID> --about-only         # print the admin URL only
  python flush_cache.py --site <SITEID> --environment <url>  # target another environment
"""
import argparse
import json
import shutil
import subprocess
import sys


def run_pac(*args):
    """Run pac and return (returncode, output). Exits only if pac isn't installed."""
    exe = shutil.which("pac")
    if not exe:
        sys.exit("pac (Power Platform CLI) isn't on PATH. Install it, or use design studio Sync.")
    r = subprocess.run([exe, *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def env_args(environment):
    return ["--environment", environment] if environment else []


def site_url(site_id, environment):
    """Best effort: the site's websiteUrl from pac, for the /_services/about URL."""
    rc, out = run_pac("power-pages", "get-website-by-id", "--id", site_id, *env_args(environment), "--json")
    if rc != 0:
        return ""
    try:
        return (json.loads(out[out.index("{"):]).get("websiteUrl") or "").rstrip("/")
    except (ValueError, AttributeError):
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True,
                    help="portal id: the `id` column of `pac power-pages get-websites`")
    ap.add_argument("--environment", help="Dataverse environment URL or id (default: active pac auth)")
    ap.add_argument("--about-only", action="store_true", help="print the /_services/about URL, don't restart")
    args = ap.parse_args()

    rc, out = run_pac("auth", "who")
    if rc != 0:
        sys.exit(f"pac isn't signed in. Run `pac auth create` first.\n{out.strip()}")
    print(out.strip())

    url = site_url(args.site, args.environment)
    if url:
        print(f"Admin clear (Administrators web role, signed in): {url}/_services/about")
    else:
        print(f"Couldn't look up site {args.site}. Check it's the portal `id` from "
              "`pac power-pages get-websites`, not the powerpagesite record id.")
        if args.about_only:
            sys.exit(1)
    if args.about_only:
        return

    print(f"Restarting site {args.site} ...")
    rc, out = run_pac("power-pages", "restart-website", "--id", args.site, *env_args(args.environment))
    print(out.strip())
    if rc != 0:
        sys.exit(f"restart-website failed (exit {rc}).")
    print("Done. Reload a real page in about two minutes; hard refresh for CSS and JS changes.")


if __name__ == "__main__":
    main()
