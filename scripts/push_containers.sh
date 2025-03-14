#!/bin/bash

set -euo pipefail

scripts/push_container.sh chainlit
scripts/push_container.sh dask
