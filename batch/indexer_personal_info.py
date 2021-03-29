"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), "JST")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import BadFunctionCallOutput
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import WEB3_HTTP_PROVIDER, DATABASE_URL, ZERO_ADDRESS
from app.model.db import Token, IDXPersonalInfo, IDXPersonalInfoBlockNumber
from app.model.blockchain import PersonalInfoContract
import batch_log
process_name = "INDEXER-Personal-Info"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_personal_info(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_personal_info(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_personal_info(self, account_address, issuer_address, personal_info, timestamp):
        _personal_info = self.db.query(IDXPersonalInfo). \
            filter(IDXPersonalInfo.account_address == to_checksum_address(account_address)). \
            filter(IDXPersonalInfo.issuer_address == to_checksum_address(issuer_address)). \
            first()
        if _personal_info is not None:
            _personal_info.personal_info = personal_info
            _personal_info.modified = timestamp
            self.db.merge(_personal_info)
            LOG.info(f"Modify: account_address={account_address}, issuer_address={issuer_address}")
        else:
            _personal_info = IDXPersonalInfo()
            _personal_info.account_address = account_address
            _personal_info.issuer_address = issuer_address
            _personal_info.personal_info = personal_info
            _personal_info.created = timestamp
            _personal_info.modified = timestamp
            self.db.add(_personal_info)
            LOG.info(f"Register: account_address={account_address}, issuer_address={issuer_address}")

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.personal_info_contract_list = []

    def process(self):
        self.__refresh_personal_info_list()
        block_number = self.__get_block_number()  # most recent blockNumber that has been synchronized with DB
        latest_block = web3.eth.blockNumber  # latest blockNumber

        if block_number >= latest_block:
            LOG.debug("skip Process")
        else:
            self.__sync_all(block_number + 1, latest_block)
            self.__set_block_number(latest_block)
            self.sink.flush()

    def __refresh_personal_info_list(self):
        self.personal_info_contract_list.clear()
        _tokens = self.db.query(Token).all()
        tmp_list = []
        for _token in _tokens:
            try:
                abi = _token.abi
                token_contract = web3.eth.contract(
                    address=_token.token_address,
                    abi=abi
                )
                personal_info_address = token_contract.functions.personalInfoAddress().call()
                if personal_info_address != ZERO_ADDRESS:
                    tmp_list.append({
                        "issuer_address": _token.issuer_address,
                        "personal_info_address": personal_info_address
                    })
            except BadFunctionCallOutput:
                LOG.warning(f"Failed to get the PersonalInfo address: token = {_token.token_address}")

        # Remove duplicates from the list
        unique_list = list(map(json.loads, set(map(json.dumps, tmp_list))))
        # Get a list of PersonalInfoContracts
        for item in unique_list:
            personal_info_contract = PersonalInfoContract(
                db_session,
                issuer_address=item["issuer_address"],
                contract_address=item["personal_info_address"]
            )
            self.personal_info_contract_list.append(personal_info_contract)

    def __get_block_number(self):
        """Get the most recent blockNumber"""
        block_number = self.db.query(IDXPersonalInfoBlockNumber).first()
        if block_number is None:
            return 0
        else:
            return block_number.latest_block_number

    def __set_block_number(self, block_number: int):
        """Setting the most recent blockNumber"""
        _block_number = self.db.query(IDXPersonalInfoBlockNumber).first()
        if _block_number is None:
            _block_number = IDXPersonalInfoBlockNumber()
            _block_number.latest_block_number = block_number
        else:
            _block_number.latest_block_number = block_number
        self.db.merge(_block_number)

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info(f"syncing from={block_from}, to={block_to}")
        self.__sync_personal_info_register(block_from, block_to)
        self.__sync_personal_info_modify(block_from, block_to)

    def __sync_personal_info_register(self, block_from, block_to):
        for _personal_info_contract in self.personal_info_contract_list:
            try:
                register_event_list = _personal_info_contract.get_register_event(block_from, block_to)
                for event in register_event_list:
                    args = event["args"]
                    account_address = args.get("account_address", ZERO_ADDRESS)
                    link_address = args.get("link_address", ZERO_ADDRESS)
                    if link_address == _personal_info_contract.issuer.issuer_address:
                        block = web3.eth.getBlock(event["blockNumber"])
                        timestamp = datetime.fromtimestamp(block["timestamp"])
                        decrypted_personal_info = _personal_info_contract.get_info(
                            account_address=account_address
                        )
                        self.sink.on_personal_info(
                            account_address=account_address,
                            issuer_address=link_address,
                            personal_info=decrypted_personal_info,
                            timestamp=timestamp
                        )
                        self.sink.flush()
            except Exception as err:
                LOG.error(err)

    def __sync_personal_info_modify(self, block_from, block_to):
        for _personal_info_contract in self.personal_info_contract_list:
            try:
                register_event_list = _personal_info_contract.get_modify_event(block_from, block_to)
                for event in register_event_list:
                    args = event["args"]
                    account_address = args.get("account_address", ZERO_ADDRESS)
                    link_address = args.get("link_address", ZERO_ADDRESS)
                    if link_address == _personal_info_contract.issuer.eth_account:
                        block = web3.eth.getBlock(event["blockNumber"])
                        timestamp = datetime.fromtimestamp(block["timestamp"])
                        decrypted_personal_info = _personal_info_contract.get_info(
                            account_address=account_address
                        )
                        self.sink.on_personal_info(
                            account_address=account_address,
                            issuer_address=link_address,
                            personal_info=decrypted_personal_info,
                            timestamp=timestamp
                        )
                        self.sink.flush()
            except Exception as err:
                LOG.error(err)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)
LOG.info("Service started successfully")

while True:
    try:
        processor.process()
        LOG.debug("Processed")
    except Exception as ex:
        LOG.exception(ex)

    time.sleep(10)
