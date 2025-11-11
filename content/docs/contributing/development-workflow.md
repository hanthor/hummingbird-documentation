---
title: Development Workflow
description: Detailed development environment setup and contribution workflow
weight: 10
aliases: [/l/development-workflow]
---

## Prerequisites

Ensure the required tools are installed:

- **Container tools**: [Podman](https://podman.io/) or [Docker](https://www.docker.com/)
- **Build tools**: `buildah`, `make`, `git`
- **Python**: Python 3 with `PyYAML` package

Install on Fedora/RHEL:

```bash
sudo dnf install podman buildah make git python3-pyyaml
```

## Repository Setup

### Fork and Clone

1. Fork the [containers repository](https://gitlab.com/redhat/hummingbird/containers/-/forks/new)
   on GitLab
2. Clone your fork with submodules:

```bash
git clone --recurse-submodules https://gitlab.com/<your-username>/containers.git
cd containers
```

1. Add the upstream remote:

```bash
git remote add upstream https://gitlab.com/redhat/hummingbird/containers.git
```

## Development Workflow

### 1. Create a Branch

Create a descriptive branch starting from upstream main:

```bash
git fetch upstream
git checkout -b feature-add-redis-image upstream/main
```

### 2. Make Changes

Edit the relevant files in `images/<image-name>/`:

- `properties.yml` - Image configuration (packages, variants, tags)
- `Containerfile.j2` - Container build template
- `tests-container.yml` - Integration tests
- `README.md.j2` - Image documentation template

### 3. Generate Files

Regenerate derived files:

```bash
# Generate GitOps configurations and Containerfiles
make generate ARGS="<image-name>"

# Or generate just Containerfiles
make generate-containerfiles ARGS="<image-name>"
```

### 4. Build Locally

Build the image to verify changes:

```bash
ci/build_images.sh <image-name>

# Build specific variant
ci/build_images.sh <image-name>/builder

# Build with verbose output
ci/build_images.sh --verbose <image-name>
```

### 5. Test Locally

Run the integration tests:

```bash
ci/run_tests_container.sh <image-name>

# Test specific variant
ci/run_tests_container.sh <image-name>/default

# Test with verbose output
ci/run_tests_container.sh --verbose <image-name>
```

**Testing with Docker:**

By default, tests use Podman. To test with Docker:

```bash
# Automatic Docker-in-Docker setup
ci/run_tests_container.sh --engine docker --setup <image-name>
```

The `--setup` flag starts a Docker-in-Docker container, configures environment variables, and waits
for the Docker daemon to be ready.

**Testing base images:**

When modifying base images (like `core-runtime`), test dependent images:

```bash
# Build and test base image and all images that depend on it
ci/build_images.sh --include-reverse-deps core-runtime
ci/run_tests_container.sh --include-reverse-deps core-runtime
```

**Troubleshooting test failures:**

If tests fail, use `--pause` flag to inspect containers before cleanup:

```bash
ci/run_tests_container.sh --pause <image-name>
```

### 6. Run Linters

Ensure code quality:

```bash
make check
```

### 7. Commit and Push

Commit changes with a descriptive message and push to the fork:

```bash
git add .
git commit -m "feat: add Redis container image

- Add Redis 7.x image with default and builder variants
- Include basic health check tests
- Add compatibility notes for official Redis image"

git push origin feature-add-redis-image
```

### 8. Open a Merge Request

Open a merge request on GitLab:

1. Go to the [containers repository](https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/new)
2. Select your fork and branch as the source, `main` as the target
3. Fill in the description with what changed, why, and what tests were added

### 9. CI Pipeline

The CI pipeline automatically:

- Builds images for multiple architectures
- Runs integration tests
- Checks for linting issues

**Note for external contributors**: If not a project member, the CI pipeline won't run automatically.
Ping one of the [project maintainers](https://gitlab.com/redhat/hummingbird/containers/-/project_members?max_role=static-40)
in the merge request to trigger the pipeline.

## Next Steps

- [Adding Images](adding-images.md) - Step-by-step guide for adding new images
- [Testing Guide](testing-images.md) - Comprehensive testing documentation
- [Image Pipeline](../background/image-pipeline.md) - How the complete pipeline works
