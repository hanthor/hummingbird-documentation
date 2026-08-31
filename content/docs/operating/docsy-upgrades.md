---
title: Upgrading Docsy
description: >-
  How to upgrade the Docsy theme and forward-port our layout overrides.
weight: 15
aliases: [/l/docsy-upgrades]
---

## Overview

Both Hummingbird documentation sites use [Docsy][docsy] as
their Hugo theme, installed as a Hugo module. Docsy releases roughly quarterly.
This runbook covers how to upgrade to a new Docsy version.

The **public docs** ([documentation][docs-repo]) own all layout overrides. The
**internal docs** ([infrastructure][infra-repo]`/internal-docs/`) only have
build scaffolding and pick up layouts from the public docs via Hugo module
import.

## Layout override inventory

We override three Docsy templates to inject the companion page banner and
sidebar lock icons. Each override is a copy of the upstream template with a
small patch applied.

### `layouts/docs/_td-content.html`

Overrides Docsy's shared `layouts/_td-content.html` for docs pages only.

**Patch:** One line added after the description lead, before `<header>`:

```go-html-template
{{ partial "companion.html" . }}
```

### `layouts/docs/list.html`

Overrides Docsy's `layouts/docs/list.html` for docs section pages.

**Patch:** Same one line added after the description lead, before `<header>`:

```go-html-template
{{ partial "companion.html" . }}
```

### `layouts/partials/sidebar-tree.html`

Overrides Docsy's `layouts/_partials/sidebar-tree.html` for the navigation
sidebar.

**Patch:** One snippet inserted in two places (foldable and non-foldable
branches), after the `{{ $s.LinkTitle }}` `</span>` and before `</a>`:

```go-html-template
{{- if isset $s.Params "companion" }}{{ if not $s.Params.companion }} <i class="fa-solid fa-lock companion-icon internal-only" title="Internal only"></i>{{ end }}{{ end -}}
```

### Other overrides (no forward-porting needed)

These files are fully custom and don't track an upstream template:

| File | Purpose |
| ---- | ------- |
| `layouts/shortcodes/include.html` | Custom file-include shortcode |
| `layouts/_default/_markup/render-link.html` | Link rewriting for hummingbird URLs and `/l/` aliases |
| `layouts/_default/_markup/render-heading.html` | Delegates to Docsy's `td/render-heading.html` |
| `layouts/partials/companion.html` | Environment-aware companion page banner |
| `layouts/partials/breadcrumb.html` | Custom breadcrumb with stable-URL display |
| `layouts/partials/footer.html` | Fully custom 3-column footer |
| `layouts/home.html` | Custom home page with cover image and feature cards |

## Upgrade procedure

### 1. Read the release notes

Check the [Docsy changelog][docsy-changelog] and
the release upgrade guide for the target version. Note any breaking changes that
affect templates we override.

### 2. Update the Hugo module

From the documentation repo worktree:

```bash
# Update to new version (replace vX.Y.Z with the target version)
podman run --pull=newer -it --rm -u 0 \
  -v $(pwd):/src:z -w /src \
  -e RUNNING_IN_CONTAINER=1 -e HUGO_CACHEDIR=/src/.hugo_cache \
  quay.io/hummingbird-ci/gitlab-ci:latest sh -c \
  "hugo mod get github.com/google/docsy/theme@vX.Y.Z && hugo mod tidy"
```

### 3. Update npm dependencies

Docsy v0.16.0+ sources Bootstrap and Font Awesome from npm:

```bash
podman run --pull=never -it --rm -u 0 \
  -v $(pwd):/src:z -w /src \
  -e RUNNING_IN_CONTAINER=1 -e HUGO_CACHEDIR=/src/.hugo_cache \
  quay.io/hummingbird-ci/gitlab-ci:latest sh -c \
  "hugo mod npm pack && npm install --no-package-lock"
```

### 4. Forward-port layout overrides

For each of the three tracked overrides:

1. Find the new upstream template in the Hugo module cache:

   ```bash
   find .hugo_cache -path "*docsy/theme@vX.Y.Z*" \
     -name "_td-content.html" -o \
     -name "sidebar-tree.html" -o \
     \( -name "list.html" -path "*docs*" \)
   ```

2. Compare the new upstream against our current override to see what changed
   upstream.

3. Start from the new upstream template and re-apply the patch documented in
   the inventory above.

4. For `docs/list.html`, keep all upstream hooks (especially
   `{{ .Render "_td-content-after-header" -}}`).

### 5. Verify dark mode and code highlighting

The site uses Docsy's light/dark mode toggle and dark-aware code syntax
highlighting. After upgrading, confirm these config and SCSS settings are
still in place:

- `config.yaml`: `params.ui.showLightDarkModeMenu: true`
- `config.yaml`: `markup.highlight.noClasses: false` (required for CSS-based
  Chroma themes to work)
- `assets/scss/_styles_project.scss`: `@import 'td/code-dark';` (loads
  light/dark Chroma themes: `friendly` for light, `native` for dark)

If a Docsy upgrade changes the dark mode mechanism, check the
[Look and Feel][docsy-lookandfeel] docs for
updated instructions.

### 6. Build and validate

```bash
make build  # or: make build-host (if Hugo/Go are available locally)
```

The build should complete with no errors and no deprecation warnings.

## Validation checklist

After upgrading, verify:

- [ ] Build passes without errors or deprecation warnings
- [ ] Companion banners render on docs pages with `companion: true` front matter
- [ ] Lock icons appear in the internal site sidebar for internal-only pages
- [ ] Home page cover image and search render correctly
- [ ] Light/dark mode toggle works and all page elements adapt (navbar, sidebar,
  footer, code blocks)
- [ ] Code blocks have dark background with readable syntax colors in dark mode
- [ ] Agent-support outputs generate, if enabled (`.md` URL variants, `/llms.txt`)
- [ ] Stable URL aliases (`/l/...`) still resolve

For the internal site, also build `infrastructure/internal-docs/` after
updating its `config/internal/config.yaml` and `go.mod` to the same Docsy
version.

## Updating the internal site

The internal site only needs config and module changes (no layout work):

1. Update `internal-docs/config/internal/config.yaml`: change the `theme:` list
   to match the public site.
2. Update the Hugo module and rebuild:

   ```bash
   cd internal-docs
   make container
   # Inside container:
   hugo mod get github.com/google/docsy/theme@vX.Y.Z && hugo mod tidy
   exit
   make setup  # npm dependencies
   make build
   ```

## Rollback

To revert to a previous Docsy version:

```bash
podman run --pull=never -it --rm -u 0 \
  -v $(pwd):/src:z -w /src \
  -e RUNNING_IN_CONTAINER=1 -e HUGO_CACHEDIR=/src/.hugo_cache \
  quay.io/hummingbird-ci/gitlab-ci:latest sh -c \
  "hugo mod get github.com/google/docsy/theme@vPREVIOUS && hugo mod tidy"
```

Then restore the layout overrides from the previous commit (`git checkout HEAD~1 -- layouts/`).

[docsy]: https://www.docsy.dev/
[docsy-changelog]: https://www.docsy.dev/project/about/changelog/
[docsy-lookandfeel]: https://www.docsy.dev/docs/content/lookandfeel/
[docs-repo]: https://gitlab.com/redhat/hummingbird/documentation
[infra-repo]: https://gitlab.com/redhat/hummingbird/infrastructure
