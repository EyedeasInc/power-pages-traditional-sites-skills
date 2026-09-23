#!/usr/bin/env python
"""PostToolUse(Skill) hook for powerpages-traditional-site.

After a content-mutating pp-* skill runs, add a short reminder that mspp_ changes are cached
(flush with /pp-cache) and that data is only reachable when table permissions + web roles allow it.
Read-only, best-effort: any error exits silently so the session is never blocked.
"""
import sys
import json

# Content-mutating skills (writes to mspp_ / powerpagecomponent). Read/CLI/lifecycle skills
# (pp-cache, pp-securityreview, pp-website, pp-download, pp-upload, pp-datamodel-migrate,
# pp-bootstrap-migrate, pp-firewall) are intentionally excluded.
CONTENT = {
    "pp-webpage", "pp-pagetemplate", "pp-webtemplate", "pp-webfile", "pp-contentsnippet",
    "pp-serverlogic", "pp-weblink", "pp-sitemarker", "pp-redirect", "pp-basicform", "pp-list",
    "pp-multistepform", "pp-webapi", "pp-webrole", "pp-tablepermission", "pp-columnpermission",
    "pp-pageaccessrule", "pp-headers",
}


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return
    tool_input = data.get("tool_input") or {}
    skill = str(tool_input.get("skill") or tool_input.get("command") or data.get("skill") or "")
    base = skill.split(":")[-1].split("/")[-1].strip().lstrip("/")
    if base not in CONTENT:
        return
    msg = (
        f"Reminder after {base}: (1) mspp_ component changes are cached — run /pp-cache to flush "
        "the portal cache before they appear; (2) data is only reachable when table permissions + web "
        "roles allow it (see /pp-tablepermission, /pp-webrole)."
    )
    out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}
    try:
        print(json.dumps(out))
    except Exception:
        return


if __name__ == "__main__":
    main()
