---
title: "ADR-0002: AI-Assisted SDLC Workqueue"
weight: 20
aliases: [/l/adr-0002]
---

- **Status:** Proposed
- **Date:** 2026-08-24
- **Author:** Michael Hofmann
- **Jira:** [HUM-6342] (spike)

## Context

The [`containers`][containers-repo] and [`rpms`][rpms-repo] repositories
produce over 1,000 automated commits per week. The automation that drives
this throughput is spread across multiple independent mechanisms: GitLab
CI scheduled jobs running shell scripts, Renovate CronJobs in the
infrastructure repo, AWS Lambda functions for MR approval, and manual
developer workflows run from dev machines. Each mechanism creates and
manages MRs with its own lifecycle, credentials, and error handling.

There is no unified system that tracks an MR from creation through
approval to merge. The [Hummingbird Agent][hummingbird-agent-docs] already
runs AI-powered failure analysis and code review on every MR, but cannot
create or modify MRs. The security foundation for agent-authored MRs is
designed in [HUM-851] but not yet implemented.

This ADR documents the current state of MR automation across all
repositories and entrypoints as discovery for a spike to design a unified
workqueue-based system.

### Scope

This document inventories what exists today. It does not prescribe the
target architecture — that is the output of the spike. Design questions
and patterns are included to inform the spike investigation.

## Current State

### Repositories

**rpms** (`redhat/hummingbird/rpms`): RPM package definitions. Each
package lives in its own directory with a `.spec` file and
`metadata/<package>.json` for upstream repo URL, CVE product mapping, and
modification status. Fedora dist-git imports and upstream version bumps
are the primary automated flows.

**containers** (`redhat/hummingbird/containers`): Container image
definitions. Each image lives in `images/<name>/` with Containerfiles and
RPM lockfiles (`rpms.lock.yaml`). Lockfile refresh and Renovate
dependency updates are the primary automated flows.

**tools** (`redhat/hummingbird/tools`): Lambdas, CLI tools, and the
Hummingbird Agent framework. Contains `mr-auto-approver`,
`gitlab-event-forwarder`, `hummingbird-agent`, and the CVE analysis
pipeline.

**infrastructure** (`redhat/hummingbird/infrastructure`): Kubernetes
manifests, AWS SAM templates, and deployment configuration. Hosts
Renovate CronJob definitions and agent deployment manifests.

### MR Creation Entrypoints

| Entrypoint                                             | Repo                 | Trigger                     | What it creates                                                 |
| ------------------------------------------------------ | -------------------- | --------------------------- | --------------------------------------------------------------- |
| [`dist_git_update_multi_mr.sh`][rpms-dist-git]         | rpms                 | GitLab schedule (every 4h)  | One MR per package needing Fedora dist-git sync                 |
| [`upstream_update_multi_mr.sh`][rpms-upstream]         | rpms                 | GitLab schedule             | One MR per package with a newer upstream release                |
| [`rebuild_multi_mr.sh`][rpms-rebuild]                  | rpms                 | Manual (operator-triggered) | One MR per package needing rebuild                              |
| [`create_lockfile_update_mrs.sh`][containers-lockfile] | containers           | GitLab schedule             | One MR per image with changed RPM lockfiles                     |
| [`ci/create_mr.sh`][containers-create-mr] (metrics)    | containers           | GitLab schedule (daily)     | Single chore MR for metrics report                              |
| Renovate (rpms)                                        | rpms                 | K8s CronJob (hourly)        | Tekton pipeline digest and Konflux release-catalog updates only |
| Renovate (containers)                                  | containers           | K8s CronJob (hourly)        | Dependency updates, lockfile maintenance, pipeline migration    |
| Renovate (tools/infra/k8s-test)                        | tools/infra/k8s-test | K8s CronJob (hourly)        | Dependency updates                                              |
| CVE analysis (`advisory_handler`)                      | CEE advisories       | K8s CronJob (30 min)        | Advisory MRs; handles rebase on conflicts                       |
| `/cve` skill                                           | rpms                 | Manual (Cursor/Claude)      | Fix MRs from staged CVE analysis data in Jira                   |
| `gitlab_sync`                                          | tools                | Various                     | File sync MRs with poll, rebase, and best-effort approve        |
| Manual dev workflows                                   | rpms/containers      | Human on dev machine        | Package updates, CVE fixes, spec changes                        |

### MR Creation Mechanism: Git Push Options

All shell-script-based MR creation uses **git push options**, not the
GitLab Merge Requests REST API. The push options control MR creation,
title, description, labels, draft status, and merge-when-pipeline-succeeds
(MWPS):

