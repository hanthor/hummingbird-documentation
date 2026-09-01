---
title: Agent-Friendly Documentation
description: >-
  How AI agents and LLMs can discover and consume the Project Hummingbird
  documentation site.
weight: 100
aliases: [/l/doc-agent-support]
---

The documentation site provides several features that make it easier for AI
agents and LLMs to discover, index, and consume its content.

## Discovery and access methods

### llms.txt

The site publishes an [llms.txt][llms-txt] file at the root, following the
[llmstxt.org][llmstxt-spec] specification. This file is a Markdown-formatted
index of all documentation pages, grouped by section, with links to each
page's markdown URL. It serves as the primary entry point for agents
discovering the site.

### llms-full.txt

The site also publishes [llms-full.txt][llms-full-txt] -- a full content dump
of all documentation pages in a single file. This is intended for LLMs with
large context windows that want to ingest the entire site in a single request
without crawling individual pages.

Pages whose rendered content exceeds a size threshold (currently 50,000
characters) are replaced with a placeholder that includes the page title,
description, and a link to the individual page's markdown URL for on-demand
fetching. This keeps the file at a manageable size while ensuring no content
is completely inaccessible.

### Per-page markdown output

Every page on the site is available in clean markdown format by appending
`/index.md` to its URL. For example:

- HTML: `https://hummingbird-project.io/docs/contributing/quickstart/`
- Markdown: `https://hummingbird-project.io/docs/contributing/quickstart/index.md`

The markdown output resolves all shortcodes (such as file includes from other
repositories) while preserving the content as markdown rather than converting
to HTML. Each markdown page includes links to both `llms.txt` and
`llms-full.txt` so agents can discover the site-wide indexes from any page.

## Specifications and tools

The site aims to follow the emerging standards for agent-friendly documentation:

- [llmstxt.org][llmstxt-spec] -- the llms.txt specification
- [Agent-Friendly Documentation Spec][afdocs-spec] -- broader specification
  for documentation sites that serve AI agents
- [AFDocs][afdocs-tool] -- scoring tool that evaluates a site's compliance
  with the Agent-Friendly Documentation Spec

## Planned features

### Content negotiation (HUM-6570)

A CloudFront content-negotiation layer will allow agents to request
`text/markdown` via the HTTP `Accept` header and receive the markdown variant
without knowing the `/index.md` URL convention. This is a requirement of the
Agent-Friendly Documentation Spec.

### HTML llms-directive (HUM-6571)

A Docsy upgrade to v0.17.0 will embed a pointer to `llms.txt` inside the HTML
`<body>` of every page, so agents landing on any HTML page can discover the
LLMS index without prior knowledge of the site structure.

## Documentation quality evaluation (HUM-6575)

A [promptfoo][promptfoo]-based evaluation harness will measure how accurately
LLMs can answer questions about Hummingbird using the published documentation.
This provides a feedback loop for identifying documentation pages that need
improvement for agent consumption.

[llms-txt]: /llms.txt
[llms-full-txt]: /llms-full.txt
[llmstxt-spec]: https://llmstxt.org/
[afdocs-spec]: https://agentdocsspec.com/
[afdocs-tool]: https://afdocs.dev/
[promptfoo]: https://github.com/promptfoo/promptfoo
