---
title: Getting Started
description: >-
  Quick start guide for using Project Hummingbird container images with examples and basic concepts.
weight: 10
---

Project Hummingbird builds a collection of minimal, hardened, and secure container images with a significantly reduced attack surface. This strong focus on security combined with a highly automated update workflow aims to minimize CVE counts, targeting near-zero vulnerabilities. All images support amd64 and arm64 architectures.

Available images include languages (Python, Go, Node.js, Rust, PHP), databases (PostgreSQL, MariaDB), web servers (httpd, Caddy, nginx), tools (curl, git), and base runtime images. Browse the complete catalog at [Quay.io](https://quay.io/organization/hummingbird).

Note that the project is currently under development. All containers are tested and built with care, but are not yet recommended for production.

## Quick Start

Getting started with Hummingbird images is simple. All images are available from the [Quay.io registry](https://quay.io/organization/hummingbird) and can be used directly with Podman or Docker:

```bash
# Run a command directly with the curl image
podman run quay.io/hummingbird/curl -v https://example.com

# Start a PostgreSQL database
podman run -e POSTGRES_PASSWORD=mysecret quay.io/hummingbird/postgresql:latest
```

Example container build using the Hummingbird Python image:

```Dockerfile
FROM quay.io/hummingbird/python:latest
COPY myapp.py /app/
WORKDIR /app
CMD ["python3", "myapp.py"]
```

You can find the documentation for each image on [Quay](https://quay.io/organization/hummingbird).

For more information, see:
- [Understanding Image Variants](image-variants.md) - Learn about different image types and tagging
- [Security Features](security-features.md) - Understand Hummingbird's security approach
- [Compatibility](compatibility.md) - Migration guide and compatibility notes

## Distroless Containers

Hummingbird builds so-called distroless containers which is a fancy way of describing that the images do not ship with a package manager and most do not even provide a shell.

The distroless design usually makes the bundled application the container's entrypoint, offering a more user-friendly experience. For example, with the Hummingbird [curl image](https://quay.io/repository/hummingbird/curl?tab=info), you can directly specify arguments to curl, like `podman run quay.io/hummingbird/curl -v https://www.redhat.com/en`.

Providing purpose-built containers means tons of work for the Project Hummingbird team, but heavily reduces the work for users. As a user, you don't have to build your own container image and then be burdened with managing the vulnerabilities of your image. Instead, you can directly use a Hummingbird image with the bundled application you need and thereby avoid CVE hell.

## Roadmap

- **RPM builds**: We're currently building Project Hummingbird containers on [Fedora Rawhide](https://docs.fedoraproject.org/en-US/releases/rawhide/). Our future plan is to manage the build pipelines for Hummingbird's RPM packages. This will allow us to quickly consume updates of stable software through a fully automated process. It also gives us the flexibility to offer packages in multiple versions and optimize them for container use.
- **Security scanning**: Once we build our own RPM packages, we will add proper SBOM metadata, and also set up a Hummingbird CVE database. Then Syft/Grype should work directly without post-processing.
- **Official Red Hat signing**: Transition from development pipeline signatures to official Red Hat signing keys and publishing infrastructure for production-ready images.
- **Increasing image catalog**: We intend to significantly expand our catalog of images.
- **Reproducibility**: Local builds of our images are reproducible, but the images published on Quay cannot be reproduced yet.
- **Image size optimization**: Building our own RPM packages will provide complete control over the software stack, enabling further optimization of image sizes through container-specific package configurations and dependency management.
