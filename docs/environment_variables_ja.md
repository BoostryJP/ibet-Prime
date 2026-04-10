# 環境変数

この資料は、アプリケーションで使用される環境変数の一覧と説明を提供します。

特記がない限り、真偽値の設定は `1` で有効、`0` で無効です。「未設定」と書かれている項目は、未設定時にコード側の既定値が使われるか、特定の実行モードでのみ必要になります。

## 共通設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `TZ` | `Asia/Tokyo` | REST API で使用するタイムゾーン。 |
| `APP_ENV` | `local` | `conf/{APP_ENV}.ini` を選択し、一部の既定値にも影響します。 |
| `RESPONSE_VALIDATION_MODE` | `false` | `1` を設定するとレスポンス検証を有効にします。 |
| `RUN_MODE` | 未設定 | エントリポイントで使用する汎用的な起動モード。 |
| `DEFAULT_CURRENCY` | `JPY` | 既定の通貨コード。 |

## DB とログ

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb` | 通常起動時に使う PostgreSQL URL。 |
| `TEST_DATABASE_URL` | `pytest` 実行時は `postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb_test` | テストで使用する PostgreSQL URL。 |
| `DATABASE_SCHEMA` | 未設定 | PostgreSQL のスキーマ名。 |
| `AUTH_LOGFILE` | `/dev/stdout` | 認証ログの出力先。 |
| `ACCESS_LOGFILE` | `/dev/stdout` | アクセスログの出力先。 |

## ibet ネットワーク監視

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `BLOCK_SYNC_STATUS_SLEEP_INTERVAL` | `3` | ブロック同期監視のスリープ間隔（秒）。 |
| `BLOCK_SYNC_STATUS_CALC_PERIOD` | `3` | ブロック同期状態の算出に使うサンプル数。 |
| `BLOCK_SYNC_REMAINING_THRESHOLD` | `2` | ブロック同期遅延の判定しきい値。 |
| `BLOCK_GENERATION_SPEED_THRESHOLD` | `APP_ENV` が `local` 以外なら `20`、それ以外は `0` | ブロック生成停止判定のしきい値。 |
| `EXPECTED_BLOCKS_PER_SEC` | `0.1` | 平均ブロック生成間隔の想定値。 |

## ibet Web3 とトークン設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `WEB3_HTTP_PROVIDER` | `http://localhost:8545` | ibet ネットワーク向けの Web3 HTTP プロバイダー。 |
| `WEB3_HTTP_PROVIDER_STANDBY` | 空リスト | 待機系 Web3 プロバイダーのカンマ区切り一覧。 |
| `CHAIN_ID` | `2017` | ibet ネットワークのチェーン ID。 |
| `TX_GAS_LIMIT` | `6000000` | トランザクションで使うガスリミット。 |
| `WEB3_REQUEST_RETRY_COUNT` | `3` | Web3 リクエストの再試行回数。 |
| `WEB3_REQUEST_WAIT_TIME` | `3` | Web3 再試行間の待機時間（秒）。 |
| `TOKEN_LIST_CONTRACT_ADDRESS` | 未設定 | TokenList コントラクトアドレス。トークン登録系機能で必要です。 |
| `E2E_MESSAGING_CONTRACT_ADDRESS` | 未設定 | E2EMessaging コントラクトアドレス。E2E メッセージング機能で必要です。 |
| `TOKEN_CACHE` | `true` | `0` を設定したときだけトークンキャッシュを無効化します。 |
| `TOKEN_CACHE_TTL` | `43200` | トークンキャッシュの TTL（秒）。 |
| `TOKEN_CACHE_TTL_JITTER` | `21600` | トークンキャッシュ TTL に加えるジッター（秒）。 |

