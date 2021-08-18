# ibet-Prime

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-21.8-blue.svg?cacheSeconds=2592000" />
  <a href="https:/doc.com" target="_blank">
    <img alt="Documentation" src="https://img.shields.io/badge/documentation-yes-brightgreen.svg" />
  </a>
  <a href="#" target="_blank">
    <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
  </a>
</p>

<img width="33%" align="right" src="https://user-images.githubusercontent.com/963333/71672471-6383c080-2db9-11ea-85b6-8815519652ec.png"/>

**The ibet-Prime security token management system for ibet network.**

## Features

- ibet-Prime is an API service that allows issuers to issue and manage security tokens on the [ibet network](https://github.com/BoostryJP/ibet-Network). 
- It supports tokens developed by the [ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract) project and various smart contracts.
- It provides the functions required by Japanese laws and regulations as a security token ledger management function.
- By calling the ibet-Prime API from your own front-end application, you can easily build a security token management service.

## Dependencies

- [python3](https://www.python.org/downloads/release/python-3811/) version 3.8 or greater
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - We support the official GoQuorum node of [ibet-Network](https://github.com/BoostryJP/ibet-Network).
  - We use [ganache-cli](https://github.com/trufflesuite/ganache-cli) for local development and unit testing, and we use the latest version.


## Supported ibet smart contract version

* ibet-SmartContract: version 21.6.0


## Starting and Stopping the Server
Install packages
```bash
$ pip install -r requirements.txt
```

Create database tables
```bash
$ ./bin/run_migration.sh init
```

You can start (or stop) the API server with:
```bash
$ ./bin/run_server.sh start(stop)
```

## Branching model

<p align='center'>
  <img alt="ibet" src="https://user-images.githubusercontent.com/963333/128751565-3268b1e3-185b-4f09-870f-b6d96519eb54.png"/>
</p>


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
