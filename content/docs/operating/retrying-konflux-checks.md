---
title: Retrying Konflux Checks
description: >-
  Automatically retrigger failed Konflux CI checks on merge requests using the retrigger script.
weight: 10
---

When Konflux CI checks fail on merge requests, you can automatically retrigger them using the provided retrigger script.

## Prerequisites

- **GITLAB_TOKEN**: GitLab API access token with `api` scope and Maintainer access

## Usage

For automated retriggers of failed Konflux pipeline runs:

```bash
# Retrigger only failed pipeline runs and wait for them to start
make retrigger-failed-checks ARGS="https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/123"

# Preview what would be retriggered without posting comments
make retrigger-failed-checks ARGS="--dry-run https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/123"
```

## How It Works

The retrigger script will:

1. Extract failed pipeline runs from the commit statuses on the merge request
2. Generate `/retest {pipeline-name}` commands for each failed run
3. Post the retest commands as merge request comments (unless `--dry-run`)
4. Wait for the pipeline runs to start (unless `--dry-run`)

## Manual Retrigger Commands

You can also manually retrigger specific checks using slash commands in merge request comments:

```
/retest {gitlab-ci--default--main-on-pull-request}
```

To retrigger a specific pipeline run as listed in [.tekton/images-on-pull-request.yaml](.tekton/images-on-pull-request.yaml).

See the [Tekton Pipelines as Code documentation][pac-commands] for more details on available commands.

[pac-commands]: https://pipelinesascode.com/docs/guide/gitops_commands/

## Examples

```bash
# Set your GitLab token
export GITLAB_TOKEN=your_token_here

# Retrigger failed checks for a specific merge request
make retrigger-failed-checks ARGS="https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/456"

# Dry run to see what would be retriggered
make retrigger-failed-checks ARGS="--dry-run https://gitlab.com/redhat/hummingbird/containers/-/merge_requests/456"
```

The script will output which pipeline runs are being retriggered and wait for them to start before completing.

## Related Operations

- [Managing Konflux Comments](managing-konflux-comments.md) - Clean up excessive comments on merge requests
