#!/usr/bin/env python3
"""
grant_table_permission.py

Create a Power Pages **table permission** (`mspp_entitypermission`) on a traditional
(enhanced-data-model, mspp_*) site and **bind it to one or more web roles** via the
`mspp_entitypermission_webrole` many-to-many intersect. Idempotent.

A table permission grants CRUD scope on a Dataverse table for the portal, but it does
NOTHING until it is bound to a web role. This script does both, and can --verify the
bindings by querying the intersect directly (the only reliable read under an app-only
service principal — see the note on INTERSECT_SET below).

Examples
--------
  # Global read on a public "announcement" table for anonymous + authenticated users
  python grant_table_permission.py --url https://ORG.crm.dynamics.com --site <SITEID> \
      --name "Announcements - Public" --table cr123_announcement \
      --scope global --privileges read \
      --web-role "Anonymous Users" --web-role "Authenticated Users"

  # Contact-scope: signed-in users create + read only THEIR OWN request records
  python grant_table_permission.py --url https://ORG.crm.dynamics.com --site <SITEID> \
      --name "Access Request - Self" --table cr123_accessrequest \
      --scope contact --contact-relationship cr123_contact_accessrequest \
      --privileges read,create \
      --web-role "Authenticated Users"

  # Verify which web roles a permission is bound to (queries the intersect directly)
  python grant_table_permission.py --url https://ORG.crm.dynamics.com --site <SITEID> \
      --name "Access Request - Self" --verify

  # Preview everything without writing
  python grant_table_permission.py ... --dry-run

Auth: reuses a workspace scripts/auth.py get_token() (the dv-connect pattern) if present,
otherwise reads a bearer token from the DATAVERSE_TOKEN env var. DATAVERSE_URL may supply
--url. Never hardcode tenant ids, site ids, secrets, or portal URLs here.
"""
import argparse
import json
import os
import sys

import requests

API_VER = "v9.2"

# mspp_scope (Access Type) option-set values — from the mspp_entitypermission metadata.
SCOPES = {
    "global":  756150000,   # every portal user (respecting web-role binding) sees all rows
    "contact": 756150001,   # rows related to the signed-in contact ("Self")
    "account": 756150002,   # rows related to the contact's parent account
    "parent":  756150003,   # inherit access from a parent permission via a relationship
    "self":    756150004,   # the contact's own contact record only
}

# privilege flag -> boolean column on mspp_entitypermission
PRIV_COLUMNS = {
    "read":     "mspp_read",
    "write":    "mspp_write",
    "create":   "mspp_create",
    "delete":   "mspp_delete",
    "append":   "mspp_append",
    "appendto": "mspp_appendto",
}

# THE load-bearing name. This is the EntitySetName of the M:N intersect entity — note the
# "-set" suffix (it is NOT "mspp_entitypermission_webroles"). Querying THIS collection is the
# only reliable way to read the bindings under an app-only service principal; a nav-property
# $expand from mspp_entitypermission returns EMPTY (reads blind) even when bindings exist.
# Legacy standard-model (adx_*) equivalent: adx_entitypermission_webroleset.
INTERSECT_SET = "mspp_entitypermission_webroleset"

# M:N navigation property used to ASSOCIATE a permission with a web role via $ref.
NAV_WEBROLE = "mspp_entitypermission_webrole"


# --------------------------------------------------------------------------- auth
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


def headers(token, write=False):
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    if write:
        h["Content-Type"] = "application/json"
    return h


# ------------------------------------------------------------------------- helpers
def odata_escape(s):
    return s.replace("'", "''")


def find_permission(api, token, site_id, name):
    r = requests.get(
        f"{api}/mspp_entitypermissions",
        headers=headers(token),
        params={
            "$filter": f"_mspp_websiteid_value eq {site_id} and mspp_name eq '{odata_escape(name)}'",
            "$select": "mspp_entitypermissionid,mspp_name,mspp_scope,mspp_entitylogicalname",
        },
    )
    r.raise_for_status()
    vals = r.json().get("value", [])
    return vals[0] if vals else None


