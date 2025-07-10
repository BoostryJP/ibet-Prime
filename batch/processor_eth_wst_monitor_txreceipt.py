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
from web3.exceptions import TimeExhausted
from web3.types import TxReceipt

from app.database import BatchAsyncSessionLocal
from app.model.db import (
    EthIbetWSTTx,
    IbetWSTEventLogAccountWhiteListAdded,
    IbetWSTEventLogAccountWhiteListDeleted,
    IbetWSTEventLogBurn,
    IbetWSTEventLogMint,
    IbetWSTEventLogTradeAccepted,
    IbetWSTEventLogTradeCancelled,
    IbetWSTEventLogTradeRejected,
    IbetWSTEventLogTradeRequested,
    IbetWSTTxStatus,
    IbetWSTTxType,
    Token,
)
from app.model.eth import IbetWST
from app.utils.eth_contract_utils import EthAsyncContractUtils
from batch import free_malloc
from batch.utils import batch_log

"""
[PROCESSOR-ETH-WST-Monitor-TxReceipt]

This processor monitors Ethereum transactions related to IbetWST 
and updates their status based on transaction receipts.
"""

process_name = "PROCESSOR-ETH-WST-Monitor-TxReceipt"
LOG = batch_log.get_logger(process_name=process_name)


class ProcessorEthWSTMonitorTxReceipt:
    """
    Processor for monitoring Ethereum transactions related to IbetWST.
    """

    async def run(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the latest finalized block number
            finalized_block_number = (
                await EthAsyncContractUtils.get_finalized_block_number()
            )

            # Get transactions waiting for block mining
            wst_tx_list: Sequence[EthIbetWSTTx] = (
                await db_session.scalars(
                    select(EthIbetWSTTx).where(
                        and_(
                            EthIbetWSTTx.status.in_(
                                [
                                    IbetWSTTxStatus.SENT,
                                    IbetWSTTxStatus.SUCCEEDED,
                                    IbetWSTTxStatus.FAILED,
                                ]
                            ),
                            EthIbetWSTTx.tx_hash.is_not(None),
                            EthIbetWSTTx.finalized.is_not(True),
                        )
                    )
                )
            ).all()
            for wst_tx in wst_tx_list:
                LOG.info(
                    f"Monitor transaction: id={wst_tx.tx_id}, type={wst_tx.tx_type}"
                )
                # Get TxReceipt
                try:
                    tx_receipt = (
                        await EthAsyncContractUtils.wait_for_transaction_receipt(
                            tx_hash=wst_tx.tx_hash, timeout=1
                        )
                    )
                except TimeExhausted:
                    LOG.info(
                        f"Transaction receipt not found, skipping processing: id={wst_tx.tx_id}"
                    )
                    continue

                # If TxReceipt is obtained, update the transaction status
                block_number = tx_receipt.get("blockNumber")
                if tx_receipt["status"] == 1:
                    # Transaction succeeded
                    wst_tx.status = IbetWSTTxStatus.SUCCEEDED
                    wst_tx.block_number = block_number
                    LOG.info(
                        f"Transaction succeeded: id={wst_tx.tx_id}, block_number={block_number}, gas_used={tx_receipt.get('gasUsed')}"
                    )
                else:
                    # Transaction failed
                    wst_tx.status = IbetWSTTxStatus.FAILED
                    wst_tx.block_number = block_number
                    LOG.info(
                        f"Transaction failed: id={wst_tx.tx_id}, block_number={block_number}, gas_used={tx_receipt.get('gasUsed')}"
                    )

                # If the block number is less than or equal to the latest finalized block number,
                # set the finalized flag to True
                is_finalized = block_number <= finalized_block_number
                wst_tx.finalized = is_finalized
                await db_session.merge(wst_tx)

                if is_finalized:
                    # Finalize the transaction
                    await finalize_tx(db_session, wst_tx, tx_receipt)
                    LOG.info(
                        f"Transaction finalized: id={wst_tx.tx_id}, block_number={block_number}, gas_used={tx_receipt.get('gasUsed')}"
                    )

                await db_session.commit()
        finally:
            # Close the session
            await db_session.close()


async def finalize_tx(
    db_session: AsyncSession, wst_tx: EthIbetWSTTx, tx_receipt: TxReceipt
):
    """
    Finalize the IbetWST transaction.
    """
    match wst_tx.tx_type:
        case IbetWSTTxType.DEPLOY:
            token = (
                await db_session.scalars(
                    select(Token).where(Token.ibet_wst_tx_id == wst_tx.tx_id).limit(1)
                )
            ).first()
            if token is None:
                return

            token.ibet_wst_deployed = True
            token.ibet_wst_address = tx_receipt.get("contractAddress", None)
            await db_session.merge(token)
        case IbetWSTTxType.MINT:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.Mint().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogMint(
                    to_address=event["args"]["to"],
                    value=event["args"]["value"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.BURN:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.Burn().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogBurn(
                    from_address=event["args"]["from"],
                    value=event["args"]["value"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.ADD_WHITELIST:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.AccountWhiteListAdded().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogAccountWhiteListAdded(
                    account_address=event["args"]["accountAddress"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.DELETE_WHITELIST:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.AccountWhiteListDeleted().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogAccountWhiteListDeleted(
                    account_address=event["args"]["accountAddress"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.REQUEST_TRADE:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeRequested().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogTradeRequested(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.CANCEL_TRADE:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeCancelled().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogTradeCancelled(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.ACCEPT_TRADE:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeAccepted().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogTradeAccepted(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.REJECT_TRADE:
            ibet_wst = IbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeRejected().process_receipt(
                txn_receipt=tx_receipt
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogTradeRejected(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                )
                await db_session.merge(wst_tx)
        case _:
            return


async def main():
    LOG.info("Service started successfully")
    processor = ProcessorEthWSTMonitorTxReceipt()

    while True:
        try:
            await processor.run()
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        await asyncio.sleep(10)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
