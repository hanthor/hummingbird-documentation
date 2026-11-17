---
title: Writing Documentation
description: >-
  How to contribute to the Project Hummingbird documentation.
weight: 40  # Keep pages sorted alphabetically by title; use increments of 10
aliases: [/l/writing-documentation]
---

## Overview

New documentation is always welcome! This guide explains how to contribute to
the Project Hummingbird documentation.

## Documentation Sites

The Project Hummingbird documentation is **open by default** and available at two
sites:

- **Public documentation**: <https://hummingbird-project.io/>
- **Internal documentation**: <https://internal-documentation.hummingbird-project.io/>

## Documentation Repositories

Documentation content comes from six repositories:

1. **[Containers repository][containers-repo]** -
   Documentation focused on container images (cross-cutting layout):
   - `documentation/contributing/` - How to add and modify container images
   - `documentation/background/` - Container image architecture and reference docs
   - `documentation/ci-scripts/` - CI script documentation
   - `documentation/operating/` - Operator runbooks for image maintenance
   - `documentation/using/` - End-user guides (custom CA certificates, etc.)
   - `README.md` - User guide
   - `CONTRIBUTING.md` - Quickstart guide

2. **[RPMs repository][rpms-repo]** -
   Documentation focused on RPM packages (cross-cutting layout):
   - `documentation/background/` - RPM pipeline architecture and Konflux deployment
   - `documentation/operating/` - Operator runbooks for package management
   - `CONTRIBUTING.md` - Contributing guide for RPM packages

3. **[Tools repository][tools-repo]** -
   Documentation for infrastructure tools and services (cross-cutting layout):
   - `documentation/background/` - Cross-cutting pages: architecture (message bus, data
     flow, artifact promotion, shared contracts) and team workflow guides
   - `documentation/components/` - One page per tool or service; components with design
     docs or DDRs are page bundles: a directory with `_index.md` as the main page plus
     child pages like `design.md`/`design-decisions.md`
   - `documentation/operating/` - Operator runbooks for tools and services

   The `contributing/` and `using/` mounts are pre-provisioned for future use; the
   shared Contributing section is containers-scoped, so the team workflow guides live
   in `background/`.

4. **[K8s test pipeline repository][k8s-test-pipeline-repo]** -
   Documentation for Kubernetes integration testing (per-component layout):
   - `documentation/` - Pipeline design, test format, and EaaS debugging

   Section mounts are pre-provisioned for a future split into the standard
   subdirectories.

5. **[Public documentation repository][docs-repo]** -
   Site infrastructure and cross-cutting guides:
   - `content/docs/using/` - End-user guides for using container images
   - `content/docs/operating/` - Infrastructure operation guides (Konflux, GitLab, etc.)
   - `content/docs/background/` - General architecture and concepts

6. **[Infrastructure repository][infra-repo]** -
   Internal-only documentation (cross-cutting layout):
   - `documentation/operating/` - Internal operational docs (AWS, DNS, GitLab, etc.)
   - `documentation/background/` - Internal background docs (error budgets, etc.)
   - `documentation/presentations/` - Team presentations and talks

### How They Work Together

The repositories are layered using Hugo Modules:

1. **Public documentation** imports specific directories from the containers, rpms, tools,
   and k8s-test-pipeline repositories
2. **Internal documentation** is built from the infrastructure repository's `internal-docs/`
   subtree. It imports the public documentation (which transitively includes the imported
   repository documentation) and mounts the infrastructure repo's `documentation/` directory
   as the Internal section

**Hugo Module Mounts:**

