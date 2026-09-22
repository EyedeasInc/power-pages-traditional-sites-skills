---
name: pp-weblink
description: "Create, edit, reorder, and delete navigation on a traditional (enhanced-data-model, mspp_*) Power Pages site — web link sets (mspp_weblinkset) and the web links (mspp_weblink) inside them, including nested sub-menus, page links, and external URLs — through the Dataverse Web API. The page template's header/footer renders a web link set; this is how the menu is managed. WHEN: add a navigation item, edit the portal menu, add a nav link, reorder menu items, create a web link set, add a dropdown/sub-menu, link the nav to a page, add an external link to the menu, remove a nav item, manage mspp_weblink, change the header/footer menu."
license: MIT
metadata:
  author: Victor Dantas
  version: "0.1.0"
---

# Navigation — web link sets & web links on a Power Pages site

Manage a traditional (enhanced-data-model, `mspp_*`) Power Pages site's **navigation** — the
**web link set** (`mspp_weblinkset`) rendered by the page template's header/footer, and the
**web links** (`mspp_weblink`) inside it — through the Dataverse Web API. Create sets, add/edit/
reorder/remove links, and build nested (dropdown) menus.

> Read `references/traditional-site-editing-model.md` first (component model, read-live-first,
> cache flush). `pp-webpage` creates a page *and* drops one link into the primary set as part of
> Step 4; use **this** skill when the job is the navigation itself — a new menu, reordering,
> sub-menus, external links, or footer links.

## The model

| Record | Holds |
|---|---|
| **`mspp_weblinkset`** | A named menu (e.g. "Default", "Footer"). Scoped to a site by `_mspp_websiteid_value`. The page template renders a set by name/id. |
| **`mspp_weblink`** | One menu item: `mspp_name` (label), `mspp_displayorder`, a target (page **or** external URL), optional parent for nesting, and the set it belongs to. |

A web link points at **either** a page (`mspp_pageid` → the **root** `mspp_webpage`) — so the
URL tracks the page and never hard-codes a path — **or** an external URL (`mspp_externalurl`).

## Step 1 — Find the set (scope by site)

```
GET /api/data/v9.2/mspp_weblinksets?$filter=_mspp_websiteid_value eq <SITEID>
    &$select=mspp_name,mspp_weblinksetid
```

The primary nav is usually named **"Default"**. To read a set's current links in order:

```
GET /api/data/v9.2/mspp_weblinks?$filter=_mspp_weblinksetid_value eq <SETID>
    &$select=mspp_name,mspp_displayorder,_mspp_pageid_value,mspp_externalurl,_mspp_parentweblinkid_value
    &$orderby=mspp_displayorder
```

## Step 2 — Create a web link set (only if you need a new menu)

```jsonc
POST /api/data/v9.2/mspp_weblinksets
{
  "mspp_name": "Footer",
  "mspp_websiteid@odata.bind": "/mspp_websites(<SITEID>)"
}
```

Most sites already have the header set — reuse it; create a set only for a genuinely separate
menu (e.g. a footer) that the template renders.

## Step 3 — Add a link

**To a page** (preferred — URL follows the page):

```jsonc
POST /api/data/v9.2/mspp_weblinks
{
  "mspp_name": "Services",
  "mspp_displayorder": 20,
  "mspp_weblinksetid@odata.bind": "/mspp_weblinksets(<SETID>)",
  "mspp_pageid@odata.bind":       "/mspp_webpages(<ROOT_WEBPAGEID>)"
}
```

**To an external URL:**

```jsonc
POST /api/data/v9.2/mspp_weblinks
{
  "mspp_name": "Docs",
  "mspp_displayorder": 30,
  "mspp_weblinksetid@odata.bind": "/mspp_weblinksets(<SETID>)",
  "mspp_externalurl": "https://learn.microsoft.com/power-pages"
}
```

Bind `mspp_pageid` to the **root** web page (not the content page) so the link resolves to the
page's partial URL.

## Step 4 — Nested (dropdown) menus

Give a child link a parent to nest it under a top-level item:

```jsonc
POST /api/data/v9.2/mspp_weblinks
{
  "mspp_name": "Field Service",
  "mspp_displayorder": 10,
  "mspp_weblinksetid@odata.bind":    "/mspp_weblinksets(<SETID>)",
  "mspp_parentweblinkid@odata.bind": "/mspp_weblinks(<PARENT_LINKID>)",
  "mspp_pageid@odata.bind":          "/mspp_webpages(<ROOT_WEBPAGEID>)"
}
```

The template must render a **multi-level** web link set for the dropdown to show; a flat header
renders only top-level links. A parent link with children often has **no** target of its own
(it's just a group header) — omit `mspp_pageid`/`mspp_externalurl` on it, or point it at a
landing page.

## Step 5 — Reorder, edit, remove

```
PATCH  /api/data/v9.2/mspp_weblinks(<LINKID>)   { "mspp_displayorder": 15 }     // reorder
PATCH  /api/data/v9.2/mspp_weblinks(<LINKID>)   { "mspp_name": "Our Services" } // relabel
DELETE /api/data/v9.2/mspp_weblinks(<LINKID>)                                    // remove item
```

Reordering is just `mspp_displayorder`; renumber siblings with gaps (10, 20, 30) so inserts are
easy. Deleting a parent orphans its children — re-parent or delete them too.

## Step 6 — Flush cache & verify

The menu is cached — changes won't show until you flush (`pp-cache`, e.g. `/_services/about` →
Clear cache). Then load the site and confirm the item appears, sits in the right order,
highlights as active on its page, and (for dropdowns) expands.

## Field & option reference

- Tables: `mspp_weblinkset`, `mspp_weblink` (enhanced model — `mspp_*`, not `adx_*`).
- Key `mspp_weblink` columns: `mspp_name` (label), `mspp_displayorder`, `mspp_pageid` (→ root
  page), `mspp_externalurl`, `mspp_parentweblinkid` (nesting), `mspp_weblinksetid`,
  `mspp_websiteid`. Optional: `mspp_openinnewwindow`, `mspp_disablepagevalidation`, robots flags.
- Always scope by `_mspp_websiteid_value`.
- Auth: Dataverse MCP (preferred for reads) or a Web API bearer token (`DATAVERSE_TOKEN`), per
  the shared backbone.