```text
git push \
  --push-option merge_request.create \
  --push-option "merge_request.title=chore(rpms): Update foo to 1.2.3" \
  --push-option merge_request.remove_source_branch \
  --push-option merge_request.merge_when_pipeline_succeeds \
  origin HEAD:refs/heads/chore/upstream-update-foo
```

Approval is always a separate step — never part of the creation scripts.

### MR Lifecycle and Approval Flows

#### GitLab Project Settings (containers and rpms)

| Setting                        | Value                                                             |
| ------------------------------ | ----------------------------------------------------------------- |
| Approvals required             | 1 (`any_approver`); author cannot self-approve                    |
| Pipeline must succeed          | Yes                                                               |
| Discussions resolved           | Required                                                          |
| Jira required                  | Yes (`prevent_merge_without_jira_issue`)                          |
| Merge trains / merge pipelines | Off (Konflux external statuses must stay blocking)                |
| Merge method                   | Merge commit                                                      |
| Auto-merge                     | MWPS via `merge_request.merge_when_pipeline_succeeds` push option |

#### Bot Identities

| Role                      | Identity                   | Token type                     |
| ------------------------- | -------------------------- | ------------------------------ |
| Create chore MRs          | `chore-mr`                 | Project access token           |
| Approve chore MRs (CI)    | `chore-mr-approval`        | Separate project access token  |
| Create lockfile MRs       | `lockfile-update`          | Project access token           |
| Approve lockfile MRs (CI) | `lockfile-update-approval` | Separate project access token  |
| Renovate + Konflux PAC    | `pipelines-as-code`        | MintMaker token                |
| Lambda approvals          | Per-project tokens         | Separate project access tokens |

#### Approval Paths

Three parallel approval mechanisms exist, with overlapping scope:

**1. CI approval jobs** — delayed jobs in each repo's `.gitlab-ci.yml`:

- rpms `chore_mr_approval`: gates on `check_konflux_statuses.py` (polls
  every 60s up to 2 hours for Konflux statuses to appear and succeed),
  then approves with `CHORE_MR_APPROVAL_GITLAB_TOKEN`. Triggered for
  author `chore-mr` or `pipelines-as-code` on `chore/*` branches.

- containers `chore_mr_approval`: same author/branch gate, approves with
  `CHORE_MR_APPROVAL_GITLAB_TOKEN`. No Konflux polling.
  `allow_failure: true`.

- containers `lockfile_update_approval`: triggered for
  `pipelines-as-code` on `lock-file-maintenance(-vulnerability)?`
  branches. Real `when: delayed` / `start_in: 10 minutes`. No Konflux
  polling.

**2. `mr-auto-approver` Lambda** — event-driven via GitLab webhooks:

```text
GitLab webhook → gitlab-event-forwarder → SNS → mr-auto-approver Lambda
```

Approves only (does not set MWPS). Rejects forks. Checks Konflux
statuses where configured.

| Project        | Allowed authors | Branch patterns                                   | Konflux check |
| -------------- | --------------- | ------------------------------------------------- | ------------- |
| containers     | PAC + chore-mr  | `renovate/.*`, `chore/.*`                         | Yes           |
| rpms           | PAC + chore-mr  | `chore/.*` only                                   | Yes           |
| tools          | PAC             | `renovate/.*` (deny `renovate/redhat-catalog/.*`) | No            |
| infrastructure | renovate token  | `renovate/.*`                                     | No            |

The Lambda is intended to replace CI approval jobs; both currently run in
parallel for chore/lockfile paths.

**3. Renovate automerge** — Renovate sets `automerge: true` in its MR
configuration, but GitLab still requires a non-author approval before
merge. For rpms Renovate MRs, neither CI approval jobs nor the Lambda
cover `renovate/.*` branches — these MRs are stuck until a human
approves.

#### Konflux Status Gate

External commit statuses prefixed `Konflux kflux-prd-rh03 /` are set by
Konflux PipelineRuns triggered via Pipelines-as-Code. The
`check_konflux_statuses.py` script (rpms) polls these statuses:

- Missing → wait (poll continues)
- Failed → do not approve
- Invoked/running/pending/success → approve (MWPS then waits for final
  green, including Testing Farm via IntegrationTestScenarios)

#### Lifecycle by MR Type

**RPMs dist-git clean** (`chore/dist-git-update-<pkg>`): schedule creates
→ MWPS at creation → GitLab CI + Konflux builds + Testing Farm → CI
approval job (poll Konflux, up to 2h) + Lambda → merge. Typical: tens of
minutes to hours.

