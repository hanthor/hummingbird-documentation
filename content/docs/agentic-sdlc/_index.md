---
title: Agentic SDLC
linktitle: Agentic SDLC
description: How Project Hummingbird uses agentic AI to drive velocity across the software development lifecycle.
weight: 50
aliases: [/l/agentic-sdlc]
---

Project Hummingbird's core mission is velocity: shipping RPM updates, CVE fixes, and new
container images as fast as possible. Managing 400+ packages and 1,750+ image builds with a
24-hour security SLO makes automation not a nice-to-have, but the only viable path.

Hummingbird is Red Hat's reference implementation for responsible agentic AI in software
engineering — not a pilot program, but a production system built incrementally and grounded
in engineering discipline.

## The vision: Agentic Software Development Lifecycle

The target state is a development pipeline driven by agents at every stage — with humans
engaged where their judgment is needed, not where their time is consumed by routine work. The
goal is to automate as much as possible, reducing the time humans spend on work that does not
require their judgment.

Every change flows through the same lifecycle:

**1. Request.** A customer, product team, or automated trigger submits a change: a new
container image, an RPM update, a feature request, a bug fix.

**2. Analysis.** A **product management agent** assesses the request — evaluating feasibility,
software licenses, priority, and fit against existing components and conventions. For
straightforward requests it proceeds automatically; for complex or ambiguous ones it surfaces
the relevant context and flags the case for human input before continuing. This is the work
that normally sits in a product manager's queue.

**3. Implementation.** The request splits based on its nature:

- *Deterministic changes* — dependency updates, lockfile syncs, rebuilds triggered by upstream
  changes — are implemented by rule-based automation and **merged automatically** once CI
  passes. No ticket, no approval, no delay.
- *Everything else* is handled by an **engineering agent**: a developer co-programming with an
  agent, or an agent working autonomously to write the code or configuration, run validation,
  and open a merge request. Agentic AI is the default answer for everything that has
  historically required a human to pick it up, think through it, and act on it. This extends
  beyond code: a **tech writer agent** drafts or updates the documentation that accompanies a
  change, and a **testing agent** generates or extends tests to cover it.

**4. Review.** Automated agents check for policy compliance and code quality, including the
production [code review agent][code-review-workflow]. The same agent capabilities that
contribute during implementation also apply here: a **tech writer agent** reviews documentation
changes for clarity and correctness, and a **testing agent** reviews test coverage and flags
gaps. A human engineer makes the final call on all of it. No agent-produced work is merged
without human approval — the human is not eliminated, but elevated to the role where judgment
actually matters.

**5. Merge.** The change ships.

The goal is not to remove humans from the process — it is to remove the parts that do not
need them.

## Responsible AI

Agent-produced code and decisions require human approval before merge. This is not a temporary
constraint — it is a design principle. Humans may stay in the loop to steer or babysit
complex work when that helps, but the standing requirement is approval — not constant
supervision of every agent run. The feedback between human judgment and agent behavior is what
keeps the system trustworthy over time.

This has a specific architectural implication: agents must learn from feedback. When a reviewer
comments on an agent-produced merge request, the agent incorporates that feedback and updates
its work. That feedback is also preserved — stored so that future agent runs can draw on it,
improving with each iteration rather than repeating the same mistakes.

This approach follows the frameworks established in Pascal Bornet's
[*Agentic Artificial Intelligence*][bornet-book].

## Building the Foundation

Deploying production agents requires a foundation. The approach that works is not to automate
first and document later — it is the reverse.

**Phase 1 — Agent as pair programmer.** Agents assist individual developers: drafting code,
explaining unfamiliar systems, proposing changes for review. This phase builds understanding
of what agents need: context, conventions, constraints.

**Phase 2 — Documentation as fuel.** Agent output quality is directly proportional to
documentation quality. Every repository carries an `AGENTS.md` — a file with instructions
targeting agents specifically, but one that mostly points to other documentation rather than
duplicating it. That underlying documentation is written for humans and agents alike: clear,
specific, and rich with rationale. The `AGENTS.md` is the entry point; the broader docs are
the substance. An agent with good documentation reasons from the same foundation as the team;
an agent without it guesses.

**Phase 3 — Agents in production.** With the foundation in place, agents move into the
critical path: first as reviewers proposing concrete changes, then as autonomous contributors
on well-defined tasks.

See [From Pair Programmer to Autonomous Agent][vrothberg-article-linkedin] by Valentin
Rothberg for the full treatment.

## Agents in Production Today

