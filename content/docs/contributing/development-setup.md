---
title: Development Setup
description: >-
  Set up your development environment for building and testing container images.
weight: 10
---

## Container Image Locations

### Release Images

All production container images are automatically published to the
[hummingbird][quay] organization on Quay.io.

[quay]: https://quay.io/organization/hummingbird

Each image is available at:

```text
quay.io/hummingbird/<image-repository>:<image-tag>
```

Examples:

- `quay.io/hummingbird/curl:latest`
- `quay.io/hummingbird/git:latest-builder`
- `quay.io/hummingbird/nodejs:20` (from `nodejs-20/`)
- `quay.io/hummingbird/nodejs:latest` (from `nodejs-24/`)

### Development Images

During development and merge request testing, images are built in the Red Hat
User Workloads registry:

```text
quay.io/redhat-user-workloads/hummingbird-tenant/<group>--<variant>--main
```

For merge request builds, images are tagged with:

```text
quay.io/redhat-user-workloads/hummingbird-tenant/<group>--<variant>--main:on-mr-<MR_ID>-<COMMIT_SHA>
```

Where `<COMMIT_SHA>` is the SHA of the branch tip commit for the merge request.

Examples:

- `quay.io/redhat-user-workloads/hummingbird-tenant/curl--default--main`
- `quay.io/redhat-user-workloads/hummingbird-tenant/nginx--builder--main:on-mr-123-abc1234`

## Build Process

### Build Environment Variables

The Makefile supports several environment variables to control behavior:

| Variable              | Default | Description                                                                                                    |
|-----------------------|---------|----------------------------------------------------------------------------------------------------------------|
| `PULL`                | `newer` | Controls image pull policy for gitlab-ci container. Options: `never`, `newer`, `always`, `missing`.            |
| `XARGS_PARALLEL_JOBS` | #cpus   | Number of parallel jobs for generation scripts. Controls parallelism in containerfile and lockfile generation. |

Example usage:

```bash
# Avoid pulling the gitlab-ci image (use local cache)
make generate-containerfiles PULL=never

# Always pull latest gitlab-ci image
make generate PULL=always

# Run generation with 8 parallel jobs
XARGS_PARALLEL_JOBS=8 make generate-containerfiles
```

### Generate Containerfiles

Creates final Containerfiles from Jinja2 templates:

```bash
make generate-containerfiles
```

Arguments for `generate_containerfiles.sh` are supported:

```bash
make generate-containerfiles ARGS="curl"
```

This combines:

- Reusable macros from `macros/`
- Service-specific templates from `images/*/Containerfile.j2`
- Variables from `images/variables.yml`

### Build Container Images

#### Using the Build Script (Recommended)

The project includes a build script that provides a consistent interface for
building container images.

Run `ci/build_images.sh --help` for basic usage information, and see the containers repository documentation for the details.

#### Manual Build

To build a single image manually, you can run the following:

```bash
buildah build -t quay.io/hummingbird/<group-name>:latest \
  --cap-add=all -f images/<group-name>/default/Containerfile images/<group-name>
```

### Complete Generation (GitOps)

Generates both Containerfiles and GitOps configurations:

```bash
make generate
```

Arguments for `generate.sh` are supported:

```bash
make generate ARGS="--help"
make generate ARGS="nginx postgresql"
```

### Linters and Checkers

The `make check` target is used to run a number of linters and static analyses
on the code including shellcheck, markdown linters, and a number of checks on
Containerfiles and the images.

Make sure to run those checks before opening a merge request.

## Next Steps

- [Adding New Images](adding-images.md) - Step-by-step guide for adding container images
- [Integration Testing](testing.md) - Learn about testing your images
- [Architecture](architecture.md) - Understand the template system and build process
