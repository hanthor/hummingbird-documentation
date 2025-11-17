---
title: Global Variables Reference
description: Complete reference for global configuration in images/variables.yml
weight: 20
---

Complete reference for global configuration settings that apply to all
container images.

## Overview

The `images/variables.yml` file contains global configuration that applies to
all container images in the repository. These settings define project-wide
defaults, security parameters, and variant-specific behavior.

**Location:** `images/variables.yml` (in the containers repository root)

**Scope:** All images inherit these settings unless overridden in
image-specific `properties.yml`

## Configuration Reference

### cpe

- **Type**: String (CPE 2.3 formatted string)
- **Default**: `"cpe:2.3:a:redhat:hummingbird:1"`
- **Description**: Common Platform Enumeration (CPE) identifier for all
  Hummingbird containers.
- **Usage**: Automatically added as a label to all generated container images
  and passed to `inject-source-info` during the build process.
- **Format**: CPE 2.3 URI binding format:
  `cpe:2.3:part:vendor:product:version:update:edition:lang:sw_edition:target_sw:target_hw:other`

### default_user

- **Type**: String (numeric UID)
- **Default**: `"65532"`
- **Description**: The default unprivileged user ID that all containers run as.
- **Usage**: Set via the `USER` instruction in generated Containerfiles.
- **Value**: `65532` is chosen as a high, non-conflicting UID that:
  - Avoids conflicts with system users (typically < 1000)
  - Avoids conflicts with regular users (typically 1000-60000)

### set_root_user

- **Type**: String (Containerfile USER directive)
- **Default**: `"USER 0"`
- **Description**: The Containerfile instruction used to override the default
  unprivileged user and make the container run as root. This is used in
  specific images where root access is necessary for the container's runtime
  functionality.
- **Usage**: Placed at the end of `Containerfile.j2` templates as `{{
  set_root_user }}` to replace the default `{{ set_default_user() }}`
  behavior. Used in builder/development variants and language runtime images
  where users need root privileges to install packages, modify filesystem, or
  avoid permission issues with mounted volumes.

### default_rpm_packages

- **Type**: Object with variant names as keys, arrays of package names as
  values
- **Default**:

  ```yaml
  default_rpm_packages:
    builder:
      - bash
      - dnf5
      - dnf5-plugins
      - shadow-utils
  ```

- **Description**: Defines packages that are automatically included in specific
  variants across all images. These are added in addition to packages defined
  in image-specific `properties.yml`.
- **Variants**: Currently only `builder` is defined, but other variants can be
  added
- **Usage**: Use this to provide variant-specific packages that should be
  available in all images using that variant. For example, builder variants
  include package management tools for development workflows.

### default_variant_repos

- **Type**: Object with variant names as keys, arrays of repository filenames
  as values
- **Default**:

  ```yaml
  default_variant_repos:
    default:
      - fedora-rawhide.repo
  ```

- **Description**: Defines which yum repositories each variant uses by default
  for package installation and lockfile generation. If a variant is not
  explicitly defined, it falls back to the `default` entry.
- **Repository Files**: References files in the `yum-repos/` directory
- **Usage**: This allows different variants to use different package sources.
- **Override**: Image-specific `additional_repos` in `properties.yml` are
  appended to the variant-specific repos
- **See Also**: [Image Configuration Reference - additional_repos][additional_repos]

## Next Steps

- [Image Configuration Reference][image-config] - Per-image configuration
- [Image Variants][image-variants] - Understanding variant types
- [Adding Images][adding-images] - How to add a new container image

[additional_repos]: ../contributing/image-configuration-reference.md#additional_repos
[image-config]: ../contributing/image-configuration-reference.md
[image-variants]: ../using/image-variants.md
[adding-images]: ../contributing/adding-images.md
