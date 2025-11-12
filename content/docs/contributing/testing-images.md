---
title: Testing Guide
description: How to run and write integration tests locally and work with CI
weight: 30
aliases: [/l/testing-images]
---

Container-based integration tests validate image functionality with both Docker and Podman.

## Running Tests Locally

### Prerequisites

- **Container Engine**: [Podman](https://podman.io/) or [Docker](https://www.docker.com/)
- **Python**: `PyYAML` package (`pip install PyYAML` or `dnf install python3-pyyaml`)

### With Podman (Recommended)

Tests work directly with Podman:

```bash
ci/run_tests_container.sh <image-name>

# Test specific variant
ci/run_tests_container.sh <image-name>/default

# Verbose output (shows passing test output and bash trace)
ci/run_tests_container.sh --verbose <image-name>
```

### With Docker

Use `--setup` to automatically configure Docker-in-Docker:

```bash
ci/run_tests_container.sh --engine docker --setup <image-name>
```

The `--setup` flag:

- Starts `hummingbird-docker-dind` container with `mirror.gcr.io/docker:dind`
- Configures environment variables (`DOCKER_HOST`, `DOCKER_CERT_PATH`, etc.)
- Waits for Docker daemon to be ready
- Reuses existing container on subsequent runs

**Prerequisites:**

- Docker CLI (`dnf install docker-cli`)
- Podman (to run the dind container)

### Building Images

Build images before testing:

```bash
# With Podman
ci/build_images.sh <image-name>

# With Docker
ci/build_images.sh --engine docker --setup <image-name>
```

### Testing Base Images

When modifying base images, test dependent images:

```bash
ci/build_images.sh --include-reverse-deps core-runtime
ci/run_tests_container.sh --include-reverse-deps core-runtime
```

### Reproducing CI Failures

Reproduce Testing Farm failures locally:

```bash
# Single variant tests
ci/run_tests_container.sh --include-reverse-deps --engine podman <image-name>/default
ci/run_tests_container.sh --include-reverse-deps --engine docker --setup <image-name>/default

# Group tests (all variants)
ci/run_tests_container.sh --engine podman <image-name>/group
ci/run_tests_container.sh --engine docker --setup <image-name>/group
```

### Troubleshooting

#### Inspecting Failed Tests

Use `--pause` to inspect containers before cleanup:

```bash
ci/run_tests_container.sh --pause <image-name>
```

#### Viewing Test Output

By default, only failing tests show output. Use `--verbose` to see passing test output:

```bash
ci/run_tests_container.sh --verbose <image-name>
```

This also enables bash trace mode (`set -x`), showing each command as it executes.

## Writing Tests

### Basic Tests

Create `images/<name>/tests-container.yml`:

```yaml
---
version-check:
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" your-service --version

basic-functionality:
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" your-service --help
```

### External Test Scripts

For complex tests, use a separate shell script:

```yaml
---
complex-test:
  command: ./test-complex-scenario.sh
```

Create `images/<name>/test-complex-scenario.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Load TEST_IMAGES array for cross-variant testing
# shellcheck disable=SC1090
source "${TEST_IMAGES_PATH:?}"

# Run test
"${TEST_ENGINE:?}" run --rm "${TEST_IMAGE:?}" your-service test
```

### Variant-Specific Tests

Limit tests to specific variants:

```yaml
build-tools-test:
  variants: [builder]
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" make --version
```

### Cross-Variant Tests

Test interactions between variants:

```yaml
cross-variant-test:
  variants: [group]
  command: |
    builder="${TEST_IMAGES[nginx/builder]:?}"
    default="${TEST_IMAGES[nginx/default]:?}"

    "${TEST_ENGINE}" run --rm "${builder}" nginx -version
    "${TEST_ENGINE}" run --rm "${default}" nginx -version
```

### Known Issues

Mark tests with known failures:

```yaml
test-with-known-issue:
  command: |
    result=$("${TEST_ENGINE}" run --rm "${TEST_IMAGE}" some-command)
    [[ "$result" == "expected" ]] || TEST_FAIL "Custom error message"
  known_issues:
    - description: "Known configuration issue"
      issue: "https://issues.redhat.com/browse/PROJ-1234"
      pattern: "Custom error message"
      fails: "sometimes"
```

See the [Test Configuration Reference](test-configuration-reference.md) for complete
configuration options.

## Working with CI Tests

### Viewing CI Test Results

1. Open the merge request in GitLab
2. Navigate to the Jobs page for the pipeline
3. Identify the Testing Farm job (e.g., `containers-main-testing-farm-x86-64`)
4. Click on the job name to go to the Konflux PipelineRun page
5. If `wait-for-results` is already finished, select it in the pipeline details, and then switch to
   the Testing Farm job via the `ARTIFACTS_URL` link in the right side pane; otherwise, select the
   `scheduler` job, switch to the Testing Farm API details via the `tf-request` link in the right
   side pane, and then follow the `run.artifacts` link in the JSON data

### Rerunning CI Tests

Retrigger a specific pipeline using slash commands in merge request comments:

```text
/retest gitlab-ci--default--main-on-pull-request
```

For automated retriggers of only failed checks, see [Retrying Konflux
Checks](../operating/retrying-konflux-checks.md).

## Next Steps

- [Test Configuration Reference](test-configuration-reference.md) - Complete test configuration
  reference
- [Adding Images](adding-images.md) - How to add new images with tests
