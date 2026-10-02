comma:= ,
space:= $() $()

PODMAN_ADDITIONAL_ARGS :=
HUGO_MODULE_REPLACEMENTS :=

ifdef CONTAINERS_REPO_PATH
	ifdef RUNNING_IN_CONTAINER
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/containers->/containers
	else
		PODMAN_ADDITIONAL_ARGS += -v $(CONTAINERS_REPO_PATH):/containers:z -e CONTAINERS_REPO_PATH=$(CONTAINERS_REPO_PATH)
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/containers->$(basename $(CONTAINERS_REPO_PATH))
	endif
endif

ifdef RPMS_REPO_PATH
	ifdef RUNNING_IN_CONTAINER
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/rpms->/rpms
	else
		PODMAN_ADDITIONAL_ARGS += -v $(RPMS_REPO_PATH):/rpms:z -e RPMS_REPO_PATH=$(RPMS_REPO_PATH)
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/rpms->$(basename $(RPMS_REPO_PATH))
	endif
endif

ifdef TOOLS_REPO_PATH
	ifdef RUNNING_IN_CONTAINER
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/tools->/tools
	else
		PODMAN_ADDITIONAL_ARGS += -v $(TOOLS_REPO_PATH):/tools:z -e TOOLS_REPO_PATH=$(TOOLS_REPO_PATH)
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/tools->$(basename $(TOOLS_REPO_PATH))
	endif
endif

ifdef K8S_TEST_PIPELINE_REPO_PATH
	ifdef RUNNING_IN_CONTAINER
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/pipelines/k8s-test-pipeline->/k8s-test-pipeline
	else
		PODMAN_ADDITIONAL_ARGS += -v $(K8S_TEST_PIPELINE_REPO_PATH):/k8s-test-pipeline:z -e K8S_TEST_PIPELINE_REPO_PATH=$(K8S_TEST_PIPELINE_REPO_PATH)
		HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/pipelines/k8s-test-pipeline->$(basename $(K8S_TEST_PIPELINE_REPO_PATH))
	endif
endif

ifneq ($(HUGO_MODULE_REPLACEMENTS),)
	export HUGO_MODULE_REPLACEMENTS := $(subst $(space),$(comma),$(HUGO_MODULE_REPLACEMENTS))
endif

PULL ?= newer
PODMAN_IMAGE := quay.io/hummingbird-ci/gitlab-ci:latest
PODMAN_RUN := podman run --pull=$(PULL) -it --rm -u 0 -v $(PWD):/src:z -w /src -e RUNNING_IN_CONTAINER=1 -e HUGO_CACHEDIR=/src/.hugo_cache $(PODMAN_ADDITIONAL_ARGS)

.PHONY: container
container:
	$(PODMAN_RUN) $(PODMAN_IMAGE) sh

.PHONY: check-host check
check-host:
	markdownlint $$(git ls-files '*.md')
check:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make check-host

# Dart Sass (required by Docsy ≥ v0.17.0). sass-embedded installs a
# platform-specific binary inside a dart-sass/ subdirectory; adding that
# directory to PATH lets Hugo's dartsass transpiler find the `sass` binary.
DART_SASS_DIR := $(shell find node_modules -name dart-sass -type d 2>/dev/null | grep -v '/src/' | head -1)
ifneq ($(DART_SASS_DIR),)
export PATH := $(abspath $(DART_SASS_DIR)):$(PATH)
endif

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

.PHONY: setup-host setup
setup-host:
	hugo mod npm pack
	npm install --no-package-lock
setup:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make setup-host

AGENT_IMAGE := quay.io/hummingbird-ci/hummingbird-agent:latest

.PHONY: eval-docs
eval-docs:
	podman run --rm -u 0 \
	  -v $$(pwd)/evals:/data:Z \
	  -v $${HOME}/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro,z \
	  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
	  -e GOOGLE_CLOUD_PROJECT \
	  $(AGENT_IMAGE) \
	  python -m hummingbird_agent.evals.docs_eval.run_eval \
	    -c /data/docs_eval.yml --results-dir /data/results

.PHONY: clean
clean:
	rm -f go.sum > /dev/null
	rm -f .hugo_build.lock > /dev/null
	git checkout HEAD go.mod
