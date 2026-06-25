<p align="center">
  <img width="33%" src="https://user-images.githubusercontent.com/963333/71672471-6383c080-2db9-11ea-85b6-8815519652ec.png"/>
</p>

# ibet-Prime

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-26.6-blue.svg?cacheSeconds=2592000" />
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

- [Python3](https://www.python.org/downloads/release/python-3142/) - version 3.14
- [PostgreSQL](https://www.postgresql.org/) - version 17
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - We support the official GoQuorum node of [ibet-Network](https://github.com/BoostryJP/ibet-Network).
  - We use [Anvil](https://www.getfoundry.sh/anvil) for local development and unit testing.


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
- An ibet node must be available and connected.
  - The TokenList and E2EMessaging contracts from the ibet-SmartContract project must be deployed in advance.
- An Ethereum node is optional, but can be set up and connected.
- An Avalanche node is optional, but can be set up and connected.

### Install packages

Create virtual environment with:
```bash
$ uv venv
```

Install python packages with:
```bash
$ make install
```

### Setting environment variables

See [docs/environment_variables.md](docs/environment_variables.md) for the list of environment variables.
Set the required variables according to each use case.

### DB migrations

See [migrations/README.md](migrations/README.md).


## Development Information

### Setting environment variables

You can create a `.env` file to define local environment variables.

### Running tests

For test container startup, see [docker-compose.yml](docker-compose.yml).
When running individual test cases, set up a local Python runtime environment and configure the required environment variables first.


## Starting the Server

You can start the API server with:
```bash
$ make run
```

Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000).

You will see the JSON response as:
```json
{"server":"ibet-Prime"}
```

### API docs

Now go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

You will see the automatic interactive API documentation provided by Swagger UI:

![swagger](https://user-images.githubusercontent.com/963333/146362141-da0fc0d2-1518-4041-a274-be2b743966a1.png)

And now, go to [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc).
You will see the alternative automatic documentation provided by ReDoc.

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
