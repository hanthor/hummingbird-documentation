---
title: Architecture
description: >-
  Template system, multi-architecture support, and Konflux integration details.
weight: 40
---

## Template System

- **Jinja2 Templates**: Each service has a `Containerfile.j2` template in `images/*/`
- **Reusable Macros**: Common patterns defined in `macros/*.yml.j2`
  - `setup_newroot()` - Configures DNF and filesystem
  - `install_newroot()` - Installs packages
  - `cleanup_newroot()` - Cleans up files
  - `final_stage()` - Creates scratch-based final image
- **Variables**: Shared configuration in `images/variables.yml`

## Multi-Architecture Support

As the container images are built for multiple architectures, it becomes
sometimes necessary to refer to architecture names in Containerfiles or
scripts.

There are two different naming schemes in use:

|               | Docker                     | Linux            |
|---------------|----------------------------|------------------|
| Intel         | `amd64`                    | `x86_64`         |
| ARM           | `arm64`                    | `aarch64`        |
| Containerfile | `$TARGETARCH` ARG variable | `$(arch)` output |

When referring to Docker-style architecture names (e.g., in Containerfiles or
for golang builds), use the `$TARGETARCH` ARG variable that is provided by
[buildah][targetarch].

When referring to Linux-style architecture names (e.g., in shell scripts or RPM
builds), use the output of [arch] or [uname -m][uname] commands.

[targetarch]: https://github.com/containers/common/blob/a5ccdae846b629b5ceaefa6ffd5c6511409c3487/docs/Containerfile.5.md#L628
[arch]: https://www.gnu.org/software/coreutils/arch
[uname]: https://www.gnu.org/software/coreutils/uname

## Security Features

- **Non-root users**: All images run as unprivileged users
- **Minimal attack surface**: Scratch-based final images
- **No package managers**: DNF removed from final images
- **Validation**: Automated checks ensure USER directives exist

## Konflux Integration

### GitOps Integration

The `konflux-templates/` directory contains Jinja2 templates for generating
the dynamic Konflux CI/CD resources:

- **konflux-resources.yml.j2**: main Jinja2 template
- **macros/**: individual resource templates, each responsible for a specific
  Konflux resource
- **rendered.yml**: generated output file with all resources

The deployment of these resources depends on the resource type:

- **Components and ImageRepositories** need to be created for Konflux to even
  attempt to build and test the images; as they are mostly immutable once
  created, they are deployed manually either from a merge request or main
  branch pipeline via the `deploy_components_to_konflux` job
- **ReleasePlanAdmissions** need to be updated whenever new images are
  onboarded to be able to publish the images; as they are mutable, they are
  only deployed automatically, either from a main branch pipeline via the
  `deploy_releases_to_konflux` job or a full pipeline in the infrastructure
  repository

### Initial Konflux Cluster Setup

When setting up in a new Konflux cluster:

1. Setup the new cluster in the [infrastructure] repository, mirroring what is
   already done for the old cluster
2. In the Konflux UI, create a new Component for the Application with the same
   name as the git repository
3. Verify the Pipeline as Code `Repository` resource is created
4. Run two successive full pipelines in the [infrastructure] repository, which
   will deploy the resources from [konflux/rendered.yml] and [fix up the owner
   references][konflux-owner-references]
5. Delete the initial Component created from the UI
6. Disable the Konflux build status comments via (might require elevated
   permissions):

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

## Image Documentation

Each image directory must contain a `README.md` file with a high-level
description of the purpose, usage instructions, and compatibility notes with
the official image.

They are built from `README.md.j2` templates with some [standard macros](./macros/readme.yml.j2), using the standard
`make generate-containerfiles` process as above.

At a minimum it should look like this:

```markdown
{{ readme_heading() }}

[CoolProject](https://coolproject.example.com/) is a powerful tool for doing
amazing things.

{{ readme_standard_sections(variants, tags) }}
```

`readme_standard_sections(variants, tags)` expands into `readme_available_tags(variants, tags)` and `readme_compatibility()` sections.
You can amend, replace, or customize these as needed. See e.g. the
[curl README](./images/curl/README.md.j2) for an example of a customized Usage
section.

Whenever a commit lands on the main branch that changes a `README.md` file, the
README content will be automatically pushed to quay.io as the image description
through the `update_quay_description` job in the main pipeline.