**RPMs dist-git conflict**: same branch, but MR is created as draft with
`no-test` label and no MWPS. Requires human conflict resolution (or
`claude_resolve_conflict.sh`), then remove draft/`no-test` and
re-trigger.

**RPMs upstream** (`chore/upstream-update-<pkg>`): same as dist-git
clean. Uses OIDC AWS lookaside upload for tarballs.

**RPMs rebuild** (`chore/rebuild-<pkg>`): same approval path. Typically
operator-triggered, not scheduled.

**RPMs Renovate** (`renovate/…`): Renovate sets automerge, but neither CI
approval job nor Lambda covers `renovate/.*` branches on rpms → stuck
until human approves. The `renovate-babysit` agent workflow posts a
triage note but does not approve or merge.

**Containers Renovate lockfile** (`lock-file-maintenance`):
`lockfile_update_approval` (10 min delay) + Lambda (`renovate/.*` with
Konflux check) → Renovate automerge / MWPS. Typical: 30–90+ minutes.

**Containers other Renovate**: Lambda covers `renovate/.*`. No
`lockfile_update_approval` unless branch matches lockfile pattern.

**Containers metrics report** (`chore/metrics-report`): daily schedule →
MWPS → `chore_mr_approval` + Lambda.

**Containers CI lockfile** (`rpm-lockfile-updates/<image>`): schedule is
currently `active: false`. Approval path is incomplete — CI rule matches
`lock-file-maintenance`, Lambda does not match
`rpm-lockfile-updates/.*`.

### Shell Script Automation Detail

#### rpms `create_mr.sh` (shared helper)

Used by all rpms multi-MR scripts. Expects commits already on HEAD.

Inputs: `--branch NAME` (required), `--title TEXT` (required), optional
`--description`, `--auto-merge`, `--draft`, `--label NAME` (repeatable).

Algorithm:

1. Count commits ahead of target branch; if 0 → exit 0.
1. Dedup: `git ls-remote --heads` for branch name. If present → exit 2
   ("MR already exists").
1. Create branch, push with MR push options.
1. Parse push stdout for MR URL; if missing → exit 1.

Exit code contract: 0 = MR created, 2 = remote branch exists (skip),
1 = failure.

Limitation: stale remote branch from a closed MR still triggers exit 2.
Does not update existing MR/branch content. No `--force-with-lease`.

#### rpms `dist_git_update_multi_mr.sh`

Creates one MR per package needing Fedora dist-git sync.

Modes: production (cwd = repo, always create MRs) vs clone dry-run vs
clone + `--create-mrs`.

Algorithm:

1. Select `metadata/*.json` files; apply `--clean-only` /
   `--modified-only` filter; skip native packages.
1. Record `START_COMMIT` on target branch.
1. For each package: run `./ci/dist_git.py update PACKAGE`. Exit 0 +
   new commit = clean update. Exit 2 + new commit = conflict update.
1. Collect all new commits, hard-reset target to `START_COMMIT`.
1. Per commit: parse subject
   (`^(Update|Sync) ([^ ]+) from ... to ...`), create branch
   `chore/dist-git-update-<pkg>`, cherry-pick.
   Conflict → draft + `no-test`, no auto-merge. Clean → `--auto-merge`.
1. Call `create_mr.sh`.

Branch convention: `chore/dist-git-update-<pkg>`. Title:
`chore(rpms): <commit subject>` or `CONFLICT: chore(rpms): <subject>`.

#### rpms `upstream_update_multi_mr.sh`

Same multi-MR / cherry-pick pattern as dist-git, for upstream version
bumps.

Algorithm: runs
`./ci/check_upstream_versions.py check --update --sign-off`,
collects commits, splits into per-package MRs. Always
`--auto-merge`. Branch: `chore/upstream-update-<pkg>`.

#### rpms `rebuild_multi_mr.sh`

Does not generate rebuilds. Expects local commits from
`dist_git.py rebuild` or `rebuild-rev-deps`, then splits them into
per-package MRs.

Unique feature: `--force` flag deletes existing remote branch before
create, working around stale branches from closed MRs. Branch:
`chore/rebuild-<pkg>`.

#### containers `create_lockfile_update_mrs.sh`

Creates or updates one MR per image group when RPM lockfiles changed.
Prerequisite: lockfiles already refreshed (`make all-host FORCE_REFRESH=true`).

Algorithm (`process_single_image`):