def resolve_web_role(api, token, site_id, role):
    """Accept a GUID or a web-role display name; return the web-role GUID."""
    role = role.strip()
    if len(role) == 36 and role.count("-") == 4:
        return role  # already a GUID
    r = requests.get(
        f"{api}/mspp_webroles",
        headers=headers(token),
        params={
            "$filter": f"_mspp_websiteid_value eq {site_id} and mspp_name eq '{odata_escape(role)}'",
            "$select": "mspp_webroleid,mspp_name",
        },
    )
    r.raise_for_status()
    vals = r.json().get("value", [])
    if not vals:
        sys.exit(f"Web role not found on this site: {role!r}")
    if len(vals) > 1:
        sys.exit(f"Web role name {role!r} is ambiguous on this site ({len(vals)} matches).")
    return vals[0]["mspp_webroleid"]


def role_name(api, token, role_id):
    r = requests.get(
        f"{api}/mspp_webroles({role_id})",
        headers=headers(token),
        params={"$select": "mspp_name"},
    )
    if r.ok:
        return r.json().get("mspp_name", role_id)
    return role_id


def list_bindings(api, token, perm_id):
    """Read (permission, web-role) pairs from the intersect DIRECTLY. Do not $expand."""
    r = requests.get(
        f"{api}/{INTERSECT_SET}",
        headers=headers(token),
        params={
            "$filter": f"mspp_entitypermissionid eq {perm_id}",
            "$select": "mspp_entitypermissionid,mspp_webroleid",
        },
    )
    r.raise_for_status()
    return [row["mspp_webroleid"] for row in r.json().get("value", [])]


# --------------------------------------------------------------------------- writes
def upsert_permission(api, token, args, site_id, dry):
    scope_val = SCOPES[args.scope]
    body = {
        "mspp_name": args.name,
        "mspp_entitylogicalname": args.table,
        "mspp_scope": scope_val,
        "mspp_websiteid@odata.bind": f"/mspp_websites({site_id})",
    }
    for flag, col in PRIV_COLUMNS.items():
        body[col] = flag in args.privileges

    if args.scope == "contact":
        if not args.contact_relationship:
            sys.exit("--scope contact requires --contact-relationship (the contact->table relationship schema name).")
        body["mspp_contactrelationship"] = args.contact_relationship
    if args.scope == "account":
        if not args.account_relationship:
            sys.exit("--scope account requires --account-relationship.")
        body["mspp_accountrelationship"] = args.account_relationship
    if args.scope == "parent":
        if not (args.parent_permission and args.parent_relationship):
            sys.exit("--scope parent requires --parent-permission <id> and --parent-relationship.")
        body["mspp_parententitypermission@odata.bind"] = f"/mspp_entitypermissions({args.parent_permission})"
        body["mspp_parentrelationship"] = args.parent_relationship

    existing = find_permission(api, token, site_id, args.name)
    if existing:
        perm_id = existing["mspp_entitypermissionid"]
        if dry:
            print(f"  [dry-run] would UPDATE permission {args.name!r} ({perm_id})")
            return perm_id
        # PATCH without the website bind (a set lookup can't be re-PATCHed the same way)
        patch = {k: v for k, v in body.items() if k != "mspp_websiteid@odata.bind"}
        r = requests.patch(f"{api}/mspp_entitypermissions({perm_id})", headers=headers(token, True), json=patch)
        r.raise_for_status()
        print(f"  [updated] permission {args.name!r} ({perm_id})")
        return perm_id

    if dry:
        print(f"  [dry-run] would CREATE permission {args.name!r} on {args.table} "
              f"scope={args.scope} privileges={','.join(sorted(args.privileges)) or '(none)'}")
        return None
    r = requests.post(
        f"{api}/mspp_entitypermissions",
        headers={**headers(token, True), "Prefer": "return=representation"},
        json=body,
    )
    r.raise_for_status()
    perm_id = r.json()["mspp_entitypermissionid"]
    print(f"  [created] permission {args.name!r} ({perm_id})")
    return perm_id


