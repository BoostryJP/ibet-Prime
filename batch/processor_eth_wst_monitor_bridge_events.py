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
import secrets
import sys
import uuid
from typing import Literal, Sequence

import uvloop
from eth_keyfile import decode_keyfile_json
from pydantic import BaseModel
from pydantic_core import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.model.db import (
    Account,
    EthIbetWSTTx,
    EthToIbetBridgeTx,
    EthToIbetBridgeTxStatus,
    EthToIbetBridgeTxType,
    IbetBridgeTxParamsForceChangeLockedAccount,
    IbetBridgeTxParamsForceUnlock,
    IbetWSTAuthorization,
    IbetWSTBridgeSyncedBlockNumber,
    IbetWSTTxParamsMint,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    Token,
)
from app.model.eth import IbetWST, IbetWSTDigestHelper
from app.utils.e2ee_utils import E2EEUtils
from app.utils.eth_contract_utils import (
    EthAsyncContractEventsView,
    EthAsyncContractUtils,
    EthWeb3,
)
from app.utils.ibet_contract_utils import (
    AsyncContractEventsView,
    AsyncContractUtils,
    async_web3 as IbetWeb3,
)
from batch import free_malloc
from batch.utils import batch_log
from config import (
    IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE,
    IBET_WST_BRIDGE_INTERVAL,
    ZERO_ADDRESS,
)
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS

"""
[PROCESSOR-ETH-WST-Monitor-Bridge-Events]

This processor monitors bridge events related to IbetWST tokens and processes them accordingly.
"""

process_name = "PROCESSOR-ETH-WST-Monitor-Bridge-Events"
LOG = batch_log.get_logger(process_name=process_name)


class BridgeEventViewer:
    """
    Class to view events related to IbetWST bridge operations.
    """

    issuer_address: str
    ibet_token_address: str
    ibet_event_view: AsyncContractEventsView
    wst_event_view: EthAsyncContractEventsView

    def __init__(self, token: Token):
        # Initialize issuer address
        self.issuer_address = token.issuer_address

        # Initialize ibet token address
        self.ibet_token_address = token.token_address

        # Initialize ibet token event view
        ibet_token_contract = IbetWeb3.eth.contract(
            address=token.token_address, abi=token.abi
        )
        self.ibet_event_view = AsyncContractEventsView(
            address=token.token_address, contract_events=ibet_token_contract.events
        )

        # Initialize IbetWST event view
        wst_contract = EthAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST", contract_address=token.ibet_wst_address
        )
        self.wst_event_view = EthAsyncContractEventsView(
            address=token.ibet_wst_address, contract_events=wst_contract.events
        )

    async def get_ibet_event_logs(
        self, event_name: str, block_from: int, block_to: int
    ) -> Sequence[dict]:
        logs = await AsyncContractUtils.get_event_logs(
            contract=self.ibet_event_view,
            event=event_name,
            block_from=block_from,
            block_to=block_to,
        )
        return logs

    async def get_wst_event_logs(
        self, event_name: str, block_from: int, block_to: int
    ) -> Sequence[dict]:
        logs = await EthAsyncContractUtils.get_event_logs(
            contract=self.wst_event_view,
            event=event_name,
            block_from=block_from,
            block_to=block_to,
        )
        return logs


class BridgeMessage(BaseModel):
    """
    Message format for IbetWST bridge operations.
    """

    message: Literal["ibet_wst_bridge"]


