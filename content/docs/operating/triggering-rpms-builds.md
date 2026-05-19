---
title: Triggering RPM builds
description: How to trigger a RPM build in Konflux
weight: 30  # Keep pages sorted alphabetically by title; use increments of 10
---

## Prerequisites

- access to the Konflux cluster where the hummingbird-tenant lives

## Setup

- Login to https://console-openshift-console.apps.kflux-prd-rh03.nnv1.p1.openshiftapps.com/dashboards
- Locate your login name in top right hand corner and click on it
- Click on `Copy login command`
- Click `Display Token` and copy the `oc login` command
- Open a Terminal and paste in the login command

```bash
oc login --token=....
```

## Trigger a RPM build

- You can now trigger a push build for a component:

```bash
export pkg=setup
kubectl annotate components/${pkg}-main build.appstudio.openshift.io/request=trigger-pac-build
```

## Finding Missing RPMs

- In the event that CI has failed to produce a RPM release for a package, you can use [ci/verify_pulp_x86_64_rpms.sh] to help create a list along with helper command line examples.

```bash
bash ci/verify_pulp_x86_64_rpms.sh --strict
```

- Example output

```text
Remote repo: https://console.redhat.com/api/pulp-content/public-hummingbird/x86_64/
Looking for x86_64 RPMs for spec files under: /home/shebert/work/hummingbird/rpms/rpms
OK     acl
OK     attr
OK     bash
OK     brotli
MISSING bzip2
MISSING ca-certificates
MISSING chkconfig
MISSING coreutils
MISSING crypto-policies
OK     curl
OK     cyrus-sasl
OK     dnf5
OK     e2fsprogs
OK     elfutils
MISSING fedora-repos
MISSING file
MISSING findutils
OK     fmt
OK     fsverity-utils
OK     gdbm
OK     grep
OK     hostname
OK     libyaml
OK     lua
MISSING lz4
MISSING ncurses
MISSING nettle
MISSING nghttp2
MISSING npth
MISSING openldap
OK     openssl
OK     pcre2
OK     popt
MISSING publicsuffix-list
MISSING readline
MISSING rootfiles
OK     rpm
MISSING sdbus-cpp
MISSING sed
MISSING setup
MISSING shadow-utils
MISSING sqlite
OK     systemd-stub
OK     tpm2-tss
OK     util-linux
MISSING xz
MISSING zchunk
MISSING zlib-ng
MISSING zstd

Checked: 49  Found: 23  Missing: 26
Missing packages (x86_64): bzip2 ca-certificates chkconfig coreutils crypto-policies fedora-repos file findutils lz4 ncurses nettle nghttp2 npth openldap publicsuffix-list readline rootfiles sdbus-cpp sed setup shadow-utils sqlite xz zchunk zlib-ng zstd

You can try to trigger RPM builds for missing packages by running:
  kubectl annotate components/bzip2-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/ca-certificates-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/chkconfig-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/coreutils-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/crypto-policies-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/fedora-repos-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/file-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/findutils-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/lz4-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/ncurses-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/nettle-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/nghttp2-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/npth-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/openldap-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/publicsuffix-list-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/readline-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/rootfiles-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/sdbus-cpp-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/sed-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/setup-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/shadow-utils-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/sqlite-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/xz-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/zchunk-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/zlib-ng-main build.appstudio.openshift.io/request=trigger-pac-build
  kubectl annotate components/zstd-main build.appstudio.openshift.io/request=trigger-pac-build
```

[ci/verify_pulp_x86_64_rpms.sh]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/verify_pulp_x86_64_rpms.sh