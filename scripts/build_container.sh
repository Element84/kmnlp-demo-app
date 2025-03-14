#!/bin/bash

set -euo pipefail

# Usage documentation
function usage() {
    echo "Usage: $(basename "$0") \"chainlit|dask\""
    echo ""
    echo "Build specified docker image."
    echo ""
}

if [[ $# -eq 0 ]]; then
    echo "Error: specify image name."
    echo ""
    usage
    exit
fi

# print usage info on --help or -h
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit
fi

ARG="${1:-"chainlit"}"
IMAGE_NAME="chainlit-demo/${ARG}:latest"

EXTRA_ARGS=("${@:2}")

# echo "extra_args: $EXTRA_ARGS"

docker buildx build \
    --ssh default \
    --build-arg BUILD_ENV_IS_CI=0 \
    -t "${IMAGE_NAME}" \
    --target "${ARG}" \
    --platform linux/amd64 \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
    .
