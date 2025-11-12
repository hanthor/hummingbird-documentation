---
title: Setting Up a Konflux Cluster
description: How to set up a new Konflux cluster
weight: 30  # Keep pages sorted alphabetically by title; use increments of 10
---

## Setting Up the Cluster

1. Set up the new cluster in the [infrastructure] repository, mirroring the existing cluster
   configuration
2. In the Konflux UI, create a new Component for the Application with the same name as the git
   repository
3. Verify the Pipeline as Code `Repository` resource is created
4. Run two successive full pipelines in the [infrastructure] repository to deploy resources from
   [konflux/rendered.yml] and [fix up owner references][konflux-owner-references]
5. Delete the initial Component created from the UI
6. Disable Konflux build status comments (requires elevated permissions):

```bash
kubectl patch \
  --namespace hummingbird-tenant \
  repository REPOSITORY_NAME \
  --type merge \
  --patch '{"spec":{"settings":{"gitlab":{"comment_strategy":"disable_all"}}}}'
```

[konflux-owner-references]: https://gitlab.com/redhat/hummingbird/infrastructure/-/tree/main/konflux-owner-references
[infrastructure]: https://gitlab.com/redhat/hummingbird/infrastructure
[konflux/rendered.yml]: https://gitlab.com/redhat/hummingbird/containers/-/blob/main/konflux-templates/rendered.yml

## Next Steps

- [Retrying Konflux Checks](retrying-konflux-checks.md) - Retrigger failed CI pipeline runs
- [Managing Konflux Comments](managing-konflux-comments.md) - Clean up excessive comments
