---
title: Setting Up Pulp Repositories
description: How to create and set up Pulp domain and repositories
weight: 50  # Keep pages sorted alphabetically by title; use increments of 10
---

## Overview

* This document and script should be used to initialize and setup a pulp domain and a set of repositories
* We choose the domain prefix of `public-` to ensure that the repositories are publicly available

## Setup

* make sure you have followed the local development setup instructions in the [infrastructure repository](https://gitlab.com/redhat/hummingbird/infrastructure)
* install pulp cli via dnf install pulp-cli
* setup the local pulp environment via:

```bash
cki_secret PULP_PUBLIC_RHEL_PRIMITIVES_CONFIG_FILE  > ~/.config/pulp/cli.toml
# or
vault kv get -mount=apps -field cli.toml hummingbird/PULP_PUBLIC_RHEL_PRIMITIVES_CONFIG_FILE > ~/.config/pulp/cli.toml
```

* Run the [creation script]

[creation script]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/pulp-setup/create-pulp-resources.sh

## Create

```bash
./create-pulp-resources.sh public-hummingbird "source,x86_64,s390x,ppc64le,aarch64"
```
