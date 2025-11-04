PODMAN_ADDITIONAL_ARGS :=
ifdef CONTAINERS_REPO_PATH
	ifdef RUNNING_IN_CONTAINER
		export HUGO_MODULE_REPLACEMENTS := gitlab.com/redhat/hummingbird/containers -> /containers
	else
		PODMAN_ADDITIONAL_ARGS := -v $(CONTAINERS_REPO_PATH):/containers:z -e CONTAINERS_REPO_PATH=$(CONTAINERS_REPO_PATH)
		export HUGO_MODULE_REPLACEMENTS := gitlab.com/redhat/hummingbird/containers -> $(CONTAINERS_REPO_PATH)
	endif
endif

PULL ?= newer
PODMAN_IMAGE := quay.io/hummingbird-ci/gitlab-ci:latest
PODMAN_RUN := podman run --pull=$(PULL) -it --rm -u 0 -v $(PWD):/src:z -w /src -e RUNNING_IN_CONTAINER=1 -e HUGO_CACHEDIR=/src/.hugo_cache $(PODMAN_ADDITIONAL_ARGS)

.PHONY: container
container:
	$(PODMAN_RUN) $(PODMAN_IMAGE) sh

.PHONY: check-host check
check-host:
	markdownlint *.md

check:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make check-host

.PHONY: build-host build
build-host:
	hugo -d public

build:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make build-host

.PHONY: server-host serve
serve-host:
	trap '$(MAKE) clean; exit 0' SIGINT; hugo serve --bind 0.0.0.0

serve:
	$(PODMAN_RUN) -p 1313:1313 $(PODMAN_IMAGE) make serve-host

.PHONY: clean
clean:
	rm -f go.sum > /dev/null
	rm -f .hugo_build.lock > /dev/null
	git checkout HEAD go.mod
