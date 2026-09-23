---
name: pp-download
description: "Download a traditional Power Pages site's content to disk with the pac pages download (or clone) CLI — for backup, diff, offline inspection, and source control. Pulls the enhanced-data-model (mspp_*) site content as YAML/files; supports scoping by entity and overwriting. A download is a point-in-time SNAPSHOT — inspect and version it, but never patch a live component from it (the live skills read live for a reason). WHEN: download a Power Pages site, back up a portal, pull site content to disk, export the site for source control, diff a portal, clone a Power Pages site, pac pages download, get a local copy of the site, snapshot the portal before a change."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Download a Power Pages site's content to disk

Pull a traditional (enhanced-data-model, `mspp_*`) Power Pages site's content to a local folder
with **`pac pages download`** — for **backup**, **diff**, **offline inspection**, and **source
control**. Use `pac pages clone` to copy already-downloaded content into a new working folder.

> ⚠️ **A download is a point-in-time snapshot, not the source of truth.** The live Dataverse
> records are. Use this copy to read, diff, back up, or feed a bulk transform (e.g.
> `pp-bootstrap-migrate`) — but to change one component, use the live-patch skills
> (`pp-webtemplate`, `pp-webfile`), which GET the live row so they don't clobber a Studio edit
> made after you downloaded. Round-tripping a whole downloaded folder back up is `pp-upload`.

## Auth

`pac` CLI — use a `pac auth` profile (see `pp-website`):

```
pac auth create --environment <ENV_URL_OR_ID>   # or: pac auth select --index <n>
pac auth list
pac pages list                                  # website names + ids
```

## Download the site

```
pac pages download --path "C:\pp\site" --webSiteId <SITEID> --modelVersion Enhanced
```

| Flag | Purpose |
|---|---|
| `--path` / `-p` | Local folder to download into (required). |
| `--webSiteId` / `-id` | The site to download (required; from `pac pages list`). |
| `--modelVersion` / `-mv` | `Enhanced` (this plugin's target) or `Standard`. Defaults to `Standard` — **pass `Enhanced`** for an `mspp_` site. |
| `--environment` / `-env` | Target env (Guid or URL); omit for the active profile. |
| `--overwrite` / `-o` | Overwrite existing content in `--path` (switch). |
| `--includeEntities` / `-ie` | Comma-separated logical names to download *only* those. |
| `--excludeEntities` / `-xe` | Comma-separated logical names to skip. |

**Scope the pull** when you only need part of the site — e.g. just templates and web files:

```
pac pages download --path "C:\pp\site" --webSiteId <SITEID> --modelVersion Enhanced \
  --includeEntities powerpagecomponent
```

## Repeatable download (script)

For a scripted, always-identical pull — a scheduled backup, a CI export, or an agent that
shouldn't hand-assemble flags — `scripts/download_site.py` wraps `pac pages download` with
argument validation and a clear pass/fail exit. It defaults to `--modelVersion Enhanced` and
uses the active `pac auth` profile:

```
python scripts/download_site.py --path "C:\pp\site" --website-id <SITEID> [--overwrite]
```

It shells out to `pac` (no Dataverse token needed) and exits non-zero if `pac` is missing or the
download fails — safe to drop into automation. For interactive, one-off pulls, the `pac pages
download` command above is fine on its own.

## Clone downloaded content into a new folder

To branch a working copy from content you already downloaded (e.g. before a risky transform):

```
pac pages clone --path "C:\pp\site" --outputDirectory "C:\pp\site-v5-work" [--name "Copy"] [--overwrite]
```

## What you get & what to do with it

- A folder of the site's content (pages, templates, web files, site settings, web roles, table
  permissions, etc.) suitable for **committing to git**, **diffing** two environments, or
  keeping as a **pre-change backup**.
- For a bulk transform (Bootstrap 3→5), hand the path to `pp-bootstrap-migrate`.
- To promote the folder to another environment, use `pp-upload`.

## Notes

- Match `--modelVersion` to the site: `Enhanced` for `mspp_` sites, `Standard` for legacy
  `adx_` sites (see `pp-datamodel-migrate` to move between them).
- Downloading is read-only against the environment — safe to run anytime for a backup.
- Keep the download timestamped; it ages the moment anyone edits the live site.
