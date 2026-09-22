---
name: pp-firewall
description: "Inspect and configure the Web Application Firewall (WAF) and IP allow-list in front of a production Power Pages site using the pac power-pages CLI (Preview) — enable/disable WAF, read and create managed/custom rules (IP/country/path blocks, rate limits), set enforcement mode (Prevention vs Detection), and restrict access to an IP allow-list. WHEN: enable the Power Pages WAF, configure the web application firewall, block an IP or country on the portal, add a rate limit, set WAF to prevention or detection mode, restrict the site to an IP allow-list, pac power-pages waf, harden a production portal against bots/brute force, check WAF status."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Web Application Firewall & IP allow-list for a Power Pages site

Inspect and configure the **WAF** (Azure Front Door-backed) and the **IP restriction allow-list**
in front of a Power Pages site with the **`pac power-pages`** CLI command group (Preview). This
is edge protection — brute-force/bot mitigation, geo/IP/path blocks, rate limits — layered in
front of the site; it complements, but never replaces, fixing the app itself (see
`pp-securityreview`).

> ⚠️ **Preview & production.** These commands are Preview, and WAF is a **production-site**
> capability (often gated by CDN/WAF being enabled — see `pp-website`
> `convert-trial-to-production --enable-waf`). Verify flags against the live reference:
> https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/power-pages

## Auth & site id

`pac` CLI — a `pac auth` profile (see `pp-website`), then the site id:

```
pac auth list
pac power-pages get-websites          # find --id (website GUID)
```

## Read current state first

```
pac power-pages get-waf-status --id <SITEID>                    # on/off + mode
pac power-pages get-waf-rules  --id <SITEID> --rule-type managed
pac power-pages get-waf-rules  --id <SITEID> --rule-type custom
pac power-pages get-allowed-ip-addresses --id <SITEID>          # current IP allow-list
```

## Enable / disable WAF

```
pac power-pages enable-waf  --id <SITEID>
pac power-pages disable-waf --id <SITEID>
```

## Enforcement mode & policy

`update-waf-policy-settings` sets **Prevention** (blocks matching requests) vs **Detection**
(logs only) and the challenge-cookie lifetimes. Only the fields you pass change:

```
pac power-pages update-waf-policy-settings --id <SITEID> --mode Prevention
pac power-pages update-waf-policy-settings --id <SITEID> \
  --javascript-challenge-expiration-in-minutes 30 --captcha-expiration-in-minutes 30
```

> Roll out in **Detection** first, watch the logs for false positives, then switch to
> **Prevention**. Flipping straight to Prevention on an unfamiliar traffic profile can block
> legitimate users.

## Custom rules (IP / country / path blocks, rate limits)

Custom and managed rules are passed as JSON arrays. Read the current rules first, compose the
new set, then create; remove with the delete counterpart:

```
pac power-pages create-waf-rules --id <SITEID> \
  --custom-rules  @custom-rules.json \
  --managed-rules @managed-rules.json

pac power-pages delete-waf-custom-rules --id <SITEID> --body @remove.json
```

Typical custom rules: block a country/region, block an IP or CIDR range, block a path
(e.g. brute-forced sign-in), or a **rate limit** on a path. (Shape the JSON per the CLI
reference / the WAF rule schema.)

## IP allow-list (restrict who can reach the site)

Lock the site to known networks (corp VPN, office ranges) — anything not on the list is refused:

```
pac power-pages add-allowed-ip-addresses    --id <SITEID> --ip-addresses '["203.0.113.10","198.51.100.0/24"]'
pac power-pages remove-allowed-ip-addresses --id <SITEID> --ip-addresses '["203.0.113.10"]'
pac power-pages get-allowed-ip-addresses    --id <SITEID>
```

> An **IP allow-list makes the whole site private to those ranges** — use it for internal/staging
> portals, not a public site. Don't lock yourself out: include your own egress IP.

## Notes

- **Read → stage in Detection → enforce.** Always `get-waf-status`/`get-waf-rules` before you
  change anything, and keep the previous rule JSON as a rollback.
- WAF/IP are **defense-in-depth**. A firewall in front of an unescaped XSS sink is not a fix —
  run `pp-securityreview` for the application-level issues.
- Everything here is Preview; if a flag is rejected, re-check the live CLI reference.
