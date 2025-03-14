#!/bin/bash

####################################################################################################
# Performs code linting and type checks. Fails if errors are found
####################################################################################################

set -eo pipefail

apt-get install shellcheck

scripts/lint.sh
