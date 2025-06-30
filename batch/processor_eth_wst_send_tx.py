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
from eth_keyfile import decode_keyfile_json
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.model.db import (
    Account,
    EthIbetWSTTx,
    IbetWSTTxParamsAcceptTrade,
    IbetWSTTxParamsAddAccountWhiteList,
    IbetWSTTxParamsBurn,
    IbetWSTTxParamsCancelTrade,
    IbetWSTTxParamsDeleteAccountWhiteList,
    IbetWSTTxParamsDeploy,
    IbetWSTTxParamsMint,
    IbetWSTTxParamsRequestTrade,
    IbetWSTTxStatus,
    IbetWSTTxType,
)
from app.model.eth import IbetWST, IbetWSTAuthorization, IbetWSTTrade
from app.utils.e2ee_utils import E2EEUtils
from app.utils.eth_contract_utils import EthAsyncContractUtils
from batch import free_malloc
from batch.utils import batch_log
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS, ETH_MASTER_PRIVATE_KEY

"""
[PROCESSOR-ETH-WST-SendTx]

This processor is responsible for sending transactions related to IbetWST on Ethereum.
"""

process_name = "PROCESSOR-ETH-WST-SendTx"
LOG = batch_log.get_logger(process_name=process_name)


class ProcessorEthWSTSendTx:
    """
    Processor for sending transactions related to IbetWST on Ethereum.
    """

    async def run(self):
        """
        Run the processor to send transactions.
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Extract unprocessed transactions
            wst_tx_list: Sequence[EthIbetWSTTx] = (
                await db_session.scalars(
                    select(EthIbetWSTTx).where(
                        and_(
                            EthIbetWSTTx.status == IbetWSTTxStatus.PENDING,
                            EthIbetWSTTx.tx_hash.is_(None),
                        )
                    )
                )
            ).all()
            for wst_tx in wst_tx_list:
                LOG.info(
                    f"Processing transaction: id={wst_tx.tx_id}, type={wst_tx.tx_type}"
                )

                # Get account information
                tx_sender_account = await get_tx_sender_account(
                    db_session=db_session,
                    tx_sender=wst_tx.tx_sender,
                )
                if not tx_sender_account:
                    # If the account is not found, output an error log and set the status to FAILED
                    LOG.error(
                        f"Account not found for transaction sender: {wst_tx.tx_sender}"
                    )
                    wst_tx.status = IbetWSTTxStatus.FAILED
                    await db_session.merge(wst_tx)
                    await db_session.commit()
                    continue

                try:
                    # Branch processing by transaction type
                    if wst_tx.tx_type == IbetWSTTxType.DEPLOY:
                        # Send deployment transaction
                        tx_hash = await send_deploy_transaction(
                            wst_tx, tx_sender_account
                        )
                    elif wst_tx.tx_type == IbetWSTTxType.ADD_WHITELIST:
                        # Send add whitelist transaction
                        tx_hash = await send_add_whitelist_transaction(
                            wst_tx, tx_sender_account
                        )
                    elif wst_tx.tx_type == IbetWSTTxType.DELETE_WHITELIST:
                        # Send delete whitelist transaction
                        tx_hash = await send_delete_whitelist_transaction(
                            wst_tx, tx_sender_account
                        )
                    elif wst_tx.tx_type == IbetWSTTxType.MINT:
                        # Send mint transaction
                        tx_hash = await send_mint_transaction(wst_tx, tx_sender_account)
                    elif wst_tx.tx_type == IbetWSTTxType.BURN:
                        # Send burn transaction
                        tx_hash = await send_burn_transaction(wst_tx, tx_sender_account)
                    elif wst_tx.tx_type == IbetWSTTxType.REQUEST_TRADE:
                        # Send request trade transaction
                        tx_hash = await send_request_trade_transaction(
                            wst_tx, tx_sender_account
                        )
                    elif wst_tx.tx_type == IbetWSTTxType.CANCEL_TRADE:
                        # Send cancel trade transaction
                        tx_hash = await cancel_trade_transaction(
                            wst_tx, tx_sender_account
                        )
                    elif wst_tx.tx_type == IbetWSTTxType.ACCEPT_TRADE:
                        # Send accept trade transaction
                        tx_hash = await accept_trade_transaction(
                            wst_tx, tx_sender_account
                        )
                    else:
                        continue

                    # If successful, update the status
                    wst_tx.status = IbetWSTTxStatus.SENT
                    wst_tx.tx_hash = tx_hash
                    await db_session.merge(wst_tx)
                    await db_session.commit()
                    LOG.info(f"Transaction sent successfully: id={wst_tx.tx_id}")
                except Exception:
                    # If sending fails, output an error log and skip processing
                    LOG.exception(f"Failed to send transaction: id={wst_tx.tx_id}")
                    continue
        finally:
            # Close the session
            await db_session.close()


class TxSenderAccount(BaseModel):
    address: str
    private_key: bytes


async def get_tx_sender_account(
    db_session: AsyncSession,
    tx_sender: str,
) -> TxSenderAccount | None:
    """
    Get the account information of the transaction sender.
    """

    if tx_sender == ETH_MASTER_ACCOUNT_ADDRESS:
        # If the transaction sender is the master account, return the master account information
        return TxSenderAccount(
            address=ETH_MASTER_ACCOUNT_ADDRESS,
            private_key=bytes.fromhex(ETH_MASTER_PRIVATE_KEY),
        )
    else:
        # If the transaction sender is not the master account, retrieve the account information from the database
        tx_sender_account = (
            await db_session.scalars(
                select(Account).where(Account.issuer_address == tx_sender).limit(1)
            )
        ).first()
        if tx_sender_account is not None:
            private_key = decode_keyfile_json(
                raw_keyfile_json=tx_sender_account.keyfile,
                password=E2EEUtils.decrypt(tx_sender_account.eoa_password).encode(
                    "utf-8"
                ),
            )
            return TxSenderAccount(
                address=tx_sender_account.issuer_address,
                private_key=private_key,
            )
        else:
            return None


async def send_deploy_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a deployment transaction for the IbetWST contract.
    """
    tx_params: IbetWSTTxParamsDeploy = wst_tx.tx_params
    tx_hash = await EthAsyncContractUtils.deploy_contract(
        contract_name="AuthIbetWST",
        args=[
            tx_params["name"],
            tx_params["initial_owner"],
        ],
        deployer=tx_sender_account.address,
        private_key=tx_sender_account.private_key,
    )
    return tx_hash


