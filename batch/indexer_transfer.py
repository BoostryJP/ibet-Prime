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
import json
import sys
from datetime import UTC, datetime
from typing import Sequence

import uvloop
from eth_utils import to_checksum_address
from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    DataMessage,
    IDXTransfer,
    IDXTransferBlockNumber,
    IDXTransferSourceEventType,
    Token,
    TokenStatus,
)
from app.utils.contract_utils import AsyncContractEventsView, AsyncContractUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc
from batch.utils import batch_log
from config import INDEXER_BLOCK_LOT_MAX_SIZE, INDEXER_SYNC_INTERVAL, ZERO_ADDRESS

process_name = "INDEXER-Transfer"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    def __init__(self):
        self.token_list: dict[str, AsyncContractEventsView] = {}

    async def sync_new_logs(self):
        db_session = BatchAsyncSessionLocal()
        try:
            await self.__get_token_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            latest_block = await web3.eth.block_number
            _from_block = await self.__get_idx_transfer_block_number(
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

            await self.__set_idx_transfer_block_number(
                db_session=db_session, block_number=latest_block
            )
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")

    async def __get_token_list(self, db_session: AsyncSession):
        issued_token_address_list: tuple[str, ...] = tuple(
            [
                record[0]
                for record in (
                    await db_session.execute(
                        select(Token.token_address)
                        .join(
                            Account,
                            and_(
                                Account.issuer_address == Token.issuer_address,
                                Account.is_deleted == False,
                            ),
                        )
                        .where(Token.token_status == TokenStatus.SUCCEEDED)
                    )
                )
                .tuples()
                .all()
            ]
        )
        loaded_token_address_list: tuple[str, ...] = tuple(self.token_list.keys())
        load_required_address_list = list(
            set(issued_token_address_list) ^ set(loaded_token_address_list)
        )

        if not load_required_address_list:
            # If there are no additional tokens to load, skip process
            return

        load_required_token_list: Sequence[Token] = (
            await db_session.scalars(
                select(Token).where(
                    and_(
                        Token.token_status == TokenStatus.SUCCEEDED,
                        Token.token_address.in_(load_required_address_list),
                    )
                )
            )
        ).all()
        for load_required_token in load_required_token_list:
            token_contract = web3.eth.contract(
                address=load_required_token.token_address, abi=load_required_token.abi
            )
            self.token_list[load_required_token.token_address] = (
                AsyncContractEventsView(token_contract.address, token_contract.events)
            )

    @staticmethod
    async def __get_idx_transfer_block_number(db_session: AsyncSession):
        _idx_transfer_block_number: IDXTransferBlockNumber | None = (
            await db_session.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        if _idx_transfer_block_number is None:
            return 0
        else:
            return _idx_transfer_block_number.latest_block_number

    @staticmethod
    async def __set_idx_transfer_block_number(
        db_session: AsyncSession, block_number: int
    ):
        _idx_transfer_block_number: IDXTransferBlockNumber | None = (
            await db_session.scalars(select(IDXTransferBlockNumber).limit(1))
        ).first()
        if _idx_transfer_block_number is None:
            _idx_transfer_block_number = IDXTransferBlockNumber()

        _idx_transfer_block_number.latest_block_number = block_number
        await db_session.merge(_idx_transfer_block_number)

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info(f"Syncing from={block_from}, to={block_to}")
        await self.__sync_transfer(db_session, block_from, block_to)
        await self.__sync_unlock(db_session, block_from, block_to)
        await self.__sync_force_unlock(db_session, block_from, block_to)

    async def __sync_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Transfer events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="Transfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].to_0x_hex()
                    block_timestamp = datetime.fromtimestamp(
                        (await web3.eth.get_block(event["blockNumber"]))["timestamp"],
                        UTC,
                    ).replace(tzinfo=None)
                    if args["value"] > sys.maxsize:
                        pass
                    else:
                        await self.__sink_on_transfer(
                            db_session=db_session,
                            transaction_hash=transaction_hash,
                            token_address=to_checksum_address(token.address),
                            from_address=args["from"],
                            to_address=args["to"],
                            amount=args["value"],
                            source_event=IDXTransferSourceEventType.TRANSFER,
                            data_str=None,
                            block_timestamp=block_timestamp,
                        )
            except Exception:
                raise

    async def __sync_unlock(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Unlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="Unlock",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].to_0x_hex()
                    block_timestamp = datetime.fromtimestamp(
                        (await web3.eth.get_block(event["blockNumber"]))["timestamp"],
                        UTC,
                    ).replace(tzinfo=None)
                    if args["value"] > sys.maxsize:
                        pass
                    else:
                        from_address = args.get("accountAddress", ZERO_ADDRESS)
                        to_address = args.get("recipientAddress", ZERO_ADDRESS)
                        data_str = args.get("data", "")
                        if from_address != to_address:
                            await self.__sink_on_transfer(
                                db_session=db_session,
                                transaction_hash=transaction_hash,
                                token_address=to_checksum_address(token.address),
                                from_address=from_address,
                                to_address=to_address,
                                amount=args["value"],
                                source_event=IDXTransferSourceEventType.UNLOCK,
                                data_str=data_str,
                                block_timestamp=block_timestamp,
                            )
            except Exception:
                raise

    async def __sync_force_unlock(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize ForceUnlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="ForceUnlock",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    transaction_hash = event["transactionHash"].to_0x_hex()
                    block_timestamp = datetime.fromtimestamp(
                        (await web3.eth.get_block(event["blockNumber"]))["timestamp"],
                        UTC,
                    ).replace(tzinfo=None)
                    if args["value"] > sys.maxsize:
                        pass
                    else:
                        from_address = args.get("accountAddress", ZERO_ADDRESS)
                        to_address = args.get("recipientAddress", ZERO_ADDRESS)
                        data_str = args.get("data", "")
                        if from_address != to_address:
                            await self.__sink_on_transfer(
                                db_session=db_session,
                                transaction_hash=transaction_hash,
                                token_address=to_checksum_address(token.address),
                                from_address=from_address,
                                to_address=to_address,
                                amount=args["value"],
                                source_event=IDXTransferSourceEventType.FORCE_UNLOCK,
                                data_str=data_str,
                                block_timestamp=block_timestamp,
                            )
            except Exception:
                raise

    @staticmethod
    async def __sink_on_transfer(
        db_session: AsyncSession,
        transaction_hash: str,
        token_address: str,
        from_address: str,
        to_address: str,
        amount: int,
        source_event: IDXTransferSourceEventType,
        data_str: str | None,
        block_timestamp: datetime,
    ):
        if data_str is not None:
            try:
                data = json.loads(data_str)
                validated_data = DataMessage(**data)
                message = validated_data.message
            except ValidationError:
                data = {}
                message = None
            except json.JSONDecodeError:
                data = {}
                message = None
        else:
            data = None
            message = None
        transfer_record = IDXTransfer()
        transfer_record.transaction_hash = transaction_hash
        transfer_record.token_address = token_address
        transfer_record.from_address = from_address
        transfer_record.to_address = to_address
        transfer_record.amount = amount
        transfer_record.source_event = source_event
        transfer_record.data = data
        transfer_record.message = message
        transfer_record.block_timestamp = block_timestamp
        db_session.add(transfer_record)
        LOG.debug(f"Transfer: transaction_hash={transaction_hash}")


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.sync_new_logs()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