## バッチ処理設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `INDEXER_BLOCK_LOT_MAX_SIZE` | `1000000` | インデクサーで使う最大ブロックロットサイズ。 |
| `BULK_TX_LOT_SIZE` | `100` | Bulk Tx のロットサイズ。 |
| `BULK_TRANSFER_INTERVAL` | `10` | Bulk Transfer 処理の間隔（秒）。 |
| `BULK_TRANSFER_WORKER_COUNT` | `5` | Bulk Transfer 処理のワーカー数。 |
| `BULK_TRANSFER_WORKER_LOT_SIZE` | `5` | Bulk Transfer ワーカーあたりのロットサイズ。 |
| `BATCH_REGISTER_PERSONAL_INFO_INTERVAL` | `60` | 個人情報登録バッチの実行間隔（秒）。 |
| `BATCH_REGISTER_PERSONAL_INFO_WORKER_COUNT` | `1` | 個人情報登録バッチのワーカー数。 |
| `BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE` | `2` | 個人情報登録バッチのワーカーあたりのロットサイズ。 |
| `SCHEDULED_EVENTS_INTERVAL` | `60` | Scheduled Events の実行間隔（秒）。 |
| `SCHEDULED_EVENTS_WORKER_COUNT` | `5` | Scheduled Events のワーカー数。 |
| `UPDATE_TOKEN_INTERVAL` | `10` | Token 更新処理の実行間隔（秒）。 |
| `CREATE_UTXO_INTERVAL` | `600` | UTXO 作成処理の実行間隔（秒）。 |
| `CREATE_UTXO_BLOCK_LOT_MAX_SIZE` | `10000` | UTXO 作成処理で使う最大ブロックロットサイズ。 |
| `ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL` | `10` | E2E Messaging の RSA キー更新間隔（秒）。 |

## パスワードと E2EE 設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `EOA_PASSWORD_CHECK_ENABLED` | `true` | `0` を設定したときだけ EOA パスワードチェックを無効化します。 |
| `E2EE_RSA_RESOURCE_MODE` | ローカル、テスト、マイグレーション時は `0`、それ以外は未設定 | E2EE RSA リソースのモード。`0` はファイル、`1` は AWS Secrets Manager を意味します。 |
| `E2EE_RSA_RESOURCE` | ローカル、テスト、マイグレーション時は `tests/data/rsa_private.pem`、それ以外は未設定 | RSA リソースのパス、または `E2EE_RSA_RESOURCE_MODE` に応じたシークレット ARN / 名前。 |
| `E2EE_RSA_PASSPHRASE` | ローカル、テスト、マイグレーション時は `password`、それ以外は未設定 | RSA リソースのパスフレーズ。 |
| `E2EE_REQUEST_ENABLED` | `true` | `0` を設定したときだけ E2EE リクエスト処理を無効化します。 |
| `EOA_PASSWORD_PATTERN` | 8 文字以上 200 文字以下の許可文字に対する正規表現 | EOA パスワードの検証パターン。 |
| `EOA_PASSWORD_PATTERN_MSG` | `password must be 8 to 200 alphanumeric or symbolic character` | EOA パスワード検証時のエラーメッセージ。 |
| `PERSONAL_INFO_RSA_PASSPHRASE_PATTERN` | 8 文字以上 200 文字以下の許可文字に対する正規表現 | 個人情報 RSA パスフレーズの検証パターン。 |
| `PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG` | `passphrase must be 8 to 200 alphanumeric or symbolic characters` | 個人情報 RSA パスフレーズ検証時のエラーメッセージ。 |
| `PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE` | `password` | 個人情報 RSA キーの既定パスフレーズ。 |
| `E2E_MESSAGING_RSA_PASSPHRASE_PATTERN` | 8 文字以上 200 文字以下の許可文字に対する正規表現 | E2E Messaging RSA パスフレーズの検証パターン。 |
| `E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG` | `passphrase must be 8 to 200 alphanumeric or symbolic characters` | E2E Messaging RSA パスフレーズ検証時のエラーメッセージ。 |
| `E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE` | `password` | E2E Messaging RSA キーの既定パスフレーズ。 |

