# Project Hummingbird Documentation

This repository contains the Hugo-based documentation site for Project Hummingbird.

## Local Development

### Prerequisites

- `podman`
- `make`

### Basic Usage

Start the development server:

```bash
make serve
```

The site will be available at the [local development server][local-server].

Check documentation for linting issues:

```bash
make check
```

### Advanced: Local Container Repository

To develop with local changes to the containers repository:

```bash
CONTAINERS_REPO_PATH=/path/to/containers make serve
```

This uses your local clone of the [containers repository][containers-repo]
instead of fetching from GitLab.

[local-server]: http://localhost:1313/
[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
