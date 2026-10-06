---
title: "HUM-7376: AI Investigation Service Architecture"
weight: 10
aliases: [/l/design-HUM-7376]
---

- **Status:** proposed
- **Authors:** Prarit Bhargava
- **Jira:** [HUM-7376][jira]
- **Created:** 2026-10-06
- **Last updated:** 2026-10-07

## Summary

This agreement establishes the architecture for a centralized AI Investigation
service that handles AI-assisted CVE investigation, package upgrades, merge
request rework, and other automated work items in the Hummingbird project.

The service is a deterministic orchestrator. Callers enqueue tagged work items;
the orchestrator looks up a YAML recipe for that tag and executes it. AI runs
in a sandboxed environment with no credentials. Results are independently
verified before any privileged write — such as a Jira update or GitLab merge
request — is performed.

The detailed design, contract schemas, component descriptions, and phased
rollout plan are in the
[AI Investigation design document][design-doc].

## Motivation

CVE investigation, package upgrades, and merge request rework are today driven
by manual, human-invoked workflows (e.g., the `/cve` Cursor skill). As ticket
volume grows, the team needs a repeatable, auditable, and secure path from
"something needs attention" to "a merge request exists for human review."

Without a centralized service, each caller (CVE analysis, upstream monitoring,
image-request forms) would grow its own AI-to-MR pipeline. This produces
inconsistent security postures, duplicated privileged code, and no common
audit trail.

The existing hummingbird-agent establishes the principle of separating
untrusted model output from privileged writes. This design follows the same
principle: AI Investigation produces a structured, credential-free result;
the caller that invoked it (e.g., the CVE agent) receives that result and
decides whether to submit a workqueue service work item for MR creation.
Privileged writes are the caller's responsibility, not the investigation
sandbox's.

## Depends on

- [HUM-851] — Enable Secure Agent MR Creation (zero CI secrets in target
  projects, restricted runners, diff blocklist). MR creation phases depend on
  HUM-851 Phase 1 being in place.
- [HUM-857] — MR creation orchestrator action (`create_merge_request` in
  actions.py). Required before the orchestrator can emit MR work items.

## Impacts

### User facing

In early phases (investigate-and-attach), there is no user-visible change.
The agent posts a Jira comment and structured attachment that replaces or
supplements a human `/cve` run. In later phases, the human step shifts from
invoking the skill to reviewing an agent-created merge request. The manual
`/cve` workflow in Cursor continues to work throughout all phases.

### Repositories

- [x] tools/ — new `hummingbird-ai-investigation` package (workflow catalog,
  schema, request builder, verifier, Jira attachment); additive changes to
  `hummingbird-agent` (new investigation workflow YAML, later a new
  `create_merge_request` action); additive changes to `cve_analysis.py`
  (flag-gated enqueue after `--resolve` defers a ticket)
- [x] rpms/ — `cve_helper.py` helper functions imported by the orchestrator
  (no behavior change)
- [x] infrastructure/ — new CronJob manifest for the investigation consume job
- [ ] documentation/
- [ ] gorget/
- [ ] containers/
- [ ] skills/

## Design

The service has five logical components. All trust boundaries are crossed via
structured JSON; no component passes raw shell sessions or credentials across
a boundary.

**Caller** — detects that work is needed and enqueues a tagged work item
(e.g., `investigate_cve`, `update_package`, `rework_mr`). A caller must not
create or merge GitLab MRs. If it cannot name the work with a known tag, it
does not enqueue.

**Orchestrator** — looks up the YAML recipe for the item's tag and executes
it. Unknown tag → reject; the orchestrator never guesses or substitutes.
Holds all credentials. Schema-checks every hop. Does not decide at runtime
whether AI is needed; that is a property of the YAML recipe the caller
selected. Exposes an API so that callers (CVE analysis CronJob, upstream
monitor, human tooling) can submit work items and retrieve structured results
without coupling to the orchestrator's internal implementation.

