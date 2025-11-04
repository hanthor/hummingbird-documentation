PULL ?= newer
PODMAN_SHELL = podman run --pull=$(PULL) -it --rm -u 0 -v $(PWD):/src:z quay.io/hummingbird-ci/gitlab-ci:latest sh

.PHONY: container
container:
	$(PODMAN_SHELL)

.PHONY: check-host
check-host:
	markdownlint *.md

.PHONY: check
check:
	$(PODMAN_SHELL) -c "make -C /src check-host"
