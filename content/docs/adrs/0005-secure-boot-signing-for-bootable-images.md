---
title: "ADR-0005: Secure Boot signing for bootable images"
weight: 50
aliases: [/l/adr-0005]
---

- **Status:** Proposed
- **Date:** 2026-11-20
- **Author:** James Reilly (Project Bluefin)
- **Jira:** Not yet assigned (external proposal)

## Context

`os-minimal` boots on Fedora's Secure Boot chain. Its lockfile takes `shim-x64`,
`grub2-efi-x64` and `kernel` from `fedora-44-updates`, and its README says that
"Hummingbird currently focuses on the userspace, while Fedora complements the
kernel and lower-level stack". The signatures in a current image match that:

| Component                              | Built by    | Signature on the EFI binary                      |
| -------------------------------------- | ----------- | ------------------------------------------------ |
| `shim-x64` 16.1-7                      | Fedora      | Microsoft Corporation UEFI CA 2011               |
| `grub2-efi-x64` 2.12-66.fc44           | Fedora      | Fedora Secure Boot CA 20250530                   |
| `kernel` 7.3.3-200.fc44                | Fedora      | Fedora Secure Boot CA 20200709 (`kernel-signer`) |
| `systemd-boot-unsigned` 261.2-1.1.hum1 | Hummingbird | None                                             |

Hummingbird builds and ships `systemd-boot-unsigned` but no signed boot binary.
It has no key in the chain: the Fedora shim accepts only binaries signed by the
Fedora CA, or keys a user enrolls through MokManager.

Several changes in flight need a decision about who signs what:

- The draft kernel import from kernel-ark
  ([rpms!4636](https://gitlab.com/redhat/hummingbird/rpms/-/merge_requests/4636))
  would replace the Fedora-signed kernel with a Hummingbird build. A kernel
  built outside Koji is signed by `%pesign` with the Red Hat Test Certificate.
  The Fedora shim rejects that kernel, so an `os-minimal` that installs it stops
  booting with Secure Boot enabled.
- Derived desktop images, such as
  [Project Bluefin's Utah](https://github.com/projectbluefin/utah), need three
  things that Fedora's chain does not provide today:
  1. Kernel fixes before Fedora ships them. For example, btrfs fs-verity reports
     intact files as corrupt from 7.2 on (fixed in mainline 254e15591ee4, v7.4-rc2).
     Utah rebuilds Fedora's kernel with that patch, and the rebuild is test-signed.
  2. A signed `systemd-boot` for systemd-boot installs and live media. Fedora
     signs `systemd-boot-x64` from Fedora 45 on (the `systemd-boot` package).
     Hummingbird's buildroot is Fedora 44, and Hummingbird builds its own `systemd`.
  3. Signed out-of-tree kernel modules: `v4l2loopback` and NVIDIA's open
     kernel module. With Secure Boot enabled, kernel lockdown refuses unsigned
     modules. The Fedora kernel's module signing key is generated for each build
     and then discarded, so no other build can sign a module that kernel trusts.
     The only alternative is a key the user enrolls in MOK.

Without a project-level decision, every downstream that needs one of these pieces
generates its own signing key. Each user then has to enroll that key in MOK.

## Decision

Hummingbird signs every UEFI binary and kernel module that it builds for bootable
images, using one chain that the shim it ships trusts. Until that chain exists,
Hummingbird does not ship a boot component that the shim would reject.

1. **Interim (Fedora's chain).** The kernel, shim and GRUB keep coming from
   Fedora. Kernel fixes that derived images need go upstream to
   [kernel-ark](https://gitlab.com/cki-project/kernel-ark) (`fedora-X.Y`
   branches) and to stable, so they reach the Fedora-signed kernel that `os-minimal` already
   consumes. When the buildroot moves to Fedora 45, Fedora's signed
   `systemd-boot-x64` becomes available the same way `shim-x64` is today.
2. **Hummingbird kernel.** The kernel import (rpms!4636) does not reach a bootable
   image until its build is signed by a CA that the shipped shim trusts. That can
   be Fedora's signing service, Red Hat's Secure Boot infrastructure through
   Konflux, or a Hummingbird shim reviewed by Microsoft. The kernel package
   carries the fixes its consumers need, using the spec's
   `linux-kernel-test.patch` hook or a kernel-ark branch.
3. **Signed systemd-boot.** Hummingbird signs its own `systemd-boot-unsigned` with
   the same chain as the kernel. It packages the result the way Fedora's
   `systemd-boot` package does: `systemd-boot-x64`, with the hardlink
   `/usr/lib/efi/systemd-boot/<version>/EFI/<vendor>/grub<arch>.efi` that
   bootupd discovers.
4. **Out-of-tree modules.** The kernel build uses a persistent module signing
   key instead of a per-build one. `v4l2loopback` and the NVIDIA open kernel
   module (`open-gpu-kernel-modules`, MIT/GPL-2.0) are kmod packages that are
   built and signed in the same pipeline as the kernel, for each kernel release.
   NVIDIA's proprietary userspace is out of scope.

Third-party kernel forks are out of scope; the Open Gaming Collective kernel is
one example. Downstreams that need them keep Secure Boot disabled or enroll their
own MOK key.

## Consequences

- Phase 1 needs no Hummingbird code. It changes where fixes are sent: kernel
  fixes go to kernel-ark and stable, not into downstream kernel rebuilds.
- Phase 2 blocks rpms!4636 from reaching `os-minimal` until signing is in place.
  This keeps a test-signed kernel out of a published image.
- Phases 3 and 4 need key management in Konflux (an HSM-backed `pesign` or
  `sign-file` step) and a rebuild trigger for each kernel release. Those
  are infrastructure costs that Hummingbird takes on.
- Derived images can drop their own kernel rebuilds and module signing keys.
  Their users never enroll a MOK key for components that Hummingbird ships.

## Open questions

- Does Hummingbird plan to own the kernel (rpms!4636), and if so, which CA signs
  it?
- Is there a Konflux path to Red Hat's Secure Boot signing for community
  images, or would Hummingbird need its own shim submission?
- Are kmod packages for `v4l2loopback` and the NVIDIA open module in scope, or
  should derived images keep building and signing them?