1. Branch: `rpm-lockfile-updates/<image>`.
1. For each distro/variant lockfile: compare to HEAD after stripping
   `.arches[].packages[].url` and `.arches[].source[].url` via `yq`
   (URL churn ignored).
1. If no meaningful changes → skip.
1. If `push-mode` ≠ `force` and `origin/<branch>` exists: compare to
   remote; if identical → skip.
1. `git switch --force-create` branch, commit lockfiles.
1. Push `--force-with-lease` + MR push options.

Key difference from rpms: uses `--force-with-lease` to update existing
branches in place. Dedup compares lockfile content, not just branch
existence.

#### containers `create_mr.sh` (simpler helper)

Used by metrics report. Creates from working tree (not existing
commits). `git add --all`, commit, `--force-with-lease` push. No dedup —
overwrites existing branch.

#### Deduplication Summary

| Script                    | Existing branch                | Content refresh                  |
| ------------------------- | ------------------------------ | -------------------------------- |
| rpms `create_mr.sh`       | Skip (exit 2)                  | Never                            |
| rpms multi-MR scripts     | Via `create_mr.sh`             | Never (unless `rebuild --force`) |
| containers lockfile       | Skip if remote content matches | Yes (`--force-with-lease`)       |
| containers `create_mr.sh` | Overwrites                     | Yes                              |

### Hummingbird Agent Framework

The [Hummingbird Agent][hummingbird-agent-docs] is an event-driven LLM
agent deployed on OpenShift that processes GitLab events via SQS.

#### Architecture

- **Event-driven**: consumes SQS events (pipeline failures, MR events,
  slash commands). No REST API — triggered only by SQS or CLI.
- **Workflow-driven**: investigation logic defined in markdown files as
  LLM system prompts. New behaviors do not require code changes.
- **Sandboxed execution**: all LLM commands run in isolated containers
  (Podman/K8s/KubeVirt) with no network access and no credentials.
- **Multi-model**: supports Gemini and Claude via Vertex AI.
- **Token separation**: model tokens (read-only, Reporter-level) are
  distinct from orchestrator tokens (write-capable, used only by
  deterministic code outside the sandbox).
- **Single output action**: `post_gitlab_note` is the only way the agent
  affects the outside world. It cannot create, modify, or merge MRs.

#### Current Workflows

**`analyze-failures`**: triggered on pipeline failure. Bulk-fetches
GitLab CI job logs, Konflux PipelineRun/TaskRun metadata and logs, and
Testing Farm results. Groups failures by root cause. Posts a structured
MR note with collapsible forensic evidence and links.

- Tools: `gitlab_get_mr_details`, `gitlab_get_mr_diff`,
  `gitlab_get_commit_statuses`, `konflux_list_pipelineruns`,
  `konflux_get_pod_log`, `tf_get_results`, `tf_get_test_log`,
  `sandbox_exec`
- Pattern: bulk metadata fetch → selective deep log pulls → grouped
  analysis → structured note
- Flexibility: medium-low (tightly coupled to Konflux/Tekton/TF
  pipelines)

**`code-review`**: triggered on MR open/update. Reads the unified diff,
prior review discussions, and per-repo rules. Posts review findings with
severity, category, and concrete code fix examples.

- Tools: `gitlab_get_mr_details`, `gitlab_get_mr_unified_diff`,
  `gitlab_get_mr_discussions`, `gitlab_get_file_at_ref`, `sandbox_exec`
- Pattern: diff-first analysis, discussion-aware follow-up (avoids
  re-raising resolved issues), per-project rules overlay
- Per-repo rules: `workflows/repo-rules/<group>-<repo>.md` files
  provide project-specific review guidance (e.g.,
  `hummingbird-rpms.md` documents package metadata conventions)
- Flexibility: high (generic for any GitLab MR; domain knowledge plugs
  in via `repo-rules/`)

**`renovate-babysit`**: triggered on successful Renovate MR pipeline.
Classifies the update as safe or risky based on diff scope, upstream
changelogs (via web search), and local API usage. Posts a triage verdict.

- Tools: `gitlab_get_mr_details`, `gitlab_get_mr_unified_diff`,
  `web_search`, `gitlab_get_repo_archive`, `sandbox_exec`
- Pattern: diff scope classification, embedded changelog first then web
  search, archive + grep for call-site impact
- Flexibility: medium-high (ecosystem-agnostic risk matrix; does not
  approve/merge — triage note only)

#### What the Agent Has That Maps to a Workqueue

