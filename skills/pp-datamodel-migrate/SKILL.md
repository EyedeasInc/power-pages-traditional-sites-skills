---
name: pp-datamodel-migrate
description: "Migrate a Power Pages site's DATA MODEL between Standard (adx_) and Enhanced (mspp_) using the pac pages migrate-datamodel CLI — the prerequisite that gets a site onto the enhanced model this whole plugin assumes. Run the migration, check its status, update the site's data-model version once data is moved, generate a site-customization report, or revert an enhanced site back to standard. WHEN: migrate a Power Pages site to the enhanced data model, move from adx_ to mspp_, upgrade the portal data model, check data model migration status, my site is on the standard/old data model, convert portal to enhanced data model, revert to standard data model, pac pages migrate-datamodel, update data model version, why don't the mspp_ tables exist on my site."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Migrate a Power Pages site's data model (standard ↔ enhanced)

Move a site between the **Standard** data model (`adx_*` tables) and the **Enhanced** data
model (`mspp_*` tables + `powerpagecomponent`) with **`pac pages migrate-datamodel`**. This is
the **prerequisite for the rest of this plugin** — every other `pp-*` content skill reads and
writes `mspp_*` / `powerpagecomponent`, which only exist once a site is on the enhanced model.

> **Why this matters.** If a site is still on the standard model, the content skills here find
> no `mspp_webpage` / `powerpagecomponent` rows to operate on. This skill is how the site gets
> onto the enhanced model in the first place — run it (or confirm the site is already enhanced)
> before `pp-webpage`, `pp-webtemplate`, `pp-webfile`, etc.

> ⚠️ This migrates real site configuration data. **Back the site up first** (`pp-download`),
> run it in a non-production environment before prod, and read the customization report before
> you flip the version. Related but different: `pp-website`'s `set-portal-data-model-version`
> only *stamps* a version flag — it does **not** move the data. This skill moves the data.

## Auth

`pac` CLI, not the Web API — use a `pac auth` profile (see `pp-website`):

```
pac auth create --environment <ENV_URL_OR_ID>   # or: pac auth select --index <n>
pac auth list
```

Every command accepts `--environment` / `-env`; omit it to use the active profile.

## Find the site id

```
pac pages list                 # website names + ids in the environment
```

## 1 — Report first (see what will move, change nothing)

Generate the site-customization report so you know what the migration will touch before you
run it. This is the safe, read-only first step:

```
pac pages migrate-datamodel --webSiteId <SITEID> \
  --siteCustomizationReportPath "C:\pp\migration-report"
```

Review the report for customizations that need attention, then proceed.

## 2 — Migrate the data (standard → enhanced)

`--mode` selects what moves. Start narrow, or use `all` for a full migration:

| `--mode` | Moves |
|---|---|
| `configurationData` | The site's configuration records. |
| `configurationDataReferences` | The reference/lookup data those records depend on. |
| `all` | Both — the full migration. |

```
pac pages migrate-datamodel --webSiteId <SITEID> --mode all
```

The migration runs server-side and can take a while on a large site.

## 3 — Check status

```
pac pages migrate-datamodel --webSiteId <SITEID> --checkMigrationStatus
```

Poll until it reports complete before moving on.

## 4 — Update the data-model version

Once the data has moved successfully, stamp the site so the runtime serves the enhanced model:

```
pac pages migrate-datamodel --webSiteId <SITEID> --updateDataModelVersion
```

After this, verify the `mspp_*` rows exist (e.g. `GET /api/data/v9.2/mspp_webpages?$top=1`) and
the site renders, then the rest of the `pp-*` skills apply.

## Revert / reset (recovery)

```
# revert an enhanced site back to the standard (adx_) model
pac pages migrate-datamodel --webSiteId <SITEID> --revertToStandardDataModel

# reset a migration that got stuck, to start over
pac pages migrate-datamodel --webSiteId <SITEID> --resetMigration
```

`--portalId` (`-pid`) targets a specific portal when the site id and portal id differ; add
`--verbose` for detailed progress on any of the above.

## Notes & gotchas

- **Sequence:** report → migrate (`--mode`) → `--checkMigrationStatus` → `--updateDataModelVersion`.
  Don't stamp the version before the data has actually finished moving.
- **Back up first** with `pp-download` (`--modelVersion Standard` for a pre-migration copy).
- The website id (`pac pages list`) is the currency here; confirm the active `pac auth`
  environment before running against production.
- After a successful migration, a content cache flush (`pp-cache`) and sometimes a
  `restart-website` (`pp-website`) help the new model surface.
