# Agentic SDLC

Project Hummingbird's core mission is velocity: shipping RPM updates, CVE fixes, and new
container images as fast as possible. Managing 400+ packages and 1,750+ image builds with a
24-hour security SLA makes automation not a nice-to-have, but the only viable path.

Hummingbird is Red Hat's reference implementation for responsible agentic AI in software
engineering — not a pilot program, but a production system built incrementally and grounded
in engineering discipline.

## The Vision: A Lights-Out Factory

The target state is a factory that runs without human intervention from the moment a request
arrives to the moment a merge request is ready for review.

A customer — a product team, a business unit, an external user — submits a request: a new
container image, a new RPM, a change to an existing component. Two agents take it from there:

**Analysis.** A product management agent refines the raw request into a well-scoped,
actionable specification — resolving ambiguities, mapping the request to existing components
and conventions, and producing a clear definition of what needs to be built. This is the work
that normally sits in a product manager's queue.

**Implementation.** An engineering agent takes that specification and implements it: writing
the configuration, code, or package definitions, running validation, and opening a merge
request with a complete description of what was done and why. This is the work that normally
sits in an engineering backlog.

The merge request is then reviewed by automated agents and a human engineer who makes the
final call. No agent-produced code is merged without human review — the human is not
eliminated, but elevated to the role where judgment actually matters.

What changes is everything that came before: intake, analysis, scoping, implementation. Work
that previously moved through queues over days now flows through agents in minutes.

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
eliminate the category of "work sitting in a queue waiting for a human to look at it."

## Responsible AI

Agent-produced code and decisions require a human in the loop. This is not a temporary
constraint — it is a design principle. The feedback between human judgment and agent behavior
is what keeps the system trustworthy over time.

This has a specific architectural implication: agents must learn from feedback. When a reviewer
comments on an agent-produced merge request, the agent incorporates that feedback and updates
its work. That feedback is also preserved — stored so that future agent runs can draw on it,
improving with each iteration rather than repeating the same mistakes.

This approach follows the frameworks established in Pascal Bornet's
[*Agentic Artificial Intelligence*][bornet-book].

## Agents in Production Today

Two agents are running in production, built on the [hummingbird-agent][hummingbird-agent-docs]
platform. Together they have contributed to thousands of commits across the
[`containers`][containers-repo] and [`rpms`][rpms-repo] repositories over the past eight
months — at a velocity that would be impossible to sustain manually.

### Failure Analysis Agent

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
documentation quality. Every repository carries an `AGENTS.md` — a reference written for
both human contributors and AI agents — with conventions and an operations index mapping
common tasks to their documentation. An agent with good documentation reasons from the same
foundation as the team; an agent without it guesses.

**Phase 3 — Agents in production.** With the foundation in place, agents move into the
critical path: first as reviewers proposing concrete changes, then as autonomous contributors
on well-defined tasks.

See [From Pair Programmer to Autonomous Agent][vrothberg-article-linkedin] by Valentin
Rothberg for the full treatment.

## Documentation and Tech Writers

In an agentic system, documentation is infrastructure. It is the primary interface between
the team and its agents, and the quality of what an agent produces is bounded by the quality
of what it can read.

Tech writers are not a prerequisite for this — engineers writing clear, intentional
documentation is sufficient to start. But their skills become more valuable in this model,
not less: precision over generality, rationale alongside rules, explicit anti-patterns. A
tech writer contributing to an agentic codebase is directly shaping the behavior of the
agents that work within it.

In Hummingbird, agents were used to draft and improve documentation throughout the project —
the documentation work itself as a demonstration of the model. The [`containers`][containers-repo]
repository is also developed in active collaboration with Red Hat tech writers, whose
customer-facing product documentation lives in the same repository as the code. When internal
conventions, agent context, and customer-facing documentation share a single repository,
knowledge is preserved across engineers, tech writers, and agents alike — no silos, no
synchronization overhead, no context lost between roles.

[containers-repo]: https://gitlab.com/redhat/hummingbird/containers
[rpms-repo]: https://gitlab.com/redhat/hummingbird/rpms
[hummingbird-agent-docs]: https://gitlab.com/redhat/hummingbird/tools/-/blob/main/documentation/hummingbird-agent.md
[vrothberg-article-linkedin]: https://www.linkedin.com/pulse/from-pair-programmer-autonomous-agent-how-actually-adopt-rothberg-qdyqe/
[bornet-book]: https://www.pascalbornet.com/book
