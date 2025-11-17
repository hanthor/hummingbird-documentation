---
title: Understanding Image Variants
description: >-
  Learn about different image variants, tagging strategies, and multi-stage build patterns.
weight: 20
aliases: [/l/image-variants]
---

Hummingbird provides different variants and base images to support various use cases while
maintaining security by default.

## Application Image Variants

Each application image (Python, Go, PostgreSQL, etc.) is available in two variants:

**Default Variant** (`:latest`)

- Distroless: no package manager, no shell
- Minimal attack surface
- Recommended for production
- Example: `quay.io/hummingbird/python:latest`

**Builder Variant** (`:latest-builder`)

- Includes `dnf` package manager and `bash`
- For installing additional dependencies
- Intended for multi-stage builds and development
- Example: `quay.io/hummingbird/python:latest-builder`

Some images provide more variants such as [PHP's FPM variant](https://quay.io/repository/hummingbird/php).

## Base Runtime Images

For multi-stage builds where you compile code in a builder variant, you can use default variants as
the base image.  For some toolchains, we recommend using the `core-runtime` base image for your
final stage:

- **`core-runtime`**: Minimal runtime environment with essential libraries (glibc, etc.). Use for
  compiled binaries from languages like C, Go, and Rust.

## Tagging Strategy

Images follow a version-based tagging scheme for stability:

- `:latest` - Most recent version (may change)
- `:<version>` - Specific version (e.g., `:3.11`, `:16`)
- `:<version>-builder` - Builder variant of specific version

**Recommendation**: For best practices on deciding which tags or even digests to use, refer to the
following article: [How to name, version, and reference container
images](https://developers.redhat.com/articles/2025/01/28/how-name-version-and-reference-container-images)

Use versioned tags in production for reproducible builds. The `:latest` tag is convenient for
development but may introduce unexpected changes.

Check [Quay.io](https://quay.io/organization/hummingbird) for available version tags for each image.

## Multi-Stage Build Pattern

The recommended pattern for compiled languages:

```Dockerfile
# Build stage: use builder variant to install dependencies and compile
FROM quay.io/hummingbird/go:latest-builder AS builder
RUN dnf install -y <build dependencies>
COPY . /src
WORKDIR /src
RUN go build -o /app .

# Runtime stage: use minimal base image for the compiled binary
FROM quay.io/hummingbird/core-runtime:latest
COPY --from=builder /app /app
ENTRYPOINT ["/app"]
```

This approach gives you build-time flexibility while maintaining a minimal production image.
