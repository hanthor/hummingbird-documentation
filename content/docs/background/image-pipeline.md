---
title: Image Pipeline
description: How the container image pipeline works from source to release
weight: 10
---

Explanation of the complete container image pipeline, from source templates
through generation, build, testing, and release.

## Overview

The container image pipeline consists of five main stages:

1. **Source Templates** - Jinja2 templates in `images/*/` define container images
2. **Generation** - Templates are rendered into Containerfiles and Konflux resources
3. **Build** - Konflux builds multi-architecture container images
4. **Testing** - Testing Farm runs integration tests via Konflux
5. **Release** - Images are published to Quay.io

## Stage 1: Source Templates

Each container image is defined by templates in `images/<image-name>/`:

- **`properties.yml`** - Image configuration (packages, variants, tags, etc.)
- **`Containerfile.j2`** - Jinja2 template for the container build
- **`README.md.j2`** - Documentation template
- **`tests-container.yml`** - Integration test definitions

Templates use reusable macros from `macros/*.yml.j2`:

- `setup_newroot()` - Configures DNF and filesystem
- `install_newroot()` - Installs packages
- `cleanup_newroot()` - Cleans up files
- `final_stage()` - Creates scratch-based final image

Shared configuration is defined in `images/variables.yml`. See [Global Variables
Reference][global-vars] for details.

## Stage 2: Generation

Templates are rendered into concrete artifacts that drive the pipeline:

- **Containerfiles** - Build instructions for each image variant
- **README documentation** - Image documentation for Quay.io
- **Konflux resources** - CI/CD pipeline definitions

### Containerfile Generation

Containerfiles are generated from templates for each image variant:

```bash
make generate-containerfiles
```

This combines:

- Reusable macros from `macros/`
- Service-specific templates from `images/*/Containerfile.j2`
- Configuration from `properties.yml` (see [Image Configuration Reference][image-config])
- Variables from `images/variables.yml` (see [Global Variables Reference][global-vars])

Output: `images/<image-name>/<variant>/Containerfile`

### README Generation

After Containerfiles are generated, README documentation is generated from `README.md.j2` templates:

1. Tag values are extracted from the generated Containerfile labels
2. README is rendered using macros from `macros/readme.yml.j2`
3. Generated README includes actual version tags from the Containerfile

Output: `images/<image-name>/README.md`

### Konflux Resource Generation

Konflux CI/CD resources are generated from templates in `konflux-templates/`:

```bash
make generate
```

This generates:

- **Components** - Define what to build (one per image variant)
- **ImageRepositories** - Define where to push images
- **ReleasePlanAdmissions** - Define how to release images

Output: `konflux-templates/rendered.yml`

These resources must be deployed to Konflux before builds can run. See the [Setting Up a Konflux
Cluster](../operating/setting-up-konflux-cluster.md) guide for deployment procedures.

## Stage 3: Build

Konflux builds container images automatically when changes are pushed to GitLab.

### Build Triggers

- **Merge Requests**: Builds all changed images and triggers tests
- **Main Branch**: Builds all changed images (tests do not run on main)

### Build Process

For each image variant:

1. Konflux Component watches the GitLab repository
2. On changes, Konflux triggers a build PipelineRun
3. The build uses the generated Containerfile from `images/<name>/<variant>/Containerfile`
4. Images are built for multiple architectures (x86_64 and aarch64)
5. Built images are pushed to the development registry

### Build Output

Development images are pushed to the Red Hat User Workloads registry:

```text
quay.io/redhat-user-workloads/hummingbird-tenant/<group>--<variant>--main
```

Merge request builds are tagged with:

```text
quay.io/redhat-user-workloads/hummingbird-tenant/<group>--<variant>--main:on-mr-<MR_ID>-<COMMIT_SHA>
```

Examples:

- `quay.io/redhat-user-workloads/hummingbird-tenant/curl--default--main`
- `quay.io/redhat-user-workloads/hummingbird-tenant/nginx--builder--main:on-mr-123-abc1234`

## Stage 4: Testing

### Testing Farm Integration

When a merge request modifies container images, automated integration tests run via [Testing
Farm][testing-farm]. Tests execute on RHEL-9-Nightly systems for both `x86_64` and `aarch64`
architectures as configured in the [infrastructure repository][infrastructure].

Test results appear as external jobs in the GitLab CI pipelines, alongside regular GitLab CI jobs.
These external jobs provide pass/fail status and link to the Testing Farm PipelineRun in Konflux.

[testing-farm]: https://docs.testing-farm.io/
[infrastructure]: https://gitlab.com/redhat/hummingbird/infrastructure

### Testing Flow

1. Developer opens MR modifying `images/nginx/`
2. GitLab CI pipeline and Konflux pipelines start in parallel, and Konflux jobs appear as external
   jobs in the GitLab CI pipeline
3. Konflux builds `nginx` image variants
4. `IntegrationTestScenario` triggers Testing Farm job
5. tmt discovers fmf plan (`ci/run_tests_container.fmf`)
6. Testing Farm provisions machines (`x86_64` and `aarch64` with RHEL-9-Nightly)
7. tmt sets up the testing environment
8. tmt runs tests via `ci/run_tests_container.sh`

### Test Triggering

Tests are only triggered on merge requests, not on main branch builds.

For a container image group at `images/<group-name>/`, tests are triggered for all changes below
that directory, excluding documentation-only changes.

Any changes below `.tekton/` or `ci/` will trigger tests for the `caddy` image to ensure
infrastructure changes work before merging.

### Test Execution

For each image group, two arch-specific pipelines per variant will be created.

If there is more than one variant in an image group, two additional arch-specific group
pipelines will be created. See [Konflux group snapshot documentation][group-snapshots] for more
details.

