# Environment Variables

This document provides a list and description of environment variables used by the application.

Unless noted otherwise, boolean flags use `1` to enable and `0` to disable. Values left as `unset` fall back to the code default or are only required in specific execution modes.

## Common application settings

| Name | Default | Description |
| --- | --- | --- |
| `TZ` | `Asia/Tokyo` | Time zone used by the REST API. |
| `APP_ENV` | `local` | Selects `conf/{APP_ENV}.ini` and affects some defaults. |
| `RESPONSE_VALIDATION_MODE` | `false` | Enables response validation when set to `1`. |
| `RUN_MODE` | unset | Generic run mode used by entry points. |
| `DEFAULT_CURRENCY` | `JPY` | Default currency code. |

## Database and logging

| Name | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb` | PostgreSQL URL for normal runtime. |
| `TEST_DATABASE_URL` | `postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb_test` when running under `pytest` | PostgreSQL URL used by tests. |
| `DATABASE_SCHEMA` | unset | PostgreSQL schema name. |
| `AUTH_LOGFILE` | `/dev/stdout` | Destination for auth logs. |
| `ACCESS_LOGFILE` | `/dev/stdout` | Destination for access logs. |

## ibet network monitoring

| Name | Default | Description |
| --- | --- | --- |
| `BLOCK_SYNC_STATUS_SLEEP_INTERVAL` | `3` | Sleep interval, in seconds, for block sync monitoring. |
| `BLOCK_SYNC_STATUS_CALC_PERIOD` | `3` | Number of monitoring samples used for block sync status. |
| `BLOCK_SYNC_REMAINING_THRESHOLD` | `2` | Threshold for the remaining block sync gap. |
| `BLOCK_GENERATION_SPEED_THRESHOLD` | `20` when `APP_ENV` is not `local`, otherwise `0` | Threshold used to decide whether block generation has stopped. |
| `EXPECTED_BLOCKS_PER_SEC` | `0.1` | Expected average block generation interval. |

## ibet Web3 and token settings

| Name | Default | Description |
| --- | --- | --- |
| `WEB3_HTTP_PROVIDER` | `http://localhost:8545` | Web3 HTTP provider for the ibet network. |
| `WEB3_HTTP_PROVIDER_STANDBY` | empty list | Comma-separated standby provider list. |
| `CHAIN_ID` | `2017` | Chain ID for the ibet network. |
| `TX_GAS_LIMIT` | `6000000` | Gas limit used for transactions. |
| `WEB3_REQUEST_RETRY_COUNT` | `3` | Retry count for Web3 requests. |
| `WEB3_REQUEST_WAIT_TIME` | `3` | Wait time, in seconds, between Web3 retries. |
| `TOKEN_LIST_CONTRACT_ADDRESS` | unset | TokenList contract address. Set this before using token registration-related features. |
| `E2E_MESSAGING_CONTRACT_ADDRESS` | unset | E2EMessaging contract address. Required for E2E messaging features. |
| `TOKEN_CACHE` | `true` | Disables token cache only when set to `0`. |
| `TOKEN_CACHE_TTL` | `43200` | Token cache TTL, in seconds. |
| `TOKEN_CACHE_TTL_JITTER` | `21600` | Jitter added to the token cache TTL, in seconds. |

## Batch processing settings

| Name | Default | Description |
| --- | --- | --- |
| `INDEXER_BLOCK_LOT_MAX_SIZE` | `1000000` | Maximum block lot size used by indexers. |
| `BULK_TX_LOT_SIZE` | `100` | Bulk transaction lot size. |
| `BULK_TRANSFER_INTERVAL` | `10` | Interval, in seconds, for the bulk transfer processor. |
| `BULK_TRANSFER_WORKER_COUNT` | `5` | Worker count for bulk transfer processing. |
| `BULK_TRANSFER_WORKER_LOT_SIZE` | `5` | Lot size per bulk transfer worker. |
| `BATCH_REGISTER_PERSONAL_INFO_INTERVAL` | `60` | Interval, in seconds, for personal info registration batches. |
| `BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT` | `1` | Worker count for personal info registration batches. |
| `BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE` | `2` | Lot size per personal info batch worker. |
| `SCHEDULED_EVENTS_INTERVAL` | `60` | Interval, in seconds, for scheduled event processing. |
| `SCHEDULED_EVENTS_WORKER_COUNT` | `5` | Worker count for scheduled events. |
| `UPDATE_TOKEN_INTERVAL` | `10` | Interval, in seconds, for token update processing. |
| `CREATE_UTXO_INTERVAL` | `600` | Interval, in seconds, for UTXO creation. |
| `CREATE_UTXO_BLOCK_LOT_MAX_SIZE` | `10000` | Maximum block lot size used by UTXO creation. |
| `ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL` | `10` | Interval, in seconds, for rotating the E2E messaging RSA key. |

## Password and E2EE settings

