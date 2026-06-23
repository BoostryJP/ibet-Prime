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
from typing import Sequence, cast

import uvloop
from sqlalchemy import and_, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import TimeExhausted
from web3.logs import DISCARD
from web3.types import TxReceipt

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    AvaIbetWSTTx,
    IbetWSTBlockchain,
    IbetWSTEventLogAccountWhiteListAdded,
    IbetWSTEventLogAccountWhiteListDeleted,
    IbetWSTEventLogBurn,
    IbetWSTEventLogMint,
    IbetWSTEventLogTradeAccepted,
    IbetWSTEventLogTradeCancelled,
    IbetWSTEventLogTradeRejected,
    IbetWSTEventLogTradeRequested,
    IbetWSTEventLogTransfer,
    IbetWSTTxParamsAddAccountWhiteList,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IDXAvaIbetWSTWhitelist,
    Token,
)
from app.model.wst import AvalancheERC20, AvalancheIbetWST
from app.utils.ava_contract_utils import AvaAsyncContractUtils
from batch import free_malloc
from batch.utils import batch_log

"""
[PROCESSOR-AVA-WST-Monitor-TxReceipt]

This processor monitors Avalanche transactions related to IbetWST 
and updates their status based on transaction receipts.
"""

process_name = "PROCESSOR-AVA-WST-Monitor-TxReceipt"
LOG = batch_log.get_logger(process_name=process_name)


