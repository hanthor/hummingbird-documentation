---
title: Managing Konflux Comments
description: >-
  Clean up and manage excessive Konflux comments on merge requests using the comment deletion tool.
weight: 20
---

When Konflux comments become excessive on merge requests, you can clean them up using the provided comment deletion tool.

## Prerequisites

- **COM_GITLAB_TOKEN**: GitLab API token with `api` scope and Maintainer access

## Usage

If Konflux comments become excessive on merge requests, you can clean them up using:

```bash
# Show help for the comment deletion tool
make delete-konflux-comments ARGS="--help"

# Example: Delete comments from a specific merge request
make delete-konflux-comments ARGS="https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/123"

# Example: Delete only failed build/test comments (dry run)
make delete-konflux-comments ARGS="--dry-run --comment-category failed -- https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/123"

# Example: Delete all Konflux comments from a merge request
make delete-konflux-comments ARGS="--all https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/123"
```

## Comment Categories

The tool can target specific types of Konflux comments:

- **failed**: Only comments related to failed builds/tests
- **all**: All Konflux-related comments (use with `--all` flag)

## Safety Features

- **Dry Run Mode**: Use `--dry-run` to preview what would be deleted without actually removing comments
- **Selective Deletion**: Target specific comment categories to avoid removing important information
- **Confirmation**: The tool will show what it plans to delete before taking action

## Examples

```bash
# Set your GitLab token
export COM_GITLAB_TOKEN=your_token_here

# Preview what failed comments would be deleted
make delete-konflux-comments ARGS="--dry-run --comment-category failed -- https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/789"

# Delete only failed build comments
make delete-konflux-comments ARGS="--comment-category failed -- https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/789"

# Delete all Konflux comments (use with caution)
make delete-konflux-comments ARGS="--all https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/789"
```

## When to Use

Consider cleaning up Konflux comments when:

- Merge requests have accumulated many outdated failure comments
- Comments are making it difficult to find relevant discussion
- You want to start fresh after resolving systematic issues
- The comment thread has become cluttered with automated messages

**Note**: Use this tool judiciously, as it permanently removes comments that might contain useful debugging information.

## Related Operations

- [Retrying Konflux Checks](retrying-konflux-checks.md) - Retrigger failed CI pipeline runs