- SQS FIFO queue with message grouping (serializes per session)
- Session persistence (S3 `context.json`)
- Config hot-reload in serve mode
- Per-project token separation (model / action / orchestrator)
- Rate limiting (per-workflow per-MR)
- Data source abstraction (GitLab, Konflux, Testing Farm)
- Auto-resolve on push/success

#### What the Agent Lacks for MR Lifecycle Management

- No MR creation capability (no git write operations, no push access)
- Read-only GitLab tokens for the model
- No workqueue for MR lifecycle state (events are fire-and-forget)
- Single output action (`post_gitlab_note` only)
- No safe-outputs pattern (no validation of proposed writes)
- No deterministic fallback paths for well-understood operations
- No request/response API (SQS consumption and CLI only; external
  services cannot invoke a workflow and retrieve structured results)

### Event Bus

The existing event pipeline could serve as the backbone for a workqueue:

```text
GitLab MR / note / pipeline webhooks
  → gitlab-event-forwarder (API Gateway → Lambda)
  → SNS hummingbird-events-topic
  → mr-auto-approver Lambda (approve safe bot MRs)
  → hummingbird-agent SQS (analyze / review / babysit)
  → hummingbird-status SQS (pipeline tracking)
```

`mr-auto-approver` is a pure rule-based approver — no LLM involvement.
`hummingbird-mr-human-tracker` detects human fixes on Renovate/bot MRs
and tracks them in Jira epics.

### Security Foundation: HUM-851

[HUM-851] ("Enable Secure Agent MR Creation") is an existing
epic (status: New) that designs the security posture for agents creating
MRs.

#### Core Principle

Instead of protecting CI secrets from agent-authored MR pipelines,
eliminate all secrets from containers/rpms/tools CI entirely. Move all
secret-dependent jobs to the infrastructure repo's CI. With zero secrets,
a compromised agent MR pipeline can only access `CI_JOB_TOKEN`
(single-project-scoped for bot users) and the runner's network.

#### What Moves to Infrastructure Repo CI

| Job                       | Current project         | Current trigger    |
| ------------------------- | ----------------------- | ------------------ |
| `deploy_hugo_tag`         | containers, rpms, tools | On merge to main   |
| `lockfile_update`         | containers              | Scheduled          |
| Lockfile/chore approval   | containers, rpms        | After MR CI passes |
| Chore MR creation         | containers, rpms        | Scheduled          |
| `dist_git_update`         | rpms                    | Scheduled          |
| `upstream_version_update` | rpms                    | Scheduled          |
| `metrics_report`          | containers              | Scheduled          |
| `update_quay_description` | containers              | Scheduled/on merge |

This migration directly enables centralized MR creation.

#### Target Security Posture

- Zero CI secrets in target projects
- Restricted runners with egress filtered to package registries only
- Agent never holds write tokens — writes happen in deterministic
  orchestrator code
- Diff safety validation — blocklist prevents changes to CI config,
  `.tekton/`, dependency files
- Human review required for every agent MR, auto-labeled
  `agent-generated`
- Rate limiting per-project and global; auto-close stale MRs
- Monitoring: every agent MR logged and Slack-notified

#### Task Breakdown

| Task      | Status | What it does                       |
| --------- | ------ | ---------------------------------- |
| [HUM-852] | New    | Threat model and security design   |
| [HUM-853] | New    | Move ops jobs to infra CI          |
| [HUM-854] | Closed | K8s CronJob/Job manifests (done)   |
| [HUM-855] | New    | Validate and remove CI variables   |
| [HUM-856] | New    | Restrict runner egress             |
| [HUM-857] | New    | MR creation orchestrator action    |
| [HUM-858] | New    | Rate limiting and abuse prevention |
| [HUM-859] | New    | Monitoring and incident response   |

### Renovate Deployment

Deployed as Kubernetes CronJobs in the infrastructure repo
([`kubernetes/renovate/20-cronjobs.yml.j2`][infra-renovate-cronjobs]):

- 5 repos: containers, infrastructure, k8s-test-pipeline, rpms, tools
- Each gets its own CronJob running hourly with
  `concurrencyPolicy: Replace`
- Uses MintMaker image (`MINTMAKER_IMAGE`)
- containers/rpms use bash wrappers and custom config files
- Custom env variables for RPM lockfile cache, Rust/Cargo paths

### CVE Analysis Pipeline

The CVE analysis pipeline is a complex, mature system. The relevant
interface points for a workqueue are:

1. **`hummingbird-cve-analysis` CronJob** (K8s, every 30 min prod) —
   runs `cve_analysis --resolve` which triages Jira Security tickets,
   transitions statuses, creates advisory MRs, manages labels.
