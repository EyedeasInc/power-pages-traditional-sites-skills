#!/usr/bin/env python
"""Download a traditional Power Pages site to disk via `pac pages download`.

A thin, deterministic wrapper around the Power Platform CLI so an agent (or a CI job)
can snapshot a site the same way every time — for backup, diff, or source control —
instead of hand-assembling the command. Enhanced data model (mspp_*) by default.

Auth: uses the active `pac auth` profile (run `pac auth create` / `pac auth list` first).
This is a CLI operation, not a Dataverse Web API call, so it does NOT use DATAVERSE_TOKEN.

Usage:
  python download_site.py --path "C:\\pp\\site" --website-id <SITEID>
  python download_site.py -p ./site -id <SITEID> --environment <ENV_URL> --overwrite
  python download_site.py -p ./site -id <SITEID> --include-entities powerpagecomponent
"""
import argparse
import shutil
import subprocess
import sys


def build_command(args):
    """Translate parsed args into an exact `pac pages download` argument list."""
    cmd = [
        "pac", "pages", "download",
        "--path", args.path,
        "--webSiteId", args.website_id,
        "--modelVersion", args.model_version,
    ]
    if args.environment:
        cmd += ["--environment", args.environment]
    if args.include_entities:
        cmd += ["--includeEntities", args.include_entities]
    if args.exclude_entities:
        cmd += ["--excludeEntities", args.exclude_entities]
    if args.overwrite:
        cmd += ["--overwrite"]
    return cmd


def main():
    parser = argparse.ArgumentParser(description="Download a Power Pages site with pac.")
    parser.add_argument("--path", "-p", required=True, help="Local folder to download into.")
    parser.add_argument("--website-id", "-id", required=True, help="Site id from `pac pages list`.")
    parser.add_argument("--environment", "-env", help="Target env (Guid or URL); omit for active profile.")
    parser.add_argument("--model-version", "-mv", default="Enhanced",
                        choices=["Enhanced", "Standard"], help="Data model (default: Enhanced).")
    parser.add_argument("--include-entities", "-ie", help="Comma-separated logical names to download only.")
    parser.add_argument("--exclude-entities", "-xe", help="Comma-separated logical names to skip.")
    parser.add_argument("--overwrite", "-o", action="store_true", help="Overwrite existing content.")
    args = parser.parse_args()

    if shutil.which("pac") is None:
        sys.exit("error: the Power Platform CLI (`pac`) is not on PATH. Install it and run `pac auth create` first.")

    cmd = build_command(args)
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)  # inherits stdout/stderr so pac's own progress shows through

    if result.returncode != 0:
        sys.exit(f"error: pac pages download failed (exit {result.returncode}). "
                 "Check the active `pac auth` profile and the website id.")
    print(f"Done. Site {args.website_id} downloaded to {args.path}.")


if __name__ == "__main__":
    main()