class WSTBridgeMonitoringProcessor:
    """
    Processor for handling IbetWST bridge operations.
    """

    def __init__(self):
        # Key: wst_address, Value: BridgeEventViewer
        self.wst_list: dict[str, BridgeEventViewer] = {}

    async def run(self):
        """
        Main method to run the WST bridge monitoring processor.
        """
        # Load the latest list of WST tokens
        await self.load_wst_list()
        # Process bridge events from ibetfin to ethereum
        await self.ibet_to_eth()
        # Process bridge events from ethereum to ibetfin
        await self.eth_to_ibet()

    async def load_wst_list(self):
        """
        Load the list of WST tokens from the database and initialize their contract events.
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the list of all WST tokens that have been deployed
            wst_address_all: tuple[str, ...] = tuple(
                [
                    record[0]
                    for record in (
                        await db_session.execute(
                            select(Token.ibet_wst_address)
                            .join(
                                Account,
                                and_(
                                    Account.issuer_address == Token.issuer_address,
                                    Account.is_deleted == False,
                                ),
                            )
                            .where(Token.ibet_wst_deployed.is_(True))
                        )
                    )
                    .tuples()
                    .all()
                ]
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

            # Get the list of WST tokens that need to be loaded
            load_required_token_list: Sequence[Token] = (
                await db_session.scalars(
                    select(Token).where(
                        Token.ibet_wst_address.in_(load_required_address_list),
                    )
                )
            ).all()
            for _token in load_required_token_list:
                self.wst_list[_token.ibet_wst_address] = BridgeEventViewer(_token)
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    async def ibet_to_eth(self):
        """
        Detect events from ibet for Fin and operate IbetWST tokens on Ethereum.
        - 1. Lock event of ibet token -> Execute mintWithAuthorization on IbetWST
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the latest block number to start monitoring
            latest_block = await self.get_latest_block_number("ibetfin")
            _block_from = await self.get_from_block_number(db_session, "ibetfin")

            # Calculate the block range to monitor
            _block_to = _block_from + IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE

            # Skip processing if the range exceeds the latest block
            if _block_from >= latest_block:
                LOG.debug("skip process")
                return

            if latest_block > _block_to:
                # If the range exceeds the latest block, process in chunks
                while _block_to < latest_block:
                    await self.__process_mint(db_session, _block_from + 1, _block_to)
                    _block_to += IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE
                    _block_from += IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE
                # Process the remaining blocks
                await self.__process_mint(db_session, _block_from + 1, latest_block)
            else:
                # If the range does not exceed the latest block, process all at once
                await self.__process_mint(db_session, _block_from + 1, latest_block)

            # Update the latest synchronized block number
            await self.set_synced_block_number(
                db_session, network="ibetfin", block_number=latest_block
            )
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    async def eth_to_ibet(self):
        """
        Detect events from IbetWST on Ethereum and operate tokens on ibet for Fin.
        - 1. Burn event of IbetWST -> Execute unlock on ibet token
        - 2. Transfer event of IbetWST -> Execute forceChangeLockedAccount on ibet token
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the latest block number to start monitoring
            latest_block = await self.get_latest_block_number("ethereum")
            _block_from = await self.get_from_block_number(db_session, "ethereum")

            # Calculate the block range to monitor
            _block_to = _block_from + IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE

            # Skip processing if the range exceeds the latest block
            if _block_from >= latest_block:
                LOG.debug("skip process")
                return

            if latest_block > _block_to:
                # If the range exceeds the latest block, process in chunks
                while _block_to < latest_block:
                    await self.__process_burn(db_session, _block_from + 1, _block_to)
                    await self.__process_transfer(
                        db_session, _block_from + 1, _block_to
                    )
                    _block_to += IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE
                    _block_from += IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE
                # Process the remaining blocks
                await self.__process_burn(db_session, _block_from + 1, latest_block)
                await self.__process_transfer(db_session, _block_from + 1, latest_block)
            else:
                # If the range does not exceed the latest block, process all at once
                await self.__process_burn(db_session, _block_from + 1, latest_block)
                await self.__process_transfer(db_session, _block_from + 1, latest_block)

            # Update the latest synchronized block number
            await self.set_synced_block_number(
                db_session, network="ethereum", block_number=latest_block
            )
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    @staticmethod
    async def get_latest_block_number(network: Literal["ethereum", "ibetfin"]):
        """
        Get the latest block number
        """
        if network == "ethereum":
            block = await EthWeb3.eth.get_block("finalized")
            block_number = block.get("number")
        else:
            block_number = await IbetWeb3.eth.block_number

        return block_number

    @staticmethod
    async def get_from_block_number(
        db_session: AsyncSession, network: Literal["ethereum", "ibetfin"]
    ) -> int:
        """
        Get the starting block number for monitoring trade events.
        """
        synced_block = (
            await db_session.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == network)
                .limit(1)
            )
        ).first()
        if synced_block is None:
            return 0
        else:
            return synced_block.latest_block_number

    @staticmethod
    async def set_synced_block_number(
        db_session: AsyncSession,
        network: Literal["ethereum", "ibetfin"],
        block_number: int,
    ) -> None:
        """
        Set the latest synchronized block number for IbetWSTBridgeSyncedBlockNumber.
        """
        synced_block = (
            await db_session.scalars(
                select(IbetWSTBridgeSyncedBlockNumber)
                .where(IbetWSTBridgeSyncedBlockNumber.network == network)
                .limit(1)
            )
        ).first()
        if synced_block is None:
            synced_block = IbetWSTBridgeSyncedBlockNumber()
            synced_block.network = network

        synced_block.latest_block_number = block_number
        await db_session.merge(synced_block)

    async def __process_mint(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Process mint events from ibet token and issue mintWithAuthorization transactions for IbetWST.
        """
        for wst_address, bridge_event_viewer in self.wst_list.items():
            # Get Lock events from ibet token
            lock_events = await bridge_event_viewer.get_ibet_event_logs(
                event_name="Lock", block_from=block_from, block_to=block_to
            )
            for lock_event in lock_events:
                # Filter out events that do not match the issuer address
                args = lock_event["args"]
                if args["lockAddress"] != bridge_event_viewer.issuer_address:
                    # Skip if the lockAddress does not match the issuer address
                    continue
                try:
                    # Skip if the data is not a valid BridgeMessage
                    BridgeMessage(**json.loads(args["data"]))
                except (json.JSONDecodeError, ValidationError, TypeError):
                    continue

                # Retrieve the issuer's private key
                issuer: Account | None = (
                    await db_session.scalars(
                        select(Account)
                        .where(
                            Account.issuer_address == bridge_event_viewer.issuer_address
                        )
                        .limit(1)
                    )
                ).first()
                if issuer is None:
                    LOG.warning(
                        f"Cannot find issuer for IbetWST address: {wst_address}"
                    )
                    continue
                issuer_pk = decode_keyfile_json(
                    raw_keyfile_json=issuer.keyfile,
                    password=E2EEUtils.decrypt(issuer.eoa_password).encode("utf-8"),
                )

                # Issue mintWithAuthorization transaction for IbetWST
                try:
                    # Get the IbetWST contract
                    wst_contract = IbetWST(wst_address)
                    # Generate nonce
                    nonce = secrets.token_bytes(32)
                    # Get domain separator
                    domain_separator = await wst_contract.domain_separator()
                    # Generate digest
                    digest = IbetWSTDigestHelper.generate_mint_digest(
                        domain_separator=domain_separator,
                        to_address=args["accountAddress"],
                        value=args["value"],
                        nonce=nonce,
                    )
                    # Sign the digest from the authorizer's private key
                    signature = EthWeb3.eth.account.unsafe_sign_hash(digest, issuer_pk)

                    # Insert transaction record
                    tx_id = str(uuid.uuid4())
                    wst_tx = EthIbetWSTTx()
                    wst_tx.tx_id = tx_id
                    wst_tx.tx_type = IbetWSTTxType.MINT
                    wst_tx.version = IbetWSTVersion.V_1
                    wst_tx.status = IbetWSTTxStatus.PENDING
                    wst_tx.ibet_wst_address = wst_address
                    wst_tx.tx_params = IbetWSTTxParamsMint(
                        to_address=args["accountAddress"],
                        value=args["value"],
                    )
                    wst_tx.tx_sender = ETH_MASTER_ACCOUNT_ADDRESS
                    wst_tx.authorizer = issuer.issuer_address
                    wst_tx.authorization = IbetWSTAuthorization(
                        nonce=nonce.hex(),
                        v=signature.v,
                        r=signature.r.to_bytes(32).hex(),
                        s=signature.s.to_bytes(32).hex(),
                    )
                    db_session.add(wst_tx)
                    LOG.info(
                        f"Minting IbetWST: {wst_address}, to={args['accountAddress']}, value={args['value']}, tx_id={tx_id}"
                    )
                except Exception as e:
                    LOG.error(f"Failed to mint WST: {wst_address}, error: {e}")
                    continue

    async def __process_burn(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Process burn events from IbetWST and issue unlock transactions for ibet tokens.
        """
        for wst_address, bridge_event_viewer in self.wst_list.items():
            # Get Burn events from IbetWST
            burn_events = await bridge_event_viewer.get_wst_event_logs(
                event_name="Burn", block_from=block_from, block_to=block_to
            )
            for burn_event in burn_events:
                args = burn_event["args"]
                # Issue unlock transaction for ibet token
                tx_id = str(uuid.uuid4())
                bridge_tx = EthToIbetBridgeTx()
                bridge_tx.tx_id = tx_id
                bridge_tx.token_address = bridge_event_viewer.ibet_token_address
                bridge_tx.tx_type = EthToIbetBridgeTxType.FORCE_UNLOCK
                bridge_tx.status = EthToIbetBridgeTxStatus.PENDING
                bridge_tx.tx_params = IbetBridgeTxParamsForceUnlock(
                    lock_address=bridge_event_viewer.issuer_address,
                    account_address=args["from"],
                    recipient_address=args["from"],
                    value=args["value"],
                    data=BridgeMessage(message="ibet_wst_bridge").model_dump(),
                )
                bridge_tx.tx_sender = bridge_event_viewer.issuer_address
                db_session.add(bridge_tx)

    async def __process_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Process transfer events from IbetWST and issue forceChangeLockedAccount transactions for ibet tokens.
        """
        for wst_address, bridge_event_viewer in self.wst_list.items():
            # Get Transfer events from IbetWST
            burn_events = await bridge_event_viewer.get_wst_event_logs(
                event_name="Transfer", block_from=block_from, block_to=block_to
            )
            for burn_event in burn_events:
                args = burn_event["args"]
                if args["from"] == ZERO_ADDRESS or args["to"] == ZERO_ADDRESS:
                    # Skip if the transfer is from or to the zero address
                    continue

                # Issue forceChangeLockedAccount transaction for ibet token
                tx_id = str(uuid.uuid4())
                bridge_tx = EthToIbetBridgeTx()
                bridge_tx.tx_id = tx_id
                bridge_tx.token_address = bridge_event_viewer.ibet_token_address
                bridge_tx.tx_type = EthToIbetBridgeTxType.FORCE_CHANGE_LOCKED_ACCOUNT
                bridge_tx.status = EthToIbetBridgeTxStatus.PENDING
                bridge_tx.tx_params = IbetBridgeTxParamsForceChangeLockedAccount(
                    lock_address=bridge_event_viewer.issuer_address,
                    before_account_address=args["from"],
                    after_account_address=args["to"],
                    value=args["value"],
                    data=BridgeMessage(message="ibet_wst_bridge").model_dump(),
                )
                bridge_tx.tx_sender = bridge_event_viewer.issuer_address
                db_session.add(bridge_tx)


async def main():
    LOG.info("Service started successfully")
    bridge_processor = WSTBridgeMonitoringProcessor()

    while True:
        try:
            await bridge_processor.run()
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during processing")

        await asyncio.sleep(IBET_WST_BRIDGE_INTERVAL)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