Two agents are running in production today — worker bees keeping the engines running. Built
on the [Hummingbird Agent][hummingbird-agent-docs] platform, they have contributed to
thousands of commits across the [`containers`][containers-repo] and [`rpms`][rpms-repo]
repositories over the past eight months — at a velocity that would be impossible to sustain
manually.

All agentic work on Hummingbird is tracked in the [HUM-687 epic][hum-687]. Readers will find
additional agents in planning there, such as the **merge conflict agent** — which will
automatically resolve conflicts that arise when rule-based automation updates `.spec` files in
the Hummingbird RPM pipeline and runs into Hummingbird-specific patches that need to be
carried forward.

### Failure Analysis Agent

Workflow definition and prompts live in the [`hummingbird/tools`][hummingbird-agent-tree]
repository ([`analyze-failures.md`][failure-analysis-workflow]).

When a merge request pipeline fails, this agent automatically investigates and posts its
findings directly on the merge request. It pulls data from multiple sources — GitLab CI job
logs, Konflux build and test pipeline runs, Testing Farm test results — and correlates them
to identify root causes. Where the same underlying issue causes multiple failures across
different images or architectures, it groups them so engineers see patterns rather than an
overwhelming list of individual failures. Every finding includes links to the specific logs
and artifacts so engineers can dig deeper without having to hunt.

What previously required an engineer to open several dashboards, cross-reference logs, and
manually piece together a root cause now happens automatically, before the author has finished
their coffee.

### Code Review Agent

Workflow definition and prompts live in the [`hummingbird/tools`][hummingbird-agent-tree]
repository ([`code-review.md`][code-review-workflow]).

When a merge request is opened, this agent performs a technical code review with the
priorities of a senior engineer: security first, then correctness, then performance, then
maintainability. It provides specific line references and concrete code examples for every
issue it raises — not vague suggestions, but actual fixes. It reads prior review discussions
before posting, avoids re-raising issues already addressed, and respects when a developer has
explained an intentional design choice.

The result is consistent, high-quality review coverage on every merge request, with human
reviewers free to focus on the issues that genuinely need their judgment.

## Documentation and Tech Writers

In an agentic system, documentation is infrastructure. It is the primary interface between
the team and its agents, and the quality of what an agent produces is bounded by the quality
of what it can read.

Critically, documentation itself should be written with agent assistance. The same agent that
helps an engineer write and review code can help write the documentation for it — capturing
decisions, explaining rationale, drafting contribution guides. This is not a shortcut; it is
the same pair-programming model applied to a different kind of output. This is how Hummingbird
bootstrapped itself as an AI-native project: agents were used from the start to draft and
improve documentation alongside code, creating a virtuous cycle where better docs made agents
more capable, and more capable agents helped produce better docs.

Tech writers are not a prerequisite for this — engineers writing clear, intentional
documentation with agent assistance is sufficient to start. But their skills become more
valuable in this model, not less: precision over generality, rationale alongside rules,
explicit anti-patterns. A tech writer contributing to an agentic codebase is directly shaping
the behavior of the agents that work within it.

The [`containers`][containers-repo] repository is developed in active collaboration with Red
Hat tech writers, whose customer-facing product documentation lives in the same repository as
the code. When internal conventions, agent context, and customer-facing documentation share a
single repository, knowledge is preserved across engineers, tech writers, and agents alike —
no silos, no synchronization overhead, no context lost between roles.

### Long-form documentation agent

The long-form documentation part of the software development lifecycle will be driven agentically.
Skills contributed by the documentation team will be encoded in an agent to handle basic
updates and creation of long-form Red Hat documentation about Hummingbird.

### User design agent

The user design part of the software development lifecycle will be driven agentically. Skills
contributed by the UX team will be encoded in an agent covering basic patterns and practices
for reviewing and creating UX-related changes.

[hum-687]: https://redhat.atlassian.net/browse/HUM-687
[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[rpms-repo]: https://gitlab.com/redhat/hummingbird/rpms
[hummingbird-agent-docs]: https://hummingbird-project.io/docs/background/tools/hummingbird-agent-design/
[hummingbird-agent-tree]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-agent
[failure-analysis-workflow]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/hummingbird-agent/workflows/analyze-failures.md
[code-review-workflow]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/hummingbird-agent/workflows/code-review.md
[vrothberg-article-linkedin]: https://www.linkedin.com/pulse/from-pair-programmer-autonomous-agent-how-actually-adopt-rothberg-qdyqe/
[bornet-book]: https://pascalbornet.com/#bestseller
