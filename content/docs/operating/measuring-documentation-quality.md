---
title: Measuring Documentation Quality
weight: 50
aliases: [/l/measuring-documentation-quality]
---

The documentation quality evaluation measures whether public documentation is
complete enough for an LLM with web search to answer questions correctly.  Low
scores indicate documentation gaps; score improvements after content changes
validate the fix.

For config schema, CLI options, and scoring details, see the
[Documentation Quality Evaluation][docs-eval-ref] reference in the tools repo.
For the general evaluation framework, see
[Hummingbird Agent Evals][evals-docs].

## How it works

The evaluation runs in two phases:

1. **Ask** -- multiple LLM configurations answer each golden question using
   web search against public documentation.  Models never see internal
   sources; the test is whether public docs contain the information.
2. **Judge** -- a separate LLM scores each response against expected facts
   and coherence criteria defined in the golden dataset.

Documentation quality is the variable being measured, not model quality.
Models are the instrument -- if scores are low across all models, the
documentation is incomplete.

The evaluation is resume-friendly: existing response and scored files are
skipped on re-run, so interrupted runs can be continued without repeating
expensive model calls.

## Golden dataset

The config and golden dataset live in `evals/docs_eval.yml` in this repo.
The file combines evaluation settings (models, judge, repetitions) with
scoring criteria (questions, expected facts, coherence checks, thresholds).

## Running

### Prerequisites

- GCP Application Default Credentials:

  ```bash
  gcloud auth application-default login
  export GOOGLE_CLOUD_PROJECT=<gcp-project>
  ```

- The [hummingbird-agent][agent-pkg] package installed (`pip install -e .`
  from the `hummingbird-agent/` directory in the tools repo), or
  the container image.

### Via Makefile

```bash
make eval-docs
```

### Manual

```bash
python -m hummingbird_agent.evals.docs_eval.run_eval \
  -c evals/docs_eval.yml
```

## Writing questions

Each question tests a documentation topic, not a model capability.  When
adding or editing questions:

- **Facts should be verifiable from public documentation.**  Avoid opinions
  or information that requires internal knowledge.
- **Assign higher weights to more important facts.**  A weight-2 fact
  contributes twice as much to the score as a weight-1 fact.
- **The coherence criterion checks narrative quality**, not just fact
  presence.  A response that lists correct facts without connecting them
  should score lower on coherence.
- **Calibrate the threshold** by running a baseline: set the threshold
  where current documentation should fail but improved documentation
  should pass.

[docs-eval-ref]: https://hummingbird-project.io/l/agent-docs-eval
[evals-docs]: https://hummingbird-project.io/l/agent-evals
[agent-pkg]: https://gitlab.com/redhat/hummingbird/tools/-/tree/main/hummingbird-agent