1. **`collect_cve_dashboard`** — runs after analysis, posts lifecycle
   data to the dashboard API.
1. **`/cve` skill** — reads staged CVE analysis data from Jira tickets
   and creates fix MRs in the rpms repo.

The workqueue integration point: when `/cve` or CVE analysis determines
an MR should be created, that request becomes a work item.

### RPM-to-Container Pipeline Flow

A single RPM spec change triggers a cascade that spans both repos and
multiple build systems. The full flow is documented in the
[RPM Pipeline][rpm-pipeline] and [Image Pipeline][image-pipeline] docs.

```text
RPM spec change (rpms repo)
  → MR validation (GitLab CI + Konflux build + Testing Farm)
  → Merge to main
  → Konflux RPM build (Tekton PipelineRun per package, mock hermetic)
  → RPM signing (Kerberos-based)
  → Publish to Pulp (packages.redhat.com)
  → Lockfile update detects new RPM versions (containers repo)
  → Lockfile MR created (Renovate or create_lockfile_update_mrs.sh)
  → Container build (Konflux, multi-arch)
  → Container testing (Testing Farm + K8s tests)
  → Enterprise Contract validation (Conforma)
  → Release to Quay.io
```

Key observations for the workqueue:

- The cascade is implicit — there is no explicit trigger from RPM
  publish to container lockfile update. Lockfile updates discover new
  RPMs by polling Pulp (via `make all-host FORCE_REFRESH=true` or
  Renovate's RPM lockfile maintenance).
- A single RPM change can fan out to many container images (any image
  that includes that package in its lockfile).
- The RPM pipeline has 5 stages (spec change, MR validation, build,
  signing, publishing). The container pipeline has 6 stages (source
  templates, generation, build, testing, Enterprise Contract, release).
- Testing Farm runs integration tests on merge requests only, not on
  main branch builds. Container tests include reverse dependency
  testing (rebuilding dependent images locally in the test
  environment).
- Enterprise Contract (Conforma) validates supply chain security,
  hermetic builds, and policy compliance before release.

## Decision

*To be determined by the spike investigation. This section will be
updated with the chosen architecture.*

The spike should investigate a unified workqueue-based system where:

- Queue feeders replace or wrap the current scheduled scripts and
  Renovate outputs
- Queue processors handle MR creation, approval, rebasing, and merge
  through deterministic code
- Agentic capabilities (review, patch generation, triage) are invoked as
  composable services with structured output
- The security model follows HUM-851's design: agents reason read-only,
  orchestrators execute writes

## Design Patterns and Prior Art

### GitHub Agentic Workflows (gh-aw)

[gh-aw] provides a reference architecture for AI-assisted
repository automation with [security guardrails][gh-aw-arch]:

- **Read-only agent execution**: agents run with no write permissions, no
  secrets
- **[Safe Outputs][gh-aw-safe-outputs]**: agents buffer intended write
  operations as structured JSON artifacts; separate permission-controlled
  jobs validate and execute them
- **Threat detection**: a separate AI agent scans agent outputs before
  write execution
- **Plan-level trust**: trust is embedded in the workflow definition
  (what the agent is allowed to do), not in the agent's runtime decisions

Key pattern: separate reasoning (agentic, sandboxed, read-only) from
execution (deterministic, permission-controlled, auditable).

### Existing Hummingbird Patterns

- **SQS FIFO queue with message grouping**: already serializes work per
  session; can be extended to serialize per-MR
- **Workflow-as-prompt**: markdown files define behavior; new behaviors
  do not need code changes
- **Data source abstraction**: GitLab API access is modular
- **Token tier separation**: model read tokens, action write tokens,
  orchestrator tokens — maps directly to the safe-outputs pattern
- **Sandbox isolation**: reusable for agentic review/analysis tasks

### Agent as Composable AI Service

One approach to bridge the agent framework and a workqueue is to evolve
the agent from a self-contained event processor into a building block
that non-AI services can call:

- **Request/response API**: HTTP endpoint accepts workflow requests,
  returns a UUID; caller polls for structured JSON results. The caller
  (e.g., a workqueue herder) applies deterministic logic to decide what
  to do with the output.
- **Structured output**: agent produces typed JSON (not just a GitLab
  note), enabling callers to process results programmatically.
- **Safe-output actions**: new action types beyond `post_gitlab_note`
  (e.g., `create_mr`, `update_mr`) with per-workflow path allowlists,
  diff size limits, and branch naming constraints. The orchestrator
  validates each action against the workflow's configured constraints
  before execution.

## Open Questions

1. **Queue technology**: extend SQS FIFO (already in use by the agent)
   or use a different queue (K8s-native, Redis, PostgreSQL)?
1. **Processor deployment**: K8s Deployments polling SQS, GitLab CI jobs
   triggered by webhooks, Lambda functions, or a combination?
1. **Renovate strategy**: keep Renovate as a separate MR creator and add
   a herder, or replace Renovate's MR creation with the workqueue?
1. **Write credentials**: per-repo project access tokens (current model)
   or a single bot account? How does HUM-851's "eliminate CI secrets"
   model interact with workqueue processors that need write access?
1. **Safe outputs validation**: simple schema validation, deterministic
   allowlist checks, or full threat detection (as in gh-aw)?
1. **Review scope**: which MRs need AI review before merging vs which
   can be auto-merged with deterministic checks only?
1. **State tracking**: queue, GitLab labels, a database, or the existing
   `hummingbird-status` PostgreSQL?
1. **Agent evolution**: request/response API, safe-output actions, or
   hybrid? How does this relate to HUM-857?
1. **HUM-851 relationship**: is the workqueue spike a superset of
   HUM-851, or a separate epic that depends on HUM-851 Phase 1?

## Consequences

*To be updated after the spike investigation determines the architecture.*

Known consequences of any workqueue approach:

- Centralizing MR creation provides a single point for audit, rate
  limiting, and monitoring
- Moving secret-dependent jobs to the infrastructure repo (per HUM-851)
  is a prerequisite regardless of workqueue design
- The existing CI approval jobs, Lambda approver, and Renovate automerge
  have overlapping scope that must be reconciled
- RPMs Renovate MRs currently have no automated approval path — any
  design must address this gap
- The agent's current workflows (failure analysis, code review, Renovate
  babysit) complement the workqueue and should not be disrupted

