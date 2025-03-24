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
import uuid
from datetime import datetime, timedelta, timezone
from itertools import groupby
from typing import Optional, Sequence

import uvloop
from eth_utils import to_checksum_address
from sqlalchemy import and_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import AsyncContract

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetExchangeInterface, IbetShareContract
from app.model.db import (
    Account,
    IDXLock,
    IDXLockedPosition,
    IDXPosition,
    IDXPositionShareBlockNumber,
    IDXUnlock,
    Notification,
    NotificationType,
    Token,
    TokenStatus,
    TokenType,
)
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.contract_utils import AsyncContractUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc
from batch.utils import batch_log
from config import INDEXER_BLOCK_LOT_MAX_SIZE, INDEXER_SYNC_INTERVAL, ZERO_ADDRESS

process_name = "INDEXER-Position-Share"
LOG = batch_log.get_logger(process_name=process_name)

UTC = timezone(timedelta(hours=0), "UTC")

web3 = AsyncWeb3Wrapper()


class Processor:
    def __init__(self):
        # List of tokens to be synchronized
        self.token_list: dict[str, AsyncContract] = {}
        # Determining which tokens require initial synchronization
        self.init_position_synced: dict[str, bool | None] = {}
        # Exchange addresses
        self.exchange_address_list: list[str] = []

    async def sync_new_logs(self):
        db_session = BatchAsyncSessionLocal()
        try:
            await self.__get_contract_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            latest_block = await web3.eth.block_number
            _from_block = await self.__get_idx_position_block_number(
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

            await self.__set_idx_position_block_number(
                db_session=db_session, block_number=latest_block
            )
            await db_session.commit()
        except Exception as e:
            await db_session.rollback()
            raise e
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")

    async def __get_contract_list(self, db_session: AsyncSession):
        self.exchange_address_list = []

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
                        .where(
                            and_(
                                Token.type == TokenType.IBET_SHARE,
                                Token.token_status == TokenStatus.SUCCEEDED,
                            )
                        )
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

        load_required_token_list: Sequence[Token] = (
            await db_session.scalars(
                select(Token).where(
                    and_(
                        Token.type == TokenType.IBET_SHARE,
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
            self.token_list[load_required_token.token_address] = token_contract
            self.init_position_synced[load_required_token.token_address] = (
                load_required_token.initial_position_synced
            )

        _exchange_list_tmp = []
        for token_contract in self.token_list.values():
            share_token = IbetShareContract(token_contract.address)
            await share_token.get()
            if share_token.tradable_exchange_contract_address != ZERO_ADDRESS:
                _exchange_list_tmp.append(
                    share_token.tradable_exchange_contract_address
                )

        # Remove duplicate exchanges from a list
        self.exchange_address_list = list(set(_exchange_list_tmp))

    @staticmethod
    async def __get_idx_position_block_number(db_session: AsyncSession):
        _idx_position_block_number: IDXPositionShareBlockNumber | None = (
            await db_session.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        if _idx_position_block_number is None:
            return 0
        else:
            return _idx_position_block_number.latest_block_number

    @staticmethod
    async def __set_idx_position_block_number(
        db_session: AsyncSession, block_number: int
    ):
        _idx_position_block_number: IDXPositionShareBlockNumber | None = (
            await db_session.scalars(select(IDXPositionShareBlockNumber).limit(1))
        ).first()
        if _idx_position_block_number is None:
            _idx_position_block_number = IDXPositionShareBlockNumber()

        _idx_position_block_number.latest_block_number = block_number
        await db_session.merge(_idx_position_block_number)

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info("Syncing from={}, to={}".format(block_from, block_to))
        await self.__sync_issuer(db_session)
        await self.__sync_issue(db_session, block_from, block_to)
        await self.__sync_transfer(db_session, block_from, block_to)
        await self.__sync_lock(db_session, block_from, block_to)
        await self.__sync_unlock(db_session, block_from, block_to)
        await self.__sync_redeem(db_session, block_from, block_to)
        await self.__sync_apply_for_transfer(db_session, block_from, block_to)
        await self.__sync_cancel_transfer(db_session, block_from, block_to)
        await self.__sync_approve_transfer(db_session, block_from, block_to)
        await self.__sync_exchange(db_session, block_from, block_to)
        await self.__sync_escrow(db_session, block_from, block_to)
        await self.__sync_dvp(db_session, block_from, block_to)

    async def __sync_issuer(self, db_session: AsyncSession):
        """Synchronize issuer position"""

        # Synchronize issuer positions only for tokens
        # that require initial synchronization.
        for token in self.token_list.values():
            if self.init_position_synced.get(token.address, False) is False:
                try:
                    share_token = IbetShareContract(token.address)
                    await share_token.get()
                    issuer_address = share_token.issuer_address
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, issuer_address
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=issuer_address,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
                    await db_session.execute(
                        update(Token)
                        .where(
                            and_(
                                Token.issuer_address == issuer_address,
                                Token.token_address == token.address,
                            )
                        )
                        .values(initial_position_synced=True)
                    )
                except Exception as e:
                    raise e

    async def __sync_issue(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Issue events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="Issue",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, account
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

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
                # Get "Transfer" events from token contract
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="Transfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    for account in [
                        args.get("from", ZERO_ADDRESS),
                        args.get("to", ZERO_ADDRESS),
                    ]:
                        if (await web3.eth.get_code(account)).to_0x_hex() == "0x":
                            (
                                balance,
                                pending_transfer,
                                exchange_balance,
                                exchange_commitment,
                            ) = await self.__get_account_balance_all(token, account)
                            await self.__sink_on_position(
                                db_session=db_session,
                                token_address=to_checksum_address(token.address),
                                account_address=account,
                                balance=balance,
                                exchange_balance=exchange_balance,
                                exchange_commitment=exchange_commitment,
                                pending_transfer=pending_transfer,
                            )
            except Exception as e:
                raise e

    async def __sync_lock(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Lock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="Lock",
                    block_from=block_from,
                    block_to=block_to,
                )

                # Update locked positions
                try:
                    lock_map: dict[str, dict[str, True]] = {}
                    for event in events:
                        args = event["args"]
                        account_address = args.get("accountAddress", "")
                        lock_address = args.get("lockAddress", "")
                        value = args.get("value", 0)
                        data = args.get("data", "")
                        event_created = await self.__gen_block_timestamp(event=event)
                        tx = await web3.eth.get_transaction(event["transactionHash"])
                        msg_sender = tx["from"]

                        # Index Lock event
                        await self.__insert_lock_idx(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"].to_0x_hex(),
                            msg_sender=msg_sender,
                            block_number=event["blockNumber"],
                            token_address=token.address,
                            lock_address=lock_address,
                            account_address=account_address,
                            value=value,
                            data_str=data,
                            block_timestamp=event_created,
                        )

                        if lock_address not in lock_map:
                            lock_map[lock_address] = {}
                        lock_map[lock_address][account_address] = True

                    for lock_address in lock_map:
                        for account_address in lock_map[lock_address]:
                            value = await self.__get_account_locked_token(
                                token_contract=token,
                                lock_address=lock_address,
                                account_address=account_address,
                            )
                            await self.__sink_on_locked_position(
                                db_session=db_session,
                                token_address=to_checksum_address(token.address),
                                lock_address=lock_address,
                                account_address=account_address,
                                value=value,
                            )
                except Exception:
                    pass

                # Update positions
                for event in events:
                    args = event["args"]
                    account = args.get("accountAddress", ZERO_ADDRESS)
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, account
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )

                # Insert Notification
                if len(events) > 0:
                    share_token = IbetShareContract(token.address)
                    await share_token.get()
                    issuer_address = share_token.issuer_address
                    for event in events:
                        args = event["args"]
                        account_address = args.get("accountAddress", "")
                        lock_address = args.get("lockAddress", "")
                        value = args.get("value", 0)
                        data = args.get("data", "")
                        await self.__sink_on_lock_info_notification(
                            db_session=db_session,
                            issuer_address=issuer_address,
                            token_address=token.address,
                            token_type=TokenType.IBET_SHARE,
                            account_address=account_address,
                            lock_address=lock_address,
                            value=value,
                            data_str=data,
                        )

            except Exception as e:
                raise e

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

                # Update locked positions
                try:
                    lock_map: dict[str, dict[str, True]] = {}
                    for event in events:
                        args = event["args"]
                        account_address = args.get("accountAddress", "")
                        lock_address = args.get("lockAddress", "")
                        recipient_address = args.get("recipientAddress", "")
                        value = args.get("value", 0)
                        data = args.get("data", "")
                        event_created = await self.__gen_block_timestamp(event=event)
                        tx = await web3.eth.get_transaction(event["transactionHash"])
                        msg_sender = tx["from"]

                        # Index Unlock event
                        await self.__insert_unlock_idx(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"].to_0x_hex(),
                            msg_sender=msg_sender,
                            block_number=event["blockNumber"],
                            token_address=token.address,
                            lock_address=lock_address,
                            account_address=account_address,
                            recipient_address=recipient_address,
                            value=value,
                            data_str=data,
                            block_timestamp=event_created,
                        )

                        if lock_address not in lock_map:
                            lock_map[lock_address] = {}
                        lock_map[lock_address][account_address] = True

                    for lock_address in lock_map:
                        for account_address in lock_map[lock_address]:
                            value = await self.__get_account_locked_token(
                                token_contract=token,
                                lock_address=lock_address,
                                account_address=account_address,
                            )
                            await self.__sink_on_locked_position(
                                db_session=db_session,
                                token_address=to_checksum_address(token.address),
                                lock_address=lock_address,
                                account_address=account_address,
                                value=value,
                            )
                except Exception:
                    pass

                # Update positions
                for event in events:
                    args = event["args"]
                    account = args.get("recipientAddress", ZERO_ADDRESS)
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, account
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )

                # Insert Notification
                if len(events) > 0:
                    share_token = IbetShareContract(token.address)
                    await share_token.get()
                    issuer_address = share_token.issuer_address
                    for event in events:
                        args = event["args"]
                        account_address = args.get("accountAddress", "")
                        lock_address = args.get("lockAddress", "")
                        recipient_address = args.get("recipientAddress", "")
                        value = args.get("value", 0)
                        data = args.get("data", "")
                        await self.__sink_on_unlock_info_notification(
                            db_session=db_session,
                            issuer_address=issuer_address,
                            token_address=token.address,
                            token_type=TokenType.IBET_SHARE,
                            account_address=account_address,
                            lock_address=lock_address,
                            recipient_address=recipient_address,
                            value=value,
                            data_str=data,
                        )

            except Exception as e:
                raise e

    async def __sync_redeem(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Synchronize Redeem events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="Redeem",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, account
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_apply_for_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync ApplyForTransfer Events

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="ApplyForTransfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, account
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_cancel_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync CancelTransfer Events

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="CancelTransfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = await self.__get_account_balance_token(
                        token, account
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer,
                    )
            except Exception as e:
                raise e

    async def __sync_approve_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync ApproveTransfer Events

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=token,
                    event="ApproveTransfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    for account in [
                        args.get("from", ZERO_ADDRESS),
                        args.get("to", ZERO_ADDRESS),
                    ]:
                        (
                            balance,
                            pending_transfer,
                        ) = await self.__get_account_balance_token(token, account)
                        await self.__sink_on_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            account_address=account,
                            balance=balance,
                            pending_transfer=pending_transfer,
                        )
            except Exception as e:
                raise e

    async def __sync_exchange(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync Events from IbetExchange

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                exchange = AsyncContractUtils.get_contract(
                    "IbetExchange", exchange_address
                )

                account_list_tmp = []

                # NewOrder event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="NewOrder",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # CancelOrder event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="CancelOrder",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # ForceCancelOrder event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="ForceCancelOrder",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "accountAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # Agree event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="Agree",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # SettlementOK event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="SettlementOK",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "buyAddress", ZERO_ADDRESS
                            ),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),
                        }
                    )

                # SettlementNG event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="SettlementNG",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get(
                                "tokenAddress", ZERO_ADDRESS
                            ),
                            "account_address": _event["args"].get(
                                "sellAddress", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    if self.token_list.get(token_address) is None:
                        continue
                    account_address = _account["account_address"]
                    (
                        exchange_balance,
                        exchange_commitment,
                    ) = await self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address,
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    async def __sync_escrow(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync Events from IbetSecurityTokenEscrow

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                escrow = AsyncContractUtils.get_contract(
                    "IbetSecurityTokenEscrow", exchange_address
                )

                account_list_tmp = []

                # EscrowCreated event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=escrow,
                    event="EscrowCreated",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),  # only sender has changed
                        }
                    )

                # EscrowCanceled event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=escrow,
                    event="EscrowCanceled",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "sender", ZERO_ADDRESS
                            ),  # only sender has changed
                        }
                    )

                # HolderChanged event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=escrow,
                    event="HolderChanged",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("from", ZERO_ADDRESS),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("to", ZERO_ADDRESS),
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    if self.token_list.get(token_address) is None:
                        continue
                    account_address = _account["account_address"]
                    (
                        exchange_balance,
                        exchange_commitment,
                    ) = await self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address,
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    async def __sync_dvp(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync Events from IbetSecurityTokenDVP

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                delivery = AsyncContractUtils.get_contract(
                    "IbetSecurityTokenDVP", exchange_address
                )

                account_list_tmp = []

                # DeliveryCreated event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=delivery,
                    event="DeliveryCreated",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "seller", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # DeliveryCanceled event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=delivery,
                    event="DeliveryCanceled",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "seller", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # DeliveryAborted event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=delivery,
                    event="DeliveryAborted",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get(
                                "seller", ZERO_ADDRESS
                            ),  # only seller has changed
                        }
                    )

                # HolderChanged event
                _event_list = await AsyncContractUtils.get_event_logs(
                    contract=delivery,
                    event="HolderChanged",
                    block_from=block_from,
                    block_to=block_to,
                )
                for _event in _event_list:
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("from", ZERO_ADDRESS),
                        }
                    )
                    account_list_tmp.append(
                        {
                            "token_address": _event["args"].get("token", ZERO_ADDRESS),
                            "account_address": _event["args"].get("to", ZERO_ADDRESS),
                        }
                    )

                # Make temporary list unique
                account_list_tmp.sort(
                    key=lambda x: (x["token_address"], x["account_address"])
                )
                account_list = []
                for k, g in groupby(
                    account_list_tmp,
                    lambda x: (x["token_address"], x["account_address"]),
                ):
                    account_list.append(
                        {"token_address": k[0], "account_address": k[1]}
                    )

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    if self.token_list.get(token_address) is None:
                        continue
                    account_address = _account["account_address"]
                    (
                        exchange_balance,
                        exchange_commitment,
                    ) = await self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address,
                    )
                    await self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment,
                    )
            except Exception as e:
                raise e

    @staticmethod
    async def __insert_lock_idx(
        db_session: AsyncSession,
        transaction_hash: str,
        msg_sender: str,
        block_number: int,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
        data_str: str,
        block_timestamp: datetime,
    ):
        """Registry Lock event data in DB

        :param transaction_hash: transaction hash
        :param msg_sender: message sender
        :param token_address: token address
        :param lock_address: lock address
        :param account_address: account address
        :param value: amount
        :param data_str: data string
        :param block_timestamp: block timestamp
        :return: None
        """
        try:
            data = json.loads(data_str)
        except Exception:
            data = {}

        lock = IDXLock()
        lock.transaction_hash = transaction_hash
        lock.msg_sender = msg_sender
        lock.block_number = block_number
        lock.token_address = token_address
        lock.lock_address = lock_address
        lock.account_address = account_address
        lock.value = value
        lock.data = data
        lock.block_timestamp = block_timestamp.replace(tzinfo=None)
        db_session.add(lock)

    @staticmethod
    async def __insert_unlock_idx(
        db_session: AsyncSession,
        transaction_hash: str,
        msg_sender: str,
        block_number: int,
        token_address: str,
        lock_address: str,
        account_address: str,
        recipient_address: str,
        value: int,
        data_str: str,
        block_timestamp: datetime,
    ):
        """Registry Unlock event data in DB

        :param transaction_hash: transaction hash
        :param msg_sender: message sender
        :param token_address: token address
        :param lock_address: lock address
        :param account_address: account address
        :param recipient_address: recipient address
        :param value: amount
        :param data_str: data string
        :param block_timestamp: block timestamp
        :return: None
        """
        try:
            data = json.loads(data_str)
        except Exception:
            data = {}

        unlock = IDXUnlock()
        unlock.transaction_hash = transaction_hash
        unlock.msg_sender = msg_sender
        unlock.block_number = block_number
        unlock.token_address = token_address
        unlock.lock_address = lock_address
        unlock.account_address = account_address
        unlock.recipient_address = recipient_address
        unlock.value = value
        unlock.data = data
        unlock.block_timestamp = block_timestamp.replace(tzinfo=None)
        db_session.add(unlock)

    @staticmethod
    async def __sink_on_position(
        db_session: AsyncSession,
        token_address: str,
        account_address: str,
        balance: Optional[int] = None,
        exchange_balance: Optional[int] = None,
        exchange_commitment: Optional[int] = None,
        pending_transfer: Optional[int] = None,
    ):
        """Update balance data

        :param db_session: database session
        :param token_address: token address
        :param account_address: account address
        :param balance: balance
        :param exchange_balance: exchange balance
        :param exchange_commitment: exchange commitment
        :param pending_transfer: pending transfer
        :return: None
        """
        position: IDXPosition | None = (
            await db_session.scalars(
                select(IDXPosition)
                .where(
                    and_(
                        IDXPosition.token_address == token_address,
                        IDXPosition.account_address == account_address,
                    )
                )
                .limit(1)
            )
        ).first()
        if position is not None:
            if balance is not None:
                position.balance = balance
            if pending_transfer is not None:
                position.pending_transfer = pending_transfer
            if exchange_balance is not None:
                position.exchange_balance = exchange_balance
            if exchange_commitment is not None:
                position.exchange_commitment = exchange_commitment
            await db_session.merge(position)
        elif any(
            value is not None and value > 0
            for value in [
                balance,
                pending_transfer,
                exchange_balance,
                exchange_commitment,
            ]
        ):
            LOG.debug(
                f"Position created (Share): token_address={token_address}, account_address={account_address}"
            )
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance or 0
            position.pending_transfer = pending_transfer or 0
            position.exchange_balance = exchange_balance or 0
            position.exchange_commitment = exchange_commitment or 0
            db_session.add(position)

    @staticmethod
    async def __sink_on_locked_position(
        db_session: AsyncSession,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
    ):
        """Update locked balance data

        :param db_session: ORM session
        :param token_address: token address
        :param lock_address: account address
        :param account_address: account address
        :param value: updated locked amount
        :return: None
        """
        locked: IDXLockedPosition | None = (
            await db_session.scalars(
                select(IDXLockedPosition)
                .where(
                    and_(
                        IDXLockedPosition.token_address == token_address,
                        IDXLockedPosition.lock_address == lock_address,
                        IDXLockedPosition.account_address == account_address,
                    )
                )
                .limit(1)
            )
        ).first()
        if locked is not None:
            locked.value = value
            await db_session.merge(locked)
        else:
            locked = IDXLockedPosition()
            locked.token_address = token_address
            locked.lock_address = lock_address
            locked.account_address = account_address
            locked.value = value
            db_session.add(locked)

    @staticmethod
    async def __sink_on_lock_info_notification(
        db_session: AsyncSession,
        issuer_address: str,
        token_address: str,
        token_type: str,
        account_address: str,
        lock_address: str,
        value: int,
        data_str: str,
    ):
        try:
            data = json.loads(data_str)
        except Exception:
            data = {}

        notification = Notification()
        notification.notice_id = str(uuid.uuid4())
        notification.issuer_address = issuer_address
        notification.priority = 0  # Low
        notification.type = NotificationType.LOCK_INFO
        notification.code = 0
        notification.metainfo = {
            "token_address": token_address,
            "token_type": token_type,
            "account_address": account_address,
            "lock_address": lock_address,
            "value": value,
            "data": data,
        }
        db_session.add(notification)

    @staticmethod
    async def __sink_on_unlock_info_notification(
        db_session: AsyncSession,
        issuer_address: str,
        token_address: str,
        token_type: str,
        account_address: str,
        lock_address: str,
        recipient_address: str,
        value: int,
        data_str: str,
    ):
        try:
            data = json.loads(data_str)
        except Exception:
            data = {}

        notification = Notification()
        notification.notice_id = str(uuid.uuid4())
        notification.issuer_address = issuer_address
        notification.priority = 0  # Low
        notification.type = NotificationType.UNLOCK_INFO
        notification.code = 0
        notification.metainfo = {
            "token_address": token_address,
            "token_type": token_type,
            "account_address": account_address,
            "lock_address": lock_address,
            "recipient_address": recipient_address,
            "value": value,
            "data": data,
        }
        db_session.add(notification)

    @staticmethod
    async def __get_account_balance_all(token_contract, account_address: str):
        """Get balance"""

        exchange_balance = 0
        exchange_commitment = 0
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContractUtils.call_function(
                    contract=token_contract,
                    function_name="balanceOf",
                    args=(account_address,),
                    default_returns=0,
                ),
                AsyncContractUtils.call_function(
                    contract=token_contract,
                    function_name="pendingTransfer",
                    args=(account_address,),
                    default_returns=0,
                ),
                max_concurrency=3,
            )
            balance, pending_transfer = (
                tasks[0].result(),
                tasks[1].result(),
            )
        except ExceptionGroup:
            raise ServiceUnavailableError

        share_token = IbetShareContract(token_contract.address)
        await share_token.get()
        tradable_exchange_address = share_token.tradable_exchange_contract_address

        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = IbetExchangeInterface(tradable_exchange_address)
            exchange_contract_balance = await exchange_contract.get_account_balance(
                account_address=account_address, token_address=token_contract.address
            )
            exchange_balance = exchange_contract_balance["balance"]
            exchange_commitment = exchange_contract_balance["commitment"]

        return balance, pending_transfer, exchange_balance, exchange_commitment

    @staticmethod
    async def __get_account_balance_token(token_contract, account_address: str):
        """Get balance on token"""

        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContractUtils.call_function(
                    contract=token_contract,
                    function_name="balanceOf",
                    args=(account_address,),
                    default_returns=0,
                ),
                AsyncContractUtils.call_function(
                    contract=token_contract,
                    function_name="pendingTransfer",
                    args=(account_address,),
                    default_returns=0,
                ),
                max_concurrency=3,
            )
            balance, pending_transfer = (tasks[0].result(), tasks[1].result())
        except ExceptionGroup:
            raise ServiceUnavailableError

        return balance, pending_transfer

    @staticmethod
    async def __get_account_locked_token(
        token_contract, lock_address: str, account_address: str
    ):
        """Get locked balance on token"""
        value = await AsyncContractUtils.call_function(
            contract=token_contract,
            function_name="lockedOf",
            args=(
                lock_address,
                account_address,
            ),
            default_returns=0,
        )
        return value

    @staticmethod
    async def __get_account_balance_exchange(
        exchange_address: str, token_address: str, account_address: str
    ):
        """Get balance on exchange"""

        exchange_contract = IbetExchangeInterface(exchange_address)
        exchange_contract_balance = await exchange_contract.get_account_balance(
            account_address=account_address, token_address=token_address
        )
        return (
            exchange_contract_balance["balance"],
            exchange_contract_balance["commitment"],
        )

    @staticmethod
    async def __gen_block_timestamp(event):
        return datetime.fromtimestamp(
            (await web3.eth.get_block(event["blockNumber"]))["timestamp"], UTC
        )


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
