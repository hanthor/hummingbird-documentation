---
title: Adding New Images
description: >-
  Step-by-step guide for adding new container images to the project with configuration examples.
weight: 20
---

1. **Create a new directory**: `mkdir images/your-service/`
2. **Copy the base templates**:
   - `cp images/Containerfile.j2 images/your-service/Containerfile.j2`
   - `cp images/properties.yml images/your-service/properties.yml`
3. **Configure packages in `properties.yml`**:
   - Define packages in the `packages` section (see Package Management below)
   - Set `main_package` for version labeling
   - Configure variants, tags, and other metadata
4. **Customize the Containerfile template**:
   - The template uses `{{ main_packages_arg() }}` macro to automatically generate package ARGs
   - Add service-specific configuration
   - Set appropriate user with `{{ set_default_user }}` or `{{ set_root_user }}`
5. **Render templates**: `make generate ARGS="your-service"`
6. **Run linting**: `make check`
7. **Submit your changes**: Create a merge request with clear description of
   what your image does and why it's needed
8. **Deploy Konflux resources**: on the merge request pipeline, click on the
   little play button next to the `deploy_resources_to_konflux` job to trigger
   a limited child pipeline in the [infrastructure] repository that will deploy
   the resources from [konflux/rendered.yml]
9. **Trigger testing**: Add `/retest` comment to your merge request

[infrastructure]: https://gitlab.com/redhat/hummingbird/infrastructure
[konflux/rendered.yml]: https://gitlab.com/redhat/hummingbird/containers/-/blob/main/konflux-templates/rendered.yml

## Image Configuration

Each image can have custom settings via a `properties.yml` file:

```yaml
# images/your-service/properties.yml
---
# Build configuration
hermetic: false                 # Optional: disable hermetic builds (defaults to true)
build_from_source: true         # Optional: build from source instead of using RPMs

# Testing configuration
reverse_dependency_tests: true  # Optional: trigger testing of dependent images

# Optional Golang modules prefetching
# Needed if building Go projects from source with a missing vendor tree
# Value points to a Golang project (e.g. git submodule)
prefetch_gomod_path: images/xcaddy/xcaddy-upstream

variants: [default, builder]    # Optional: image variants to generate
                                # (defaults to [default, builder])
rpm_packages:                   # RPM package definitions (see Package Management section)
  all:
    - coreutils-single
    - your-main-package
    - additional-package
  builder:
    - builder-variant-only-package
  custom:
    - custom-variant-only-package
  build-deps:
    - not-installed-package
additional_repos:               # Optional: extra yum repositories
  - konflux-ci-rpm-lockfile-prototype-main-fedora-rawhide.repo

# Package versioning
# For RPM-based images, specify the package name
main_package: package-name      # Optional: to create the VERSION file
# For source-built images with git submodules, specify the submodule path
# Version will be automatically extracted from .gitmodules
main_package: images/xcaddy/xcaddy-upstream  # Example for xcaddy

# Release configuration
repository: custom-repo-name    # Optional: override repository name
tags:                           # define tags, see below for help methods
  - value: latest
  - value: '{{ package_major_version("<package-name>") }}'
    label: MAJOR_VERSION
  - value: '{{ package_major_minor_version("<package-name>") }}'
    label: MAJOR_MINOR_VERSION
  - value: '{{ package_version("<package-name>") }}'
    label: VERSION
```

For images that have multiple versions, make sure to only set `:latest` on
the latest version.

## Versioning for Source-Built Images

Images built from source using git submodules automatically extract their
version from the `.gitmodules` file. This eliminates the need for manual
version configuration and ensures consistency during automated updates.

**How it works:**

1. Set `build_from_source: true` in `properties.yml`
2. Set `main_package` to the submodule path (e.g., `images/xcaddy/xcaddy-upstream`)
3. Ensure the submodule has a `branch` field in `.gitmodules` specifying the
   version tag
4. The build system automatically extracts the version from `.gitmodules` using
   `ci/internal/parse_gitmodules.py`

**Benefits:**

- **Automated updates**: When renovate bot or mintmaker updates the submodule,
  the version is automatically updated without manual `properties.yml` changes
- **Single source of truth**: Version information lives only in `.gitmodules`
- **No stale state**: Prevents inconsistencies where the submodule is updated
  but the properties file still contains the old version

**Example:**

For xcaddy, the `.gitmodules` entry looks like:

```ini
[submodule "images/xcaddy/xcaddy-upstream"]
    path = images/xcaddy/xcaddy-upstream
    url = https://github.com/caddyserver/xcaddy
    branch = v0.4.5
```

And the `properties.yml` references the submodule path:

```yaml
main_package: images/xcaddy/xcaddy-upstream
build_from_source: true
```

The `package_version()` macro will then return `v0.4.5` extracted from
`.gitmodules`.

## Image Variants

Images can have multiple variants (e.g., `default` and `builder`):

- **default**: Minimal runtime environment
- **builder**: Includes development tools and build dependencies
- **custom**: Define custom variants in `properties.yml`

Each variant gets its own:

- Containerfile in `images/<name>/<variant>/Containerfile`
- RPM lockfiles in `images/<name>/<variant>/rpms`
- Build pipeline and release tags (non-default variants get `-<variant>` suffix)

## Package Management and Hermetic Builds

Packages are defined in `properties.yml` under `rpm_packages`:

```yaml
rpm_packages:
  all:                    # Included in ALL variants (Containerfiles + lockfiles)
    - coreutils-single
    - your-main-package

  build-deps:             # Included ONLY in lockfiles (for hermetic builds)
    - build-dependencies
    - development-tools

  builder:               # Included only in "builder" variant
    - compiler-packages
    - debug-tools

  custom-variant:        # Included only in "custom-variant" variant
    - variant-specific-packages
```

### Hermetic Build Process

For hermetic builds (enabled by default), all packages from:

- `rpm_packages.all` - included in Containerfiles AND lockfiles
- `rpm_packages.build-deps` - included ONLY in lockfiles
- `rpm_packages.<variant>` - included for matching variants
- `default_rpm_packages.builder` (from `images/variables.yml`) - automatically added for builder variants

are added to `rpms.lock.yaml` and pre-fetched using cachi2 for offline builds.