## File and System Inventory

### Infrastructure repo

| Path                                                | Contents                               |
| --------------------------------------------------- | -------------------------------------- |
| [`kubernetes/renovate/`][infra-renovate]            | Renovate CronJob definitions (5 repos) |
| [`kubernetes/hummingbird-agent/`][infra-agent]      | Agent deployment manifests (8 files)   |
| [`kubernetes/hummingbird-cve-analysis/`][infra-cve] | CVE analysis CronJob                   |
| [`aws/hummingbird-agent/`][infra-agent-aws]         | Agent SQS/SNS SAM templates            |

### Tools repo

| Path                                                          | Contents                                                                     |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [`hummingbird-agent/`][tools-agent]                           | Agent framework (loop, sandbox, models, data sources, workflows)             |
| [`hummingbird-agent/workflows/`][tools-workflows]             | Workflow definitions (`analyze-failures`, `code-review`, `renovate-babysit`) |
| [`hummingbird-agent/workflows/repo-rules/`][tools-repo-rules] | Per-project review rules (`hummingbird-rpms.md`)                             |
| [`hummingbird-cve-analysis/`][tools-cve]                      | CVE analysis pipeline (preserve)                                             |
| [`hummingbird-dashboard/`][tools-dashboard]                   | Dashboard web app (preserve)                                                 |
| [`mr-auto-approver/`][tools-approver]                         | Lambda: rule-based MR approval                                               |
| [`hummingbird-mr-human-tracker/`][tools-tracker]              | Lambda: tracks human fixes on bot MRs                                        |
| [`gitlab-ci/gitlab_sync/`][tools-sync]                        | File sync MR creation with rebase                                            |
| [`gitlab-event-forwarder/`][tools-forwarder]                  | Webhook → SNS bridge                                                         |
| [`hummingbird-events-topic/`][tools-events]                   | SNS topic infrastructure                                                     |

### RPMs repo

| Path                                                 | Contents                                                    |
| ---------------------------------------------------- | ----------------------------------------------------------- |
| [`ci/create_mr.sh`][rpms-create-mr]                  | Shared MR creation helper (push options, dedup by branch)   |
| [`ci/dist_git_update_multi_mr.sh`][rpms-dist-git]    | Dist-git sync: commit-all → reset → cherry-pick per package |
| [`ci/upstream_update_multi_mr.sh`][rpms-upstream]    | Upstream version bumps: same cherry-pick pattern            |
| [`ci/rebuild_multi_mr.sh`][rpms-rebuild]             | Rebuild MR splitter (with `--force` for stale branches)     |
| [`ci/dist_git.py`][rpms-dist-git-py]                 | CLI for import/update/sync/rebuild operations               |
| [`ci/check_konflux_statuses.py`][rpms-konflux-check] | Polls Konflux external statuses before approval             |
| [`ci/claude_resolve_conflict.sh`][rpms-conflict]     | AI-assisted conflict resolution for dist-git MRs            |
| `metadata/<package>.json`                            | Per-package metadata (upstream URL, CVE mapping, status)    |

