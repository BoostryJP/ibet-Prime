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

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import (
    DATABASE_URL,
    ZERO_ADDRESS
)
from app.model.db import (
    Token,
    TokenType,
    IDXPersonalInfo,
    Account,
    AccountRsaKeyTemporary,
    AccountRsaStatus
)
from app.model.blockchain import (
    PersonalInfoContract,
    IbetShareContract,
    IbetStraightBondContract
)
import batch_log

process_name = "PROCESSOR-Modify-Personal-Info"
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
            sink.on_completed(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_completed(self, issuer_address):
        account = self.db.query(Account). \
            filter(Account.issuer_address == issuer_address). \
            first()
        if account is not None:
            account.rsa_status = AccountRsaStatus.SET.value
            self.db.merge(account)
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

        temporary_list = self.__get_temporary_list()
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
                        isRegistered(idx_personal_info.account_address, idx_personal_info.issuer_address). \
                        call()
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

    def __get_temporary_list(self):
        # NOTE: rsa_private_key in Account DB and AccountRsaKeyTemporary DB is the same when API is executed,
        #       Account DB is changed when RSA generate batch is completed.
        temporary_list = self.db.query(AccountRsaKeyTemporary). \
            join(Account, AccountRsaKeyTemporary.issuer_address == Account.issuer_address). \
            filter(AccountRsaKeyTemporary.rsa_private_key != Account.rsa_private_key). \
            all()

        return temporary_list

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
        # Backup origin RSA
        org_rsa_private_key = personal_info_contract_accessor.issuer.rsa_private_key
        org_rsa_passphrase = personal_info_contract_accessor.issuer.rsa_passphrase
        # Replace RSA
        personal_info_contract_accessor.issuer.rsa_private_key = temporary.rsa_private_key
        personal_info_contract_accessor.issuer.rsa_passphrase = temporary.rsa_passphrase
        # Modify
        LOG.info(
            f"Modify Start: issuer_address={temporary.issuer_address}, account_address={idx_personal_info.account_address}")
        info = personal_info_contract_accessor.get_info(idx_personal_info.account_address)
        LOG.info(
            f"Modify End: issuer_address={temporary.issuer_address}, account_address={idx_personal_info.account_address}")
        # Back RSA
        personal_info_contract_accessor.issuer.rsa_private_key = org_rsa_private_key
        personal_info_contract_accessor.issuer.rsa_passphrase = org_rsa_passphrase
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


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.process()
            LOG.debug("Processed")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(10)


if __name__ == "__main__":
    main()
