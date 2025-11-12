---
title: Test Configuration Reference
description: Complete reference for test definition format and configuration options
weight: 45
---

Complete reference for configuring container image tests via `tests-container.yml`.

## Test Definition Format

Each image can have container tests defined in `images/<name>/tests-container.yml`:

```yaml
---
script:
  command: ./test.sh

inline:
  command: |
    image=${TEST_IMAGE?}
    "${TEST_ENGINE?}" run --rm "${image}" --version
```

## Environment Variables

The test runner provides these environment variables to test commands:

| Variable           | Description                                            |
|--------------------|--------------------------------------------------------|
| `TEST_IMAGE`       | The container image being tested                       |
| `TEST_IMAGES`      | Associative array with all `group/variant` image URLs  |
| `TEST_IMAGES_PATH` | Path to file containing serialized `TEST_IMAGES` array |
| `TEST_ENGINE`      | Container engine to use (`podman` or `docker`)         |
| `TEST_USER_ID`     | Current user ID (for permission handling)              |
| `TEST_VERBOSE`     | Show output for passing tests (`true` or `false`)      |
| `TEST_GROUP`       | The image group being tested (`nginx`, `python`, etc.) |
| `TEST_VARIANT`     | The variant being tested (`default`, `builder`, etc.)  |

## Variant-Aware Testing

The testing system automatically includes variant-specific default tests:

- **Global tests** from `ci/{variant}-tests/tests-container.yml`
- **Image-specific tests** from `images/<name>/tests-container.yml`

## Variant Selection

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

## Group Test Mode

When running tests for all variants (without specifying a specific variant), the system supports
a special "group" test mode for tests that need to work across multiple variants simultaneously:

```yaml
# Test that runs only in group mode
cross-variant-compatibility-test:
  variants: [group]
  command: |
    # Access specific group/variant combinations using TEST_GROUP
    builder_image=${TEST_IMAGES[${TEST_GROUP}/builder]:?}
    default_image=${TEST_IMAGES[${TEST_GROUP}/default]:?}

    echo "Builder variant: ${builder_image}"
    echo "Default variant: ${default_image}"

    # Test that both variants have compatible APIs
    "${TEST_ENGINE}" run --rm "${builder_image}" nginx -version
    "${TEST_ENGINE}" run --rm "${default_image}" nginx -version
```

## Using TEST_IMAGES in External Scripts

External shell scripts that need to reference other image variants must source the TEST_IMAGES
array file at the beginning:

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

**Note:** Inline test commands in YAML files automatically have access to TEST_IMAGES and do not
need this sourcing pattern.

## Using TEST_GROUP for Dynamic References

The `TEST_GROUP` variable contains the current image group name (e.g., `nginx`, `python`,
`aspnet-runtime-8-0`). Use it with `TEST_IMAGES` to dynamically reference the current image's
variants without hardcoding the group name:

```yaml
multi-stage-build:
  variants: [builder]
  command: |
    # Build in builder variant, run in default variant
    "${TEST_ENGINE}" build -t localhost/myapp -f - . <<EOF
    FROM ${TEST_IMAGES[${TEST_GROUP}/builder]:?}
    # ... build steps ...

    FROM ${TEST_IMAGES[${TEST_GROUP}/default]:?}
    COPY --from=0 /app /app
    EOF

    "${TEST_ENGINE}" run --rm localhost/myapp /app/myapp
```

## Test Helper Functions

The test runner provides helper functions available in test commands:

### TEST_FAIL(message)

Immediately fails the test with a custom error message sent to stderr:

```yaml
test-name:
  command: |
    result=$("${TEST_ENGINE}" run --rm "${TEST_IMAGE}" some-command)
    [[ "$result" == "expected" ]] || TEST_FAIL "Expected 'expected', got '$result'"
```

## Known Issues

Tests can specify known log patterns that should not cause the test to report an error (for which
support is still unimplemented) or failure. This helps distinguish between expected failures
(tracked issues) and unexpected failures (new regressions), and detects when expected failures
stop occurring.

Add `known_issues` to any test to specify patterns matching expected failures:

```yaml
test-name:
  command: |
    result=$("${TEST_ENGINE}" run --rm "${TEST_IMAGE}" some-command)
    [[ "$result" == "expected" ]] || TEST_FAIL "Custom error message"
  known_issues:
    - description: "Known configuration issue"
      issue: "https://issues.redhat.com/browse/PROJ-1234"
      pattern: "Custom error message"
      fails: "sometimes"  # optional, defaults to "always"
```

### Fields

- **description**: Human-readable explanation of the issue *(required)*
- **issue**: Full URL to the issue tracking this problem *(required)*
- **pattern**: Regular expression(s) to match against test output *(required)*
- **fails**: Frequency of failure *(optional, defaults to "always")*

### Pattern Support

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

### Failure Frequency

- **always**: Known failures that consistently fail every time *(default)*
- **sometimes**: Intermittent failures that may pass on retry (flaky tests)

### Unexpected Pass Detection

The system automatically detects when tests with known issues labeled as `fails: "always"`
suddenly start passing. This will not prevent missing known issues being masked by other (still
occurring) known issues.

## Automatic Retries

The test runner automatically retries tests that fail with certain transient infrastructure
errors. This helps avoid false test failures caused by temporary issues with external services
like container registries or network problems.

**Retry Behavior:**

- Failed tests are checked against a list of retriable error patterns
- If a match is found, the test is automatically retried
- If the test still fails after all attempts, it's reported as a normal failure

## Next Steps

- [Testing Guide](testing-images.md) - How to run and write tests
- [Adding Images](adding-images.md) - How to add new images with tests