### Containers repo

| Path                                                      | Contents                                                         |
| --------------------------------------------------------- | ---------------------------------------------------------------- |
| [`ci/create_lockfile_update_mrs.sh`][containers-lockfile] | Per-image lockfile MR creation (force-with-lease, content dedup) |
| [`ci/create_mr.sh`][containers-create-mr]                 | Generic chore MR helper (force-with-lease, no dedup)             |
| [`ci/internal/shared_lib.sh`][containers-shared-lib]      | Shared utilities (`get_distro_variants`, build helpers)          |
| `images/<name>/`                                          | Per-image Containerfiles and RPM lockfiles                       |

[containers-create-mr]: https://gitlab.com/redhat/hummingbird/containers/-/blob/main/ci/create_mr.sh
[containers-lockfile]: https://gitlab.com/redhat/hummingbird/containers/-/blob/main/ci/create_lockfile_update_mrs.sh
[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[containers-shared-lib]: https://gitlab.com/redhat/hummingbird/containers/-/blob/main/ci/internal/shared_lib.sh
[gh-aw]: https://github.github.com/gh-aw/
[gh-aw-arch]: https://github.github.com/gh-aw/introduction/architecture/
[gh-aw-safe-outputs]: https://github.github.com/gh-aw/reference/safe-outputs/
[hum-6342]: https://redhat.atlassian.net/browse/HUM-6342
[hum-851]: https://redhat.atlassian.net/browse/HUM-851
[hum-852]: https://redhat.atlassian.net/browse/HUM-852
[hum-853]: https://redhat.atlassian.net/browse/HUM-853
[hum-854]: https://redhat.atlassian.net/browse/HUM-854
[hum-855]: https://redhat.atlassian.net/browse/HUM-855
[hum-856]: https://redhat.atlassian.net/browse/HUM-856
[hum-857]: https://redhat.atlassian.net/browse/HUM-857
[hum-858]: https://redhat.atlassian.net/browse/HUM-858
[hum-859]: https://redhat.atlassian.net/browse/HUM-859
[hummingbird-agent-docs]: https://hummingbird-project.io/docs/background/tools/hummingbird-agent-design/
[image-pipeline]: https://gitlab.com/redhat/hummingbird/containers/-/blob/main/documentation/background/image-pipeline.md
[infra-agent]: https://gitlab.com/redhat/hummingbird/infrastructure/-/tree/main/kubernetes/hummingbird-agent
[infra-agent-aws]: https://gitlab.com/redhat/hummingbird/infrastructure/-/tree/main/aws/hummingbird-agent
[infra-cve]: https://gitlab.com/redhat/hummingbird/infrastructure/-/tree/main/kubernetes/hummingbird-cve-analysis
[infra-renovate]: https://gitlab.com/redhat/hummingbird/infrastructure/-/tree/main/kubernetes/renovate
[infra-renovate-cronjobs]: https://gitlab.com/redhat/hummingbird/infrastructure/-/blob/main/kubernetes/renovate/20-cronjobs.yml.j2
[rpm-pipeline]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/documentation/background/rpm-pipeline.md
[rpms-conflict]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/claude_resolve_conflict.sh
[rpms-create-mr]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/create_mr.sh
[rpms-dist-git]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/dist_git_update_multi_mr.sh
[rpms-dist-git-py]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/dist_git.py
[rpms-konflux-check]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/check_konflux_statuses.py
[rpms-rebuild]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/rebuild_multi_mr.sh
[rpms-repo]: https://gitlab.com/redhat/hummingbird/rpms
[rpms-upstream]: https://gitlab.com/redhat/hummingbird/rpms/-/blob/main/ci/upstream_update_multi_mr.sh
[tools-agent]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-agent
[tools-approver]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/mr-auto-approver
[tools-cve]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-cve-analysis
[tools-dashboard]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-dashboard
[tools-events]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-events-topic
[tools-forwarder]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/gitlab-event-forwarder
[tools-repo-rules]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-agent/workflows/repo-rules
[tools-sync]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/gitlab-ci/gitlab_sync
[tools-tracker]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-mr-human-tracker
[tools-workflows]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-agent/workflows
