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
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import (
    DATABASE_URL,
    ZERO_ADDRESS,
    INDEXER_SYNC_INTERVAL
)
from app.model.db import (
    Token,
    IDXPersonalInfo,
    IDXPersonalInfoBlockNumber
)
from app.model.blockchain import PersonalInfoContract
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import ServiceUnavailableError
import batch_log

process_name = "INDEXER-Personal-Info"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def __init__(self):
        self.latest_block = web3.eth.blockNumber
        self.personal_info_contract_list = []

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            self.__refresh_personal_info_list(db_session=db_session)
            # most recent blockNumber that has been synchronized with DB
            block_number = self.__get_block_number(db_session=db_session)
            latest_block = web3.eth.blockNumber  # latest blockNumber

            if block_number >= latest_block:
                LOG.debug("skip Process")
            else:
                self.__sync_all(
                    db_session=db_session,
                    block_from=block_number + 1,
                    block_to=latest_block)
                self.__set_block_number(
                    db_session=db_session,
                    block_number=latest_block)
                db_session.commit()
        finally:
            db_session.close()

    def __refresh_personal_info_list(self, db_session: Session):
        self.personal_info_contract_list.clear()
        _tokens = db_session.query(Token).filter(Token.token_status == 1).all()
        tmp_list = []
        for _token in _tokens:
            abi = _token.abi
            token_contract = web3.eth.contract(
                address=_token.token_address,
                abi=abi
            )
            personal_info_address = ContractUtils.call_function(
                contract=token_contract,
                function_name="personalInfoAddress",
                args=(),
                default_returns=ZERO_ADDRESS
            )
            if personal_info_address != ZERO_ADDRESS:
                tmp_list.append({
                    "issuer_address": _token.issuer_address,
                    "personal_info_address": personal_info_address
                })

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

    def __get_block_number(self, db_session: Session):
        """Get the most recent blockNumber"""
        block_number = db_session.query(IDXPersonalInfoBlockNumber).first()
        if block_number is None:
            return 0
        else:
            return block_number.latest_block_number

    def __set_block_number(self, db_session: Session, block_number: int):
        """Setting the most recent blockNumber"""
        _block_number = db_session.query(IDXPersonalInfoBlockNumber).first()
        if _block_number is None:
            _block_number = IDXPersonalInfoBlockNumber()
            _block_number.latest_block_number = block_number
        else:
            _block_number.latest_block_number = block_number
        db_session.merge(_block_number)

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info(f"syncing from={block_from}, to={block_to}")
        self.__sync_personal_info_register(
            db_session=db_session,
            block_from=block_from,
            block_to=block_to)
        self.__sync_personal_info_modify(
            db_session=db_session,
            block_from=block_from,
            block_to=block_to
        )

    def __sync_personal_info_register(self, db_session: Session, block_from, block_to):
        for _personal_info_contract in self.personal_info_contract_list:
            try:
                register_event_list = _personal_info_contract.get_register_event(block_from, block_to)
                for event in register_event_list:
                    args = event["args"]
                    account_address = args.get("account_address", ZERO_ADDRESS)
                    link_address = args.get("link_address", ZERO_ADDRESS)
                    if link_address == _personal_info_contract.issuer.issuer_address:
                        block = web3.eth.get_block(event["blockNumber"])
                        timestamp = datetime.utcfromtimestamp(block["timestamp"])
                        decrypted_personal_info = _personal_info_contract.get_info(
                            account_address=account_address,
                            default_value=None
                        )
                        self.__sink_on_personal_info(
                            db_session=db_session,
                            account_address=account_address,
                            issuer_address=link_address,
                            personal_info=decrypted_personal_info,
                            timestamp=timestamp
                        )
                        db_session.commit()
            except Exception:
                LOG.exception("An exception occurred during event synchronization")

    def __sync_personal_info_modify(self, db_session: Session, block_from, block_to):
        for _personal_info_contract in self.personal_info_contract_list:
            try:
                register_event_list = _personal_info_contract.get_modify_event(block_from, block_to)
                for event in register_event_list:
                    args = event["args"]
                    account_address = args.get("account_address", ZERO_ADDRESS)
                    link_address = args.get("link_address", ZERO_ADDRESS)
                    if link_address == _personal_info_contract.issuer.issuer_address:
                        block = web3.eth.get_block(event["blockNumber"])
                        timestamp = datetime.utcfromtimestamp(block["timestamp"])
                        decrypted_personal_info = _personal_info_contract.get_info(
                            account_address=account_address,
                            default_value=None
                        )
                        self.__sink_on_personal_info(
                            db_session=db_session,
                            account_address=account_address,
                            issuer_address=link_address,
                            personal_info=decrypted_personal_info,
                            timestamp=timestamp
                        )
                        db_session.commit()
            except Exception:
                LOG.exception("An exception occurred during event synchronization")

    @staticmethod
    def __sink_on_personal_info(db_session: Session,
                                account_address: str,
                                issuer_address: str,
                                personal_info: dict,
                                timestamp: datetime):
        _personal_info = db_session.query(IDXPersonalInfo). \
            filter(IDXPersonalInfo.account_address == to_checksum_address(account_address)). \
            filter(IDXPersonalInfo.issuer_address == to_checksum_address(issuer_address)). \
            first()
        if _personal_info is not None:
            _personal_info.personal_info = personal_info
            _personal_info.modified = timestamp
            db_session.merge(_personal_info)
            LOG.debug(f"Modify: account_address={account_address}, issuer_address={issuer_address}")
        else:
            _personal_info = IDXPersonalInfo()
            _personal_info.account_address = account_address
            _personal_info.issuer_address = issuer_address
            _personal_info.personal_info = personal_info
            _personal_info.created = timestamp
            _personal_info.modified = timestamp
            db_session.add(_personal_info)
            LOG.debug(f"Register: account_address={account_address}, issuer_address={issuer_address}")


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.process()
            LOG.debug("Processed")
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()