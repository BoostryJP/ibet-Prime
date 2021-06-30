# ibet-Prime

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-0.1-blue.svg?cacheSeconds=2592000" />
  <a href="https:/doc.com" target="_blank">
    <img alt="Documentation" src="https://img.shields.io/badge/documentation-yes-brightgreen.svg" />
  </a>
  <a href="#" target="_blank">
    <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
  </a>
</p>


## About this repository

ibet-Prime is an API service for issuers to issue various tokens on the [ibet network](https://github.com/BoostryJP/ibet-Network).

It supports the tokens developed by [ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract).


## Supported contract version

* ibet-SmartContract: version 21.6.0


## Prerequisites

Set up an execution environment of Python 3.8 or higher.


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
