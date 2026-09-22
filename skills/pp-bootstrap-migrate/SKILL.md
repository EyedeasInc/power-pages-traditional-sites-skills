---
name: pp-bootstrap-migrate
description: "Migrate a traditional (Liquid) Power Pages site's markup from Bootstrap 3 to Bootstrap 5 using the pac pages bootstrap-migrate CLI engine, then fix the residual grid/navbar/card/page-header changes the engine can only flag. Non-destructive: the engine writes a new V5 copy of downloaded site content and never edits the source. WHEN: migrate Power Pages from Bootstrap 3 to Bootstrap 5, upgrade bootstrap on a portal, bootstrap v3 to v5, fix bootstrap classes on Liquid templates, pac pages bootstrap-migrate, modernize portal markup, my portal still uses Bootstrap 3."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Bootstrap 3 → 5 migration for a traditional Power Pages site

Upgrade the markup of a **traditional (Liquid) Power Pages** site from **Bootstrap 3** to
**Bootstrap 5** with the **`pac pages bootstrap-migrate`** engine. The engine does the bulk,
mechanical class renames across downloaded site content; you then handle the structural changes
it can only flag (grid, navbar, panel→card, page-header).

> This is a **site-content** operation on files downloaded to disk, not a single live-component
> patch. It pairs with `pp-download` (pull the content) and `pp-upload` (push the V5 result
> back). The engine is **non-destructive** — it writes a new `V5` copy and never edits the
> source folder.

## 1 — Download the site content

Pull the site to disk first (see `pp-download`):

```
pac pages download --path "C:\pp\site" --webSiteId <SITEID> --modelVersion Enhanced
```

## 2 — Run the migration engine

Point it at the downloaded content path:

```
pac pages bootstrap-migrate --path "C:\pp\site"
```

The engine writes a new **`V5`** copy alongside the source and performs the bulk Bootstrap 3→5
class renames (e.g. `col-xs-*` → `col-*`, `img-responsive` → `img-fluid`, `hidden-*` utilities,
`pull-left`/`pull-right` → `float-*`, `btn-default` → `btn-secondary`, etc.).

## 3 — Fix the residuals the engine flags

Bootstrap 5 changed structure, not just class names — the engine renames what it safely can and
**flags the rest for a human**. Work these categories in the `V5` copy (edit the templates/web
files there, then upload):

- **Grid:** `xs` tier removed (use unprefixed columns); gutters and `.row`/`.container`
  behavior changed. Re-check responsive breakpoints.
- **Navbar:** markup restructured (`navbar-nav`, `navbar-toggler`, `data-bs-*` attributes);
  Bootstrap 5 dropped jQuery — inline `data-toggle` becomes `data-bs-toggle`.
- **Panel → Card:** `.panel`/`.panel-heading`/`.panel-body` become `.card`/`.card-header`/
  `.card-body`.
- **Page header / wells / other dropped components:** replaced with utilities or cards; the
  engine flags each site of use.
- **JS plugins:** `data-*` toggles now `data-bs-*`; anything relying on Bootstrap 3 + jQuery
  plugins needs the Bootstrap 5 bundle.

## 4 — Upload the V5 result and enable the runtime flag

Push the migrated content back (see `pp-upload`):

```
pac pages upload --path "C:\pp\site\...V5..." --modelVersion Enhanced
```

The site must run the **Bootstrap 5 runtime**. If your theme/site setting still pins Bootstrap
3, flip it (the platform exposes a Bootstrap-5-enabled flag — for provisioned sites,
`pp-website`'s `set-portal-bootstrap-v5-enabled` stamps it). Then flush the cache (`pp-cache`)
and verify pages render — spot-check the navbar, grid, and any cards first.

## Notes

- **Non-destructive engine** — the source folder is untouched; review the `V5` diff before you
  upload, and keep the pre-migration download as a rollback.
- Traditional/Liquid sites only. (Code sites don't use this — they own their own CSS build.)
- Budget time for the flagged residuals: the class renames are minutes; the navbar/grid
  structural fixes are where the real work is.