```yaml
# In documentation/config.yaml
module:
  imports:
    - path: gitlab.com/redhat/hummingbird/containers
      mounts:
        - {source: 'README.md', target: content/snippets/readme.md}
        - {source: 'CONTRIBUTING.md', target: content/snippets/contributing.md}
        - {source: 'documentation/contributing', target: content/docs/contributing, files: "*.md"}
        - {source: 'documentation/background', target: content/docs/background/containers, files: "*.md"}
        - {source: 'documentation/ci-scripts', target: content/docs/background/containers/ci-scripts, files: "*.md"}
        - {source: 'documentation/operating', target: content/docs/operating, files: "*.md"}
        - {source: 'documentation/using', target: content/docs/using, files: "*.md"}
    - path: gitlab.com/redhat/hummingbird/rpms
      mounts:
        - {source: 'CONTRIBUTING.md', target: content/snippets/rpms-contributing.md}
        - {source: 'documentation/background', target: content/docs/background/rpms, files: "*.md"}
        - {source: 'documentation/contributing', target: content/docs/contributing, files: "*.md"}
        - {source: 'documentation/operating', target: content/docs/operating, files: "*.md"}
        - {source: 'documentation/using', target: content/docs/using, files: "*.md"}
    - path: gitlab.com/redhat/hummingbird/tools
      mounts:
        - {source: 'documentation/background', target: content/docs/background/tools, files: "*.md"}
        # Per-component page bundles: multi-file components are branch
        # bundles (_index.md + child pages); the recursive glob plus the
        # shared target keeps each component's main-page URL flat.
        - {source: 'documentation/components', target: content/docs/background/tools, files: ["*.md", "**/*.md"]}
        - {source: 'documentation/contributing', target: content/docs/contributing, files: "*.md"}
        - {source: 'documentation/operating', target: content/docs/operating, files: "*.md"}
        - {source: 'documentation/using', target: content/docs/using, files: "*.md"}
    - path: gitlab.com/redhat/hummingbird/pipelines/k8s-test-pipeline
      mounts:
        # Serves the current flat layout; the section mounts below are
        # ready for whenever the repository adopts the standard subdirs.
        - {source: 'documentation', target: content/docs/background/k8s-test-pipeline, files: "*.md"}
        - {source: 'documentation/background', target: content/docs/background/k8s-test-pipeline, files: "*.md"}
        - {source: 'documentation/contributing', target: content/docs/contributing, files: "*.md"}
        - {source: 'documentation/operating', target: content/docs/operating, files: "*.md"}
        - {source: 'documentation/using', target: content/docs/using, files: "*.md"}
```

For README.md and CONTRIBUTING.md, front matter is provided via wrapper files.

This creates a unified documentation site from multiple repositories without duplication.

### Documentation Layout Patterns

Source repositories use one of two layout patterns depending on their content:

**Cross-cutting layout** (containers, rpms, tools): The repository documents cross-cutting
concerns like contributing, operating, and background information. Documentation is
organized into subdirectories matching the site sections:

- `documentation/background/` - Explanation and reference material
- `documentation/contributing/` - How to contribute
- `documentation/operating/` - Operator runbooks
- `documentation/using/` - End-user guides

Each subdirectory is mounted into the matching site section, so operating docs from
different repositories appear together under Operating. Not every repository uses every
subdirectory: the tools repository keeps its team workflow guides in `background/` (the
shared Contributing section is currently containers-scoped) and leaves `contributing/`
and `using/` to the pre-provisioned mounts, unused for now.

The tools repository combines the cross-cutting sections with per-component page bundles
inside `components/`: one page per component, and components with design docs or DDRs
become bundles — a directory with `_index.md` as the main page plus child pages like
`design.md` or `design-decisions.md`. The recursive `components` mount targets the same
`content/docs/background/tools` path as the other background mounts, so a bundle's main
page keeps a flat URL (`/docs/background/tools/<component>/`) while its child pages nest
one level below it (`/docs/background/tools/<component>/design/`).

**Per-component layout** (k8s-test-pipeline): The repository is a monorepo where
each documentation page covers one tool or component. Documentation is a flat directory
with one file per component:

- `documentation/<component-name>.md`

The entire directory is mounted under `background/<repo-name>/` on the site. Section
mounts for the standard subdirectories are pre-provisioned in the site configuration,
so the repository can adopt the cross-cutting layout without further site changes.

