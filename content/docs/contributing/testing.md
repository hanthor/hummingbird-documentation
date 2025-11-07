---
title: Integration Testing
description: >-
  Comprehensive guide for running integration tests with Docker and Podman support.
weight: 30
---

## Overview

The project includes container-based integration tests that validate image
functionality. Tests support both Docker and Podman engines.

## Prerequisites

1. **Container Engine**: Either [Podman](https://podman.io/) or
   [Docker](https://www.docker.com/)
2. **Python Dependencies**: Standard `yaml` package (`pip install PyYAML` or
   `dnf install python3-pyyaml`)

## Local Setup

### Using Podman (Recommended)

No additional setup required. Tests work directly with Podman.

### Using Docker for Testing

The test scripts support three Docker configurations, automatically detecting
which one is available:

#### 1. Automatically Managed Docker-in-Docker (Recommended)

Use the `--setup` flag to automatically set up an isolated Docker-in-Docker
environment in a `hummingbird-docker-dind` Podman container:

```bash
ci/run_tests_container.sh --engine docker --setup <group_name>
```

The `--setup` flag will:

- Start a `hummingbird-docker-dind` container with `mirror.gcr.io/docker:dind`
- Configure environment variables (`DOCKER_HOST`, `DOCKER_CERT_PATH`, etc.)
- Wait for the Docker daemon to be ready
- Reuse the existing container on subsequent runs (idempotent)

**Prerequisites:**

- Docker CLI must be installed (`dnf install docker-cli` or downloaded from
  [docker.com][docker-install])
- Podman must be available (to run the dind container)

#### 2. System-Level Docker Daemon

If you have Docker installed and running on your system, no additional setup is
needed:

```bash
ci/run_tests_container.sh --engine docker <group_name>
```

The test script will automatically connect to the system Docker daemon.

#### 3. Manually Managed Docker Installation

For full control, provide the following environment variables to configure how
to connect to the Docker daemon:

```bash
mkdir -p ~/.cache/docker-dind/{certs,tmp}
podman run -d --privileged --name hummingbird-docker-dind \
  -p 2376:2376 \
  -v ~/.cache/docker-dind/certs:/certs:z \
  -v ${PWD}:${PWD}:ro,z \
  mirror.gcr.io/docker:dind
export DOCKER_HOST=tcp://localhost:2376
export DOCKER_CERT_PATH=~/.cache/docker-dind/certs/client
export DOCKER_TLS_VERIFY=1
```

The test script will automatically detect and use these environment variables.
Export them in each shell session, add them to your shell profile (`~/.bashrc`),
or use [direnv][direnv] with an `.envrc` file.

#### Building Images for Docker

When building and loading images into Docker, the build script also supports the
`--setup` flag:

```bash
# With automatic docker-in-docker setup
ci/build_images.sh --engine docker --setup <group_name>

# Or use existing Docker daemon
ci/build_images.sh --engine docker <group_name>
```

The same smart fallback logic applies: the script will automatically try system
Docker first, then existing `hummingbird-docker-dind`, before failing.

[docker-install]: https://docs.docker.com/engine/install/
[direnv]: https://direnv.net/

## Running Tests

The project includes containerized integration tests that validate image
functionality. Run `ci/run_tests_container.sh --help` for basic usage
information, and see the containers repository documentation for the details.

## Test Configuration

### Test Definition Format

Each image can have container tests defined in
`images/<name>/tests-container.yml`:

```yaml
---
script:
  command: ./test.sh

inline:
  command: |
    image=${TEST_IMAGE?}
    "${TEST_ENGINE?}" run --rm "${image}" --version
```

### TEST Environment Variables

| Variable           | Description                                           |
|--------------------|-------------------------------------------------------|
| `TEST_IMAGE`       | The container image being tested                      |
| `TEST_IMAGES`      | Associative array with all `group/variant` image URLs |
| `TEST_IMAGES_PATH` | Path to file containing serialized TEST_IMAGES array  |
| `TEST_ENGINE`      | Container engine to use (`podman` or `docker`)        |
| `TEST_USER_ID`     | Current user ID (for permission handling)             |
| `TEST_VERBOSE`     | Show output for passing tests (`true` or `false`)     |
| `TEST_VARIANT`     | The variant being tested (`default`, `builder`, etc.) |

### Variant-Aware Testing

The testing system automatically includes variant-specific default tests:

- **Global tests** from `ci/{variant}-tests/tests-container.yml`
- **Image-specific tests** from `images/<name>/tests-container.yml`

### Variant Selection in Tests

Tests can specify which variants they apply to using the `variants` field:

```yaml
# Test that only runs for builder variants
build-tools-test:
  variants: [builder]
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" make --version

# Test that runs for multiple specific variants
multi-variant-test:
  variants: [default, builder]
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" echo "Hello"

# Test that runs for all variants (no variants field)
universal-test:
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" echo "Always runs"
```

### Group Test Mode

When running tests for all variants (without specifying a specific variant), the
system supports a special "group" test mode for tests that need to work across
multiple variants simultaneously:

```yaml
# Test that runs only in group mode
cross-variant-compatibility-test:
  variants: [group]
  command: |
    # Access specific group/variant combinations
    builder_image=${TEST_IMAGES[nginx/builder]:?}
    default_image=${TEST_IMAGES[nginx/default]:?}

    echo "Builder variant: ${builder_image}"
    echo "Default variant: ${default_image}"

    # Test that both variants have compatible APIs
    "${TEST_ENGINE}" run --rm "${builder_image}" nginx -version
    "${TEST_ENGINE}" run --rm "${default_image}" nginx -version
```

### Using TEST_IMAGES in External Test Scripts

External shell scripts that need to reference other image variants must source the
TEST_IMAGES array file at the beginning:

```bash
#!/bin/bash
set -euo pipefail

# Load TEST_IMAGES array
# shellcheck disable=SC1090
source "${TEST_IMAGES_PATH:?}"

# Now TEST_IMAGES is available - always use :? for proper error checking
"${TEST_ENGINE:?}" run --rm "${TEST_IMAGES[curl/default]:?}" ...
"${TEST_ENGINE:?}" run --rm "${TEST_IMAGES[httpd/default]:?}" ...
```

**Note:** Inline test commands in YAML files automatically have access to TEST_IMAGES
and do not need this sourcing pattern.

### Test Helper Functions

The test runner provides helper functions available in test commands:

#### `TEST_FAIL(message)`

Immediately fails the test with a custom error message sent to stderr:

```yaml
test-name:
  command: |
    result=$("${TEST_ENGINE}" run --rm "${TEST_IMAGE}" some-command)
    [[ "$result" == "expected" ]] || TEST_FAIL "Expected 'expected', got '$result'"
```

## Known Issues Handling

Tests can specify known log patterns that should not cause the test to report
an error (for which support is still unimplemented) or failure. This system
helps distinguish between "expected" failures (tracked issues) and
"unexpected" failures (new regressions), and can detect when expected
failures stop occurring.

### Known Issues Configuration

Add `known_issues` to any test in `images/<name>/tests-container.yml`, to
specify patterns that match expected failures:

```yaml
test-name:
  command: |
    # your test command here
    result=$("${TEST_ENGINE}" run --rm "${TEST_IMAGE}" some-command)
    [[ "$result" == "expected" ]] || TEST_FAIL "Custom error message"
  known_issues:
    - description: "Known configuration issue"
      issue: "https://issues.redhat.com/browse/PROJ-1234"
      pattern: "Custom error message"
      fails: "sometimes"  # optional, defaults to "always"
```

#### Fields

- **description**: Human-readable explanation of the issue *(required)*
- **issue**: Full URL to the issue tracking this problem *(required)*
- **pattern**: Regular expression(s) to match against test output *(required)*
- **fails**: Frequency of failure *(optional, defaults to "always")*

#### Pattern Support (pattern)

The `pattern` field supports both single patterns and arrays of patterns:

```yaml
known_issues:
  # Single pattern
  - description: "Simple failure case"
    issue: "https://issues.redhat.com/browse/PROJ-1"
    pattern: "Connection failed"

  # Multiple patterns (any match triggers)
  - description: "Network connectivity issues"
    issue: "https://issues.redhat.com/browse/PROJ-2"
    pattern:
      - "Connection timeout"
      - "Network unreachable"
      - "curl: \\(28\\)"
    fails: "sometimes"
```

#### Failure Frequency (fails)

- **always**: Known failures that consistently fail every time *(default)*
- **sometimes**: Intermittent failures that may pass on retry (flaky tests)

#### Unexpected Pass Detection

The system automatically detects when tests with known issues labeled as
`fails: "always"` suddenly start passing. This will not prevent missing known
issues being masked by other (still occurring) known issues.

#### Automatic Retries for Transient Infrastructure Failures

The test runner automatically retries tests that fail with certain transient
infrastructure errors. This helps avoid false test failures caused by temporary
issues with external services like container registries or network problems.

**Retry Behavior**:

- Failed tests are checked against a list of retriable error patterns
- If a match is found, the test is automatically retried
- If the test still fails after all attempts, it's reported as a normal failure
