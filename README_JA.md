<p align="center">
  <img width="33%" src="https://user-images.githubusercontent.com/963333/71672471-6383c080-2db9-11ea-85b6-8815519652ec.png"/>
</p>

# ibet-Prime

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-26.6-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

[English](./README.md) | 日本語

**ibet-Prime は ibet network 向けの証券トークン管理システムです。**

## 機能概要

- ibet-Prime is an API service that enables the issuance and management of security tokens on the [ibet network](https://github.com/BoostryJP/ibet-Network).
- ibet-Prime は、 [ibet network](https://github.com/BoostryJP/ibet-Network) 上で証券トークンの発行、期中管理を行うことができる API サービスです。
- [ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract) プロジェクトで開発されているトークンや様々なスマートコントラクトをサポートしています。
- 証券トークンの台帳管理システムとして、ibet-Prime は日本の法令要件として必要な様々な機能群を提供します。
- フロントエンドのアプリケーションから ibet-Prime の API を呼び出すことによって、簡単に証券トークンの管理サービスを構築することが可能です。

## 依存

- [Python3](https://www.python.org/downloads/release/python-3146/) - バージョン 3.14
- [PostgreSQL](https://www.postgresql.org/) - バージョン 17
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - [ibet-Network](https://github.com/BoostryJP/ibet-Network) の公式の GoQuorum をサポートしています。
  - ローカル開発およびユニットテストでは [Anvil](https://www.getfoundry.sh/anvil) を利用しています。

## コントラクトのバージョン

* ibet-SmartContract: 最新バージョンのコントラクトの仕様をサポートしています。
* [詳細](./contracts/contract_version.md)を参照ください。

## セットアップ

### Prerequisites

- Python 実行環境を整備してください。
- PostgreSQL を設定し、以下のDBを事前に作成してください。
  - デフォルトでは以下の設定が必要になります。
    - ユーザー: issuerapi
    - パスワード: issuerapipass
    - DB: issuerapidb
    - テスト用 DB: issuerapidb_test
- ibet Node を構築し、接続できる状態にしてください。
  - ibet-SmartContract プロジェクトの TokenList および E2EMessaging コントラクトを事前にデプロイしてください。
- （任意）ethereum Node を構築し、接続できる状態にしてください。
- （任意）Avalanche Node を構築し、接続できる状態にしてください。

### パッケージインストール

以下のコマンドで Python の仮想環境を作成します。
```bash
$ uv venv
```

以下のコマンドで Python パッケージをインストールします。
```bash
$ make install
```

### 環境変数の設定

環境変数の一覧は [docs/environment_variables_ja.md](docs/environment_variables_ja.md) を参照してください。
各ユースケースに応じて、必要な環境変数を設定してください。

### DB マイグレーション

[migrations/README.md](migrations/README.md) を確認してください。

## サーバーの起動

API サーバーの起動は、以下を実行します。
```bash
$ make run
```

ブラウザで、[http://127.0.0.1:8000](http://127.0.0.1:8000) を開くと、以下のJSONのレスポンスを確認できるはずです。
```json
{"server":"ibet-Prime"}
```

### API 仕様書

サーバーを起動した状態で、[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) を開いてください。

Swagger UI 形式のドキュメントを参照することができるはずです。

![swagger](https://user-images.githubusercontent.com/963333/146362141-da0fc0d2-1518-4041-a274-be2b743966a1.png)

同様に、[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) では、ReDoc 形式のドキュメントを参照することができます。


## 開発環境に関する情報

### 環境変数の設定

ローカル環境の環境変数は、`.env` ファイルを作成し、定義することが可能です。

### テスト実行

テスト用コンテナの起動に関しては、`docker-compose.yml` を参照してください。
個別にテストケースを実行する場合は、ローカルに Python 実行環境を構築し、環境変数を設定した上で、テストケースを実行してください。

## ブランチ作成方針

このリポジトリは以下の図で示されるフローでバージョン管理が行われています。

![branching_model](https://user-images.githubusercontent.com/963333/153910560-2c67f8ad-73ae-4aaa-9e9f-9242643f6098.png)

## License

ibet-Prime は Apache License, Version 2.0 でライセンスされています。

## Contact information

私たちは、皆様のユースケースをサポートするために、オープンソースに取り組んでいます。
私たちは、あなたがこのライブラリをどのように使用し、どのような問題の解決に役立っているかを知りたいと思います。 
私たちは、2つのコミュニケーション用の手段を用意しています。

* [public discussion group](https://github.com/BoostryJP/ibet-Prime/discussions) では、ロードマップ、アップデート、イベント等を共有します。

* [dev@boostry.co.jp](mailto:dev@boostry.co.jp) のEメール宛に連絡をいただければ、直接私たちに連絡することができます。

機密事項の送信はご遠慮ください。過去に送信したメッセージの削除を希望される場合は、ご連絡ください。


## スポンサー

[BOOSTRY Co., Ltd.](https://boostry.co.jp/)
