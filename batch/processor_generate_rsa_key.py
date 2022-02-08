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

from Crypto import Random
from Crypto.PublicKey import RSA
from sqlalchemy import (
    create_engine,
    or_
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import DATABASE_URL
from app.model.db import (
    Account,
    AccountRsaStatus
)
from app.utils.e2ee_utils import E2EEUtils
import batch_log

process_name = "PROCESSOR-Generate-RSA-Key"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False)


class Processor:

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            account_list = self.__get_account_list(db_session=db_session)

            for account in account_list:
                # rsa_passphrase is encrypted, so decrypt it.
                passphrase = E2EEUtils.decrypt(account.rsa_passphrase)

                LOG.info(f"Generate Start: issuer_address={account.issuer_address}")
                rsa_private_pem, rsa_public_pem = self.__generate_rsa_key(passphrase)
                LOG.info(f"Generate End: issuer_address={account.issuer_address}")

                self.__sink_on_account(
                    db_session=db_session,
                    issuer_address=account.issuer_address,
                    rsa_private_pem=rsa_private_pem,
                    rsa_public_pem=rsa_public_pem
                )
                db_session.commit()
        finally:
            db_session.close()

    def __get_account_list(self, db_session: Session):
        account_list = db_session.query(Account). \
            filter(
            or_(
                Account.rsa_status == AccountRsaStatus.CREATING.value,
                Account.rsa_status == AccountRsaStatus.CHANGING.value)). \
            all()

        return account_list

    def __generate_rsa_key(self, passphrase: str):
        random_func = Random.new().read
        rsa = RSA.generate(10240, random_func)
        rsa_private_pem = rsa.exportKey(format="PEM", passphrase=passphrase).decode()
        rsa_public_pem = rsa.publickey().exportKey().decode()

        return rsa_private_pem, rsa_public_pem

    @staticmethod
    def __sink_on_account(db_session: Session, issuer_address: str, rsa_private_pem: str, rsa_public_pem: str):
        account = db_session.query(Account). \
            filter(Account.issuer_address == issuer_address). \
            first()
        if account is not None:
            rsa_status = AccountRsaStatus.SET.value
            if account.rsa_status == AccountRsaStatus.CHANGING.value:
                # NOTE: rsa_status is updated to AccountRsaStatus.SET,
                #       when PersonalInfo modify is completed on the other batch.
                rsa_status = AccountRsaStatus.CHANGING.value
            account.rsa_private_key = rsa_private_pem
            account.rsa_public_key = rsa_public_pem
            account.rsa_status = rsa_status
            db_session.merge(account)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.process()
            LOG.debug("Processed")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(10)


if __name__ == "__main__":
    main()
