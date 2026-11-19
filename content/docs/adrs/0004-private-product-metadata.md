---
title: "ADR-0004: Move private_product into package metadata"
weight: 40
aliases: [/l/adr-0004, /l/design-HUM-11758]
---

- **Status:** Accepted
- **Authors:** Prarit Bhargava
- **Jira:** [HUM-11758][jira]
- **Date:** 2026-11-05
- **Accepted:** 2026-11-18
- **Last updated:** 2026-11-19

This record relocates the design approved in [infrastructure!1979][original-design].
The decision is unchanged.

## Summary

This ADR moves the per-package `private_product` setting out of
`ci/package-overrides.yaml` in the `rpms` repository and into the package
metadata JSON (`metadata/<package>.json`). It also requires that every read,
write, and validation of `private_product` is implemented in the core library,
`hum.meta`, and that the CI scripts that use the value go through that library
instead of parsing YAML or JSON themselves.

The [RPM metadata and versioning specification][metadata-spec] defines the
authoritative metadata contract. This ADR records the decision and rationale
for extending it.

## Motivation

`private_product` routes a package to a private, per-product Pulp repository
(for example `nodejs20`) instead of the public one. A private product groups
packages for publication to access-restricted repositories. Today the setting
is stored in `ci/package-overrides.yaml`, which is a build-configuration file,
not package metadata. This causes the following problems:

- **Implicit classification.** Because the setting is not part of the package
  metadata, other tooling tends to infer private or long-term-support (LTS)
  status from the package name, for example a `-lts` suffix. A name is not a
  reliable signal: an upstream project can legitimately have a name that ends
  in `-lts` without being an LTS package. Routing and classification must be
  driven by explicit data, never by naming conventions.
- **Split source of truth.** Everything else about a package (origin, version,
  modification status, upstream tracking) lives in `metadata/<package>.json`
  and is handled by `hum.meta`. `private_product` is the exception, so a
  reader has to consult two files to understand one package.
- **Duplicated file handling.** `ci/generate_resources.py`,
  `ci/check_nevr_conflicts.py`, and `ci/dist_git.py` each read or edit
  `package-overrides.yaml` directly. `dist_git.add_private_product()` edits the
  file line by line to preserve formatting. This is the kind of direct file
  manipulation that `hum.meta` exists to replace, and it is not covered by the
  library's validation.

## Depends on

- [ADR-0003: RPM metadata and versioning][adr-0003] adopts the metadata
  specification that this ADR extends.
- [HUM-6232][hum-6232] ported the metadata consumers onto `hum.meta`.

## Impacts

### User facing

None for external users. Packages continue to be built and published to the
same repositories. Maintainers set `private_product` in the package's metadata
JSON instead of `package-overrides.yaml`.

### Repositories

- [x] documentation/
- [ ] gorget/
- [x] rpms/
- [ ] containers/
- [x] infrastructure/
- [ ] skills/
- [ ] tools/ (CI, Website)

`rpms/` holds the metadata, the library, and all affected scripts.
`documentation/` holds this ADR and the metadata specification.
`infrastructure/` removes the original design document in favor of this ADR.

## Decision

### 1. Metadata field

Add an optional `private_product` field to `metadata/<package>.json`:

- Type: string. When absent, the package is public.
- The value is the product name and must match the `private_product` of an
  entry in `ci/konflux_rpa_config.yml`.
- The field is valid in every metadata state; it is orthogonal to the
  clean, modified, and independent states.
- The `private_product` key in `ci/konflux_rpa_config.yml` is a property of
  the RPA entry, not of a package. It is unchanged by this ADR.

### 2. Core library changes (`hum.meta`)

All handling of the field is implemented in `hum.meta`. No script may read or
write `private_product` by parsing a metadata or overrides file directly.

- **`hum.meta.model`**: add `private_product: str | None` to
  `PackageMetadata` and the concrete subclasses, with a validated setter and
  JSON round-tripping.
- **`hum.meta.validation`**: validate the value (non-empty string, allowed
  character set). Check that it matches an RPA entry in
  `ci/konflux_rpa_config.yml`; this check moves out of
  `generate_resources.py`.
- **`hum.meta.repository`**: provide the read and write paths. Setting the field
  is a `load`, set, `save` operation on `MetadataRepository`, which replaces
  the line-based YAML edit.
- **Queries**: provide library helpers to enumerate packages by product
  (`{package: private_product}` and the inverse) so consumers do not scan
  files.
- **Tests** in `hum/meta/tests/` cover the field, its validation, and the
  repository round trip.

### 3. Consumers

Each consumer switches to the library:

| File                         | Change                                                                                                                                                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ci/generate_resources.py`   | Use the library for per-package product lookup and the RPA cross-check. Public RPAs still exclude packages that have a product.                                           |
| `ci/check_nevr_conflicts.py` | Replace `load_private_products()` with a library query. Behavior is unchanged.                                                                                            |
| `ci/dist_git.py`             | `add_private_product()` sets the field through `MetadataRepository` instead of editing `package-overrides.yaml`. It still adds the RPA entry in `konflux_rpa_config.yml`. |

The `private_product` documentation block in `ci/package-overrides.yaml` is
removed once no entries remain.

### 4. Migration

Existing entries (`nodejs20` and the `example` entry) are moved into the
matching `metadata/<package>.json` files in the same MR that ports the
consumers, so the data and the code change together. This follows the pattern
used for HUM-6232. A one-time script is acceptable, but it is not kept in the
repository afterwards. During the migration, no package may have the field in
both places.

## Risks and open questions

- **Schema change process.** Metadata changes require an ADR and a corresponding
  specification update. Review and approve this ADR with the specification
  update before merging any implementation MRs.
- **Two-file consistency.** A package's product and the RPA entry live in
  different files. The library validation in section 2 is the guard against
  drift. The open question is whether the RPA entry should also move into
  metadata in a later ADR.
- **Allowed characters.** The allowed character set for product names still
  needs to be defined.
- **Other readers of the overrides file.** Scripts outside `rpms/ci` and
  documentation may refer to `private_product` in `package-overrides.yaml`.
  The implementation MR must search for these before the key is removed.

## Implementation notes

- Implementation is tracked in [HUM-13038][hum-13038].
- Land the library change (`hum.meta`, with tests) first, then the consumer
  and migration MR, then the operating documentation updates.
- Documentation to update in `rpms/`: `documentation/operating/private-rpm-repositories.md`,
  `documentation/operating/package-metadata-fields.md`, and
  `documentation/background/rpm-pipeline.md`.
- Update the tests in `test/test_generate_resources.py`,
  `test/test_check_nevr_conflicts.py`, and `test/test_dist_git.py` to build
  their fixtures from metadata JSON instead of `package-overrides.yaml`.
- When the implementation is complete, a follow-up MR changes this ADR's status
  to Implemented.

[jira]: https://redhat.atlassian.net/browse/HUM-11758
[original-design]: https://gitlab.com/redhat/hummingbird/infrastructure/-/merge_requests/1979
[hum-6232]: https://redhat.atlassian.net/browse/HUM-6232
[hum-13038]: https://redhat.atlassian.net/browse/HUM-13038
[adr-0003]: 0003-metadata-and-versioning.md
[metadata-spec]: ../specs/rpm-metadata-and-versioning.md
