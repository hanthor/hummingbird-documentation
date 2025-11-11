---
title: Writing Documentation
description: >-
  How to contribute to the Project Hummingbird documentation.
weight: 70
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

1. **[Containers repository](https://gitlab.com/redhat/hummingbird/containers)** - Technical
   documentation in the `documentation/` directory
2. **[Public documentation repository](https://gitlab.com/redhat/hummingbird/documentation)** -
   User guides, contributor guides, and operating guides
3. **[Internal documentation
   repository](https://gitlab.com/redhat/hummingbird/internal-documentation)** - Internal-only
   confidential content

### How They Work Together

The repositories are layered using Hugo Modules:

1. **Public documentation** imports the containers repository documentation
2. **Internal documentation** imports the public documentation (which transitively
   includes the containers documentation)

Files in later layers can override earlier ones, creating this structure:

1. Containers repository documentation
2. Public documentation repository
3. Internal documentation repository (can add or override)

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
[direnv](https://direnv.net/):

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

## Stable Incoming Links

**Page URLs are not stable** - they change when pages are renamed, moved, or
reorganized. For external references, use aliases to create stable URLs that won't
break.

Add an alias in the page front matter:

```yaml
---
title: "Konflux Integration"
aliases: [/l/konflux-integration]
---
```

Now you can link to `https://hummingbird-project.io/l/konflux-integration` and it
will continue working even if the page moves.

**Naming convention:**

- Use `/l/` prefix for all stable links
- Keep names short, memorable, and descriptive
- Use kebab-case (lowercase with hyphens)

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
