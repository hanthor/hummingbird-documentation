comma:= ,
space:= $() $()

PODMAN_ADDITIONAL_ARGS :=
HUGO_MODULE_REPLACEMENTS :=

ifdef CONTAINERS_REPO_PATH
	CONTAINERS_REPO_ABSPATH := $(abspath $(CONTAINERS_REPO_PATH))
	ifndef RUNNING_IN_CONTAINER
		PODMAN_ADDITIONAL_ARGS += -v $(CONTAINERS_REPO_ABSPATH):$(CONTAINERS_REPO_ABSPATH):z -e CONTAINERS_REPO_PATH=$(CONTAINERS_REPO_ABSPATH)
	endif
	HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/containers->$(CONTAINERS_REPO_ABSPATH)
endif

ifdef RPMS_REPO_PATH
	RPMS_REPO_ABSPATH := $(abspath $(RPMS_REPO_PATH))
	ifndef RUNNING_IN_CONTAINER
		PODMAN_ADDITIONAL_ARGS += -v $(RPMS_REPO_ABSPATH):$(RPMS_REPO_ABSPATH):z -e RPMS_REPO_PATH=$(RPMS_REPO_ABSPATH)
	endif
	HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/rpms->$(RPMS_REPO_ABSPATH)
endif

ifdef TOOLS_REPO_PATH
	TOOLS_REPO_ABSPATH := $(abspath $(TOOLS_REPO_PATH))
	ifndef RUNNING_IN_CONTAINER
		PODMAN_ADDITIONAL_ARGS += -v $(TOOLS_REPO_ABSPATH):$(TOOLS_REPO_ABSPATH):z -e TOOLS_REPO_PATH=$(TOOLS_REPO_ABSPATH)
	endif
	HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/tools->$(TOOLS_REPO_ABSPATH)
endif

ifdef K8S_TEST_PIPELINE_REPO_PATH
	K8S_TEST_PIPELINE_REPO_ABSPATH := $(abspath $(K8S_TEST_PIPELINE_REPO_PATH))
	ifndef RUNNING_IN_CONTAINER
		PODMAN_ADDITIONAL_ARGS += -v $(K8S_TEST_PIPELINE_REPO_ABSPATH):$(K8S_TEST_PIPELINE_REPO_ABSPATH):z -e K8S_TEST_PIPELINE_REPO_PATH=$(K8S_TEST_PIPELINE_REPO_ABSPATH)
	endif
	HUGO_MODULE_REPLACEMENTS += gitlab.com/redhat/hummingbird/pipelines/k8s-test-pipeline->$(K8S_TEST_PIPELINE_REPO_ABSPATH)
endif

ifneq ($(HUGO_MODULE_REPLACEMENTS),)
	export HUGO_MODULE_REPLACEMENTS := $(subst $(space),$(comma),$(HUGO_MODULE_REPLACEMENTS))
endif

PULL ?= newer
PODMAN_IMAGE := quay.io/hummingbird-ci/gitlab-ci:latest
PODMAN_RUN := podman run --pull=$(PULL) -it --rm -u 0 -v $(PWD):$(PWD):z -w $(PWD) -e RUNNING_IN_CONTAINER=1 -e HUGO_CACHEDIR=$(PWD)/.hugo_cache $(PODMAN_ADDITIONAL_ARGS)

.PHONY: container
container:
	$(PODMAN_RUN) $(PODMAN_IMAGE) sh

.PHONY: check-host check
check-host:
	markdownlint $$(git ls-files '*.md')
check:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make check-host

AFDOCS_CHECKS := llms-txt-exists,llms-txt-valid,llms-txt-size,llms-txt-links-resolve,llms-txt-links-markdown,llms-txt-directive-html,llms-txt-directive-md,markdown-url-support,rendering-strategy,page-size-markdown,page-size-html,page-size-transfer,content-start-position,single-fetch-completeness,tabbed-content-serialization,section-header-quality,markdown-code-fence-validity,markdown-link-portability,embedded-data-serialization,http-status-codes,redirect-behavior,llms-txt-coverage,markdown-content-parity

.PHONY: check-afdocs-host check-afdocs
check-afdocs-host:
	trap 'kill %1 2>/dev/null' EXIT; \
	hugo serve --bind 0.0.0.0 & \
	for i in $$(seq 1 60); do curl -sf http://localhost:1313 >/dev/null 2>&1 && break; sleep 1; done; \
	npx --yes afdocs check http://localhost:1313 \
	  --canonical-origin https://hummingbird-project.io \
	  --checks $(AFDOCS_CHECKS) \
	  --llms-txt-url http://localhost:1313/llms.txt \
	  --max-links 200 \
	  --verbose
check-afdocs:
	$(PODMAN_RUN) -p 1313:1313 $(PODMAN_IMAGE) make check-afdocs-host

.PHONY: test-host test
test-host:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
test:
	$(PODMAN_RUN) $(PODMAN_IMAGE) make test-host

# Dart Sass (required by Docsy ≥ v0.17.0). sass-embedded installs the native
# binary in a platform-specific package (sass-embedded-<os>-<arch>) under
# dart-sass/. Prepend that directory to PATH so Hugo's dartsass transpiler
# finds the `sass` binary regardless of architecture.
export PATH := $(abspath $(wildcard node_modules/sass-embedded-*/dart-sass)):$(PATH)

.PHONY: build-host build build-mr-host
build-host:
	hugo -d public
build-mr-host:
	hugo -d public_mr
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
