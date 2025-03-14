#!/bin/bash

set -e -o pipefail

echo "Building Python package ..."
python -m build

echo "Building docker images ..."
scripts/build_container.sh chainlit
scripts/build_container.sh dask