[group-snapshots]: https://konflux-ci.dev/docs/testing/integration/snapshots/group-snapshots/

Each pipeline will run tests for Podman and Docker engines. Tests will be selected based on the
`variants` field in the group-specific `tests-container.yml` files. Additionally, global tests from
`ci/{variant}-tests/tests-container.yml` will also be included.

The group pipelines will run tests that specify `variants: [group]`, allowing tests to validate
functionality across multiple variants.

For groups that specify `reverse_dependency_tests: true` in their `properties.yml`, tests from
dependent images are also included, with those images being built locally in the testing environment
to ensure compatibility with the code under test.

### Integration Test Scenarios

Integration tests are triggered via `IntegrationTestScenario` resources defined in the
[infrastructure repository][infrastructure]:

| Application           | Tests Images From | Purpose                       |
|-----------------------|-------------------|-------------------------------|
| `containers-main/`    | `images/`         | Production user-facing images |
| `containers-ci-main/` | `ci/images/`      | Internal CI tooling images    |

The integration tests use the upstream [Testing Farm container testing pipeline for Konflux
CI][integrations-konflux]:

[integrations-konflux]: https://gitlab.com/testing-farm/integrations-konflux

```yaml
kind: IntegrationTestScenario
spec:
  contexts:
    - {name: pull_request}
  params:
    - {name: COMPOSE, value: RHEL-9-Nightly}
    - {name: ARCH, value: x86_64|aarch64}  # one for each
    - {name: IMAGE_TAG, value: v3.2}
  resolverRef:
    resolver: bundles
    params:
      - {name: bundle, value: quay.io/testing-farm/tmt-via-testing-farm:$(params.IMAGE_TAG)}
      - {name: name, value: tmt-via-testing-farm}
      - {name: kind, value: pipeline}
```

Testing Farm provides these environment variables to the test plan:

| Variable        | Description                                    |
|-----------------|------------------------------------------------|
| `IMAGE_NAME`    | Single component (e.g., `curl--default--main`) |
| `IMAGE_NAMES`   | Multiple components for group pipelines        |
| `IMAGE_URL`     | Image URL from Konflux                         |
| `IMAGE_URL_...` | Image URLs from Konflux for group pipelines    |
| `SNAPSHOT_b64`  | Snapshot metadata (base64 encoded)             |

### FMF Test Plan

The root folder of the `containers` repository is marked with a `.fmf` directory to enable Testing
Farm support. The actual test plan in `ci/run_tests_container.fmf` runs the following steps:

1. Install `podman` for container testing
2. Download and install Docker CLI for Docker-in-Docker tests
3. Fix git submodules until [TFT-3991] is resolved
4. For regular pipelines:
   - If needed, build reverse dependency images locally via Buildah
   - Run Podman and Docker tests for the component under test via `ci/run_tests_container.sh
     --component-name`
5. For group pipelines:
   - Run Podman and Docker group tests for the updated components via `ci/run_tests_container.sh
     --group-component-name`

[TFT-3991]: https://issues.redhat.com/browse/TFT-3991

### Reverse Dependency Testing

When a base image like `core-runtime` changes, dependent images (rust, xcaddy, etc.) need to be
tested to ensure compatibility. Images can opt-in to the required reverse dependency testing by
adding `reverse_dependency_tests: true` in their `properties.yml`.

Dependent images are rebuilt locally in the testing environment. This prevents version skew between
container images and tests and ensures that the dependent images are in sync with the repository
status in the merge request under test.

For example, when `core-runtime` changes:

1. Konflux builds `core-runtime` image
2. Testing Farm builds dependent images locally (`rust`, `xcaddy`)
3. Tests run for `core-runtime` (from Konflux) and dependent images (local builds)

## Stage 5: Release

After images pass testing in merge requests and are merged to main, they are released to production.

### Release Process

1. Merge request passes all tests
2. Merge request is merged to main branch
3. Konflux builds images from main
4. ReleasePlanAdmission resources trigger the release pipeline
5. Images are copied from development registry to production registry
6. Tags are applied based on `properties.yml` configuration

### Release Output

Production images are published to the [hummingbird][quay] organization on Quay.io:

[quay]: https://quay.io/organization/hummingbird

```text
quay.io/hummingbird/<image-repository>:<image-tag>
```

Examples:

- `quay.io/hummingbird/curl:latest`
- `quay.io/hummingbird/git:latest-builder`
- `quay.io/hummingbird/nodejs:20` (from `nodejs-20/`)
- `quay.io/hummingbird/nodejs:latest` (from `nodejs-24/`)

### Release Tags

Tags are extracted from Containerfile labels as defined in `properties.yml`:

- `latest` - Latest version of the image
- `<major>` - Major version (e.g., `20` for Node.js 20.x)
- `<major>.<minor>` - Major.minor version (e.g., `20.11`)
- `<full-version>` - Complete version with release (e.g., `20.11.1-1.fc42`)

Non-default variants receive a `-<variant>` suffix (e.g., `latest-builder`).

### Image Documentation

When a commit to main changes a `README.md` file, the content is automatically
pushed to quay.io as the image description via the `update_quay_description`
job.

## Next Steps

- [Development Workflow][dev-workflow] - Practical guide for contributing
- [Adding Images][adding-images] - Step-by-step guide for adding new images
- [Testing Guide][testing] - How to run and write tests locally
- [Image Configuration Reference][image-config] - Complete `properties.yml` reference

[global-vars]: global-variables-reference.md
[image-config]: ../contributing/image-configuration-reference.md
[dev-workflow]: ../contributing/development-workflow.md
[adding-images]: ../contributing/adding-images.md
[testing]: ../contributing/testing-images.md
