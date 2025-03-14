#!/bin/bash

# ################################################################################
# Build script called by the CI pipeline
#
# This script is not fit to build images locally because it expects a CI_JOB_TOKEN
# that can be used to clone private repositories in GitLab.
# ################################################################################

set -e -o pipefail

echo "Building docker images ..."

docker buildx build \
    --secret id=CI_JOB_TOKEN \
    -t "chainlit-demo/build" \
    --target build \
    --platform linux/amd64 \
    .