**AI Investigation sandbox** — an untrusted model loop implemented by
hummingbird-agent, invoked via the orchestrator API with a new investigation
workflow. Receives a request JSON and an isolated git worktree. Has no
orchestrator tokens and no unconstrained shell. Returns a result JSON and, if
a code change was produced, a git ref on the worktree. Prompt injection and
stochastic errors are assumed.

**Independent verifier** — a second model loop or deterministic checker that
receives the result JSON without the original tool trace. Confirms that the
evidence is internally consistent and that any patch actually addresses the
stated issue. Discovery does not verify its own work.

**MR service** — the only component allowed to hold GitLab write tokens.
Validates paths against a blocklist, pushes branches, opens MRs labelled
`agent-generated`, and watches CI. Does not invoke the model. Does not
auto-merge until a later, explicitly authorized phase.

### Core rules

| Rule | Meaning |
| ---- | ------- |
| AI is untrusted | Treat AI output as potentially injected or erroneous. |
| AI never holds tokens | Passwords, GitLab PATs, Jira tokens stay in orchestrator / MR service only. |
| Callers tag, YAML defines, orchestrator executes | The caller names the work; the recipe decides whether AI is involved. |
| Evidence before automation | A patch is not mergeable because the model said so. The result must cite sources and commits. |
| Independent verification | Discovery must not verify its own work. |
| Human review until trust is earned | MR creation requires human approval. Auto-merge is a later phase. |
| Existing code is reused, not replaced | `cve_analysis.py`, the `/cve` skill, `cve_helper.py`, and `dist_git.py` continue to work unchanged. |

## Risks and open questions

- **Working tree vs canonical push.** Investigation uses a sandbox clone.
  HUM-857 targets MR branches on the canonical project (`agent/<workflow>/...`)
  because forks are not a Konflux security boundary. The split is likely:
  agent writes only in the sandbox clone; MR service pushes to whatever target
  HUM-851 settles on.
- **Where the orchestrator lives.** New service vs an action on the existing
  hummingbird-agent event consumer. Meeting preference is a central service,
  not a library inside `cve_analysis.py`.
- **Verifier implementation.** Second LLM with no shared session vs
  deterministic checks (patch applies, commit in NVR, allowlist). Likely both:
  deterministic gates first, LLM verifier for semantic coverage.
- **Service account split.** A dedicated account for AI Investigation is
  needed, separate from the CVE-analysis Jira bot.
- **Read-only public fetches.** Whether investigation HTTP is public-only or
  routed through a credential-isolating proxy is undecided.

## Implementation notes

Rollout is phased so that each phase is independently production-safe and does
not require rewriting earlier phases:

- **Phase A** — Contract and dry run. Publish JSON schema, build request from
  ticket key, run AI Investigation with no write tokens, log results. No Jira
  or GitLab writes.
- **Phase B** — Investigate and attach. Orchestrator posts a structured result
  to the appropriate destination for the workflow type: a Jira comment and
  `ai-investigation.json` attachment for CVE and package workflows; a GitLab
  MR comment for rework and rebase workflows (which may have no Jira ticket).
- **Phase C** — Verifier. Deterministic gates first; LLM verifier second.
  Reject means no MR and `cve-needs-attention` stays in place.
- **Phase D** — MR creation. Only after HUM-851 Phase 1 and HUM-857. Human
  approval required.
- **Phase E** — Rework, rebase, and (eventually) auto-merge.

New code lives in a separate package and must not change the behavior of
existing jobs when the feature flag is off. The first merge may touch existing
trees (agent workflow YAML, CVE Job wrapper) but prod behavior stays identical
until the flag is enabled.

[design-doc]: https://docs.google.com/document/d/1zpyoqX71qIKbv5b4SoTaahWtxzVjQq3d9UJMUACSQfE/
[jira]: https://issues.redhat.com/browse/HUM-7376
[HUM-851]: https://issues.redhat.com/browse/HUM-851
[HUM-857]: https://issues.redhat.com/browse/HUM-857
