#!/bin/bash

####################################################################################################
# Pulls downs the latest requirements as defined in the pyproject.toml and requirements.in files.
####################################################################################################

set -e -o pipefail

uv pip compile \
  --refresh \
  --all-extras \
  pyproject.toml \
  -o requirements.txt
