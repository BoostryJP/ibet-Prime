#!/usr/bin/env bash

set -euo pipefail

CHAIN_ID="${CHAIN_ID:?CHAIN_ID is required}"
BLOCK_GAS_LIMIT="${BLOCK_GAS_LIMIT:?BLOCK_GAS_LIMIT is required}"
ANVIL_HARDFORK="${ANVIL_HARDFORK:-latest}"
ANVIL_HOST="${ANVIL_HOST:-0.0.0.0}"
ANVIL_PORT="${ANVIL_PORT:-8545}"
ANVIL_SLOTS_IN_AN_EPOCH="${ANVIL_SLOTS_IN_AN_EPOCH:-1}"
BALANCE="${ANVIL_BALANCE:-0x21e19e0c9bab2400000}"
RPC_URL="http://127.0.0.1:${ANVIL_PORT}"

anvil \
  --host "${ANVIL_HOST}" \
  --port "${ANVIL_PORT}" \
  --chain-id "${CHAIN_ID}" \
  --hardfork "${ANVIL_HARDFORK}" \
  --slots-in-an-epoch "${ANVIL_SLOTS_IN_AN_EPOCH}" \
  --gas-price 0 \
  --block-base-fee-per-gas 0 \
  --gas-limit "${BLOCK_GAS_LIMIT}" &
ANVIL_PID=$!

cleanup() {
  kill "${ANVIL_PID}" 2>/dev/null || true
  wait "${ANVIL_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

until cast rpc --rpc-url "${RPC_URL}" web3_clientVersion >/dev/null 2>&1; do
  sleep 0.2
done

for ADDRESS in \
  0xeD6ef822d2cc46a8D7CfDb8A4b7BcF7E9B95F946 \
  0x3Ec9E2880285FAC4fF92514754924E5d0E6264Cb \
  0x85a8b8887a4bD76859751b10C8aC8EC5f3aA1bDB \
  0xC195574baDAA5d8410bd58968591E26a4aB8C5d2 \
  0x07Ff56207a0Dc2e7585B311897B24DB27b4Edac5
do
  cast rpc --rpc-url "${RPC_URL}" anvil_setBalance "${ADDRESS}" "${BALANCE}" >/dev/null
done

wait "${ANVIL_PID}"