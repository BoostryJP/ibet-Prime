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
from typing import Sequence

import uvloop
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    Account,
    IbetWSTBlockchain,
    IDXAvaIbetWSTTrade,
    IDXAvaIbetWSTTradeBlockNumber,
    Token,
)
from app.model.wst import AvalancheIbetWST, IbetWSTTrade
from app.utils.ava_contract_utils import (
    AvaAsyncContractEventsView,
    AvaAsyncContractUtils,
)
from batch import free_malloc
from batch.utils import batch_log
from config import (
    INDEXER_BLOCK_LOT_MAX_SIZE,
    INDEXER_SYNC_INTERVAL,
)

process_name = "INDEXER-Ava-WST-Trades"
LOG = batch_log.get_logger(process_name=process_name)


class Processor:
    def __init__(self):
        self.wst_list: dict[str, AvaAsyncContractEventsView] = {}

    async def sync_events(self):
        db_session = BatchAsyncSessionLocal()
        try:
            await self.load_wst_list(db_session=db_session)

            # Get the latest block number to start monitoring
            latest_finalized_block = await self.get_finalized_block_number()
            _block_from = await self.get_from_block_number(db_session)

            # Calculate the block range to monitor
            _block_to = _block_from + INDEXER_BLOCK_LOT_MAX_SIZE

            # Skip processing if the range exceeds the latest block
            if _block_from >= latest_finalized_block:
                LOG.debug("skip process")
                return

            if latest_finalized_block > _block_to:
                # If the range exceeds the latest block, process in chunks
                while _block_to < latest_finalized_block:
                    # Sync WST trade events in chunks
                    await self.sync_wst_trade_events(
                        db_session=db_session,
                        block_from=_block_from + 1,
                        block_to=_block_to,
                    )
                    _block_to += INDEXER_BLOCK_LOT_MAX_SIZE
                    _block_from += INDEXER_BLOCK_LOT_MAX_SIZE
                # Process the remaining blocks
                await self.sync_wst_trade_events(
                    db_session=db_session,
                    block_from=_block_from + 1,
                    block_to=latest_finalized_block,
                )
            else:
                # If the range does not exceed the latest block, process all at once
                await self.sync_wst_trade_events(
                    db_session=db_session,
                    block_from=_block_from + 1,
                    block_to=latest_finalized_block,
                )

            # Set the latest block number to be monitored
            await self.set_synced_block_number(db_session, latest_finalized_block)
            # Commit the changes to the database
            await db_session.commit()
            LOG.info("Sync completed successfully")
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    async def load_wst_list(self, db_session: AsyncSession):
        """
        Load the list of WST tokens from the database and initialize their contract events.
        """
        token_list: Sequence[Token] = (
            await db_session.scalars(
                select(Token).join(
                    Account,
                    and_(
                        Account.issuer_address == Token.issuer_address,
                        Account.is_deleted == False,
                    ),
                )
            )
        ).all()

        wst_address_all: tuple[str, ...] = tuple(
            {
                wst_address
                for token in token_list
                if token.is_ibet_wst_deployed(IbetWSTBlockchain.AVALANCHE)
                if (
                    wst_address := token.get_ibet_wst_address(
                        IbetWSTBlockchain.AVALANCHE
                    )
                )
                is not None
            }
        )

        # Get the list of all WST tokens that have been loaded
        loaded_address_list: tuple[str, ...] = tuple(self.wst_list.keys())

        # Get the list of WST addresses that need to be loaded
        load_required_address_list = list(
            set(wst_address_all) ^ set(loaded_address_list)
        )

        if not load_required_address_list:
            # If there are no additional tokens to load, skip process
            return

        for _token in token_list:
            wst_address = _token.get_ibet_wst_address(IbetWSTBlockchain.AVALANCHE)
            if wst_address is None:
                continue
            if wst_address not in load_required_address_list:
                continue
            wst = AvalancheIbetWST(wst_address)
            self.wst_list[wst_address] = AvaAsyncContractEventsView(
                wst_address, wst.contract.events
            )

    @staticmethod
    async def get_finalized_block_number() -> int:
        """Get the finalized block number

        :return: finalized block number
        """
        return await AvaAsyncContractUtils.get_finalized_block_number()

    @staticmethod
    async def get_from_block_number(db_session: AsyncSession) -> int:
        """
        Get the starting block number for monitoring trade events.
        """
        _idx_transfer_block_number = (
            await db_session.scalars(select(IDXAvaIbetWSTTradeBlockNumber).limit(1))
        ).first()
        if _idx_transfer_block_number is None:
            return 0
        else:
            return _idx_transfer_block_number.latest_block_number

    @staticmethod
    async def set_synced_block_number(
        db_session: AsyncSession, block_number: int
    ) -> None:
        """
        Set the latest synchronized block number for IDXAvaIbetWSTTradeBlockNumber.
        """
        idx_synced = (
            await db_session.scalars(select(IDXAvaIbetWSTTradeBlockNumber).limit(1))
        ).first()
        if idx_synced is None:
            idx_synced = IDXAvaIbetWSTTradeBlockNumber()

        idx_synced.latest_block_number = block_number
        await db_session.merge(idx_synced)

    async def sync_wst_trade_events(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info(f"Syncing IbetWST trade events from={block_from}, to={block_to}")
        await self.__sync_trade_requested(db_session, block_from, block_to)
        await self.__sync_trade_accepted(db_session, block_from, block_to)
        await self.__sync_trade_cancelled(db_session, block_from, block_to)
        await self.__sync_trade_rejected(db_session, block_from, block_to)

    async def __sync_trade_requested(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Sync trade requested events from the WST contracts.
        """
        for wst_address, wst_events in self.wst_list.items():
            # Fetch TradeRequested events from the contract
            events = await AvaAsyncContractUtils.get_event_logs(
                contract=wst_events,
                event="TradeRequested",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                trade_index = event["args"]["index"]
                # Fetch the trade details from the contract
                wst_contract = AvalancheIbetWST(wst_address)
                wst_trade: IbetWSTTrade = await wst_contract.get_trade(trade_index)
                # Upsert the trade into the database
                await self.__upsert_trade(
                    db_session=db_session,
                    wst_address=wst_address,
                    wst_trade_index=trade_index,
                    wst_trade=wst_trade,
                )

    async def __sync_trade_accepted(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Sync trade accepted events from the WST contracts.
        """
        for wst_address, wst_events in self.wst_list.items():
            # Fetch TradeAccepted events from the contract
            events = await AvaAsyncContractUtils.get_event_logs(
                contract=wst_events,
                event="TradeAccepted",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                trade_index = event["args"]["index"]
                # Fetch the trade details from the contract
                wst_contract = AvalancheIbetWST(wst_address)
                wst_trade: IbetWSTTrade = await wst_contract.get_trade(trade_index)
                # Upsert the trade into the database
                await self.__upsert_trade(
                    db_session=db_session,
                    wst_address=wst_address,
                    wst_trade_index=trade_index,
                    wst_trade=wst_trade,
                )

    async def __sync_trade_cancelled(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Sync trade cancelled events from the WST contracts.
        """
        for wst_address, wst_events in self.wst_list.items():
            # Fetch TradeCancelled events from the contract
            events = await AvaAsyncContractUtils.get_event_logs(
                contract=wst_events,
                event="TradeCancelled",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                trade_index = event["args"]["index"]
                # Fetch the trade details from the contract
                wst_contract = AvalancheIbetWST(wst_address)
                wst_trade: IbetWSTTrade = await wst_contract.get_trade(trade_index)
                # Upsert the trade into the database
                await self.__upsert_trade(
                    db_session=db_session,
                    wst_address=wst_address,
                    wst_trade_index=trade_index,
                    wst_trade=wst_trade,
                )

    async def __sync_trade_rejected(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Sync trade rejected events from the WST contracts.
        """
        for wst_address, wst_events in self.wst_list.items():
            # Fetch TradeCancelled events from the contract
            events = await AvaAsyncContractUtils.get_event_logs(
                contract=wst_events,
                event="TradeRejected",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                trade_index = event["args"]["index"]
                # Fetch the trade details from the contract
                wst_contract = AvalancheIbetWST(wst_address)
                wst_trade: IbetWSTTrade = await wst_contract.get_trade(trade_index)
                # Upsert the trade into the database
                await self.__upsert_trade(
                    db_session=db_session,
                    wst_address=wst_address,
                    wst_trade_index=trade_index,
                    wst_trade=wst_trade,
                )

    @staticmethod
    async def __upsert_trade(
        db_session: AsyncSession,
        wst_address: str,
        wst_trade_index: int,
        wst_trade: IbetWSTTrade,
    ):
        """
        Upsert a trade record into the database.
        """
        # Create or update the trade record
        idx_trade = IDXAvaIbetWSTTrade(
            ibet_wst_address=wst_address,
            index=wst_trade_index,
            seller_st_account_address=wst_trade.seller_st_account,
            buyer_st_account_address=wst_trade.buyer_st_account,
            sc_token_address=wst_trade.sc_token_address,
            seller_sc_account_address=wst_trade.seller_sc_account,
            buyer_sc_account_address=wst_trade.buyer_sc_account,
            st_value=wst_trade.st_value,
            sc_value=wst_trade.sc_value,
            state=wst_trade.state,
            memo=wst_trade.memo,
        )
        await db_session.merge(idx_trade)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.sync_events()
        except ServiceUnavailableError as ex:
            LOG.error(f"All blockchain nodes are unavailable: {ex}")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during processing")

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
