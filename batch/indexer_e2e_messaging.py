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
import base64
import json
import sys
import time
from datetime import UTC, datetime

import uvloop
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import unpad
from sqlalchemy import and_, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    E2EMessagingAccount,
    E2EMessagingAccountRsaKey,
    IDXE2EMessaging,
    IDXE2EMessagingBlockNumber,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper
from batch import free_malloc
from batch.utils import batch_log
from config import (
    E2E_MESSAGING_CONTRACT_ADDRESS,
    INDEXER_BLOCK_LOT_MAX_SIZE,
    INDEXER_SYNC_INTERVAL,
)

process_name = "INDEXER-E2E-Messaging"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


"""
Acceptable message formats follow.

{
  "type": "string",
  "text": {
    "cipher_key": "string(base64 encoded AES-256-CBC key encrypted with own RSA key)",
    "message": "string(base64 encoded message encrypted with `cipher_key`)"
  }
}

type's max length is 50.
decoded message's max length is 5000.
"""


class Processor:
    def __init__(self):
        self.e2e_messaging_contract = AsyncContractUtils.get_contract(
            contract_name="E2EMessaging",
            contract_address=E2E_MESSAGING_CONTRACT_ADDRESS,
        )

    async def process(self):
        db_session = BatchAsyncSessionLocal()
        try:
            # Get from_block_number and to_block_number for contract event filter
            latest_block = await web3.eth.block_number
            _from_block = await self.__get_idx_e2e_messaging_block_number(
                db_session=db_session
            )
            _to_block = _from_block + INDEXER_BLOCK_LOT_MAX_SIZE

            # Skip processing if the latest block is not counted up
            if _from_block >= latest_block:
                LOG.debug("skip process")
                return

            # Create index data with the upper limit of one process
            # as INDEXER_BLOCK_LOT_MAX_SIZE(1_000_000 blocks)
            if latest_block > _to_block:
                while _to_block < latest_block:
                    await self.__sync_all(
                        db_session=db_session,
                        block_from=_from_block + 1,
                        block_to=_to_block,
                    )
                    _to_block += INDEXER_BLOCK_LOT_MAX_SIZE
                    _from_block += INDEXER_BLOCK_LOT_MAX_SIZE
                await self.__sync_all(
                    db_session=db_session,
                    block_from=_from_block + 1,
                    block_to=latest_block,
                )
            else:
                await self.__sync_all(
                    db_session=db_session,
                    block_from=_from_block + 1,
                    block_to=latest_block,
                )

            await self.__set_idx_e2e_messaging_block_number(
                db_session=db_session, block_number=latest_block
            )
            await db_session.commit()
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")

    @staticmethod
    async def __get_idx_e2e_messaging_block_number(db_session: AsyncSession):
        _idx_e2e_messaging_block_number: IDXE2EMessagingBlockNumber | None = (
            await db_session.scalars(select(IDXE2EMessagingBlockNumber).limit(1))
        ).first()
        if _idx_e2e_messaging_block_number is None:
            return 0
        else:
            return _idx_e2e_messaging_block_number.latest_block_number

    @staticmethod
    async def __set_idx_e2e_messaging_block_number(
        db_session: AsyncSession, block_number: int
    ):
        _idx_e2e_messaging_block_number: IDXE2EMessagingBlockNumber | None = (
            await db_session.scalars(select(IDXE2EMessagingBlockNumber).limit(1))
        ).first()
        if _idx_e2e_messaging_block_number is None:
            _idx_e2e_messaging_block_number = IDXE2EMessagingBlockNumber()

        _idx_e2e_messaging_block_number.latest_block_number = block_number
        await db_session.merge(_idx_e2e_messaging_block_number)

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info(f"Syncing from={block_from}, to={block_to}")
        await self.__sync_message(db_session, block_from, block_to)

    async def __sync_message(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Message events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        try:
            events = await AsyncContractUtils.get_event_logs(
                contract=self.e2e_messaging_contract,
                event="Message",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                transaction_hash = event["transactionHash"].to_0x_hex()
                block_timestamp = datetime.fromtimestamp(
                    (await web3.eth.get_block(event["blockNumber"]))["timestamp"], UTC
                ).replace(tzinfo=None)
                args = event["args"]
                from_address = args["sender"]
                to_address = args["receiver"]
                send_timestamp = datetime.fromtimestamp(args["time"], UTC).replace(
                    tzinfo=None
                )
                text = args["text"]

                # Check if the message receiver is owned accounts
                _e2e_messaging_account = await self.__get_e2e_messaging_account(
                    db_session=db_session, to_address=to_address
                )
                if _e2e_messaging_account is None:
                    continue

                # Get the received message
                message_type = await self.__get_message(
                    db_session=db_session,
                    to_address=to_address,
                    text=text,
                    block_timestamp=block_timestamp,
                )
                if message_type is None:
                    continue
                message, _type = message_type

                await self.__sink_on_e2e_messaging(
                    db_session=db_session,
                    transaction_hash=transaction_hash,
                    from_address=from_address,
                    to_address=to_address,
                    send_timestamp=send_timestamp,
                    _type=_type,
                    message=message,
                    block_timestamp=block_timestamp,
                )
        except Exception:
            raise

    @staticmethod
    async def __get_e2e_messaging_account(db_session: AsyncSession, to_address: str):
        # NOTE: Self sending data is registered at the time of sending.
        _e2e_messaging_account: E2EMessagingAccount | None = (
            await db_session.scalars(
                select(E2EMessagingAccount)
                .where(
                    and_(
                        E2EMessagingAccount.account_address == to_address,
                        E2EMessagingAccount.is_deleted == False,
                    )
                )
                .limit(1)
            )
        ).first()
        return _e2e_messaging_account

    @staticmethod
    async def __get_message(
        db_session: AsyncSession, to_address: str, text: str, block_timestamp: datetime
    ):
        # Check message format
        try:
            text_dict = json.loads(text)
        except json.decoder.JSONDecodeError:
            LOG.warning(f"Message could not be decoded: text={text}")
            return None
        _type = text_dict.get("type")
        message_text = text_dict.get("text")
        if _type is None or message_text is None or len(_type) > 50:
            return None
        cipher_key = message_text.get("cipher_key")
        message = message_text.get("message")
        if cipher_key is None or message is None:
            LOG.warning(f"Message could not be decoded: text={text}")
            return None

        # Get RSA key
        account_rsa_key: E2EMessagingAccountRsaKey | None = (
            await db_session.scalars(
                select(E2EMessagingAccountRsaKey)
                .where(
                    and_(
                        E2EMessagingAccountRsaKey.account_address == to_address,
                        E2EMessagingAccountRsaKey.block_timestamp <= block_timestamp,
                    )
                )
                .order_by(desc(E2EMessagingAccountRsaKey.block_timestamp))
                .limit(1)
            )
        ).first()
        if account_rsa_key is None:
            LOG.warning(f"RSA key does not exist: account_address={to_address}")
            return None

        # Decrypt AES key
        rsa_private_key = account_rsa_key.rsa_private_key
        rsa_passphrase = E2EEUtils.decrypt(account_rsa_key.rsa_passphrase)
        try:
            rsa_key = RSA.importKey(rsa_private_key, passphrase=rsa_passphrase)
            rsa_cipher = PKCS1_OAEP.new(rsa_key)
            aes_key = rsa_cipher.decrypt(base64.decodebytes(cipher_key.encode("utf-8")))
        except Exception as e:
            LOG.warning(f"Message could not be decoded: text={text}", exc_info=e)
            return None

        # Decrypt message
        try:
            message_org = base64.b64decode(message)
            aes_iv = message_org[: AES.block_size]
            aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
            pad_message = aes_cipher.decrypt(message_org[AES.block_size :])
            decrypt_message = unpad(pad_message, AES.block_size).decode()
        except Exception as e:
            LOG.warning(f"Message could not be decoded: text={text}", exc_info=e)
            return None

        if len(decrypt_message) > 5000:
            LOG.warning(f"Message could not be decoded: text={text}")
            return None

        return decrypt_message, _type

    @staticmethod
    async def __sink_on_e2e_messaging(
        db_session: AsyncSession,
        transaction_hash: str,
        from_address: str,
        to_address: str,
        _type: str,
        message: str,
        send_timestamp: datetime,
        block_timestamp: datetime,
    ):
        _idx_e2e_messaging = IDXE2EMessaging()
        _idx_e2e_messaging.transaction_hash = transaction_hash
        _idx_e2e_messaging.from_address = from_address
        _idx_e2e_messaging.to_address = to_address
        _idx_e2e_messaging.type = _type
        _idx_e2e_messaging.message = message
        _idx_e2e_messaging.send_timestamp = send_timestamp
        _idx_e2e_messaging.block_timestamp = block_timestamp
        db_session.add(_idx_e2e_messaging)
        LOG.debug(f"E2EMessaging: transaction_hash={transaction_hash}")


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
            LOG.exception(ex)

        elapsed_time = time.time() - start_time
        await asyncio.sleep(max(INDEXER_SYNC_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