## Getting Started

### Quick Start

Clone, install dependencies, and start the documentation server:

```bash
git clone https://gitlab.com/redhat/hummingbird/documentation
cd documentation
make setup  # Installs npm dependencies; only needed once per checkout
make serve  # Available at http://localhost:1313/
```

For the internal documentation:

```bash
git clone https://gitlab.com/redhat/hummingbird/infrastructure
cd infrastructure/internal-docs
make serve  # Available at http://localhost:1314/
```

### Recommended Setup

For the best development experience, set up all repositories with
[direnv]:

```bash
mkdir -p ~/git/hummingbird
cd ~/git/hummingbird

# Clone all repositories
git clone https://gitlab.com/redhat/hummingbird/containers
git clone https://gitlab.com/redhat/hummingbird/rpms
git clone https://gitlab.com/redhat/hummingbird/tools
git clone https://gitlab.com/redhat/hummingbird/pipelines/k8s-test-pipeline
git clone https://gitlab.com/redhat/hummingbird/documentation
git clone https://gitlab.com/redhat/hummingbird/infrastructure

# Set up environment variables
cat > .envrc << 'EOF'
export CONTAINERS_REPO_PATH=$(pwd)/containers
export RPMS_REPO_PATH=$(pwd)/rpms
export TOOLS_REPO_PATH=$(pwd)/tools
export K8S_TEST_PIPELINE_REPO_PATH=$(pwd)/k8s-test-pipeline
export DOCUMENTATION_REPO_PATH=$(pwd)/documentation
export INFRASTRUCTURE_REPO_PATH=$(pwd)/infrastructure
EOF
direnv allow
```

This automatically uses your local repositories for imported content, making changes
immediately visible in the documentation preview.

## Adding Documentation

Add new documentation as markdown files inside the appropriate directory under
`content/`. Every file should end in `.md`.

Preview your changes:

```bash
make serve  # Starts local server with live reload
```

Check for problems:

```bash
make check  # Runs linters and validation
```

After `make setup`, run the Docsy print-layout regression tests:

```bash
make test
```

These tests build a small site with Mermaid diagrams in section and child pages.
They check renderer inclusion in normal and combined print views, including nested
sections and `no_print` exclusions. After changing print rendering, also check a
diagram page and its "Print entire section" view in a browser, then export a PDF
and confirm that the diagrams remain visible.

## Link Format

Documentation uses two types of internal links depending on the context:

### Same-Directory Links and Cross-Section Links in the Documentation Repository

Use relative `.md` links for pages in the same directory, and for cross-section
links in the documentation repository:

```markdown
[Testing Guide](testing-images.md)
[Adding Images](adding-images.md)
```

### Cross-Section and Cross-Repository Links

Use full URLs with `/l/` aliases for links across repositories or across
sections in all repositories:

```markdown
[Image Pipeline][image-pipeline]
[Global Variables][global-vars]
[Retrying Checks][retrying-checks]

[image-pipeline]: https://hummingbird-project.io/l/image-pipeline
[global-vars]: https://hummingbird-project.io/l/global-variables-reference
[retrying-checks]: https://hummingbird-project.io/l/retrying-konflux-checks
```

**Why full URLs?**

- Work in standalone contexts (GitHub, text editors, when files are copied)
- Hugo's link render hook automatically converts them to relative links in the rendered site
- Stable even when files are moved or reorganized
- Clear and explicit about which page is being referenced

### URL Stability

Documentation URLs (for example, `/docs/background/tools/page/`) are **not stable**.
They change whenever content is reorganized, and a moved page's previous URL returns a
404 by design.

Only `/l/` aliases are stable and guaranteed to keep resolving. Use them for any
reference that must survive reorganization:

- Cross-repository links
- Cross-section links
- Merge request comments
- Scripts
- Bookmarks

### Link Render Hook

The documentation site includes a custom link render hook
(`layouts/_default/_markup/render-link.html`) that:

