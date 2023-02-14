# global service name
SERVICE                 := exobot

#######################################################################
#                 OVERRIDE THIS TO MATCH YOUR PROJECT                 #
#######################################################################

# Most applications have their own method of maintaining a version number.
# Override this command to populate the
#APP_VERSION             := $(shell echo `cat gradle.properties | grep version | awk -F = '{print $$2}'`)
APP_VERSION             := 1.0.0

# Builds should be repeatable, therefore we need a method to reference the git
# sha where a version came from.
GIT_VERSION          		?= $(shell echo `git describe --match=NeVeRmAtCh --always --dirty`)
GIT_COMMIT          		?= $(shell echo `git log | grep -m1 -oE '[^ ]+$'`)
GIT_COMMITTED_AT        ?= $(shell echo `git log -1 --format=%ct`)
GIT_BRANCH_FULL							?= $(shell echo `git rev-parse --abbrev-ref HEAD`)
GIT_BRANCH            := $(shell echo $(GIT_BRANCH) | sed "s,/,-,g")
FULL_VERSION            := v$(APP_VERSION)-g$(GIT_VERSION)-$(GIT_BRANCH)

# location for artifact repositories
HELM_REPO_NAME          := machaao-helm
HELM_REPO_URL           := s3://$(HELM_REPO_NAME)/charts
DOCKER_INT_REGISTRY     := registry.machaao.com

ENV                     ?= dev
KUBECONFIG              ?=~/.kube/config.${ENV}

# Check for required dev tools installed
preflight:
	which docker
	which helm
	KUBECONFIG=${KUBECONFIG} helm repo list | grep $(HELM_REPO_NAME)

clean-all: clean
	docker rmi -f $(docker images -a -q)
	docker rm -f $(docker ps -a -q)

# Build docker images and tag them consistently
build: 
	docker build --build-arg GIT_BRANCH=${GIT_BRANCH} --build-arg GIT_COMMIT_SHA=${GIT_COMMIT} --build-arg FULL_VERSION=${FULL_VERSION} -t $(SERVICE) .
	docker tag $(SERVICE) $(DOCKER_INT_REGISTRY)/$(SERVICE):$(FULL_VERSION)
	docker tag $(SERVICE) $(DOCKER_INT_REGISTRY)/$(SERVICE):latest


#######################################################################
#          OVERRIDE this to match your docker/service config          #
#######################################################################

# Run the docker image local for development and testing. This is may be
# specific to each project, however, it should run with the minimal of inputs.
run:
	docker run -it -p 5005:5005  $(SERVICE)

# Publish artifacts to shared repositories. This includeds the docker image as
# well as  the helm chart for coordinated deployment on a k8s infrastructure.
release: helm-chart
	@echo $(DISPLAY_BOLD)"Publishing container to $(DOCKER_INT_REPO) registry"$(DISPLAY_RESET)
	docker -D push $(DOCKER_INT_REGISTRY)/$(SERVICE):$(FULL_VERSION)
	@echo $(DISPLAY_BOLD)"Publishing chart to $(SERVICE) registry"$(DISPLAY_RESET)
	KUBECONFIG=${KUBECONFIG} helm s3 push --force ./dist/$(SERVICE)-$(FULL_VERSION).tgz $(HELM_REPO_NAME)

#######################################################################
#                      OVERRIDE the HELM_FILES                        #
#######################################################################
# Build the helm chart package
helm-chart:
	rm -rf charts/build/* dist/*
	mkdir ./dist
	cp -pr charts/$(SERVICE) charts/build/$(SERVICE)
	rsync -ar vars/$(ENV)/ charts/build/$(SERVICE)

	KUBECONFIG=${KUBECONFIG} helm lint --debug charts/build/$(SERVICE)
	KUBECONFIG=${KUBECONFIG} helm package charts/build/$(SERVICE) -d ./dist --debug --version $(FULL_VERSION) --app-version $(FULL_VERSION)


# Deploy the helm chart on the k8s cluster
CHART_INSTALLED := $(shell KUBECONFIG=${KUBECONFIG} helm list | grep $(SERVICE) | grep -v FAILED)
deploy:
ifeq ($(CHART_INSTALLED),)
	KUBECONFIG=${KUBECONFIG} helm delete --purge $(SERVICE) || :
	KUBECONFIG=${KUBECONFIG} helm install charts/build/$(SERVICE) --wait --name $(SERVICE) --version $(FULL_VERSION) --set image.tag=$(FULL_VERSION) --timeout 700
else
	KUBECONFIG=${KUBECONFIG} helm upgrade $(SERVICE) charts/build/$(SERVICE) --wait --install --version $(FULL_VERSION) --set image.tag=$(FULL_VERSION) --timeout 700
endif

.PHONY:  build
