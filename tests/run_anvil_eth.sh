#!/usr/bin/env bash

set -euo pipefail

export CHAIN_ID=11111
export BLOCK_GAS_LIMIT=60000000
export ANVIL_HARDFORK=amsterdam
exec bash /app/ibet-Prime/tests/run_anvil.sh
