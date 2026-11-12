---
title: Agentic SDLC
linktitle: Agentic SDLC
description: How Project Hummingbird uses agentic AI to drive velocity across the software development lifecycle.
weight: 50
aliases: [/l/agentic-sdlc]
---

Project Hummingbird's core mission is velocity: shipping RPM updates, CVE fixes, and new
container images as fast as possible. The pipeline already delivers at a scale unprecedented
within Red Hat — consistently over 1,000 automated commits per week across the
[`containers`][containers-repo] and [`rpms`][rpms-repo] repositories, a throughput that would
be impossible to sustain manually — work that in most Linux distributions is still performed
manually by dedicated teams. Managing 400+ packages and 1,750+ image builds with a
24-hour security SLO, that pipeline is not a nice-to-have — it is what makes the project
viable with a small team.

The pipeline solves throughput. What it does not solve is the full software development
lifecycle: assessing what to build, implementing it, documenting it, testing it, reviewing UX,
coordinating releases. For a small team maintaining hundreds of containers and building an
entire OS, staffing all of those functions manually does not scale — and agentic AI is what
changes that equation. Where rule-based automation handles the deterministic, agents take on
everything that has historically required a human to pick up, think through, and act on.
Hummingbird is building toward becoming an open source reference implementation for responsible
agentic AI in software engineering: demonstrating through production use, not promises, that
this kind of automation can be adopted incrementally and grounded in engineering discipline.

## The Agentic SDLC Vision

The target state is a development pipeline driven by agents at every stage — with humans
engaged where their judgment is needed, not where their time is consumed by routine work.

Every change flows through the same lifecycle:

**1. Request.** A customer, product team, or automated trigger submits a change: a new
container image, an RPM update, a feature request, a bug fix.

**2. Analysis.** A **product management agent** assesses the request — evaluating feasibility,
priority, and fit against existing components and conventions. For
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
  historically required a human to pick it up, think through it, and act on it.
- Specialist agents contribute alongside: a **tech writer agent** drafts or updates the
  documentation and long-form Red Hat product content; a **testing agent** generates or extends
  tests; and a **user design agent** applies UX patterns and practices to any interface-related
  changes.

**4. Review.** Automated agents check for policy compliance and code quality, including the
production [code review agent][code-review-workflow]. The same agent capabilities that
contribute during implementation also apply here: a **tech writer agent** reviews documentation
changes for clarity and correctness; a **testing agent** reviews test coverage and flags gaps;
and a **user design agent** reviews UX-related changes against established patterns. A human
engineer makes the final call on all of it. No agent-produced work is merged without human
approval — the human is not eliminated, but elevated to the role where judgment actually
matters.

**5. Merge.** The change ships.

The goal is maximum automation, pursued pragmatically rather than dogmatically — the right
tool for each kind of work. Where agentic AI excels is in the space just before human judgment
is required: gathering context, surfacing options, resolving the routine, so that when a human
does engage, the decision in front of them is sharp, informed, and fast.

## Responsible AI

Agent-produced code and decisions require human approval before merge. This is not a temporary
constraint — it is a design principle. Humans may stay in the loop to steer or closely supervise
complex work when that helps, but the standing requirement is approval — not constant
supervision of every agent run. The feedback between human judgment and agent behavior is what
keeps the system trustworthy over time.

The high-velocity automated pipeline — over 1,000 commits per week — operates through
rule-based automation and does not involve agents; no human review is required there. The
failure analysis agent does run at high volume — triggering on every pipeline, build, or test
failure — but it produces analysis and comments, not code changes requiring approval. That
alone saves hundreds of minutes per week of manual log triage. Agent work that requires human
approval is scoped to SDLC tasks: feature requests, documentation, code review — a much lower
volume where the requirement is entirely manageable.

### Security

Agents run in containers — locally via Podman, in production on OpenShift. This is not a novel
security model: it is the same approach the industry has long used for untrusted code, applied
consistently. The Hummingbird agent platform is architecturally designed to ensure agents have
no access to secrets or tokens. That single constraint effectively neutralizes prompt injection
as a threat: an agent that cannot access credentials or act on external systems is, in practice,
just another contributor — and the review process treats it as such. The same gatekeeping that
applies to any third-party contribution applies to agent-produced work. The worst-case outcome
is a low-quality merge request — and that is precisely what the review process, including the
review agents themselves, is designed to catch.

### Learning from Feedback

Agents learn from feedback — and this is already working in production. When a reviewer
comments on an agent-produced merge request, the agent reads those conversations, incorporates
the feedback, and updates its work. It avoids re-raising issues already addressed and respects
when a developer has explained an intentional design choice. That feedback is also preserved —
stored so that future agent runs can draw on it, improving with each iteration rather than
repeating the same mistakes — an approach grounded in the frameworks established in Pascal
Bornet's [*Agentic Artificial Intelligence*][bornet-book].

## From Pair Programmer to Autonomous Agent

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
on well-defined tasks. The next section describes what that looks like in practice for
Hummingbird today.

An agent running autonomously in production is not fundamentally different from a developer
running an agent during pair programming. The same agent, the same context, the same
documentation — the difference is who initiates the run and how much human supervision
follows. If an agent consistently does good work when a developer is in the loop,
that is a strong signal the project is ready to let it operate more independently. The quality
of pair programming performance is the leading indicator for autonomous deployment readiness.
Trust is built incrementally, one well-handled task at a time.

See [From Pair Programmer to Autonomous Agent][vrothberg-article-linkedin] by Valentin
Rothberg for the full treatment.

