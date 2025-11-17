# Documentation Guidelines

## Link Format

Always use file-based links in Markdown that Hugo will rewrite:

### ✅ Good: File-based links

```markdown
- [Quickstart Guide](quickstart.md)
- [Adding Images](adding-images.md)
- [Operating section](../operating/_index.md)
```

### ❌ Bad: Directory-based links

```markdown
- [Quickstart Guide](quickstart/)
- [Adding Images](adding-images/)
- [Operating section](/docs/operating/)
```

**Why**: Hugo automatically rewrites `.md` file links to the appropriate URLs
based on the site configuration. Using file-based links ensures consistency and
makes it clear which file is being referenced.

### Reference Style Links

Always use reference style links for better readability and maintainability:

### ✅ Good: Reference style links

```markdown
See the [Image Configuration Reference][image-config] for per-image settings
and [Global Variables Reference][global-vars] for project-wide configuration.

For more details, see [default_variant_repos documentation][default-variant-repos].

[image-config]: ../contributing/image-configuration-reference.md
[global-vars]: ../background/global-variables-reference.md
[default-variant-repos]: ../background/global-variables-reference.md#default_variant_repos
```

### ❌ Bad: Inline links

```markdown
See the [Image Configuration
Reference](../contributing/image-configuration-reference.md) for per-image
settings and [Global Variables
Reference](../background/global-variables-reference.md) for project-wide
configuration.
```

**Why**: Reference style links separate content from URLs, making the text more
readable and easier to maintain. Link definitions at the end act as a table of
contents for external references. This is especially important for:

- Long URLs or URLs with anchors
- Links that appear multiple times
- "See Also" and "Next Steps" sections
- Any page with multiple cross-references

### Stable Link Aliases

For pages that need stable URLs (e.g., referenced from external repositories),
add an `aliases` field to the frontmatter:

```markdown
---
title: Testing Guide
aliases: [/l/testing-images]
---
```

**Rules for aliases:**

- Use the `/l/` prefix for stable links
- Use flat, non-nested paths (no slashes in the alias name)
- Use descriptive names that won't change

✅ Good:

```markdown
aliases: [/l/testing-images]
aliases: [/l/adding-images]
aliases: [/l/development-workflow]
```

❌ Bad:

```markdown
aliases: [/l/contributing/testing]  # Nested path
aliases: [/l/test]                   # Too generic
```

**Why**: Flat aliases are simpler to manage and less likely to conflict. The
`/l/` prefix clearly indicates these are stable links meant for external
references.

### Cross-References and Next Steps

Use "Next Steps" sections at the end of pages to guide readers to related
content. Follow these principles:

**Link to logical next actions:**

✅ Good:

- How-to guide → Related how-to guides, relevant reference docs
- Reference doc → Related reference docs, how-to guides that use it
- Explanation → How-to guides for practical application

❌ Bad:

- Linking to the same pages from every document
- Circular references without adding value
- Links to unrelated content

**Example for a how-to guide:**

```markdown
## Next Steps

- [Testing Guide](testing.md) - How to test your changes
- [Image Configuration Reference](image-configuration-reference.md) - Complete
  configuration reference
```

**Example for a reference document:**

```markdown
## Next Steps

- [Adding Images](adding-images.md) - Step-by-step guide using this configuration
- [Architecture](architecture.md) - Understanding the template system
```

**Why**: Next Steps should create a natural learning path, not just list
related pages. Each link should represent a logical next action for the reader.

## Documentation Structure

Follow these principles when organizing documentation:

### Documentation Types

1. **Tutorials** - Learning-oriented, gets someone started
2. **How-to Guides** - Task-oriented, solves a specific problem
3. **Reference** - Information-oriented, describes the system
4. **Explanation** - Understanding-oriented, clarifies concepts

### Title Style by Document Type

**How-to Guides (Procedural)**: Use gerund form (verb-ing)

✅ Good:

- "Setting Up a Konflux Cluster"
- "Adding New Images"
- "Testing Images Locally"

❌ Bad:

- "Konflux Cluster Setup" (noun phrase)
- "Set Up a Konflux Cluster" (imperative)
- "Add New Images" (imperative)

**Reference Documentation**: Use noun phrases

✅ Good:

- "Architecture"
- "Image Configuration Reference"
- "Test Configuration Reference"

❌ Bad:

- "Configuring Images" (gerund)
- "Configure Images" (imperative)

**Why**: Gerunds emphasize the activity/process (appropriate for how-to
guides), while noun phrases emphasize the subject matter (appropriate for
reference documentation).

### Minimalism

- Each page should have one clear purpose
- Use progressive disclosure: link to details instead of including everything
- Keep quickstart guides short and actionable
- Move detailed content to reference pages

### Audience Segmentation

Organize content by audience:

- **New Contributors** - Quickstart, basic workflow
- **Image Contributors** - How-to guides for adding/modifying images
- **Infrastructure Operators** - Konflux, CI/CD operations
- **Advanced Developers** - Architecture, internals

### Page Weight Management

Hugo uses the `weight` field in frontmatter to control page ordering. Use
increments of 5 or 10 to allow inserting pages later.

**For sections with inherent order** (e.g., Getting Started → Guides → Reference):

```markdown
---
title: Quickstart Guide
weight: 5
---

---
title: Development Workflow
weight: 10
---

---
title: Adding Images
weight: 20
---

---
title: Image Configuration Reference
weight: 25
---
```

**For sections without inherent order** (e.g., infrastructure services):

Sort alphabetically by title and add a comment:

