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

The target state is a delivery pipeline driven by agents at every stage — with humans engaged
where their judgment is needed, not where their time is simply being consumed by routine work.

A customer — a product team, a business unit, an external user — submits a request: a new
container image, a new RPM, a change to an existing component. Agents take it from there:

**Analysis.** A **product management agent** refines the raw request into a well-scoped,
actionable specification — resolving ambiguities, mapping the request to existing components
and conventions, and producing a clear definition of what needs to be built. This is the work
that normally sits in a product manager's queue: assessing feasibility, evaluating software
licenses, setting priorities, and determining whether and how a request fits the product.
Some of these decisions carry enough complexity or risk that human review is warranted before
implementation begins — the agent surfaces the relevant context and flags those cases rather
than proceeding blindly.

**Implementation.** An engineering agent takes that specification and implements it: writing
the configuration, code, or package definitions, running validation, and opening a merge
request with a complete description of what was done and why. This is the work that normally
sits in an engineering backlog.

The merge request is then reviewed by automated checks, including the production
[code review agent][code-review-workflow], and a human engineer who makes the final call. No
agent-produced code is merged without human review — the human is not eliminated, but elevated
to the role where judgment actually matters.

The goal is not to remove humans from the process — it is to remove the parts of the process
that do not need them. Intake, triage, analysis, scoping, implementation: work that previously
moved through queues over days now flows through agents in minutes, with humans engaged at the
points where their input genuinely changes the outcome.

## The Strategy

Not all work is the same. The strategy distinguishes between two categories:

**Rule-based automation** handles changes that are deterministic and well-understood: updating
an RPM to a new upstream version, syncing a package lockfile, rebuilding an image after a
dependency change. These changes follow documented rules and carry no ambiguity. With proper
CI/CD pipelines and testing in place, they can be — and should be — **merged automatically
without human review**. No ticket, no approval, no delay.

**Agentic AI is the default answer for everything that has historically required a human.**
If a task previously needed someone to pick it up, think through it, and act on it, that is
exactly where agents belong:

- A developer co-programming with an agent to implement a feature or work through a complex
  change — the agent as a capable collaborator, not just an autocomplete tool.
- Agents running autonomously to review merge requests, catch issues, and propose concrete
  fixes — reducing review burden without removing human judgment from the final call.
- Agents debugging CI failures, analyzing root causes, and surfacing actionable findings
  directly in the merge request where engineers are already working.
- Agents implementing well-scoped tasks end-to-end — opening the merge request, responding
  to feedback, iterating until the work is ready to ship.

The dividing line is not complexity — it is determinism. If the correct output can be derived
from rules, automate it fully. If it requires judgment, drive it agentically. The goal is to
automate as much as possible, reducing the time humans spend on work that does not require
their judgment.

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

## Agents in Production Today

Two agents are running in production, built on the [Hummingbird Agent][hummingbird-agent-docs]
platform. Together they have contributed to thousands of commits across the
[`containers`][containers-repo] and [`rpms`][rpms-repo] repositories over the past eight
months — at a velocity that would be impossible to sustain manually.

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

[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[rpms-repo]: https://gitlab.com/redhat/hummingbird/rpms
[hummingbird-agent-docs]: https://hummingbird-project.io/docs/background/tools/hummingbird-agent-design/
[hummingbird-agent-tree]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-agent
[failure-analysis-workflow]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/hummingbird-agent/workflows/analyze-failures.md
[code-review-workflow]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/hummingbird-agent/workflows/code-review.md
[vrothberg-article-linkedin]: https://www.linkedin.com/pulse/from-pair-programmer-autonomous-agent-how-actually-adopt-rothberg-qdyqe/
[bornet-book]: https://www.pascalbornet.com/book
