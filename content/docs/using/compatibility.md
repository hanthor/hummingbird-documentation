---
title: Compatibility
description: >-
  Migration guide and compatibility notes for switching from other container images.
weight: 40
---

Hummingbird images are designed for compatibility with popular images from Docker Hub, Red Hat UBI,
and other registries, enabling straightforward migration of existing workloads.

**Key Difference**: Hummingbird images default to a non-root user (UID 65532) where technically
possible, while most traditional images run as root. This may require adjusting file permissions on
mounted volumes:

```bash
# Ensure correct ownership for mounted data
chown -R 65532:65532 /path/to/data
```

For detailed comparisons (environment variables, ports, sizes, default users), see the compatibility
report in the containers repository, which documents differences between each Hummingbird image and
its traditional counterpart.
