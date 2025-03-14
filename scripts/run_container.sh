#!/bin/bash

set -euo pipefail

# Usage documentation
function usage() {
    echo "Usage: $(basename "$0") \"chainlit|dask\""
    echo ""
    echo "Run specified docker image."
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

case "$ARG" in
chainlit)
    docker run \
        -p 8000:8000 \
        -e AWS_PROFILE="${AWS_PROFILE:?}" \
        -e DASK_ADDRESS="${DASK_ADDRESS:?}" \
        -e ZARR_REFERENCE_PATH="${ZARR_REFERENCE_PATH:?}" \
        -v ~/.aws:/root/.aws:ro \
        ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
        "${IMAGE_NAME}"
    ;;
dask)
    docker run --rm -it \
        --network host \
        -e AWS_PROFILE="$AWS_PROFILE" \
        -e ZARR_REFERENCE_PATH="$ZARR_REFERENCE_PATH" \
        -v ~/.aws:/root/.aws:ro \
        ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
        "${IMAGE_NAME}"
    ;;
*)
    echo "Invalid argument: $ARG"
    echo "Allowed values are: chainlit, dask"
    exit 1
    ;;
esac