| Name | Default | Description |
| --- | --- | --- |
| `EOA_PASSWORD_CHECK_ENABLED` | `true` | Disables EOA password checks only when set to `0`. |
| `E2EE_RSA_RESOURCE_MODE` | `0` in local, test, and migration contexts; otherwise unset | E2EE RSA resource mode. `0` means file, `1` means AWS Secrets Manager. |
| `E2EE_RSA_RESOURCE` | `tests/data/rsa_private.pem` in local, test, and migration contexts; otherwise unset | RSA resource path or secret ARN/name, depending on `E2EE_RSA_RESOURCE_MODE`. |
| `E2EE_RSA_PASSPHRASE` | `password` in local, test, and migration contexts; otherwise unset | Passphrase for the RSA resource. |
| `E2EE_REQUEST_ENABLED` | `true` | Disables E2EE request handling only when set to `0`. |
| `EOA_PASSWORD_PATTERN` | regex for 8 to 200 allowed characters | Validation pattern for EOA passwords. |
| `EOA_PASSWORD_PATTERN_MSG` | `password must be 8 to 200 alphanumeric or symbolic character` | Error message for EOA password validation. |
| `PERSONAL_INFO_RSA_PASSPHRASE_PATTERN` | regex for 8 to 200 allowed characters | Validation pattern for personal info RSA passphrases. |
| `PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG` | `passphrase must be 8 to 200 alphanumeric or symbolic characters` | Error message for personal info RSA passphrase validation. |
| `PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE` | `password` | Default passphrase for personal info RSA keys. |
| `E2E_MESSAGING_RSA_PASSPHRASE_PATTERN` | regex for 8 to 200 allowed characters | Validation pattern for E2E messaging RSA passphrases. |
| `E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG` | `passphrase must be 8 to 200 alphanumeric or symbolic characters` | Error message for E2E messaging RSA passphrase validation. |
| `E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE` | `password` | Default passphrase for E2E messaging RSA keys. |

## Feature flags and operational settings

| Name | Default | Description |
| --- | --- | --- |
| `AWS_REGION_NAME` | `ap-northeast-1` | AWS region used by AWS-backed features. |
| `AWS_KMS_GENERATE_RANDOM_ENABLED` | `false` | Uses AWS KMS to generate random bytes when set to `1`. |
| `DEDICATED_OFFCHAIN_TX_MODE` | `false` | Boot mode for the off-chain transaction dedicated server. |
| `DEDICATED_DVP_AGENT_MODE` | `false` | Boot mode for the DvP agent dedicated server. |
| `DEDICATED_DVP_AGENT_ID` | unset | Dedicated agent ID used by DvP agent features. |
| `FREEZE_LOG_FEATURE_ENABLED` | `false` | Enables FreezeLog-related features. |
| `FREEZE_LOG_CONTRACT_ADDRESS` | unset | FreezeLog contract address. Required when FreezeLog features are used. |
| `DVP_AGENT_FEATURE_ENABLED` | `false` | Enables DvP agent features. |
| `DVP_DATA_ENCRYPTION_MODE` | unset | DvP data encryption mode. Set to `aes-256-cbc` to enable AES encryption. |
| `DVP_DATA_ENCRYPTION_KEY` | unset | Base64-encoded AES key used when `DVP_DATA_ENCRYPTION_MODE` is `aes-256-cbc`. |
| `IBET_WST_ETH_FEATURE_ENABLED` | `false` | Enables ibet WST features on Ethereum. |
| `IBET_WST_AVA_FEATURE_ENABLED` | `false` | Enables ibet WST features on Avalanche. |
| `IBET_WST_BRIDGE_INTERVAL` | `10` | Interval, in seconds, for WST bridge processing. |
| `IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE` | `10000` | Maximum block lot size for WST bridge processing. |
| `MAX_UPLOAD_FILE_SIZE` | `100000000` | Maximum upload file size, in bytes. |
| `BC_EXPLORER_ENABLED` | `false` | Enables the blockchain explorer UI and APIs. |

## Ethereum settings

| Name | Default | Description |
| --- | --- | --- |
| `ETH_MASTER_ACCOUNT_ADDRESS` | unset | Master account address for Ethereum transactions. |
| `ETH_MASTER_PRIVATE_KEY_RESOURCE` | `os_environ` | Source of the Ethereum master private key. Use `os_environ` or `aws_secrets_manager`. |
| `ETH_MASTER_PRIVATE_KEY` | unset | Raw private key when `ETH_MASTER_PRIVATE_KEY_RESOURCE` is `os_environ`, or the secret ID when it is `aws_secrets_manager`. |
| `ETH_CHAIN_ID` | `11111` | Chain ID for Ethereum transactions. |
| `ETH_WEB3_HTTP_PROVIDER` | `http://localhost:8546` | Web3 HTTP provider for Ethereum. |
| `ETH_WEB3_HTTP_PROVIDER_STANDBY` | empty list | Comma-separated standby provider list for Ethereum. |

## Avalanche settings

| Name | Default | Description |
| --- | --- | --- |
| `AVA_MASTER_ACCOUNT_ADDRESS` | unset | Master account address for Avalanche transactions. |
| `AVA_MASTER_PRIVATE_KEY_RESOURCE` | `os_environ` | Source of the Avalanche master private key. Use `os_environ` or `aws_secrets_manager`. |
| `AVA_MASTER_PRIVATE_KEY` | unset | Raw private key when `AVA_MASTER_PRIVATE_KEY_RESOURCE` is `os_environ`, or the secret ID when it is `aws_secrets_manager`. |
| `AVA_CHAIN_ID` | `22222` | Chain ID for Avalanche transactions. |
| `AVA_WEB3_HTTP_PROVIDER` | `http://localhost:8547` | Web3 HTTP provider for Avalanche. |
| `AVA_WEB3_HTTP_PROVIDER_STANDBY` | empty list | Comma-separated standby provider list for Avalanche. |

## Profiling settings

| Name | Default | Description |
| --- | --- | --- |
| `PROFILING_MODE` | `false` | Enables profiling when set to `1`. |
| `PYROSCOPE_SERVER_URL` | unset | Pyroscope server URL. |
