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
import os
import sys
import time
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import DATABASE_URL, ZERO_ADDRESS
from app.model.db import Token, TokenType, IDXPersonalInfo, Account, AccountRsaKeyTemporary
from app.model.blockchain import PersonalInfoContract, IbetShareContract, IbetStraightBondContract
import batch_log

process_name = "PROCESSOR-Account-RSA-Key-Temporary"
LOG = batch_log.get_logger(process_name=process_name)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_completed(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_account(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_completed(self, issuer_address):
        temporary = self.db.query(AccountRsaKeyTemporary). \
            filter(Account.issuer_address == issuer_address). \
            first()
        if temporary is not None:
            self.db.delete(temporary)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db

    def process(self):

        temporary_list = self.db.query(AccountRsaKeyTemporary).all()
        for temporary in temporary_list:

            contract_accessor_list = self.__get_personal_info_contract_accessor_list(temporary.issuer_address)

            # Get target PersonalInfo account address
            idx_personal_info_list = self.db.query(IDXPersonalInfo).filter(
                IDXPersonalInfo.issuer_address == temporary.issuer_address).all()

            count = len(idx_personal_info_list)
            completed_count = 0
            for idx_personal_info in idx_personal_info_list:

                # Get target PersonalInfo contract accessor
                for contract_accessor in contract_accessor_list:
                    is_registered = contract_accessor. \
                        personal_info_contract.functions. \
                        isRegistered(). \
                        call(idx_personal_info.account_address, idx_personal_info.issuer_address)
                    if is_registered:
                        target_contract_accessor = contract_accessor
                        break

                is_modify = self.__modify_personal_info(temporary, idx_personal_info, target_contract_accessor)
                if not is_modify:
                    # Confirm after being reflected in Contract.
                    # Confirm to that modify data is not modified in the next process.
                    completed_count += 1

            if count == completed_count:
                self.sink.on_completed(temporary.issuer_address)
                self.sink.flush()

    def __get_personal_info_contract_accessor_list(self, issuer_address):
        token_list = self.db.query(Token).filter(Token.issuer_address == issuer_address).all()
        personal_info_contract_list = set()
        for token in token_list:
            if token.type == TokenType.IBET_SHARE:
                token_contract = IbetShareContract.get(token.token_address)
            elif token.type == TokenType.IBET_STRAIGHT_BOND:
                token_contract = IbetStraightBondContract.get(token.token_address)
            else:
                continue

            contract_address = token_contract.personal_info_contract_address
            if contract_address != ZERO_ADDRESS:
                personal_info_contract_list.add(
                    PersonalInfoContract(
                        self.db,
                        issuer_address=issuer_address,
                        contract_address=contract_address))

        return personal_info_contract_list

    def __modify_personal_info(self, temporary, idx_personal_info, personal_info_contract_accessor):

        # Unset information assumes completed.
        personal_info_state = personal_info_contract_accessor.personal_info_contract.functions. \
            personal_info(idx_personal_info.account_address, idx_personal_info.issuer_address). \
            call()
        encrypted_info = personal_info_state[2]
        if encrypted_info == "":
            return False

        # If previous rsa key decrypted succeed, need modify.
        org_rsa_private_key = personal_info_contract_accessor.issuer.rsa_private_key
        personal_info_contract_accessor.issuer.rsa_private_key = temporary.rsa_private_key
        info = personal_info_contract_accessor.get_info(idx_personal_info.account_address)
        personal_info_contract_accessor.issuer.rsa_private_key = org_rsa_private_key
        default_info = {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None
        }
        if info == default_info:
            return False

        # Modify personal information
        personal_info_contract_accessor.modify_info(idx_personal_info.account_address, info)
        return True


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)
LOG.info("Service started successfully")

while True:
    try:
        processor.process()
        logging.debug("Processed")
    except Exception as ex:
        logging.exception(ex)

    time.sleep(10)
