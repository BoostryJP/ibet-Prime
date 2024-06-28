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

import asyncio
import sys
import time
from datetime import UTC, datetime
from typing import Sequence

import uvloop
from Crypto import Random
from Crypto.PublicKey import RSA
from eth_keyfile import decode_keyfile_json
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import (
    ContractRevertError,
    SendTransactionError,
    ServiceUnavailableError,
)
from app.model.blockchain import E2EMessaging
from app.model.db import E2EMessagingAccount, E2EMessagingAccountRsaKey
from app.utils.contract_utils import AsyncContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import batch_log
from config import E2E_MESSAGING_CONTRACT_ADDRESS, ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL

"""
[PROCESSOR-Rotate-E2E-Messaging-RSA-Key]

Processor for key rotation for encrypted E2E messaging on the blockchain
"""

process_name = "PROCESSOR-Rotate-E2E-Messaging-RSA-Key"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    def __init__(self):
        self.e2e_messaging_contract = AsyncContractUtils.get_contract(
            contract_name="E2EMessaging",
            contract_address=E2E_MESSAGING_CONTRACT_ADDRESS,
        )

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            base_time = int(time.time())
            e2e_messaging_account_list = await self.__get_e2e_messaging_account_list(
                db_session=db_session
            )
            for _e2e_messaging_account in e2e_messaging_account_list:
                await self.__auto_generate_rsa_key(
                    db_session=db_session,
                    base_time=base_time,
                    e2e_messaging_account=_e2e_messaging_account,
                )
                await self.__rotate_rsa_key(
                    db_session=db_session, e2e_messaging_account=_e2e_messaging_account
                )
                await db_session.commit()
        finally:
            await db_session.close()

    @staticmethod
    async def __get_e2e_messaging_account_list(db_session: AsyncSession):
        e2e_messaging_account_list: Sequence[E2EMessagingAccount] = (
            await db_session.scalars(
                select(E2EMessagingAccount)
                .where(E2EMessagingAccount.is_deleted == False)
                .order_by(E2EMessagingAccount.account_address)
            )
        ).all()
        return e2e_messaging_account_list

    @staticmethod
    async def __auto_generate_rsa_key(
        db_session: AsyncSession,
        base_time: int,
        e2e_messaging_account: E2EMessagingAccount,
    ):
        if e2e_messaging_account.rsa_key_generate_interval > 0:
            # Get latest RSA key
            _account_rsa_key: E2EMessagingAccountRsaKey | None = (
                await db_session.scalars(
                    select(E2EMessagingAccountRsaKey)
                    .where(
                        E2EMessagingAccountRsaKey.account_address
                        == e2e_messaging_account.account_address
                    )
                    .order_by(desc(E2EMessagingAccountRsaKey.block_timestamp))
                    .limit(1)
                )
            ).first()

            latest_time = int(_account_rsa_key.block_timestamp.timestamp())
            interval = e2e_messaging_account.rsa_key_generate_interval * 3600
            if base_time - latest_time < interval:
                # SKIP if within the interval
                return
            pass_phrase = E2EEUtils.decrypt(_account_rsa_key.rsa_passphrase)

            # Generate RSA key
            random_func = Random.new().read
            rsa = RSA.generate(4096, random_func)
            rsa_private_key = rsa.exportKey(
                format="PEM", passphrase=pass_phrase
            ).decode()
            rsa_public_key = rsa.publickey().exportKey().decode()

            # Register RSA Public key to Blockchain
            try:
                eoa_password = E2EEUtils.decrypt(e2e_messaging_account.eoa_password)
                private_key = decode_keyfile_json(
                    raw_keyfile_json=e2e_messaging_account.keyfile,
                    password=eoa_password.encode("utf-8"),
                )
            except Exception:
                LOG.exception(
                    f"Could not get the EOA private key: "
                    f"account_address={e2e_messaging_account.account_address}"
                )
                return
            try:
                tx_hash, _ = await E2EMessaging(
                    E2E_MESSAGING_CONTRACT_ADDRESS
                ).set_public_key(
                    public_key=rsa_public_key,
                    key_type="RSA4096",
                    tx_from=e2e_messaging_account.account_address,
                    private_key=private_key,
                )
                LOG.info(
                    f"New RSA key created: account_address={e2e_messaging_account.account_address}"
                )
            except ContractRevertError as e:
                LOG.warning(
                    f"Transaction reverted: account_address=<{e2e_messaging_account.account_address}> error_code:<{e.code}> error_msg:<{e.message}>"
                )
                return
            except SendTransactionError:
                LOG.warning(
                    f"Failed to send transaction: account_address={e2e_messaging_account.account_address}"
                )
                return

            # Register RSA key to DB
            block = await AsyncContractUtils.get_block_by_transaction_hash(
                tx_hash=tx_hash
            )
            _account_rsa_key = E2EMessagingAccountRsaKey()
            _account_rsa_key.transaction_hash = tx_hash
            _account_rsa_key.account_address = e2e_messaging_account.account_address
            _account_rsa_key.rsa_private_key = rsa_private_key
            _account_rsa_key.rsa_public_key = rsa_public_key
            _account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(pass_phrase)
            _account_rsa_key.block_timestamp = datetime.fromtimestamp(
                block["timestamp"], UTC
            ).replace(tzinfo=None)
            db_session.add(_account_rsa_key)

    @staticmethod
    async def __rotate_rsa_key(
        db_session: AsyncSession, e2e_messaging_account: E2EMessagingAccount
    ):
        if e2e_messaging_account.rsa_generation > 0:
            # Delete RSA key that exceeds the number of generations
            _account_rsa_key_over_generation_list: Sequence[
                E2EMessagingAccountRsaKey
            ] = (
                await db_session.scalars(
                    select(E2EMessagingAccountRsaKey)
                    .where(
                        E2EMessagingAccountRsaKey.account_address
                        == e2e_messaging_account.account_address
                    )
                    .order_by(desc(E2EMessagingAccountRsaKey.block_timestamp))
                    .offset(e2e_messaging_account.rsa_generation)
                )
            ).all()
            for _account_rsa_key in _account_rsa_key_over_generation_list:
                await db_session.delete(_account_rsa_key)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        start_time = time.time()
        try:
            await processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.error(ex)

        elapsed_time = time.time() - start_time
        await asyncio.sleep(
            max(ROTATE_E2E_MESSAGING_RSA_KEY_INTERVAL - elapsed_time, 0)
        )


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
