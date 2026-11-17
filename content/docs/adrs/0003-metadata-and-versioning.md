---
title: "ADR-0003: RPM metadata and versioning"
weight: 30
aliases: [/l/adr-0003]
---

- **Status:** Accepted
- **Date:** 2026-08-31
- **Accepted:** 2026-11-17
- **Author:** Brent Baude
- **Jira:** [HUM-6212][hum-6212]

## Context

Each RPM package has build inputs in `rpms/<package>/` and a machine-readable record in
`metadata/<package>.json`. Automation uses metadata to decide whether Fedora updates may
overwrite local build inputs, which upstream project to track, and how CVE analysis maps a
package to its upstream identity.

Package metadata needs consistent definitions for the relationship to Fedora, required fields,
and versioning behavior. In particular, storing a release base that can disagree with the spec's
current `Release:` value caused incorrect rebuild increments in HUM-5182.

This ADR originally contained the full metadata specification. Subsequent proposals to change
the metadata contract need a single current specification, rather than definitions spread across
the original ADR and later decisions.

## Decision

Adopt the [RPM metadata and versioning specification][metadata-spec] as the authoritative contract
for `metadata/<package>.json` and its relationship to RPM versioning. The specification was
extracted from this ADR without changing the metadata contract.

The adopted model records a package's relationship to Fedora through `modification_status` and
Fedora provenance. Metadata `version` matches the spec's resolved `Version:`. The spec's `Release:`
line is the sole authoritative release value for what ships. `fedora.release`, when present,
records only the Fedora base from which that value is built.

No metadata field records a release base for packages ahead of Fedora or packages without a
Fedora origin. Rebuilds increment the spec's current release directly in those cases, removing the
stored value that could disagree with the spec and cause the bug class behind HUM-5182.

### Specification changes

Changes to the metadata contract or its semantics require an ADR and a corresponding specification
update. The ADR records the proposal, rationale, and compatibility implications. The specification
defines the resulting contract and remains the source of truth.

Review the ADR and specification update together, using linked merge requests when necessary.
Mark the ADR accepted when the specification change is approved, and record the change in the
specification's change history with a reference to that ADR. Editorial corrections and example
clarifications that do not change the contract do not require an ADR.

## Consequences

- `metadata/*.json` across the rpms repository must be brought in line with the specification.
  That migration remains separate, tracked work. Accepted status records the decision, not
  completion of the migration.
- `dist_git.py`, `check_upstream_versions.py`, and CVE analysis tooling can implement the
  specification's [validation rules][validation-rules] directly.
- The spec's `Release:` line remains the sole authoritative value for what ships; no metadata
  field may be treated as a substitute for it, including `fedora.release`.
- Future contract changes update the standalone specification, without rewriting this ADR's
  original metadata decision or requiring readers to assemble the contract from multiple ADRs.
- RPM operating documentation explains workflows and links to the specification for definitions.
  It does not define a competing metadata contract.

## Specification sections

The following headings preserve links to sections originally embedded in this ADR.

### Package states

See [Package states][package-states] in the specification.

### Field reference

See [Field reference][field-reference] in the specification.

### Computing the built NVR

See [Computing the built NVR][built-nvr] in the specification.

### Validation rules

See [Validation rules][validation-rules] in the specification.

### Examples

See [Examples][examples] in the specification.

[hum-6212]: https://redhat.atlassian.net/browse/HUM-6212
[metadata-spec]: ../specs/rpm-metadata-and-versioning.md
[package-states]: ../specs/rpm-metadata-and-versioning.md#package-states
[field-reference]: ../specs/rpm-metadata-and-versioning.md#field-reference
[built-nvr]: ../specs/rpm-metadata-and-versioning.md#computing-the-built-nvr
[validation-rules]: ../specs/rpm-metadata-and-versioning.md#validation-rules
[examples]: ../specs/rpm-metadata-and-versioning.md#examples
