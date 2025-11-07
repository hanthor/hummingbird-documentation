---
title: Security Features
description: >-
  Security hardening measures, image verification, and vulnerability scanning capabilities.
weight: 30
---

The project applies a number of measures to harden the Hummingbird containers:

- **Minimal Software Footprint**: Images include only essential software packages required for the workload, significantly reducing the attack surface and the number of CVEs per image.
- **Rapid Update Deployment**: Software package updates are shipped as quickly as possible, ensuring that fixes are consumed early.
- **Non-Root User Default**: Containers default to a non-root user where technically possible, increasing security by reducing privileges within the container.
- **Hermetic Build Environment**: All containers are built in a hermetic environment without network access. This prevents unintended package drift and gives the Hummingbird project full control over the software versions used.
- **Distroless Security**: The distroless nature of Hummingbird containers, shipping only what is strictly necessary for the given workload, reduces the attack surface and further improves security by making certain types of attacks impossible.

## Image Verification

**Development Status**: Hummingbird images are currently signed by our Tekton pipeline for development and testing purposes. Official production images will be signed with Red Hat keys and published through Red Hat's official pipeline in the future.

To verify an image was built by the Hummingbird Tekton pipeline:

- Save the public key to a file (e.g., `key.pub`):

```raw
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEtYRltxRJvXLMpXT+pIIu86CLhDP7
Q6VznCXqlzV3AO4AK/ge/HYtv6wMPfe4NHP3VQkCWoUokegC926FB+MTyA==
-----END PUBLIC KEY-----
```

- Verify the image signature:

```bash
cosign verify --key key.pub --insecure-ignore-tlog quay.io/hummingbird/<image>:<tag>
```

## Vulnerability Scanning

For security vulnerability scanning, Hummingbird uses [Syft](https://github.com/anchore/syft) for SBOM generation and [Grype](https://github.com/anchore/grype) for vulnerability detection.

However, Syft's output needs to be post-processed for accurate vulnerability matching with Fedora packages. For the time being (see Roadmap below), our [`ci/syft-hummingbird.sh`](https://gitlab.com/redhat/hummingbird/containers/blob/main/ci/syft-hummingbird.sh) calls `syft` and enhances the output with CPE dictionary lookups for better Grype matching.

To scan a Hummingbird image for vulnerabilities:

```bash
ci/syft-hummingbird.sh quay.io/hummingbird/<image>:<tag> | grype
```

This will produce results like in the compatibility report, or the per-image reports.

Known invalid or outdated CVEs are filtered out using the global ignore list in [`images/vulnerabilities-ignore.yml`](https://gitlab.com/redhat/hummingbird/containers/blob/main/images/vulnerabilities-ignore.yml).
