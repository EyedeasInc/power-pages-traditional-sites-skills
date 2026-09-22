---
name: pp-upload
description: "Upload a traditional Power Pages site's content from a local folder to a Dataverse environment with the pac pages upload CLI — the bulk push tool for promoting a site across environments (dev → test → prod), using deployment profiles for per-environment values. WHEN: upload a Power Pages site, deploy portal content, promote a site to another environment, push the site folder to Dataverse, pac pages upload, publish downloaded site content, apply a deployment profile, force upload all site content, move a portal from dev to prod."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Upload a Power Pages site's content to an environment

Push a traditional (enhanced-data-model, `mspp_*`) Power Pages site from a local folder into a
Dataverse environment with **`pac pages upload`**. This is the **bulk** promotion tool — the
counterpart to `pp-download` — for moving a whole site (or its changed content) **across
environments**: dev → test → prod.

> **Bulk upload vs single-component patch.** `pac pages upload` writes the whole content folder
> (changed items by default, everything with `--forceUploadAll`). That's exactly what you want
> for **environment promotion**. It is **not** the tool for tweaking one live template on a
> running site — for that, `pp-webtemplate` / `pp-webfile` patch the single live component so a
> concurrent Studio edit isn't overwritten. Pick upload when you're promoting a folder;
> pick the live-patch skills when you're editing one thing in place.

## Auth

`pac` CLI — use a `pac auth` profile pointed at the **target** environment (see `pp-website`):

```
pac auth create --environment <TARGET_ENV_URL_OR_ID>   # or: pac auth select --index <n>
pac auth list                                          # confirm the ACTIVE env is the target
```

Confirm the active environment before every upload — this writes to whichever env the profile
points at.

## Upload the content

```
pac pages upload --path "C:\pp\site" --modelVersion Enhanced
```

| Flag | Purpose |
|---|---|
| `--path` / `-p` | Local folder to upload from (required; a `pp-download` output). |
| `--modelVersion` / `-mv` | `Enhanced` (this plugin's target) or `Standard` — match the folder/site. |
| `--deploymentProfile` / `-dp` | Deployment profile name (default `default`) — per-environment value overrides. |
| `--forceUploadAll` / `-f` | Upload **all** content, not just detected changes (switch). |
| `--environment` / `-env` | Target env (Guid or URL); omit for the active profile. |

## Deployment profiles (per-environment values)

A **deployment profile** lets one downloaded folder carry environment-specific values (site
settings, connection details, URLs) so dev/test/prod differ without maintaining separate copies.
Profiles live under the content folder's `deployment-profiles/<name>.deployment.yml`; select one
at upload time:

```
pac pages upload --path "C:\pp\site" --deploymentProfile prod --modelVersion Enhanced
```

Keep a profile per target environment (`dev`, `test`, `prod`); the default profile is used when
`--deploymentProfile` is omitted.

## Typical promotion flow

```
1. pp-download   (from source env)   → pull the site to a folder
2. commit / review the folder in source control
3. pac auth select   → switch the active profile to the TARGET env
4. pp-upload --deploymentProfile <target>   → push it
5. pp-cache (+ pp-website restart if needed) → make changes surface
6. smoke-test the target site
```

## Notes

- `--forceUploadAll` re-pushes everything — use it for a first deploy to an empty target or to
  guarantee parity; omit it for faster incremental promotions.
- Match `--modelVersion` to both the folder and the target site (`Enhanced` for `mspp_`).
- After upload, flush the portal cache (`pp-cache`); a `restart-website` (`pp-website`) helps
  larger changes surface.
- Uploading writes many records at once against the target env — run it against the intended
  environment and, for prod, during a change window.