## 機能フラグと運用設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `AWS_REGION_NAME` | `ap-northeast-1` | AWS ベースの機能で使う AWS リージョン。 |
| `AWS_KMS_GENERATE_RANDOM_ENABLED` | `false` | `1` を設定すると AWS KMS で乱数を生成します。 |
| `DEDICATED_OFFCHAIN_TX_MODE` | `false` | Off-chain transaction 専用サーバーの起動モード。 |
| `DEDICATED_DVP_AGENT_MODE` | `false` | DvP agent 専用サーバーの起動モード。 |
| `DEDICATED_DVP_AGENT_ID` | 未設定 | DvP agent 機能で使う専用エージェント ID。 |
| `FREEZE_LOG_FEATURE_ENABLED` | `false` | FreezeLog 関連機能を有効化します。 |
| `FREEZE_LOG_CONTRACT_ADDRESS` | 未設定 | FreezeLog コントラクトアドレス。FreezeLog 機能で必要です。 |
| `DVP_AGENT_FEATURE_ENABLED` | `false` | DvP agent 機能を有効化します。 |
| `DVP_DATA_ENCRYPTION_MODE` | 未設定 | DvP データの暗号化モード。AES を使う場合は `aes-256-cbc` を設定します。 |
| `DVP_DATA_ENCRYPTION_KEY` | 未設定 | `DVP_DATA_ENCRYPTION_MODE` が `aes-256-cbc` のときに使う Base64 文字列の AES 鍵。 |
| `IBET_WST_ETH_FEATURE_ENABLED` | `false` | Ethereum 上の ibet WST 機能を有効化します。 |
| `IBET_WST_AVA_FEATURE_ENABLED` | `false` | Avalanche 上の ibet WST 機能を有効化します。 |
| `IBET_WST_BRIDGE_INTERVAL` | `10` | WST ブリッジ処理の実行間隔（秒）。 |
| `IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE` | `10000` | WST ブリッジ処理で使う最大ブロックロットサイズ。 |
| `MAX_UPLOAD_FILE_SIZE` | `100000000` | アップロード可能な最大ファイルサイズ（バイト）。 |
| `BC_EXPLORER_ENABLED` | `false` | ブロックチェーンエクスプローラ UI / API を有効化します。 |

## Ethereum 設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `ETH_MASTER_ACCOUNT_ADDRESS` | 未設定 | Ethereum トランザクション用のマスターアカウントアドレス。 |
| `ETH_MASTER_PRIVATE_KEY_RESOURCE` | `os_environ` | Ethereum マスター秘密鍵の取得元。`os_environ` または `aws_secrets_manager` を指定します。 |
| `ETH_MASTER_PRIVATE_KEY` | 未設定 | `ETH_MASTER_PRIVATE_KEY_RESOURCE` が `os_environ` の場合は秘密鍵そのもの、`aws_secrets_manager` の場合はシークレット ID。 |
| `ETH_CHAIN_ID` | `11111` | Ethereum トランザクション用のチェーン ID。 |
| `ETH_WEB3_HTTP_PROVIDER` | `http://localhost:8546` | Ethereum 用 Web3 HTTP プロバイダー。 |
| `ETH_WEB3_HTTP_PROVIDER_STANDBY` | 空リスト | Ethereum 用の待機系 Web3 プロバイダーのカンマ区切り一覧。 |

## Avalanche 設定

| 名前 | 既定値 | 説明 |
| --- | --- | --- |
| `AVA_MASTER_ACCOUNT_ADDRESS` | 未設定 | Avalanche トランザクション用のマスターアカウントアドレス。 |
| `AVA_MASTER_PRIVATE_KEY_RESOURCE` | `os_environ` | Avalanche マスター秘密鍵の取得元。`os_environ` または `aws_secrets_manager` を指定します。 |
| `AVA_MASTER_PRIVATE_KEY` | 未設定 | `AVA_MASTER_PRIVATE_KEY_RESOURCE` が `os_environ` の場合は秘密鍵そのもの、`aws_secrets_manager` の場合はシークレット ID。 |
| `AVA_CHAIN_ID` | `22222` | Avalanche トランザクション用のチェーン ID。 |
| `AVA_WEB3_HTTP_PROVIDER` | `http://localhost:8547` | Avalanche 用 Web3 HTTP プロバイダー。 |
| `AVA_WEB3_HTTP_PROVIDER_STANDBY` | 空リスト | Avalanche 用の待機系 Web3 プロバイダーのカンマ区切り一覧。 |

## プロファイリング設定

| 名前             | 既定値  | 説明               |
| ---------------- | ------- | ------------------ |
| `PROFILING_MODE` | `false` | `1` を設定するとプロファイリングを有効にします。 |
| `PYROSCOPE_SERVER_URL` | 未設定 | Pyroscope サーバー URL。