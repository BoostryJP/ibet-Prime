<p align="center">
  <img width="33%" src="https://user-images.githubusercontent.com/963333/71672471-6383c080-2db9-11ea-85b6-8815519652ec.png"/>
</p>

# ibet-Prime

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-25.9-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

English | [日本語](./README_JA.md)

**The ibet-Prime security token management system for ibet network.**

## Features

- ibet-Prime is an API service that enables the issuance and management of security tokens on the [ibet network](https://github.com/BoostryJP/ibet-Network).
- It supports tokens and various smart contracts developed by the [ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract) project.
- As a security token ledger management system, ibet-Prime provides a variety of functions required under Japanese regulations.
- By integrating the ibet-Prime API into your front-end application, you can easily build a security token management service.

## Dependencies

- [Python3](https://www.python.org/downloads/release/python-3811/) - version 3.12
- [PostgreSQL](https://www.postgresql.org/) - version 16
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - We support the official GoQuorum node of [ibet-Network](https://github.com/BoostryJP/ibet-Network).
  - We use [hardhat network](https://hardhat.org/hardhat-network/) for local development and unit testing, and we use the latest version.


## Supported ibet smart contract version

* ibet-SmartContract: Supports the latest version of contract specifications.
* See [details](./contracts/contract_version.md).


## Setup

### Prerequisites

- A Python runtime environment must be set up.
- The database must be created on PostgreSQL beforehand.
  - By default, the following settings are required:
    - User: issuerapi
    - Password: issuerapipass
    - Database: issuerapidb
    - Test database: issuerapidb_test
- The TokenList and E2EMessaging contracts from the ibet-SmartContract project must be deployed in advance.

### Install packages

Create virtual environment with:
```bash
$ uv venv
```

Install python packages with:
```bash
$ uv sync --frozen --no-install-project --no-dev --all-extras
```

### Install pre-commit hook
```bash
$ uv run pre-commit install
```

### Install hardhat
```bash
$ npm install
```

### Setting environment variables

The main environment variables are as follows. 

<table style="border-collapse: collapse" id="env-table">
    <tr bgcolor="#000000">
        <th style="width: 25%">Variable Name</th>
        <th style="width: 10%">Required</th>
        <th style="width: 30%">Details</th>
        <th>Example</th>
    </tr>
    <tr>
        <td>DATABASE_URL</td>
        <td>False</td>
        <td nowrap>Database URL</td>
        <td>postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb</td>
    </tr>
    <tr>
        <td>TEST_DATABASE_URL</td>
        <td>False</td>
        <td nowrap>Test database URL</td>
        <td>postgresql://issuerapi:issuerapipass@localhost:5432/issuerapidb</td>
    </tr>
    <tr>
        <td>DATABASE_SCHEMA</td>
        <td>False</td>
        <td nowrap>Database schema</td>
        <td></td>
    </tr>
    <tr>
        <td>WEB3_HTTP_PROVIDER</td>
        <td>False</td>
        <td nowrap>Web3 provider for ibet network</td>
        <td>http://localhost:8545</td>
    </tr>
    <tr>
        <td>CHAIN_ID</td>
        <td>False</td>
        <td nowrap>Blockchain network ID</td>
        <td>1010032</td>
    </tr>
    <tr>
        <td>TOKEN_LIST_CONTRACT_ADDRESS</td>
        <td>True</td>
        <td nowrap>TokenList contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>E2E_MESSAGING_CONTRACT_ADDRESS</td>
        <td>True</td>
        <td nowrap>E2EMessaging contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>BC_EXPLORER_ENABLED</td>
        <td>False</td>
        <td nowrap>Whether to use the BC Explorer</td>
        <td>0(not use) / 1(use)</td>
    </tr>
    <tr>
        <td>TZ</td>
        <td>False</td>
        <td nowrap>Timezone</td>
        <td>Asia/Tokyo</td>
    </tr>
    <tr>
        <td>ETH_WEB3_HTTP_PROVIDER</td>
        <td>False</td>
        <td nowrap>Web3 provider for Ethereum network</td>
        <td>http://localhost:8545</td>
    </tr>
    <tr>
        <td>IBET_WST_FEATURE_ENABLED</td>
        <td>False</td>
        <td nowrap>Weather to use IbetWST features</td>
        <td>1</td>
    </tr>
</table>

Other environment variables that can be set can be found in `config.py`.

### DB migrations

See [migrations/README.md](migrations/README.md).


## Starting the Server

You can start the API server with:
```bash
$ ./run.sh server (Press CTRL+C to quit)
```

Open your browser at [http://0.0.0.0:5000](http://0.0.0.0:5000).

You will see the JSON response as:
```json
{"server":"ibet-Prime"}
```

### API docs

#### Swagger UI

Now go to [http://0.0.0.0:5000/docs](http://0.0.0.0:5000/docs).

You will see the automatic interactive API documentation provided by Swagger UI:

![swagger](https://user-images.githubusercontent.com/963333/146362141-da0fc0d2-1518-4041-a274-be2b743966a1.png)


#### ReDoc

And now, go to [http://0.0.0.0:5000/redoc](http://0.0.0.0:5000/redoc).

You will see the alternative automatic documentation provided by ReDoc:

![redoc](https://user-images.githubusercontent.com/963333/146362775-c1ec56fa-f0b0-48a4-8926-75c2b7159c90.png)


## Branching model

This repository is version controlled using the following flow.

![branching_model](https://user-images.githubusercontent.com/963333/153910560-2c67f8ad-73ae-4aaa-9e9f-9242643f6098.png)

## License

ibet-Prime is licensed under the Apache License, Version 2.0.

## Contact information

We are committed to open-sourcing our work to support your use cases. 
We want to know how you use this library and what problems it helps you to solve. 
We have two communication channels for you to contact us:

* A [public discussion group](https://github.com/BoostryJP/ibet-Prime/discussions)
where we will also share our preliminary roadmap, updates, events, and more.

* A private email alias at
[dev@boostry.co.jp](mailto:dev@boostry.co.jp)
where you can reach out to us directly about your use cases and what more we can
do to help and improve the library.
  
Please refrain from sending any sensitive or confidential information. 
If you wish to delete a message you've previously sent, please contact us.

## Sponsors

[BOOSTRY Co., Ltd.](https://boostry.co.jp/)
