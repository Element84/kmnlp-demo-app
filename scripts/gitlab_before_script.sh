#!/bin/bash

####################################################################################################
# Sets up the gitlab runner docker image to install additional things needed for build steps.
####################################################################################################

set -euo pipefail

# Get Docker's official GPG key
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "${VERSION_CODENAME:-}") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update apt and install necessary dependencies.
apt-get update && \
  apt-get install -y \
  git \
  docker.io \
  docker-buildx-plugin

# Update config config to fetch 2 privat repos over https using the CI job token
git config --global url."https://gitlab-ci-token:${CI_JOB_TOKEN:-}@repo.element84.com/".insteadOf ssh://git@repo.element84.com/
