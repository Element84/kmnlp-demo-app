#!/bin/bash

# #######################################################
# Push a container to ECR
#
# This script is used both when running locally and in CI
# #######################################################

set -eo pipefail

# Usage documentation
function usage() {
    echo "Usage: $(basename "$0") \"chainlit|dask\""
    echo ""
    echo "Publish specified docker image to ECR."
    echo ""
}

if [[ $# -eq 0 ]]; then
    echo "Error: specify image name."
    echo ""
    usage
    exit
fi

# print usage info on --help or -h
if [[ "${1:-}" = "--help" ]]; then
    usage
    exit
fi

ARG="${1:-"chainlit"}"
IMAGE_NAME="chainlit-demo/${ARG}:latest"

# Set AWS credentials if region and account_id not already provided.
# NOTE: In CI, these should have been exported in the push_container script.
if [[ -z "$AWS_REGION" || -z "$AWS_ACCOUNT_ID" ]]; then
  AWS_PROFILE="${AWS_PROFILE:-kmnlp}"
  AWS_REGION="$(aws configure get region --profile "$AWS_PROFILE")"
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --output text --query 'Account' --profile "$AWS_PROFILE")"
else
  AWS_PROFILE=""
fi

# Ensure required AWS details were retrieved
if [[ -z "$AWS_REGION" || -z "$AWS_ACCOUNT_ID" ]]; then
    echo "Error: Failed to retrieve AWS account ID or region."
    exit 1
fi

# Construct ECR URL and tag
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_TAG="${ECR_URL}/${IMAGE_NAME}"

# Authenticate Docker with ECR
if [[ -n $AWS_PROFILE ]]; then
  aws ecr get-login-password --profile "$AWS_PROFILE" |
    docker login --username AWS --password-stdin "$ECR_URL"
else
  aws ecr get-login-password |
    docker login --username AWS --password-stdin "$ECR_URL"
fi

# Tag and push image
docker tag "$IMAGE_NAME" "$ECR_TAG"
docker push "$ECR_TAG"