async def send_add_whitelist_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to add an account to the IbetWST whitelist.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsAddAccountWhiteList = wst_tx.tx_params
    tx_hash = await wst_contract.add_account_white_list_with_authorization(
        account=tx_params["account_address"],
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def send_delete_whitelist_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to delete an account from the IbetWST whitelist.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsDeleteAccountWhiteList = wst_tx.tx_params
    tx_hash = await wst_contract.delete_account_white_list_with_authorization(
        account=tx_params["account_address"],
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def send_mint_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to mint IbetWST tokens.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsMint = wst_tx.tx_params
    tx_hash = await wst_contract.mint_with_authorization(
        to_address=tx_params["to_address"],
        value=wst_tx.tx_params["value"],
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def send_burn_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to burn IbetWST tokens.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsBurn = wst_tx.tx_params
    tx_hash = await wst_contract.burn_with_authorization(
        from_address=tx_params["from_address"],
        value=wst_tx.tx_params["value"],
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def send_request_trade_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to request a trade for the IbetWST.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsRequestTrade = wst_tx.tx_params
    tx_hash = await wst_contract.request_trade_with_authorization(
        trade=IbetWSTTrade(
            seller_st_account=tx_params["seller_st_account_address"],
            buyer_st_account=tx_params["buyer_st_account_address"],
            sc_token_address=tx_params["sc_token_address"],
            seller_sc_account=tx_params["seller_sc_account_address"],
            buyer_sc_account=tx_params["buyer_sc_account_address"],
            st_value=tx_params["st_value"],
            sc_value=tx_params["sc_value"],
            memo=tx_params["memo"],
        ),
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def cancel_trade_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to cancel a trade for the IbetWST.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsCancelTrade = wst_tx.tx_params
    tx_hash = await wst_contract.cancel_trade_with_authorization(
        index=tx_params["index"],
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def accept_trade_transaction(
    wst_tx: EthIbetWSTTx,
    tx_sender_account: TxSenderAccount,
) -> str:
    """
    Send a transaction to accept a trade for the IbetWST.
    """
    wst_contract = IbetWST(wst_tx.ibet_wst_address)
    tx_params: IbetWSTTxParamsAcceptTrade = wst_tx.tx_params
    tx_hash = await wst_contract.accept_trade_with_authorization(
        index=tx_params["index"],
        authorization=IbetWSTAuthorization(
            nonce=bytes(32).fromhex(wst_tx.authorization["nonce"]),
            v=wst_tx.authorization["v"],
            r=bytes(32).fromhex(wst_tx.authorization["r"]),
            s=bytes(32).fromhex(wst_tx.authorization["s"]),
        ),
        tx_sender=tx_sender_account.address,
        tx_sender_key=tx_sender_account.private_key,
    )
    return tx_hash


async def main():
    LOG.info("Service started successfully")
    processor = ProcessorEthWSTSendTx()

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
