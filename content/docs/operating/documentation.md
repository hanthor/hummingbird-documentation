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

Documentation content comes from three repositories:

1. **[Containers repository][containers-repo]** -
   Documentation focused on container images:
   - `documentation/contributing/` - How to add and modify container images
   - `documentation/background/` - Container image architecture and reference docs
   - `documentation/ci-scripts/` - CI script documentation
   - `CONTRIBUTING.md` - Quickstart guide (mounted as quickstart.md)

2. **[Public documentation repository][docs-repo]** -
   Infrastructure and user guides:
   - `content/docs/using/` - End-user guides for using container images
   - `content/docs/operating/` - Infrastructure operation guides (Konflux, GitLab, etc.)
   - `content/docs/background/` - General architecture and concepts

3. **[Internal documentation repository][internal-docs-repo]** -
   Internal-only confidential content

### How They Work Together

The repositories are layered using Hugo Modules:

1. **Public documentation** imports specific directories from the containers repository
2. **Internal documentation** imports the public documentation (which transitively includes
   the containers documentation)

**Hugo Module Mounts:**

```yaml
# In documentation/config.yaml
module:
  imports:
    - path: gitlab.com/redhat/hummingbird/containers
      mounts:
        - {source: 'CONTRIBUTING.md', target: content/docs/contributing/quickstart.md}
        - {source: 'documentation/contributing', target: content/docs/contributing}
        - {source: 'documentation/background', target: content/docs/background/containers}
        - {source: 'documentation/ci-scripts', target: content/docs/background/containers/ci-scripts}
```

This creates a unified documentation site from multiple repositories without duplication.

## Getting Started

### Quick Start

Clone and start the documentation server:

```bash
git clone https://gitlab.com/redhat/hummingbird/documentation
cd documentation
make serve  # Available at http://localhost:1313/
```

For the internal documentation:

```bash
git clone https://gitlab.com/redhat/hummingbird/internal-documentation
cd internal-documentation
make serve  # Available at http://localhost:1314/
```

### Recommended Setup

For the best development experience, set up all three repositories with
[direnv]:

```bash
mkdir -p ~/git/hummingbird
cd ~/git/hummingbird

# Clone all repositories
git clone https://gitlab.com/redhat/hummingbird/containers
git clone https://gitlab.com/redhat/hummingbird/documentation
git clone https://gitlab.com/redhat/hummingbird/internal-documentation

# Set up environment variables
cat > .envrc << 'EOF'
export CONTAINERS_REPO_PATH=$(pwd)/containers
export DOCUMENTATION_REPO_PATH=$(pwd)/documentation
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

## Documentation Structure

The public documentation is organized into several main sections:

- **Using** - Guides for users of Project Hummingbird container images
- **Contributing** - Guides for contributors to the project
- **Operating** - Guides for infrastructure operators
- **Background** - Technical background and architecture information

The internal documentation adds:

- **Internal** - Internal-only infrastructure, permissions, and team documentation

When adding new documentation, place it in the most appropriate section.

[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[docs-repo]: https://gitlab.com/redhat/hummingbird/documentation
[internal-docs-repo]: https://gitlab.com/redhat/hummingbird/internal-documentation
[direnv]: https://direnv.net/
