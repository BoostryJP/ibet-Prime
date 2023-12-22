# ibet-Prime

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-24.3-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

[English](./README.md) | 日本語

<img width="33%" align="right" src="https://user-images.githubusercontent.com/963333/71672471-6383c080-2db9-11ea-85b6-8815519652ec.png"/>

**ibet-Prime は ibet network 向けの証券トークン管理システムです。**

## 機能概要

- ibet-Prime is an API service that enables the issuance and management of security tokens on the [ibet network](https://github.com/BoostryJP/ibet-Network).
- ibet-Prime は、 [ibet network](https://github.com/BoostryJP/ibet-Network) 上で証券トークンの発行、期中管理を行うことができる API サービスです。
- [ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract) プロジェクトで開発されているトークンや様々なスマートコントラクトをサポートしています。
- 証券トークンの台帳管理システムとして、ibet-Prime は日本の法令要件として必要な様々な機能群を提供します。
- フロントエンドのアプリケーションから ibet-Prime の API を呼び出すことによって、簡単に証券トークンの管理サービスを構築することが可能です。

## 依存

- [Python3](https://www.python.org/downloads/release/python-3811/) - バージョン 3.11
- [PostgreSQL](https://www.postgresql.org/) - バージョン 15
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - [ibet-Network](https://github.com/BoostryJP/ibet-Network) の公式の GoQuorum をサポートしています。
  - 最新の [ganache](https://github.com/trufflesuite/ganache) (ganache-cli) をローカル開発およびユニットテストで利用しています。

## コントラクトのバージョン

* ibet-SmartContract: バージョン 22.12.0
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
- ibet-SmartContract の以下のコントラクトを事前にデプロイする必要があります。
  - TokenList
  - E2EMessaging

### パッケージインストール

以下のコマンドで Python パッケージをインストールします。
```bash
$ poetry install --no-root --only main -E ibet-explorer
```

### pre-commit hookのインストール
```bash
$ poetry run pre-commit install
```

### 環境変数の設定

主要な環境変数は以下の通りです。

<table style="border-collapse: collapse" id="env-table">
    <tr bgcolor="#000000">
        <th style="width: 25%">環境変数名</th>
        <th style="width: 10%">必須</th>
        <th style="width: 30%">詳細</th>
        <th>設定例</th>
    </tr>
    <tr>
        <td>DATABASE_URL</td>
        <td>False</td>
        <td nowrap>データベース URL</td>
        <td>postgresql+psycopg://issuerapi:issuerapipass@localhost:5432/issuerapidb</td>
    </tr>
    <tr>
        <td>TEST_DATABASE_URL</td>
        <td>False</td>
        <td nowrap>テスト用データベース URL</td>
        <td>postgresql+psycopg://issuerapi:issuerapipass@localhost:5432/issuerapidb</td>
    </tr>
    <tr>
        <td>DATABASE_SCHEMA</td>
        <td>False</td>
        <td nowrap>データベースのスキーマ</td>
        <td></td>
    </tr>
    <tr>
        <td>WEB3_HTTP_PROVIDER</td>
        <td>False</td>
        <td nowrap>Web3 プロバイダー</td>
        <td>http://localhost:8545</td>
    </tr>
    <tr>
        <td>CHAIN_ID</td>
        <td>False</td>
        <td nowrap>ブロックチェーンネットワーク ID</td>
        <td>1010032</td>
    </tr>
    <tr>
        <td>TOKEN_LIST_CONTRACT_ADDRESS</td>
        <td>True</td>
        <td nowrap>TokenList コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>E2E_MESSAGING_CONTRACT_ADDRESS</td>
        <td>True</td>
        <td nowrap>E2EMessaging コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>TZ</td>
        <td>False</td>
        <td nowrap>タイムゾーン</td>
        <td>Asia/Tokyo</td>
    </tr>
</table>

その他の環境変数の設定は、`config.py` で確認することができます。

### DB マイグレーション

[migrations/README.md](migrations/README.md) を確認してください。

## サーバーの起動

API サーバーの起動は、以下を実行します。
```bash
$ ./run.sh server (Press CTRL+C to quit)
```

ブラウザで、[http://0.0.0.0:5000](http://0.0.0.0:5000) を開くと、以下のJSONのレスポンスを確認できるはずです。
```json
{"server":"ibet-Prime"}
```

### API 仕様書

#### Swagger UI

サーバーを起動した状態で、[http://0.0.0.0:5000/docs](http://0.0.0.0:5000/docs) を開いてください。

Swagger UI 形式のドキュメントを参照することができるはずです。

![swagger](https://user-images.githubusercontent.com/963333/146362141-da0fc0d2-1518-4041-a274-be2b743966a1.png)


#### ReDoc

同様に、[http://0.0.0.0:5000/redoc](http://0.0.0.0:5000/redoc) を開いてください。

ReDoc 形式のドキュメントを参照することができるはずです。

![redoc](https://user-images.githubusercontent.com/963333/146362775-c1ec56fa-f0b0-48a4-8926-75c2b7159c90.png)


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