class ProcessorAvaWSTMonitorTxReceipt:
    """
    Processor for monitoring Avalanche transactions related to IbetWST.
    """

    async def run(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the latest finalized block number
            finalized_block_number = (
                await AvaAsyncContractUtils.get_finalized_block_number()
            )

            # Get transactions waiting for block mining
            wst_tx_list: Sequence[AvaIbetWSTTx] = (
                await db_session.scalars(
                    select(AvaIbetWSTTx).where(
                        and_(
                            AvaIbetWSTTx.status.in_(
                                [
                                    IbetWSTTxStatus.SENT,
                                    IbetWSTTxStatus.SUCCEEDED,
                                    IbetWSTTxStatus.FAILED,
                                ]
                            ),
                            AvaIbetWSTTx.tx_hash.is_not(None),
                            AvaIbetWSTTx.finalized.is_not(True),
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
                    assert wst_tx.tx_hash is not None
                    tx_receipt = (
                        await AvaAsyncContractUtils.wait_for_transaction_receipt(
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
                    wst_tx.gas_used = tx_receipt.get("gasUsed")
                    # If the transaction type is DEPLOY, set the IbetWST address
                    if wst_tx.tx_type == IbetWSTTxType.DEPLOY:
                        wst_tx.ibet_wst_address = tx_receipt.get("contractAddress")
                    LOG.info(
                        f"Transaction succeeded: id={wst_tx.tx_id}, block_number={block_number}, gas_used={tx_receipt.get('gasUsed')}"
                    )
                else:
                    # Transaction failed
                    wst_tx.status = IbetWSTTxStatus.FAILED
                    wst_tx.block_number = block_number
                    wst_tx.gas_used = tx_receipt.get("gasUsed")
                    LOG.info(
                        f"Transaction failed: id={wst_tx.tx_id}, block_number={block_number}, gas_used={tx_receipt.get('gasUsed')}"
                    )

                # If the block number is less than or equal to the latest finalized block number,
                # set the finalized flag to True
                is_finalized = block_number <= finalized_block_number
                wst_tx.finalized = is_finalized
                await db_session.merge(wst_tx)

                if not is_finalized and wst_tx.status == IbetWSTTxStatus.SUCCEEDED:
                    # If the block is not finalized, update the data for immediate reflection
                    await reflect_unfinalized_tx(db_session, wst_tx, tx_receipt)
                elif is_finalized and wst_tx.status == IbetWSTTxStatus.SUCCEEDED:
                    # Finalize the transaction
                    await finalize_tx(db_session, wst_tx, tx_receipt)
                    LOG.info(
                        f"Transaction finalized: id={wst_tx.tx_id}, block_number={block_number}, gas_used={tx_receipt.get('gasUsed')}"
                    )

                await db_session.commit()
        finally:
            # Close the session
            await db_session.close()


async def reflect_unfinalized_tx(
    db_session: AsyncSession, wst_tx: AvaIbetWSTTx, tx_receipt: TxReceipt
):
    """
    Reflect unfinalized IbetWST transaction.

    Note:
        This function only processes ADD_WHITELIST and DELETE_WHITELIST transactions.
        Other transaction types are processed upon finalization.
    """
    assert wst_tx.ibet_wst_address is not None

    match wst_tx.tx_type:
        case IbetWSTTxType.ADD_WHITELIST:
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.AccountWhiteListAdded().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogAccountWhiteListAdded(
                    account_address=event["args"]["accountAddress"],
                )
                await db_session.merge(wst_tx)
            # Add to whitelist table
            tx_params = cast(IbetWSTTxParamsAddAccountWhiteList, wst_tx.tx_params)
            await db_session.merge(
                IDXAvaIbetWSTWhitelist(
                    ibet_wst_address=wst_tx.ibet_wst_address,
                    st_account_address=tx_params["st_account"],
                    sc_account_address_in=tx_params["sc_account_in"],
                    sc_account_address_out=tx_params["sc_account_out"],
                )
            )
        case IbetWSTTxType.DELETE_WHITELIST:
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.AccountWhiteListDeleted().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogAccountWhiteListDeleted(
                    account_address=event["args"]["accountAddress"],
                )
                await db_session.merge(wst_tx)
                # Delete from whitelist table
                await db_session.execute(
                    delete(IDXAvaIbetWSTWhitelist).where(
                        and_(
                            IDXAvaIbetWSTWhitelist.ibet_wst_address
                            == wst_tx.ibet_wst_address,
                            IDXAvaIbetWSTWhitelist.st_account_address
                            == event["args"]["accountAddress"],
                        )
                    )
                )
        case _:
            return


async def finalize_tx(
    db_session: AsyncSession, wst_tx: AvaIbetWSTTx, tx_receipt: TxReceipt
):
    """
    Finalize the IbetWST transaction.
    """
    # If the transaction is successful,
    # update token information and event logs.
    match wst_tx.tx_type:
        case IbetWSTTxType.DEPLOY:
            # Update wst address
            token = (
                await db_session.scalars(
                    select(Token).where(Token.ibet_wst_tx_id == wst_tx.tx_id).limit(1)
                )
            ).first()
            if token is None:
                return

            token.set_ibet_wst_deployed(IbetWSTBlockchain.AVALANCHE, True)
            token.set_ibet_wst_address(
                IbetWSTBlockchain.AVALANCHE,
                tx_receipt.get("contractAddress", None),
            )
            await db_session.merge(token)
        case IbetWSTTxType.MINT:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.Mint().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogMint(
                    to_address=event["args"]["to"],
                    value=event["args"]["value"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.BURN:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.Burn().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogBurn(
                    from_address=event["args"]["from"],
                    value=event["args"]["value"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.FORCE_BURN:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.Burn().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogBurn(
                    from_address=event["args"]["from"],
                    value=event["args"]["value"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.ADD_WHITELIST:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.AccountWhiteListAdded().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogAccountWhiteListAdded(
                    account_address=event["args"]["accountAddress"],
                )
                await db_session.merge(wst_tx)
            # Add to whitelist table
            tx_params = cast(IbetWSTTxParamsAddAccountWhiteList, wst_tx.tx_params)
            await db_session.merge(
                IDXAvaIbetWSTWhitelist(
                    ibet_wst_address=wst_tx.ibet_wst_address,
                    st_account_address=tx_params["st_account"],
                    sc_account_address_in=tx_params["sc_account_in"],
                    sc_account_address_out=tx_params["sc_account_out"],
                )
            )
        case IbetWSTTxType.DELETE_WHITELIST:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.AccountWhiteListDeleted().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogAccountWhiteListDeleted(
                    account_address=event["args"]["accountAddress"],
                )
                await db_session.merge(wst_tx)
                # Delete from whitelist table
                await db_session.execute(
                    delete(IDXAvaIbetWSTWhitelist).where(
                        and_(
                            IDXAvaIbetWSTWhitelist.ibet_wst_address
                            == wst_tx.ibet_wst_address,
                            IDXAvaIbetWSTWhitelist.st_account_address
                            == event["args"]["accountAddress"],
                        )
                    )
                )
        case IbetWSTTxType.TRANSFER:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.Transfer().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                wst_tx.event_log = IbetWSTEventLogTransfer(
                    from_address=event["args"]["from"],
                    to_address=event["args"]["to"],
                    value=event["args"]["value"],
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.REQUEST_TRADE:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeRequested().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                sc_token = AvalancheERC20(event["args"]["SCTokenAddress"])
                wst_tx.event_log = IbetWSTEventLogTradeRequested(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                    sc_decimals=(await sc_token.decimals()),
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.CANCEL_TRADE:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeCancelled().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                sc_token = AvalancheERC20(event["args"]["SCTokenAddress"])
                wst_tx.event_log = IbetWSTEventLogTradeCancelled(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                    sc_decimals=(await sc_token.decimals()),
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.ACCEPT_TRADE:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeAccepted().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                sc_token = AvalancheERC20(event["args"]["SCTokenAddress"])
                wst_tx.event_log = IbetWSTEventLogTradeAccepted(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                    sc_decimals=(await sc_token.decimals()),
                )
                await db_session.merge(wst_tx)
        case IbetWSTTxType.REJECT_TRADE:
            assert wst_tx.ibet_wst_address is not None
            # Update the IbetWST transaction with the event log
            ibet_wst = AvalancheIbetWST(wst_tx.ibet_wst_address)
            events = ibet_wst.contract.events.TradeRejected().process_receipt(
                txn_receipt=tx_receipt, errors=DISCARD
            )
            event = events[0] if len(events) > 0 else None
            if event is not None:
                sc_token = AvalancheERC20(event["args"]["SCTokenAddress"])
                wst_tx.event_log = IbetWSTEventLogTradeRejected(
                    index=event["args"]["index"],
                    seller_st_account_address=event["args"]["sellerSTAccountAddress"],
                    buyer_st_account_address=event["args"]["buyerSTAccountAddress"],
                    sc_token_address=event["args"]["SCTokenAddress"],
                    seller_sc_account_address=event["args"]["sellerSCAccountAddress"],
                    buyer_sc_account_address=event["args"]["buyerSCAccountAddress"],
                    st_value=event["args"]["STValue"],
                    sc_value=event["args"]["SCValue"],
                    sc_decimals=(await sc_token.decimals()),
                )
                await db_session.merge(wst_tx)
        case _:
            return

    # If there are transactions with duplicate nonces,
    # update the status of all such records to FAILED.
    duplicate_tx_list: Sequence[AvaIbetWSTTx] = (
        await db_session.scalars(
            select(AvaIbetWSTTx).where(
                and_(
                    AvaIbetWSTTx.tx_sender == wst_tx.tx_sender,
                    AvaIbetWSTTx.tx_nonce == wst_tx.tx_nonce,
                    AvaIbetWSTTx.tx_id != wst_tx.tx_id,
                    AvaIbetWSTTx.status == IbetWSTTxStatus.SENT,
                    AvaIbetWSTTx.finalized.is_not(True),
                )
            )
        )
    ).all()
    if len(duplicate_tx_list) > 0:
        # Update the status of all duplicate transactions to FAILED
        for duplicate_tx in duplicate_tx_list:
            LOG.warning(
                f"Duplicate transaction found: id={duplicate_tx.tx_id}, sender={duplicate_tx.tx_sender}, nonce={duplicate_tx.tx_nonce}"
            )
            duplicate_tx.status = IbetWSTTxStatus.FAILED
            duplicate_tx.finalized = True
            await db_session.merge(duplicate_tx)


async def main():
    LOG.info("Service started successfully")
    processor = ProcessorAvaWSTMonitorTxReceipt()

    while True:
        try:
            await processor.run()
        except ServiceUnavailableError as ex:
            LOG.error(f"All blockchain nodes are unavailable: {ex}")
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