```markdown
---
title: "GitLab"
weight: 20  # Keep pages sorted alphabetically by title; use increments of 10
---

---
title: "Konflux"
weight: 50  # Keep pages sorted alphabetically by title; use increments of 10
---

---
title: "Quay.io"
weight: 60  # Keep pages sorted alphabetically by title; use increments of 10
---
```

**Why**: Consistent weight increments make it easy to insert new pages without
renumbering everything. Alphabetical sorting (where appropriate) makes pages
predictable and easy to find.

## Writing Style

Avoid using personal pronouns in documentation:

### ❌ Bad: Using "we/you/the team"

```markdown
When you open a merge request, we automatically run tests.
The team maintains these tests.
You should check the results.
```

### ✅ Good: Impersonal, direct style

```markdown
When a merge request is opened, tests run automatically.
Tests are maintained in the infrastructure repository.
Check the results in the pipeline view.
```

**Benefits:**

- More professional and authoritative tone
- Avoids assumptions about team structure
- Clearer for international audiences
- Focuses on actions and systems, not people

## Markdown Formatting

### Line Wrapping

Wrap lines at 100 characters for better readability in text editors and diffs.

### ✅ Good: Lines wrapped at 100 characters

```markdown
On the merge request pipeline, click the play button next to the `deploy_resources_to_konflux` job
to deploy the Konflux resources for the new image. After the job completes, add a `/retest` comment
to the merge request to trigger the CI pipeline for the newly added image.
```

### ❌ Bad: Long unwrapped lines

```markdown
On the merge request pipeline, click the play button next to the `deploy_resources_to_konflux` job to deploy the Konflux resources for the new image. After the job completes, add a `/retest` comment to the merge request to trigger the CI pipeline for the newly added image.
```

**Why**: Wrapped lines are easier to read in text editors, produce cleaner diffs, and work better
with version control systems.

### Frontmatter and Headings

When a markdown file has Hugo frontmatter with a `title` field, do not include an H1 (`#`) heading
in the markdown content:

### ❌ Bad: Duplicate H1 headings

```markdown
---
title: Quickstart Guide
---

# Quickstart Guide

Content starts here...
```

### ✅ Good: Title only in frontmatter

```markdown
---
title: Quickstart Guide
---

Content starts here...

## First Section
```

**Why**: Hugo automatically generates the H1 heading from the frontmatter
`title`. Including another H1 in the markdown creates duplicate top-level
headings, which is semantically incorrect and confusing for readers.

### Index Pages and Sub-page Listing

By default, Hugo/Docsy `_index.md` files automatically list all sub-pages. To
disable this and provide a custom manual list, add `no_list: true` to the
frontmatter:

### ✅ Good: Manual list with no_list

```markdown
---
title: Contributing
no_list: true
---

Custom introduction text.

## Getting Started

- [Quickstart](quickstart.md) - Quick intro
- [Workflow](workflow.md) - Detailed workflow

## Advanced

- [Architecture](architecture.md) - System internals
```

### ❌ Bad: Manual list without no_list

```markdown
---
title: Contributing
---

Custom introduction text.

## Getting Started

- [Quickstart](quickstart.md)
...
```

**Why**: Without `no_list: true`, both the manual list and the automatic
*sub-page listing will appear, creating duplication. Only use `no_list: true`
*when providing a manual list that adds value through grouping or custom
*organization.

**When to use manual lists:**

- When sub-pages need logical grouping (e.g., "Getting Started" vs "Advanced")
- When sub-pages need custom ordering beyond Hugo's weight system
- When sub-pages need custom descriptions different from their frontmatter

**When NOT to use manual lists:**

- Simple flat lists where automatic listing works fine
- When sub-pages already have good descriptions in frontmatter

### Table Alignment

Always use aligned columns in markdown tables for better readability. Keep each
table cell on a single line, even if it exceeds 100 characters.

### ✅ Good: Aligned columns, single-line cells

```markdown
| Variable        | Description                                           |
|-----------------|-------------------------------------------------------|
| `TEST_IMAGE`    | The container image being tested                      |
| `TEST_ENGINE`   | Container engine to use (`podman` or `docker`)        |
| `TEST_VERBOSE`  | Show output for passing tests (`true` or `false`)     |
```

### ❌ Bad: Unaligned columns

```markdown
| Variable | Description |
|----------|-------------|
| `TEST_IMAGE` | The container image being tested |
| `TEST_ENGINE` | Container engine (`podman` or `docker`) |
```

### ❌ Bad: Multi-line cells

```markdown
| Variable              | Default | Description                                                    |
|-----------------------|---------|----------------------------------------------------------------|
| `PULL`                | `newer` | Image pull policy for gitlab-ci container. Options: `never`,   |
|                       |         | `newer`, `always`, `missing`.                                  |
```

**Why**: In Markdown, each line in a table is a separate row. Multi-line cells
create multiple table rows, breaking the table structure create multiple table
rows, breaking the table structure. The 100-character line wrapping guideline
does not apply to table cells.

## Git Workflow

### Splitting Commits

To split a commit into multiple commits, prefer `git reset` over `git rebase`:

✅ **Good: Using git reset**

```bash
# Reset the last commit, keeping changes unstaged
git reset HEAD~1

# Stage and commit files individually
git add file1.md
git commit -m "docs: update file1"

git add file2.md
git commit -m "docs: update file2"
```

❌ **Bad: Using git rebase for simple splits**

```bash
git rebase -i HEAD~1
# Then manually editing and splitting...
```

**Why**: `git reset` is simpler, safer, and more straightforward for splitting
commits. `git rebase` is complex, error-prone, and difficult to use correctly
(especially for automated agents). Avoid it unless absolutely necessary for
complex history rewriting.

## Linting

Run linters on file changes:

```bash
make check
```
