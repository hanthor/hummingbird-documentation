---
title: Adding New Images
description: Step-by-step guide for adding new container images to the project
weight: 20
aliases: [/l/adding-images]
---

Follow these steps to add a new container image to the project.

## 1. Create Image Directory

Create a directory for the new image:

```bash
mkdir images/your-service
```

## 2. Copy Base Templates

Copy the template files:

```bash
cp images/properties.yml images/your-service/properties.yml
cp images/Containerfile.j2 images/your-service/Containerfile.j2
```

## 3. Configure properties.yml

Edit `images/your-service/properties.yml` to configure:

- **Variants**: Define variants (default: `[default, builder]`)
- **Packages**: List RPM packages needed in `rpm_packages.all`
- **Main package**: Set `main_package` for version labeling
- **Tags**: Configure image tags

Example minimal configuration:

```yaml
---
rpm_packages:
  all:
    - coreutils-single
    - your-main-package

main_package: your-main-package

tags:
  - value: latest
```

See the [Image Configuration Reference](image-configuration-reference.md) for complete
`properties.yml` options.

## 4. Customize Containerfile Template

Edit `images/your-service/Containerfile.j2`:

- Add service-specific configuration
- Set the appropriate user:
  - `{{ set_default_user }}` for non-root (recommended)
  - `{{ set_root_user }}` if root is required
- Configure exposed ports, volumes, and entrypoint

The template automatically includes packages from `properties.yml` via the
`{{ main_packages_arg() }}` macro.

### Multi-Architecture Support

When Containerfiles or build scripts need to reference the target architecture (e.g., downloading
architecture-specific binaries), use the correct naming convention for each context.

|               | Docker                     | Linux            |
|---------------|----------------------------|------------------|
| Intel         | `amd64`                    | `x86_64`         |
| ARM           | `arm64`                    | `aarch64`        |
| Containerfile | `$TARGETARCH` ARG variable | `$(arch)` output |

- **In Containerfiles or Go builds**: Use the `$TARGETARCH` ARG variable provided by
  [buildah][targetarch] (values: `amd64`, `arm64`)
- **In shell scripts or RPM builds**: Use the [arch] or [uname -m][uname] commands (values:
  `x86_64`, `aarch64`)

[targetarch]: https://github.com/containers/common/blob/a5ccdae846b629b5ceaefa6ffd5c6511409c3487/docs/Containerfile.5.md#L628
[arch]: https://www.gnu.org/software/coreutils/arch
[uname]: https://www.gnu.org/software/coreutils/uname

## 5. Add Integration Tests

Create `images/your-service/tests-container.yml` with basic tests:

```yaml
---
version-check:
  command: |
    "${TEST_ENGINE}" run --rm "${TEST_IMAGE}" your-service --version
```

See the [Testing Guide](testing-images.md) for how to write and run tests.

## 6. Add Image Documentation

Create `images/your-service/README.md.j2` with a high-level description, usage instructions, and
compatibility notes:

```markdown
{{ readme_heading() }}

[YourService](https://yourservice.example.com/) is a tool for...

{{ readme_standard_sections(variants, tags) }}
```

The `readme_standard_sections()` macro automatically generates sections for available tags and
compatibility information.

## 7. Follow Standard Workflow

Follow the standard contribution workflow from the [Development Workflow guide](development-workflow.md):

- Generate files (`make generate ARGS="your-service"`)
- Build locally (`ci/build_images.sh your-service`)
- Test locally (`ci/run_tests_container.sh your-service`)
- Run linters (`make check`)
- Commit and push changes
- Open a merge request
- Wait for CI pipeline

## 8. Deploy Konflux Resources and Trigger Testing

On the merge request pipeline, click the play button next to the `deploy_resources_to_konflux` job
to deploy the Konflux resources for the new image. After the job completes, add a `/retest` comment
to the merge request to trigger the CI pipeline for the newly added image.

## Next Steps

- [Testing Guide](testing-images.md) - How to run and write tests
- [Image Configuration Reference](image-configuration-reference.md) - Complete `properties.yml` reference
- [Image Pipeline](../background/image-pipeline.md) - How the complete pipeline works
