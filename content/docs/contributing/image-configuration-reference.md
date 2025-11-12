---
title: Image Configuration Reference
description: Complete reference for properties.yml configuration and image settings
weight: 40
---

Complete reference for configuring container images via `properties.yml`.

## properties.yml Overview

Each image can have custom settings via a `properties.yml` file. This reference documents all
available configuration options.

**Minimal example:**

```yaml
---
rpm_packages:
  all:
    - nginx
main_package: nginx
tags:
  - value: latest
```

**Complete structure:**

```yaml
---
# Image variants (see Image Variants section)
variants: [default, builder]

# Package management (see Package Management section)
rpm_packages:
  build-deps: [...]
  all: [...]
  <variant>: [...]
additional_repos: [...]

# Build configuration (see Build Configuration section)
hermetic: false
build_from_source: true
prefetch_gomod_path: xcaddy-upstream

# Versioning (see Versioning section)
main_package: package-name

# Testing configuration (see Testing Configuration section)
reverse_dependency_tests: true

# Release configuration (see Release Configuration section)
repository: custom-repo-name
tags:
  - value: latest
  - value: '{{ package_major_version("package-name") }}'
    label: MAJOR_VERSION
```

## Image Variants

Images can have multiple variants (e.g., `default` and `builder`):

- **default**: Minimal runtime environment
- **builder**: Includes development tools and build dependencies
- **custom**: Define custom variants in `properties.yml`

Each variant gets its own:

- Containerfile in `images/<name>/<variant>/Containerfile`
- RPM lockfiles in `images/<name>/<variant>/rpms`
- Build pipeline and release tags (non-default variants get `-<variant>` suffix)

### variants

- **Type**: Array of strings
- **Default**: `[default, builder]`
- **Description**: List of image variants to generate. Each variant gets its own Containerfile,
  lockfiles, build pipeline, and release tags. Non-default variants get a `-<variant>` suffix in
  their image tags.
- **Example**: `[default, builder, fpm, fpm-builder]` (PHP image with 4 variants)

## Package Management

Packages are defined in `properties.yml` under `rpm_packages`:

```yaml
rpm_packages:
  build-deps:             # Build-time dependencies (installed in builder layer, not in final
                          # image). Included in lockfiles for hermetic builds.
    - golang              # Example: Go compiler for building from source
    - rpm-build           # Example: Tools for building RPMs during image construction

  all:                    # Included in all variants (Containerfiles and lockfiles)
    - coreutils-single
    - your-main-package

  builder:                # Included only in "builder" variant
    - compiler-packages
    - debug-tools

  custom-variant:         # Included only in "custom-variant" variant
    - variant-specific-packages
```

### rpm_packages.build-deps

- **Type**: Array of strings
- **Description**: Build-time dependencies needed during image construction. Automatically installed
  in the builder layer (not in the final image) and included in lockfiles for hermetic builds. Use
  for compilers, build tools, and other packages needed only during the build process.

### rpm_packages.all

- **Type**: Array of strings
- **Description**: Packages included in all variants, in both Containerfiles and lockfiles

### rpm_packages.\<variant\>

- **Type**: Array of strings
- **Description**: Packages included only in the specified variant

### additional_repos

- **Type**: Array of strings (repository filenames)
- **Default**: None
- **Description**: Additional yum repository files from `yum-repos/` to include in the RPM lockfile
  generation. These repos are added to the standard Fedora and Hummingbird repos. Specify only the
  filename, not the full path.
- **Example**: `[konflux-ci-rpm-lockfile-prototype-main-fedora-rawhide.repo]`
- **Usage**: Only needed for packages not available in standard Fedora or Hummingbird repos

## Hermetic Builds

For hermetic builds (enabled by default), all packages from:

- `rpm_packages.build-deps` - included in lockfiles and Containerfiles (builder layer only)
- `rpm_packages.all` - included in lockfiles and Containerfiles (final image)
- `rpm_packages.<variant>` - included in lockfiles and Containerfiles for matching variants
- `default_rpm_packages.builder` (from `images/variables.yml`) - automatically added for builder
  variants

are added to `rpms.lock.yaml` and prefetched using cachi2 for offline builds.

**Build-time vs Runtime Packages:**

- **`rpm_packages.build-deps`**: Installed in the builder layer only (not in final image)
- **`rpm_packages.all`**: Installed in `${NEWROOT}` (the final image)
- **`rpm_packages.<variant>`**: Installed in `${NEWROOT}` for the specified variant

## Build Configuration

### hermetic

- **Type**: Boolean
- **Default**: `true`
- **Description**: Controls whether the Konflux build pipeline passes `HERMETIC=true` to the buildah
  task, enabling hermetic (offline, network-isolated) builds with prefetched dependencies.