def bind_role(api, token, perm_id, role_id, already, dry):
    if role_id in already:
        print(f"    [skip] already bound to web role {role_id}")
        return
    if dry:
        print(f"    [dry-run] would BIND web role {role_id}")
        return
    # Associate via $ref on the M:N navigation property.
    r = requests.post(
        f"{api}/mspp_entitypermissions({perm_id})/{NAV_WEBROLE}/$ref",
        headers=headers(token, True),
        json={"@odata.id": f"{api}/mspp_webroles({role_id})"},
    )
    if r.status_code in (204, 200):
        print(f"    [bound] web role {role_id}")
    elif r.status_code in (400, 412) and "duplicate" in r.text.lower():
        print(f"    [skip] already bound to web role {role_id}")
    else:
        r.raise_for_status()


# --------------------------------------------------------------------------- verify
def do_verify(api, token, site_id, name):
    perm = find_permission(api, token, site_id, name)
    if not perm:
        sys.exit(f"No permission named {name!r} on this site.")
    perm_id = perm["mspp_entitypermissionid"]
    print(f"Permission {name!r} ({perm_id})")
    print(f"  table={perm.get('mspp_entitylogicalname')}  scope-option={perm.get('mspp_scope')}")
    role_ids = list_bindings(api, token, perm_id)
    if not role_ids:
        print("  bound web roles: (none) -- this permission grants nothing until bound.")
        return
    print(f"  bound web roles ({len(role_ids)}) [read from {INTERSECT_SET} intersect]:")
    for rid in role_ids:
        print(f"    - {role_name(api, token, rid)}  ({rid})")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Create/bind a Power Pages table permission (mspp_entitypermission).")
    ap.add_argument("--url", default=os.environ.get("DATAVERSE_URL"), help="Dataverse org URL (or env DATAVERSE_URL).")
    ap.add_argument("--site", required=True, help="mspp_website id (GUID) — scope everything to one site.")
    ap.add_argument("--name", required=True, help="Table permission name (unique per site).")
    ap.add_argument("--table", help="Target table LOGICAL name (e.g. cr123_announcement). Required unless --verify.")
    ap.add_argument("--scope", choices=list(SCOPES), help="Access scope. Required unless --verify.")
    ap.add_argument("--privileges", default="", help="Comma list: read,write,create,delete,append,appendto.")
    ap.add_argument("--contact-relationship", help="Relationship schema name for --scope contact.")
    ap.add_argument("--account-relationship", help="Relationship schema name for --scope account.")
    ap.add_argument("--parent-permission", help="Parent mspp_entitypermission id for --scope parent.")
    ap.add_argument("--parent-relationship", help="Relationship schema name for --scope parent.")
    ap.add_argument("--web-role", action="append", default=[], dest="web_roles",
                    help="Web role GUID or display name to bind. Repeatable.")
    ap.add_argument("--verify", action="store_true", help="List the permission's web-role bindings and exit.")
    ap.add_argument("--dry-run", action="store_true", help="Print intended changes without writing.")
    args = ap.parse_args()

    if not args.url:
        sys.exit("Provide --url or set DATAVERSE_URL.")
    api = f"{args.url.rstrip('/')}/api/data/{API_VER}"
    token = get_token()

    if args.verify:
        do_verify(api, token, args.site, args.name)
        return

    if not args.table or not args.scope:
        sys.exit("--table and --scope are required (unless --verify).")

    args.privileges = {p.strip().lower() for p in args.privileges.split(",") if p.strip()}
    bad = args.privileges - set(PRIV_COLUMNS)
    if bad:
        sys.exit(f"Unknown privileges: {', '.join(sorted(bad))}. Allowed: {', '.join(PRIV_COLUMNS)}.")

    print(f"Site {args.site} @ {args.url}")
    print("Upserting table permission...")
    perm_id = upsert_permission(api, token, args, args.site, args.dry_run)

    if args.web_roles:
        role_ids = [resolve_web_role(api, token, args.site, r) for r in args.web_roles]
        already = [] if (args.dry_run and perm_id is None) else (list_bindings(api, token, perm_id) if perm_id else [])
        print("Binding web roles...")
        for rid in role_ids:
            bind_role(api, token, perm_id, rid, already, args.dry_run)
    else:
        print("  (no --web-role given: permission created but bound to NOTHING -- it grants no access yet.)")

    if perm_id and not args.dry_run:
        print("\nVerifying via intersect:")
        do_verify(api, token, args.site, args.name)
    print("\nDone.")


if __name__ == "__main__":
    main()