## Documentation as Infrastructure

### Writing Documentation with Agents

In an agentic system, documentation is infrastructure — the primary interface between the
team and its agents, and the quality of what an agent produces is bounded by the quality of
what it can read. That makes writing documentation with agent assistance not a separate task
but a natural extension of the work: the same agent that helps an engineer write and review
code can help write the documentation for it — capturing decisions, explaining rationale,
drafting contribution guides. This is not a shortcut; it is the same pair-programming model
applied to a different kind of output. This is how Hummingbird built its documentation from
the start: engineers worked alongside agents to draft and improve it in the same way they
wrote code — iteratively, collaboratively, with humans in the lead. The result is a virtuous
cycle: better docs make agents more capable,
and more capable agents help produce better docs.

Tech writers are not a prerequisite — engineers writing clear, intentional documentation with
agent assistance is sufficient to start. But their skills become more valuable in this model,
not less: precision over generality, rationale alongside rules, explicit anti-patterns. A tech
writer contributing to an agentic codebase is directly shaping the behavior of the agents
that work within it.

In Hummingbird, this is not theoretical. The [`containers`][containers-repo] repository is
developed in active collaboration with Red Hat tech writers, whose customer-facing product
documentation lives in the same repository as the code — keeping internal conventions, agent
context, and customer-facing content in one place, shared across engineers, tech writers, and
agents alike.

### Knowledge Transfer Across Teams

The same principle — knowledge encoded in markdown, readable by humans and agents alike —
also answers a broader question: how does one team's expertise become available to agents
maintained by another? The answer is the same as everything else in this system —
markdown. A UX team encodes their patterns and design practices in a skills file; the user
design agent picks it up. The documentation team maintains their style guide, standards, and
best practices — including Red Hat's documentation guidelines — encoded once and available to
every agent that produces or reviews written content. No code changes, no integrations, no
handoff meetings. Any team can contribute their domain knowledge to the agentic system simply
by writing it down in a form that both humans and agents can read. The markdown file is the
interface between teams.

## Agents in Production Today

Two agents are running in production today, built on the
[Hummingbird Agent][hummingbird-agent-docs] platform. They operate on every merge request
across the [`containers`][containers-repo] and [`rpms`][rpms-repo] repositories, which
together see over 1,000 automated commits per week — a throughput that would be impossible to
review and maintain manually without agent assistance.

More agents are under active development in parallel, with production deployment planned after
Red Hat Summit 2026 — likely by end of Q2. One example is the **merge conflict agent** — which
will automatically resolve merge conflicts that arise during automated RPM updates. The full
roadmap is tracked in the [HUM-687 epic][hum-687].

### Failure Analysis Agent

When a merge request pipeline fails, this agent automatically investigates and posts its
findings directly on the merge request. It pulls data from multiple sources — GitLab CI job
logs, Konflux build and test pipeline runs, Testing Farm test results — and correlates them
to identify root causes. Where the same underlying issue causes multiple failures across
different images or architectures, it groups them so engineers see patterns rather than an
overwhelming list of individual failures. Every finding includes links to the specific logs
and artifacts so engineers can dig deeper without having to hunt.

What previously required clicking through multiple levels of web UI, downloading logs, and
working through thousands of lines of output to find a single root cause now happens
automatically. It is not rocket science — but it is some of the most time-consuming and
draining work an engineer can be asked to do repeatedly.

*Workflow definition: [`analyze-failures.md`][failure-analysis-workflow]*

### Code Review Agent

When a merge request is opened, this agent performs a technical code review with the
priorities of a senior engineer: security first, then correctness, then performance, then
maintainability. It provides specific line references and concrete code examples for every
issue it raises — not vague suggestions, but actual fixes. It reads prior review discussions
before posting, avoids re-raising issues already addressed, and respects when a developer has
explained an intentional design choice.

The result is consistent, high-quality review coverage on every merge request, with human
reviewers free to focus on the issues that genuinely need their judgment.

The team is already pleased with the quality of the reviews — and this is only the beginning.
A false positive costs nothing: a human reviewer reads it, disagrees, and moves on. The design
ensures that bad agent output has no blast radius. And as human reviewers comment on
agent-produced work, the agent learns and incorporates that feedback — improving with every
iteration.

*Workflow definition: [`code-review.md`][code-review-workflow]*

The near-term impact is measured in cycle time. A feature request that previously took weeks
to move from intake through product assessment, implementation, documentation, and review can
be compressed to days, sometimes hours. That changes what a small team can realistically take
on. The longer-term picture is equally straightforward: the system already delivers value
today. If agents continue to improve, Hummingbird benefits more. If they plateau, the team
continues to operate at a level that would otherwise require far more people. The
infrastructure built now is not a bet on a technology that might not materialize — it is an
investment that is already paying off, with optionality for more.

[hum-687]: https://redhat.atlassian.net/browse/HUM-687
[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[rpms-repo]: https://gitlab.com/redhat/hummingbird/rpms
[hummingbird-agent-docs]: https://hummingbird-project.io/l/agent-design
[failure-analysis-workflow]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/hummingbird-agent/workflows/analyze-failures.md
[code-review-workflow]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/hummingbird-agent/workflows/code-review.md
[vrothberg-article-linkedin]: https://www.linkedin.com/pulse/from-pair-programmer-autonomous-agent-how-actually-adopt-rothberg-qdyqe/
[bornet-book]: https://pascalbornet.com/#bestseller