- **Important**: Images with `hermetic: false` are **blocked from release** by the [Conforma
  hermetic_task policy](https://conforma.dev/docs/policy/packages/release_hermetic_task.html#hermetic_task__hermetic).
  Only use `hermetic: false` for non-production images in `ci/images/`.

### build_from_source

- **Type**: Boolean
- **Default**: `false`
- **Description**: Controls version extraction in the `package_version()` macro. When `true`,
  extracts version from `.gitmodules` for images built from git submodules. When `false`, extracts
  version from RPM package metadata. Does not control whether source code is compiled in the
  Containerfile.

### prefetch_gomod_path

- **Type**: String (path relative to image directory)
- **Default**: None
- **Description**: Path to a Golang project directory (typically a git submodule) for prefetching Go
  modules via cachi2. Enables hermetic builds for Go projects without a vendor tree. The path is
  relative to the image directory (e.g., `xcaddy-upstream` for `images/xcaddy/xcaddy-upstream`).
- **Example**: `xcaddy-upstream`
- **Usage**: Only needed for images that build Go projects from source

## Versioning

### main_package

- **Type**: String
- **Description**: Specifies the main package for version labeling

**For RPM-based images:**

Set to the package name. Version is extracted from RPM package metadata.

```yaml
main_package: nginx
```

**For source-built images:**

Set to the submodule path. Version is extracted from the `branch` field in `.gitmodules`.

```yaml
main_package: images/xcaddy/xcaddy-upstream
build_from_source: true
```

Example `.gitmodules` entry:

```ini
[submodule "images/xcaddy/xcaddy-upstream"]
    path = images/xcaddy/xcaddy-upstream
    url = https://github.com/caddyserver/xcaddy
    branch = v0.4.5
```

## Testing Configuration

### reverse_dependency_tests

- **Type**: Boolean
- **Default**: `false`
- **Description**: Enables reverse dependency testing. When `true`, changes to this image trigger
  rebuilds and tests of all images that depend on it. Dependencies are detected by searching for
  `TEST_IMAGES[...]` references in test scripts. Use for images that are
  used as base images in multi-stage builds.
- **Example**: Set to `true` for `core-runtime`, which is used as a base image in xcaddy's
  multi-stage test build and to run compiled binaries for rust

## Release Configuration

### repository

- **Type**: String
- **Default**: Image directory name
- **Description**: Override the Quay.io repository name. Used when multiple image directories should
  publish to the same repository (e.g., `nodejs-20` and `nodejs-24` both use `repository: nodejs`).
  Also used for README generation to group related images.
- **Example**: `nodejs` (used by `nodejs-20` and `nodejs-24` directories)
- **Usage**: Only needed when the directory name differs from the desired Quay.io repository name

### tags

- **Type**: Array of objects
- **Description**: Define image tags for Quay.io releases. Each variant gets these tags, with
  non-default variants receiving a `-<variant>` suffix.

**Tag Object Fields:**

- **`value`** (required): The tag value. Can be a literal string (e.g., `latest`) or a Jinja2
  template using helper functions.
- **`label`** (optional): If specified, the tag value is written as a `LABEL` in the Containerfile,
  and the actual rendered value from the label is used as the image tag. This ensures version tags
  match the actual package versions in the image.

**Tag Helper Functions:**

- `package_version("<package-name>")` - Full version (e.g., `1.2.3-4.fc42`)
- `package_major_version("<package-name>")` - Major version only (e.g., `1`)
- `package_major_minor_version("<package-name>")` - Major.minor version (e.g., `1.2`)

**Example:**

```yaml
tags:
  - value: latest                                        # Literal tag, no label
  - value: '{{ package_major_version("nginx") }}'        # Template tag with label
    label: MAJOR_VERSION                                 # Writes LABEL MAJOR_VERSION=1 in Containerfile
  - value: '{{ package_major_minor_version("nginx") }}'  # Tag becomes actual version from label
    label: MAJOR_MINOR_VERSION
  - value: '{{ package_version("nginx") }}'
    label: VERSION
```

**Note**: For images with multiple versions, only set `latest` on the latest version.

**How Labels Work:**

1. Template is rendered and written to Containerfile: `LABEL VERSION=1.27.3-1.fc42`
2. Build system extracts the actual value from the Containerfile label
3. Image is tagged with the extracted value: `quay.io/hummingbird/nginx:1.27.3-1.fc42`

This ensures tags always match the actual package versions built into the image.

## Next Steps

- [Adding Images](adding-images.md) - Step-by-step guide for adding new images
- [Image Pipeline](../background/image-pipeline.md) - How the complete pipeline works
