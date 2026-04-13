#!/usr/bin/env bash

set -euo pipefail

export CHAIN_ID=22222
export BLOCK_GAS_LIMIT=16777216
export ANVIL_HARDFORK=osaka
exec bash /app/ibet-Prime/tests/run_anvil.sh