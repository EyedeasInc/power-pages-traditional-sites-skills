---
name: pp-cache
description: "Make Power Pages component changes visible by refreshing the portal's server cache (web templates, web files, content snippets, site settings, table permissions, web pages, page access rules). A PATCH to Dataverse updates the record but the running portal keeps serving the cached version. Default: restart the site with pac power-pages restart-website (reaches every instance, no portal sign in). Alternative: Clear cache on /_services/about, which only works for a signed in contact with the Administrators web role. WHEN: my change isn't showing on the portal, clear Power Pages cache, flush portal cache, portal still shows old version, invalidate cache, changes not appearing after edit, /_services/about, restart the site, force portal to refresh."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.2.0"
---

# Refresh the Power Pages portal cache

On a traditional (enhanced data model) Power Pages site, the running portal serves components
(web templates, web files, content snippets, site settings, table permissions, page access rules,
web pages) from a **server-side cache**. When you PATCH a component in Dataverse, as every editing
skill in this plugin does, the record changes at once but visitors keep seeing the **cached**
version until the cache is refreshed.

See `../../references/traditional-site-editing-model.md` for the editing model these changes come from.

## When you need it

After `pp-webtemplate`, `pp-webfile` (also bump the URL cache buster, see that skill),
`pp-serverlogic`, `pp-webapi` (site settings), `pp-tablepermission`, `pp-pageaccessrule`,
`pp-webpage` (`mspp_copy` PUTs do **not** auto-bust), or content snippet and site setting edits.

## Choose a method

| Method | Needs | Reaches | Use when |
|---|---|---|---|
| **1. Restart the site** (default) | `pac auth` on the site's environment | every instance | after any change, from an agent or a script |
| 2. Clear cache on `/_services/about` | a browser session signed in as a contact with the **Administrators** web role | the instance that served the request | you're already signed in as a portal admin and want it now |
| 3. Power Pages design studio **Sync** | maker access to the site | the studio preview and the site | you're working in the studio anyway |

### 1. Restart the site (default)

```
pac power-pages restart-website --id <SITEID>
```

The site comes back in about **two minutes**. Every instance re-reads components from Dataverse,
which a single `/_services/about` clear can't guarantee on a scaled-out site. Confirm the active
`pac auth` environment first (`pac auth who`), or pass `--environment <url-or-id>`.

`<SITEID>` is the **portal id**: the `id` column of
`pac power-pages get-websites --columns id,name,websiteUrl` (see `pp-website`). It is **not** the
Dataverse `powerpagesite` record id (`websiteRecordId` in that output, `powerpagesiteid` in the
Web API); passing that one fails.

### 2. Clear cache on `/_services/about` (portal admins only)

1. Open `<websiteUrl>/_services/about` in a browser **signed in to the portal** (`websiteUrl` comes
   from `pac power-pages get-website-by-id --id <SITEID> --json`, or a custom domain).
2. The **Clear cache** button only appears for a contact with the **Administrators** web role.
   Without that role the page shows version details only, and nothing is cleared.
3. Select **Clear cache**. A plain `GET` of the URL, signed in or not, does **not** clear it.

Need the role? Assign the signed in contact to the **Administrators** web role with `pp-webrole`
(dev and test sites only; never grant it to real users to work around caching).

### 3. Design studio Sync

In Power Pages design studio for the site, select **Sync**. Reliable when the portal host
doesn't resolve from your machine.

### Browser cache (CSS and JS)

A server refresh doesn't reach a browser that already holds the old file. Bump the `?v=` cache
buster where the file is referenced (see `pp-webfile`), then hard refresh.

## Bundled helper

`scripts/flush_cache.py` restarts the site through pac (method 1) and prints the
`/_services/about` URL for method 2. Needs `pac` on PATH and signed in (`pac auth create`); use
`python3` on macOS and Linux.

```
python scripts/flush_cache.py --site <SITEID>                      # restart (default)
python scripts/flush_cache.py --site <SITEID> --about-only         # just print the admin URL
python scripts/flush_cache.py --site <SITEID> --environment <url>  # target another environment
```

## Verify

Reload a real page (not the API) after the restart finishes. If it still shows the old content:
1. Confirm you restarted or cleared the **right site** (a tenant can host several).
2. For CSS and JS, confirm the `?v=` cache buster was bumped, then hard refresh.
3. Confirm the component was saved to the same website and, where it applies, published.

## Notes and gotchas

- `/_services/about` is per instance: on a scaled-out site, other instances keep their cache.
- New table permissions, page access rules, and site settings follow the same rule: refresh the
  cache before you judge whether they work.
- Don't loop restarts: each one takes the site offline for a minute or two.
- Restarting doesn't fix a component saved to the **wrong site**; check that first.
- List and form reads are cached (community reports about 15 minutes). Portal writes clear the
  cache, but Dataverse side changes (flows, plugins, model driven app edits) don't; design for that
  lag rather than restarting on every edit.
