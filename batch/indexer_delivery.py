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
from datetime import UTC, datetime
from typing import Literal, Optional, Sequence

import uvloop
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import AsyncContract

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import (
    Account,
    DeliveryStatus,
    IDXDelivery,
    IDXDeliveryBlockNumber,
    Token,
    TokenType,
)
from app.utils.contract_utils import AsyncContractUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import batch_log
from config import INDEXER_BLOCK_LOT_MAX_SIZE, INDEXER_SYNC_INTERVAL, ZERO_ADDRESS

process_name = "INDEXER-Delivery"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


"""
Batch process for indexing security token dvp delivery events

ibetSecurityTokenDVP
  - CreateDelivery
  - CancelDelivery
  - ConfirmDelivery
  - FinishDelivery
  - AbortDelivery
"""


class Processor:
    def __init__(self):
        self.token_list: list[str] = []
        self.exchange_list: list[AsyncContract] = []

    async def sync_new_logs(self):
        db_session = BatchAsyncSessionLocal()
        try:
            await self.__get_contract_list(db_session=db_session)

            latest_block = await web3.eth.block_number
            for contract in self.exchange_list:
                # Get from_block_number and to_block_number for contract event filter
                _from_block = await self.__get_idx_delivery_block_number(
                    db_session=db_session, exchange_address=contract.address
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
                            exchange=contract,
                        )
                        _to_block += INDEXER_BLOCK_LOT_MAX_SIZE
                        _from_block += INDEXER_BLOCK_LOT_MAX_SIZE
                    await self.__sync_all(
                        db_session=db_session,
                        block_from=_from_block + 1,
                        block_to=latest_block,
                        exchange=contract,
                    )
                else:
                    await self.__sync_all(
                        db_session=db_session,
                        block_from=_from_block + 1,
                        block_to=latest_block,
                        exchange=contract,
                    )

                await self.__set_idx_delivery_block_number(
                    db_session=db_session,
                    exchange_address=contract.address,
                    block_number=latest_block,
                )
                await db_session.commit()
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")

    async def __get_contract_list(self, db_session: AsyncSession):
        """Get DVP contract list to index delivery event"""
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
                        .where(Token.token_status == 1)
                    )
                )
                .tuples()
                .all()
            ]
        )
        loaded_exchange_address_list: tuple[str, ...] = tuple(self.token_list)
        load_required_address_list = list(
            set(issued_token_address_list) ^ set(loaded_exchange_address_list)
        )

        load_required_token_list: Sequence[Token] = (
            await db_session.scalars(
                select(Token).where(
                    and_(
                        Token.token_status == 1,
                        Token.token_address.in_(load_required_address_list),
                    )
                )
            )
        ).all()

        _exchange_list_tmp = []
        for load_required_token in load_required_token_list:
            self.token_list.append(load_required_token.token_address)
            token_contract = web3.eth.contract(
                address=load_required_token.token_address, abi=load_required_token.abi
            )
            tradable_exchange_address = ZERO_ADDRESS
            if load_required_token.type == TokenType.IBET_STRAIGHT_BOND.value:
                bond_token = IbetStraightBondContract(token_contract.address)
                await bond_token.get()
                tradable_exchange_address = (
                    bond_token.tradable_exchange_contract_address
                )
            elif load_required_token.type == TokenType.IBET_SHARE.value:
                share_token = IbetShareContract(token_contract.address)
                await share_token.get()
                tradable_exchange_address = (
                    share_token.tradable_exchange_contract_address
                )

            if tradable_exchange_address != ZERO_ADDRESS:
                _exchange_list_tmp.append(tradable_exchange_address)

        # Remove duplicate exchanges from a list
        loaded_exchange_address_list: tuple[str, ...] = tuple(
            [exchange.address for exchange in self.exchange_list]
        )
        for _exchange_address in list(set(_exchange_list_tmp)):
            if _exchange_address not in loaded_exchange_address_list:
                exchange_contract = AsyncContractUtils.get_contract(
                    contract_name="IbetSecurityTokenDVP",
                    contract_address=_exchange_address,
                )
                self.exchange_list.append(exchange_contract)

    @staticmethod
    async def __get_idx_delivery_block_number(
        db_session: AsyncSession, exchange_address: str
    ):
        """Get block number of delivery index"""
        _idx_delivery_block_number = (
            await db_session.scalars(
                select(IDXDeliveryBlockNumber)
                .where(IDXDeliveryBlockNumber.exchange_address == exchange_address)
                .limit(1)
            )
        ).first()
        if _idx_delivery_block_number is None:
            return 0
        else:
            return _idx_delivery_block_number.latest_block_number

    @staticmethod
    async def __set_idx_delivery_block_number(
        db_session: AsyncSession,
        exchange_address: str,
        block_number: int,
    ):
        """Set block number of delivery index"""
        _idx_delivery_block_number = (
            await db_session.scalars(
                select(IDXDeliveryBlockNumber)
                .where(IDXDeliveryBlockNumber.exchange_address == exchange_address)
                .limit(1)
            )
        ).first()
        if _idx_delivery_block_number is None:
            _idx_delivery_block_number = IDXDeliveryBlockNumber()
        _idx_delivery_block_number.latest_block_number = block_number
        _idx_delivery_block_number.exchange_address = exchange_address
        await db_session.merge(_idx_delivery_block_number)

    async def __sync_all(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        exchange: AsyncContract,
    ):
        LOG.info(
            f"Syncing from={block_from}, to={block_to}, exchange={exchange.address}"
        )
        await self.__sync_delivery_created(
            db_session, block_from, block_to, exchange=exchange
        )
        await self.__sync_delivery_canceled(
            db_session, block_from, block_to, exchange=exchange
        )
        await self.__sync_delivery_confirmed(
            db_session, block_from, block_to, exchange=exchange
        )
        await self.__sync_delivery_finished(
            db_session, block_from, block_to, exchange=exchange
        )
        await self.__sync_delivery_aborted(
            db_session, block_from, block_to, exchange=exchange
        )

    async def __sync_delivery_created(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        exchange: AsyncContract,
    ):
        """Sync DeliveryCreated events of IbetSecurityTokenDVP
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        if block_from > block_to:
            return
        try:
            events = await AsyncContractUtils.get_event_logs(
                contract=exchange,
                event="DeliveryCreated",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                transaction_hash = event["transactionHash"].hex()
                args = event["args"]
                amount = args.get("amount", 0)
                if amount > sys.maxsize:  # suppress overflow
                    continue
                block_timestamp = await self.__get_block_timestamp(event=event)
                await self.__sink_on_delivery(
                    db_session=db_session,
                    event_type="Created",
                    exchange_address=exchange.address,
                    delivery_id=args.get("deliveryId"),
                    token_address=args.get("token", ZERO_ADDRESS),
                    seller_address=args.get("seller", ZERO_ADDRESS),
                    buyer_address=args.get("buyer", ZERO_ADDRESS),
                    amount=amount,
                    agent_address=args.get("agent", ZERO_ADDRESS),
                    block_timestamp=block_timestamp,
                    transaction_hash=transaction_hash,
                    data=args.get("data"),
                )
        except Exception:
            raise

    async def __sync_delivery_canceled(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        exchange: AsyncContract,
    ):
        """Sync DeliveryCanceled events of IbetSecurityTokenDVP
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        if block_from > block_to:
            return
        try:
            events = await AsyncContractUtils.get_event_logs(
                contract=exchange,
                event="DeliveryCanceled",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                transaction_hash = event["transactionHash"].hex()
                args = event["args"]
                amount = args.get("amount", 0)
                if amount > sys.maxsize:  # suppress overflow
                    continue
                block_timestamp = await self.__get_block_timestamp(event=event)
                await self.__sink_on_delivery(
                    db_session=db_session,
                    event_type="Canceled",
                    exchange_address=exchange.address,
                    delivery_id=args.get("deliveryId"),
                    token_address=args.get("token", ZERO_ADDRESS),
                    seller_address=args.get("seller", ZERO_ADDRESS),
                    buyer_address=args.get("buyer", ZERO_ADDRESS),
                    amount=amount,
                    agent_address=args.get("agent", ZERO_ADDRESS),
                    block_timestamp=block_timestamp,
                    transaction_hash=transaction_hash,
                )
        except Exception:
            raise

    async def __sync_delivery_confirmed(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        exchange: AsyncContract,
    ):
        """Sync DeliveryConfirmed events of IbetSecurityTokenDVP
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        if block_from > block_to:
            return
        try:
            events = await AsyncContractUtils.get_event_logs(
                contract=exchange,
                event="DeliveryConfirmed",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                transaction_hash = event["transactionHash"].hex()
                args = event["args"]
                amount = args.get("amount", 0)
                if amount > sys.maxsize:  # suppress overflow
                    continue
                block_timestamp = await self.__get_block_timestamp(event=event)
                await self.__sink_on_delivery(
                    db_session=db_session,
                    event_type="Confirmed",
                    exchange_address=exchange.address,
                    delivery_id=args.get("deliveryId"),
                    token_address=args.get("token", ZERO_ADDRESS),
                    seller_address=args.get("seller", ZERO_ADDRESS),
                    buyer_address=args.get("buyer", ZERO_ADDRESS),
                    amount=amount,
                    agent_address=args.get("agent", ZERO_ADDRESS),
                    block_timestamp=block_timestamp,
                    transaction_hash=transaction_hash,
                )
        except Exception:
            raise

    async def __sync_delivery_finished(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        exchange: AsyncContract,
    ):
        """Sync DeliveryFinished events of IbetSecurityTokenDVP
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        if block_from > block_to:
            return
        try:
            events = await AsyncContractUtils.get_event_logs(
                contract=exchange,
                event="DeliveryFinished",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                transaction_hash = event["transactionHash"].hex()
                args = event["args"]
                amount = args.get("amount", 0)
                if amount > sys.maxsize:  # suppress overflow
                    continue
                block_timestamp = await self.__get_block_timestamp(event=event)
                await self.__sink_on_delivery(
                    db_session=db_session,
                    event_type="Finished",
                    exchange_address=exchange.address,
                    delivery_id=args.get("deliveryId"),
                    token_address=args.get("token", ZERO_ADDRESS),
                    seller_address=args.get("seller", ZERO_ADDRESS),
                    buyer_address=args.get("buyer", ZERO_ADDRESS),
                    amount=amount,
                    agent_address=args.get("agent", ZERO_ADDRESS),
                    block_timestamp=block_timestamp,
                    transaction_hash=transaction_hash,
                )
        except Exception:
            raise

    async def __sync_delivery_aborted(
        self,
        db_session: AsyncSession,
        block_from: int,
        block_to: int,
        exchange: AsyncContract,
    ):
        """Sync DeliveryAborted events of IbetSecurityTokenDVP
        :param db_session: ORM session
        :param block_to: To Block
        :return: None
        """
        if block_from > block_to:
            return
        try:
            events = await AsyncContractUtils.get_event_logs(
                contract=exchange,
                event="DeliveryAborted",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                transaction_hash = event["transactionHash"].hex()
                args = event["args"]
                amount = args.get("amount", 0)
                if amount > sys.maxsize:  # suppress overflow
                    continue
                block_timestamp = await self.__get_block_timestamp(event=event)
                await self.__sink_on_delivery(
                    db_session=db_session,
                    event_type="Aborted",
                    exchange_address=exchange.address,
                    delivery_id=args.get("deliveryId"),
                    token_address=args.get("token", ZERO_ADDRESS),
                    seller_address=args.get("seller", ZERO_ADDRESS),
                    buyer_address=args.get("buyer", ZERO_ADDRESS),
                    amount=amount,
                    agent_address=args.get("agent", ZERO_ADDRESS),
                    block_timestamp=block_timestamp,
                    transaction_hash=transaction_hash,
                )
        except Exception:
            raise

    @staticmethod
    async def __get_block_timestamp(event) -> int:
        block_timestamp = (await web3.eth.get_block(event["blockNumber"]))["timestamp"]
        return block_timestamp

    @staticmethod
    async def __sink_on_delivery(
        db_session: AsyncSession,
        event_type: Literal["Created", "Canceled", "Confirmed", "Finished", "Aborted"],
        exchange_address: str,
        delivery_id: int,
        token_address: str,
        buyer_address: str,
        seller_address: str,
        amount: int,
        agent_address: str,
        block_timestamp: int,
        transaction_hash: str,
        data: Optional[str] = None,
    ):
        """Update Delivery data in DB
        :param db_session: ORM session
        :param event_type: event type ["Created", "Canceled", "Confirmed", "Finished", "Aborted"]
        :param token_address: token address
        :param exchange_address: exchange address
        :param delivery_id: delivery id
        :param buyer_address: delivery buyer address
        :param seller_address: delivery seller address
        :param amount: delivery amount
        :param agent_address: delivery agent address
        :param data: optional data (Created)
        :param block_timestamp: block timestamp
        :return: None
        """
        delivery = (
            await db_session.scalars(
                select(IDXDelivery)
                .where(IDXDelivery.exchange_address == exchange_address)
                .where(IDXDelivery.delivery_id == delivery_id)
                .limit(1)
            )
        ).first()
        if event_type == "Created":
            if delivery is None:
                delivery = IDXDelivery()
                delivery.exchange_address = exchange_address
                delivery.delivery_id = delivery_id
                delivery.token_address = token_address
                delivery.buyer_address = buyer_address
                delivery.seller_address = seller_address
                delivery.amount = amount
                delivery.agent_address = agent_address
                delivery.data = data
                delivery.create_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                )
                delivery.create_transaction_hash = transaction_hash
                delivery.confirmed = False
                delivery.valid = True
                delivery.status = DeliveryStatus.DELIVERY_CREATED
        elif event_type == "Canceled":
            if delivery is not None:
                delivery.cancel_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                )
                delivery.cancel_transaction_hash = transaction_hash
                delivery.valid = False
                delivery.status = DeliveryStatus.DELIVERY_CANCELED
        elif event_type == "Confirmed":
            if delivery is not None:
                delivery.confirm_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                )
                delivery.confirm_transaction_hash = transaction_hash
                delivery.confirmed = True
                delivery.status = DeliveryStatus.DELIVERY_CONFIRMED
        elif event_type == "Finished":
            if delivery is not None:
                delivery.finish_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                )
                delivery.finish_transaction_hash = transaction_hash
                delivery.valid = False
                delivery.status = DeliveryStatus.DELIVERY_FINISHED
        elif event_type == "Aborted":
            if delivery is not None:
                delivery.abort_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                )
                delivery.abort_transaction_hash = transaction_hash
                delivery.valid = False
                delivery.status = DeliveryStatus.DELIVERY_ABORTED
        await db_session.merge(delivery)


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
        except Exception as ex:
            LOG.error(ex)

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
