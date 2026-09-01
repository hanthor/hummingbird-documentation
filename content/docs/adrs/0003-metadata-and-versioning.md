---
title: "ADR-0003: Metadata and Versioning Specification"
weight: 30
aliases: [/l/adr-0003]
---

- **Status:** Proposed
- **Date:** 2026-08-31
- **Author:** Brent Baude
- **Jira:** [HUM-6212][hum-6212]

## Context

The metadata file at `metadata/<package>.json` and the package directory at `rpms/<package>/`
form a pair, one per package. The package directory holds the build input: the spec file,
patches, and the `sources` checksum manifest that `mock` consumes to produce RPMs. This
specification does not change anything about that directory.

The metadata file is the machine-readable record of a package's relationship to Fedora and
upstream. Automation reads it to decide what it may do: whether `dist_git.py update` may
overwrite the package directory, which upstream project `check_upstream_versions.py` tracks, and
how CVE analysis maps the package to its upstream identity.

The metadata file does not duplicate build inputs, and it does not record the release currently
shipped: the spec's `Release:` line is the sole authoritative value for what ships, and is what
NVR computation uses (see [Computing the built NVR](#computing-the-built-nvr)). For packages on
Fedora's version, `fedora.release` also appears in metadata — but only as the base value the
spec's `Release:` is built from, never as a substitute for it.

The two locations are updated independently; neither is derived from the other. They must stay
consistent by convention, not by construction — `modification_status` is correct only if it
accurately reflects whether the package directory actually diverges from Fedora's import.

This document normatively defines the target structure of `metadata/<package>.json` and how
`release` and versioning behave as a function of `modification_status`. It describes the target
metadata shape, not what is present on disk in `metadata/*.json` today. Bringing existing
metadata in line with this specification is separate, tracked work.

## Decision

### Package states

Every package occupies exactly one of three states, describing its relationship to Fedora at a
given moment. A state is not itself a metadata field — it is what `modification_status` means in
combination with which version the package currently ships. The rest of this specification refers
to these states by name, so they are defined here first.

A package's state follows from its `modification_status`, which is itself defined by the
package's relationship to a Fedora origin. `modification_status` is one of three values:

- **`clean`** — the package has a Fedora origin, and currently matches that Fedora import.
- **`modified`** — the package has a Fedora origin, but currently diverges from it — either
  through local changes while still on Fedora's version, or by having moved ahead to a newer
  upstream version.
- **`independent`** — the package has no Fedora origin at all.

For a `modified` package, the state further depends on whether it currently ships Fedora's exact
version or has moved ahead to a newer upstream version. The `fedora` object's shape — complete or
partial — records which of those is the case; it does not itself define the state.

The table below names all three states by the version they currently ship, not just by
`modification_status`, since `modified` alone is ambiguous between the two Fedora-origin cases:

| Version currently shipped           | `modification_status` |
|-------------------------------------|-----------------------|
| Fedora's version                    | `clean` or `modified` |
| An upstream version ahead of Fedora | `modified` only       |
| No Fedora origin (independent)      | `independent`         |

### Field reference

This is the complete field-by-field reference for `metadata/<package>.json` — every field
consumed by tooling in this repository, not only the fields that determine `modification_status`
or the Fedora relationship. Fields are listed in four groups, in order: package identity and state
(`version` through `modification_reason`), the Fedora-origin group (`fedora` and its sub-fields),
fields that configure upstream-version tracking, and fields unrelated to either Fedora or upstream
tracking (`cve_product`, `version_transform`, `fix_status`). The "Presence" column states the
condition under which a field appears in the JSON; fields are omitted entirely rather than set to
`null` or an empty value when their condition does not hold.

| Field | Type | Presence | Description |
| ----- | ---- | -------- | ----------- |
| `version` | string | Always | The version currently shipped. |
| `modification_status` | enum: `clean`, `modified`, `independent` | Always | Whether the package matches its Fedora import unmodified (`clean`), carries local changes (`modified`), or has no Fedora origin at all (`independent`). |
| `modification_reason` | string | Only in the `modified` state | Why the package carries local changes. Absent for `clean` and `independent` packages. |
| `fedora` | object | In the `clean` state or either sub-case of the `modified` state | Everything about the Fedora build this package tracks or last tracked. Absent entirely in the `independent` state. |
| `fedora.git_url` | string | Whenever `fedora` is present | The Fedora dist-git repository URL. |
| `fedora.branch` | string | Whenever `fedora` is present | The Fedora dist-git branch (e.g. `rawhide`). |
| `fedora.sha` | string | Whenever `fedora` is present | The exact Fedora commit imported or last synced. |
| `fedora.release` | string | Only in the on-Fedora-version state (`clean`, or `modified` while still on Fedora's version) | The release number of the Fedora build tracked, dist tag stripped. Absent once the package moves to an upstream version ahead of Fedora. |
| `upstream_repo` | string (git URL) | Always | The canonical upstream project repository. Falls back to the Fedora dist-git URL when no independent upstream repository exists. |
| `upstream_branch` | string | Optional — independent of state | Pins one package's upstream line when several packages share a single `upstream_repo` (e.g. an `nodejs2x`-style family). |
| `version_from_ref` | object: `{"type": "commit-date"}` | Optional — independent of state; requires `upstream_repo` | Configures `dist_git.py update`'s fixed-ref pin-refresh logic to compute a gorget source-pipeline's `--version` string automatically from a newly-pinned commit, instead of requiring manual resolution. `commit-date` is currently the only supported `type`. |
| `track_upstream` | string: `"latest"` or a version prefix (e.g. `"1.26"`) | Optional — independent of state | Enables `check_upstream_versions.py` tracking of this package; a version prefix constrains which upstream releases are accepted. |
| `release_monitoring_project_id` | integer or string | Optional — independent of state; only meaningful paired with `track_upstream` | The release-monitoring.org (Anitya) project ID or name `check_upstream_versions.py` queries. |
| `version_source` | string: currently only `"gitlab_tags"` | Optional — independent of state | Selects an alternate upstream-version source for `check_upstream_versions.py` instead of Anitya. |
| `tag_strip_prefix` | string, default `"v"` | Optional — independent of state | Used with `version_source: "gitlab_tags"` to strip a tag-name prefix before comparing versions. |
| `version_suffix_strip` | string | Optional — independent of state | A suffix `check_upstream_versions.py` strips from an Anitya-reported version before comparison and update (e.g. `"-RELEASE"`). |
| `upstream_version_transform` | string | Optional — independent of state | A named transform `check_upstream_versions.py` applies to normalize an Anitya-reported version into RPM version syntax (e.g. `openjdk_to_rpm`). A distinct field from `version_transform` below, with a different consumer — do not conflate the two. |
| `source_availability_check` | string | Optional — independent of state | A named checker (registered in `SOURCE_AVAILABILITY_CHECKERS`) that HEAD-probes a candidate source URL before `check_upstream_versions.py` accepts that version. |
| `cve_product` | string, or list of strings | Optional — independent of state | A CVE vendor/product override, independent of Fedora or upstream tracking. |
| `version_transform` | string | Optional — independent of state | A version-mapping rule consumed by CVE analysis tooling in the `tools` repository (e.g. `dotnet_sdk_to_runtime`). Not consumed by anything in this repository's own `ci/` scripts. |
| `fix_status` | integer | Optional — independent of state | Not consumed by any tooling in this repository today. Carried over from history and likely stale — not a field to use for new work. |

### Computing the built NVR

The built RPM is identified by its NVR: Name, Version, and Release. Name is the spec/package name
and is unaffected by any of this — only `Version:` and `Release:` vary with state.

Metadata `version` and the spec `Version:` line always match — metadata stores it separately not
because the two can diverge, but because reading `Version:` reliably from every spec (which may
build it from macros or indirection) isn't practical, so metadata is the field automation trusts
instead. `Release:` works the other way: the spec `Release:` line is the sole authoritative
value for what ships, in every state. `fedora.release`, when present, is only the base value
`Release:` is built from — never a substitute for it.

The table below shows, for each state, where the spec's `Version:` and `Release:` lines come
from. The prose beneath it gives the precise rebuild-increment rules that don't compress into a
table cell.

| Version currently shipped | Spec `Version:` | Spec `Release:` |
| -------------------------- | ---------------- | ----------------- |
| Fedora's version (`clean` or `modified`) | Matches metadata `version` | `fedora.release` plus `%{?dist}`, with an optional trailing `.N` for local rebuilds |
| An upstream version ahead of Fedora (`modified` only) | Matches metadata `version` | Starts at `0.1%{?dist}` the first time the package moves ahead of Fedora; local rebuilds increment the trailing `.N` directly from the spec's own current value |
| No Fedora origin (independent) | Matches metadata `version` | A one-time human-chosen base (typically `1` or `0.1`) plus `%{?dist}`; local rebuilds increment the trailing `.N` directly |

**On Fedora version (`clean` or `modified`):** `fedora.release` holds Fedora's confirmed release
number, dist tag stripped. The spec `Release:` is that value plus `%{?dist}`, with an optional
trailing `.N` if the package has been locally rebuilt without a source change since the last
import or sync. `dist_git.py rebuild` computes the next `.N` by comparing the spec's current
`Release:` against `fedora.release`: if they match exactly, this is the first local rebuild since
import or sync, and `.1` is appended; if the spec already carries a trailing `.N` ahead of
`fedora.release`, that trailing number is incremented.

**On upstream version (always `modified`):** No `fedora.release`, and no other metadata field
records a base value. The spec uses `Release: 0.1%{?dist}` the first time a package moves ahead
of Fedora. Every subsequent local rebuild increments the trailing dot-number directly from the
spec's own current `Release:` value (`0.1` → `0.2` → `0.3`, and so on) — never by re-deriving it
from a stored metadata value, because none exists. This is what makes the bug class behind
HUM-5182 structurally impossible: that bug occurred because a stored placeholder value could
disagree with the spec's actual current `Release:`; with nothing stored to disagree with, the
mis-increment cannot happen.

**Independent:** The same rule as the on-upstream-version case applies — no metadata field
records a base value, and the spec `Release:` is authoritative. Rebuilds increment its trailing
`.N` directly. The only difference is the very first value chosen when the package is added
(typically `1` or `0.1`) is a one-time human decision, not derived from anything.

### Validation rules

Every rule below is a single, unconditional statement: given the field values present, exactly
one outcome is correct. None of them carry a qualifier like "should," "generally," or "in most
cases," and none fold an exception into the wording — a rule that needs an exception is really two
rules, stated separately. The rationale for *why* each rule holds lives elsewhere in this document
(Package states, Field reference, Computing the built NVR); this section exists so a validator can
implement each line as a direct check with nothing left to interpret.

1. `version` is present.
2. `modification_status` is present.
3. `upstream_repo` is present.
4. `modification_status` is `clean`, `modified`, or `independent`.
5. `version_source`, when present, is `gitlab_tags`.
6. `source_availability_check`, when present, is a name registered in
   `SOURCE_AVAILABILITY_CHECKERS`.
7. The top-level field `release` does not appear.
8. If `modification_status` is `clean`, `fedora` is present.
9. If `modification_status` is `modified`, `fedora` is present.
10. If `modification_status` is `independent`, `fedora` is absent.
11. If `fedora` is present, it includes `git_url`, `branch`, and `sha`.
12. If `modification_status` is `clean`, `fedora.release` is present.
13. If `modification_status` is `modified`, `fedora.release` is present if and only if `version`
    equals the version Fedora ships at `fedora.sha`.
14. `fedora.release`, when present, does not include a dist-tag suffix (e.g. `.fc42`, `.el9`).
15. If `modification_status` is `modified`, `modification_reason` is present.
16. If `modification_status` is `clean` or `independent`, `modification_reason` is absent.
17. If `track_upstream` is present and `version_source` is absent, `release_monitoring_project_id`
    is present.
18. If `release_monitoring_project_id` is present, `track_upstream` is present.
19. If `version_source` is `gitlab_tags`, `release_monitoring_project_id` is absent.
20. If `tag_strip_prefix` is present, `version_source` is `gitlab_tags`.
21. The spec's `Version:` line, resolved through macro expansion, equals metadata `version`.
22. If `version_from_ref` is present, `upstream_repo` is present.
23. `version_from_ref.type`, when present, is `commit-date`.

### Examples

Metadata for a package on Fedora version, `clean`:

```json
{
  "version": "5.4.3.0",
  "modification_status": "clean",
  "fedora": {
    "release": "2",
    "git_url": "https://src.fedoraproject.org/rpms/dnf5.git",
    "branch": "rawhide",
    "sha": "f174d0fcedc78a34d74b800697862b93683ad5e0"
  },
  "upstream_repo": "https://github.com/rpm-software-management/dnf5"
}
```

Metadata for a package on Fedora version, `modified`:

```json
{
  "version": "5.3.15",
  "modification_status": "modified",
  "modification_reason": "Added gorget source-pipeline.yaml (HUM-5841; pattern from HUM-4622): a fresh fetch of Source0's bash-5.3.tar.gz no longer matches the recorded checksum -- upstream re-published the base tarball (translation file + build stamp only, GPG signature re-verified against the already-trusted key) -- so Fedora's cache no longer serves bytes matching the corrected checksum",
  "fedora": {
    "release": "2",
    "git_url": "https://src.fedoraproject.org/rpms/bash.git",
    "branch": "rawhide",
    "sha": "2768211b5135c7169f513965d79e9f89e0ca6124"
  },
  "upstream_repo": "https://git.savannah.gnu.org/git/bash.git"
}
```

Metadata for a package on an upstream version ahead of Fedora, `modified`:

```json
{
  "version": "0.9~rc4",
  "modification_status": "modified",
  "modification_reason": "update to 0.9rc4",
  "fedora": {
    "git_url": "https://src.fedoraproject.org/rpms/avahi.git",
    "branch": "rawhide",
    "sha": "195919c9f9a8dff0e996921afd8736df8f12715b"
  },
  "upstream_repo": "https://github.com/avahi/avahi"
}
```

Note the absence of `fedora.release` and of any top-level `release` field — this package is ahead
of whatever Fedora currently ships, so there is no confirmed Fedora release to record.

Metadata for an `independent` package:

```json
{
  "version": "1.3.3",
  "modification_status": "independent",
  "upstream_repo": "https://github.com/oras-project/oras",
  "track_upstream": "latest",
  "release_monitoring_project_id": 205787
}
```

No `fedora` object and no release-related field — the release currently shipped lives only in
that package's spec `Release:` line.

## Consequences

- `metadata/*.json` across the rpms repository must be brought in line with this specification;
  that migration is separate, tracked work and is not complete as of this ADR.
- `dist_git.py`, `check_upstream_versions.py`, and CVE analysis tooling can implement the
  [Validation rules](#validation-rules) directly, since each rule is a single unconditional
  check with no interpretation left to the implementer.
- The spec's `Release:` line remains the sole authoritative value for what ships; no metadata
  field may be treated as a substitute for it, including `fedora.release`.
- Removing a stored base value for the on-upstream-version and independent states (see
  [Computing the built NVR](#computing-the-built-nvr)) makes the bug class behind HUM-5182
  structurally impossible, since there is no longer a stored value that can disagree with the
  spec's actual current `Release:`.

[hum-6212]: https://redhat.atlassian.net/browse/HUM-6212