1. Detects `https://hummingbird-project.io/l/...` URLs
2. Looks up the page with the matching alias
3. Converts to a relative link in the rendered HTML
4. Keeps external links as-is with `target="_blank"`

This provides the best of both worlds: full URLs in markdown source files that work
everywhere, and optimized relative links in the rendered site.

## Stable Link Aliases

**All cross-referenced pages should have stable `/l/` aliases.** These aliases serve two purposes:

1. **Incoming links from external sources** (documentation, scripts, merge request comments)
2. **Cross-references within documentation** (across sections or repositories)

### Stability Policy

Only `/l/` aliases are stable and guaranteed to keep resolving. Documentation URLs change
whenever content is reorganized, and a moved page's previous URL returns a 404 by design.

Never add an alias for a page's previous URL after a move — aliases are curated stable
links, not a redirect backlog.

### Adding an Alias

Add an alias in the page front matter:

```yaml
---
title: "Konflux Integration"
aliases: [/l/konflux-integration]
---
```

Now you can link to `https://hummingbird-project.io/l/konflux-integration` and it
will continue working even if the page moves.

### When to Add Aliases

Add `/l/` aliases to pages that:

- Are referenced from other repositories (e.g., containers repo → docs repo)
- Are linked to from CI scripts or infrastructure
- Are shared in merge request comments or external documentation
- Are referenced across documentation sections

### Naming Convention

- Use `/l/` prefix for all stable links
- Keep names short, memorable, and descriptive
- Use kebab-case (lowercase with hyphens)
- No nested paths (flat structure only)

## Submitting Changes

1. Fork the repository on GitLab
2. Clone your fork locally
3. Create a new branch for your changes
4. Make your changes and test them with `make serve`
5. Run `make check` to ensure there are no errors
6. Commit your changes with a descriptive commit message
7. Push to your fork
8. Create a merge request against the main repository

## Source Repository Checks

Merge requests that change mounted documentation are checked in the source
repository's own pipeline. The containers, rpms, tools, and
pipelines/k8s-test-pipeline repositories each have a `check-afdocs` job that
builds this site with the merge request's working tree mounted in place of the
published module, then runs the same agent-friendly docs (afdocs) suite the
documentation repository runs on its own merge requests. The infrastructure
repository has the equivalent job for the internal documentation site
(`check-afdocs-internal-docs`), which also covers the internal documentation
mounted from that repository.

- The job runs automatically when a merge request changes a path the site
  mounts, and is available as an optional manual job otherwise.
- A failure means the rendered site would break. Fix it in the source
  repository — a broken link or oversized page is a content problem there, not
  a build problem here.
- Like a production build, the check resolves the other repositories'
  documentation at their default branches, so a failure can also come from
  another repository's `main`. Re-run the job once that repository is fixed.

```bash
# Run the same check locally from a documentation checkout:
make check-afdocs TOOLS_REPO_PATH=/path/to/tools
```

## Documentation Structure

The public documentation is organized into several main sections:

- **Using** - Guides for users of Project Hummingbird container images
- **Contributing** - Guides for contributors to the project
- **Operating** - Guides for infrastructure operators
- **Background** - Technical background and architecture information

The internal documentation adds:

- **Internal** - Internal-only infrastructure documentation, organized into:
  - **Operating** - AWS, DNS, GitLab, OpenShift, and other service runbooks
  - **Background** - Error budgets, SLIs/SLOs
  - **Presentations** - Team talks and lightning talks

When adding new documentation, place it in the most appropriate section.

[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[rpms-repo]: https://gitlab.com/redhat/hummingbird/rpms
[tools-repo]: https://gitlab.com/redhat/hummingbird/tools
[k8s-test-pipeline-repo]: https://gitlab.com/redhat/hummingbird/pipelines/k8s-test-pipeline
[docs-repo]: https://gitlab.com/redhat/hummingbird/documentation
[infra-repo]: https://gitlab.com/redhat/hummingbird/infrastructure
[direnv]: https://direnv.net/
