---
name: pp-website
description: "Provision and run the Power Pages WEBSITE itself — the site record and its lifecycle — on a traditional (enhanced-data-model, mspp_*) site, using the pac power-pages CLI command group (Preview). Create a new website from a template, list and inspect sites, start / stop / restart, convert a trial to production, change site visibility and the security group, and delete a site. This is the site container; page/template/web-file CONTENT is authored with the other pp-* skills through the mspp_ model. WHEN: create a Power Pages website, provision a new portal, spin up a site, list my Power Pages sites, get a website id, start or stop or restart a portal, take a site offline, convert a trial site to production, change site visibility, set the site security group, delete a Power Pages website, pac power-pages, which template to use for a new site."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# The Power Pages website itself — provision, run, retire

Manage the **site container** on a traditional (enhanced-data-model, `mspp_*`) Power Pages
site through the **`pac power-pages`** CLI command group (Preview). This is the layer *above*
content: creating the website, listing and inspecting sites, starting/stopping/restarting,
converting a trial to production, changing visibility, and deleting.

> **Division of labour.** `pac power-pages` operates on the **website** (provision, run,
> secure, delete). The page/template/web-file/Liquid **content** inside a site is authored
> with the other skills in this plugin (`pp-webpage`, `pp-webtemplate`, `pp-webfile`,
> `pp-serverlogic`, `pp-liquid`) by writing `mspp_*` / `powerpagecomponent` rows directly.
> Use this skill to stand a site up or manage its lifecycle; use those to build what's in it.

> ⚠️ **Preview.** Every `pac power-pages` command is Preview and its surface can change.
> Verify against the live reference before relying on exact flags:
> https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/power-pages

## Auth (once)

These are `pac` CLI commands, not Dataverse Web API calls — they use a **pac auth profile**,
not the `DATAVERSE_TOKEN` the content skills use. Create or select a profile first:

```
pac auth create --environment <ENV_URL_OR_ID>     # or: pac auth select --index <n>
pac auth list                                     # confirm the active profile / environment
```

Every command below accepts `--environment` / `-env` (a Guid or the https org URL); when
omitted it targets the active profile's environment.

## Find the site you're operating on

Almost every command is keyed by the **website id** (a GUID), not the site name or URL. List
the sites in the environment and read the id:

```
pac power-pages get-websites                         # table of sites in the env
pac power-pages get-website-by-id --id <SITEID>      # full details for one site
```

Use `--json` for the complete record (the table view truncates), or `--columns name,id,...`
to pick fields.

## Create a website

```
pac power-pages create-website \
  --name "Field Service Portal" \
  --subdomain field-service-portal \
  --dataverse-organization-id <ORG_ID> \
  --selected-base-language 1033 \
  --template-name StarterLayout1
```

Required flags:

| Flag | What it is |
|---|---|
| `--name` | Display name of the website. |
| `--subdomain` | The subdomain for the site URL (`<subdomain>.powerappsportals.com`). Must be globally unique. |
| `--dataverse-organization-id` | The target Dataverse org's unique id (the site's backing environment). |
| `--selected-base-language` | LCID of the base language (e.g. `1033` = en-US). LCID list: https://go.microsoft.com/fwlink/?linkid=2208135 |
| `--template-name` | Provisioning template (see below). |

`--website-record-id` is optional (supply a specific Dataverse record id for the site).

**Template names** (`--template-name`). Power Pages (blank/starter/scenario) templates give
you a **traditional, enhanced-data-model** site — the kind this plugin targets:

- Starter / blank: `StarterLayout1`…`StarterLayout5`, `BlankPage`, `DefaultPortalTemplate`
- Scenario (Power Pages): `BookMeetings`, `FAQ`, `ProgramRegistration`, `BuildingPermit`,
  `PowerPortals_ProgramRegistration`, `PowerPortals_BookMeeting`
- Dynamics 365 templates (only if the matching D365 app is installed): `Community`,
  `EventPortal`, `CustomerSelfServicePortal`, `EmployeeSelfServicePortal`, `PartnerPortal`,
  `CustomerPortal`, `FieldService`

Provisioning is **asynchronous** — the command triggers creation and returns; the site takes
a few minutes to come up. Poll `get-websites` until it appears, then `get-website-by-id` for
its URL and status. For a blank traditional site to start from, `StarterLayout1` (aka
`DefaultPortalTemplate`) or `BlankPage` is the usual pick.

## Run / pause a site

```
pac power-pages start-website    --id <SITEID>    # bring an idle/stopped site online
pac power-pages stop-website     --id <SITEID>    # take it offline
pac power-pages restart-website  --id <SITEID>    # restart (clears the running instance)
```

> `restart-website` recycles the running site — useful when a change won't surface even after
> a content cache flush. It is **not** the content cache flush itself; for that, see `pp-cache`.

## Convert a trial to production

```
pac power-pages convert-trial-to-production --id <SITEID> [--enable-cdn] [--enable-waf]
```

Optional `--enable-cdn`, `--enable-waf`, and `--use-dynamics365-portal-add-on-license`.

## Visibility & access to the site

```
pac power-pages update-site-visibility        --id <SITEID> --site-visibility <value>
pac power-pages update-portal-security-group   --id <SITEID> --security-group-id <GROUP_ID>
```

Site visibility gates whether the site is reachable at all; the security group restricts who
in the tenant can see it. (Per-page and per-table access *inside* the site is the job of web
roles + `pp-tablepermission`, not these commands.)

## Data-model / bootstrap stamps

```
pac power-pages set-portal-data-model-version --id <SITEID> --is-new-data-model true
pac power-pages set-portal-bootstrap-v5-enabled --id <SITEID>
```

`--is-new-data-model true` stamps the **enhanced (`mspp_*`) data model** — the model this
whole plugin assumes. Only touch these when a site's stamp is wrong; new Power Pages sites are
already on the enhanced model.

## Delete a website  ⚠️ destructive

```
pac power-pages delete-website --id <SITEID>
```

Triggers deletion of the site. This is **irreversible** — confirm the `--id` is the intended
site (run `get-website-by-id` first) and that the owner approved before you run it. Deleting
the website does not, on its own, clean up the `mspp_*` content records the site referenced.

## Related surfaces (same command group)

Not core lifecycle, but in `pac power-pages` when you need them — see the CLI reference:

- **Security scans:** `start-quick-scan`, `start-deep-scan`, `get-security-scan-report`,
  `get-security-scan-score` → folded into the **`pp-securityreview`** skill.
- **Firewall / network:** `enable-waf` / `disable-waf` / `get-waf-status` / `get-waf-rules` /
  `create-waf-rules` / `update-waf-policy-settings`, and the IP allow-list
  (`get`/`add`/`remove-allowed-ip-addresses`).
- **Custom domains / SSL:** `create-custom-domain`, `list-host-names-for-portal`,
  `upload-certificate`, `add-ssl-binding-by-portal`, and the delete counterparts.

## Notes

- The website id is the currency of this command group — resolve it once with `get-websites`
  and reuse it.
- These commands act on the **environment's** sites; a tenant can host many, so always target
  by id, and confirm the active `pac auth` environment before a create or delete.
- Everything here is Preview: if a flag is rejected, re-check the live CLI reference above.
