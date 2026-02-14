---
title: Deleting RPMs from Hummingbird Repos
description: How to delete RPM packages from Hummingbird repositories
weight: 40  # Keep pages sorted alphabetically by title; use increments of 10
---

## Overview

* This document should be used to remove RPMs from the Hummingbird repositories

## Setup

* make sure you have followed the local development setup instructions in the [infrastructure repository](https://gitlab.com/redhat/hummingbird/infrastructure)
* install pulp cli via dnf install pulp-cli
* setup the local pulp environment via:

```bash
cki_secret PULP_PUBLIC_RHEL_PRIMITIVES_CONFIG_FILE  > ~/.config/pulp/cli.toml
# or
vault kv get -mount=apps -field cli.toml hummingbird/PULP_PUBLIC_RHEL_PRIMITIVES_CONFIG_FILE > ~/.config/pulp/cli.toml
```

## Steps

* Note the names of the rpms to delete. In this example, we'll use `systemd-stub`
* Obtain the relevant metadata required to delete.
  * You need to execute this command once for each architecture.

```bash
pulp --domain public-hummingbird rpm content -t package list --name systemd-stub | jq -r '.[] | "\(.pulp_href)"'
```

or for prettier content,

```bash
pulp --domain public-hummingbird rpm content -t package list --name systemd-stub | jq -r '.[] | "\(.name) \(.version)-\(.release)  \(.arch)  \(.pulp_created)  \(.pulp_href)"'
```

Example output from basic command:

```text
/api/pulp/public-hummingbird/api/v3/content/rpm/packages/019b0e50-b89e-749b-a82b-405e00cdd1ed/
/api/pulp/public-hummingbird/api/v3/content/rpm/packages/019b0ded-4234-72b6-82e2-36803fc57a3b/
```

* Using the `hrefs`, construct your delete commands:

```bash
pulp --domain public-hummingbird rpm repository content remove --repository aarch64 --package-href /api/pulp/public-hummingbird/api/v3/content/rpm/packages/019b0e50-b89e-749b-a82b-405e00cdd1ed/
pulp --domain public-hummingbird rpm repository content remove --repository aarch64 --package-href /api/pulp/public-hummingbird/api/v3/content/rpm/packages/019b0ded-4234-72b6-82e2-36803fc57a3b/
```

* Repeat for `x64_64` and `source` repositories
* Verify deletion by navigating to <https://console.redhat.com/api/pulp-content/public-hummingbird/>
* Deletion is a serial operation that can be impacted by other automated jobs updating the repositories.

## Related Operations

* [Setting Up Pulp Repositories](setting-up-pulp-repositories.md)
