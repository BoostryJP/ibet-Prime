#!/usr/bin/env bash

set -euo pipefail

export CHAIN_ID=2017
export BLOCK_GAS_LIMIT=800000000
export ANVIL_HARDFORK=osaka
exec bash /app/ibet-Prime/tests/run_anvil.sh