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
from typing import Any, Literal, Sequence, cast

import uvloop
from eth_keyfile.keyfile import decode_keyfile_json
from eth_utils.address import to_checksum_address
from pydantic import BaseModel
from pydantic_core import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.model.db import (
    Account,
    AvaIbetWSTTx,
    AvaToIbetBridgeTx,
    IbetBridgeTxParamsForceChangeLockedAccount,
    IbetBridgeTxParamsForceUnlock,
    IbetWSTAuthorization,
    IbetWSTBlockchain,
    IbetWSTBridgeSyncedBlockNumber,
    IbetWSTTxParamsMint,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    ToIbetBridgeTxStatus,
    ToIbetBridgeTxType,
    Token,
)
from app.model.wst import AvalancheIbetWST, IbetWSTDigestHelper
from app.utils.ava_contract_utils import (
    AvaAsyncContractEventsView,
    AvaAsyncContractUtils,
    AvaWeb3,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import (
    AsyncContractEventsView,
    AsyncContractUtils,
    async_web3 as IbetWeb3,
)
from avalanche_config import AVA_MASTER_ACCOUNT_ADDRESS
from batch import free_malloc
from batch.utils import batch_log
from config import (
    IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE,
    IBET_WST_BRIDGE_INTERVAL,
    ZERO_ADDRESS,
)

"""
[PROCESSOR-AVA-WST-Monitor-Bridge-Events]

This processor monitors bridge events related to Avalanche IbetWST tokens and processes them accordingly.
"""

process_name = "PROCESSOR-AVA-WST-Monitor-Bridge-Events"
LOG = batch_log.get_logger(process_name=process_name)


EventLog = dict[str, Any]


class AvaBridgeEventViewer:
    """
    Class to view events related to AVA IbetWST bridge operations.
    """

    issuer_address: str
    ibet_token_address: str
    ibet_event_view: AsyncContractEventsView
    wst_event_view: AvaAsyncContractEventsView

    def __init__(self, token: Token):
        wst_address = token.get_ibet_wst_address(IbetWSTBlockchain.AVALANCHE)
        if wst_address is None:
            raise ValueError("IbetWST address is not configured for avalanche")

        # Initialize issuer address
        self.issuer_address = token.issuer_address

        # Initialize ibet token address
        self.ibet_token_address = token.token_address

        # Initialize ibet token event view
        ibet_token_contract = IbetWeb3.eth.contract(
            address=to_checksum_address(token.token_address),
            abi=token.abi,
        )
        self.ibet_event_view = AsyncContractEventsView(
            address=token.token_address, contract_events=ibet_token_contract.events
        )

        # Initialize IbetWST event view
        wst_contract = AvaAsyncContractUtils.get_contract(
            contract_name="AuthIbetWST", contract_address=wst_address
        )
        self.wst_event_view = AvaAsyncContractEventsView(
            address=wst_address, contract_events=wst_contract.events
        )

    async def get_ibet_event_logs(
        self, event_name: str, block_from: int, block_to: int
    ) -> list[EventLog]:
        logs = await AsyncContractUtils.get_event_logs(
            contract=self.ibet_event_view,
            event=event_name,
            block_from=block_from,
            block_to=block_to,
        )
        return cast(list[EventLog], logs)

    async def get_wst_event_logs(
        self, event_name: str, block_from: int, block_to: int
    ) -> list[EventLog]:
        logs = await AvaAsyncContractUtils.get_event_logs(
            contract=self.wst_event_view,
            event=event_name,
            block_from=block_from,
            block_to=block_to,
        )
        return cast(list[EventLog], logs)


class BridgeMessageMint(BaseModel):
    """
    Message format for IbetWST mint operations.
    """

    message: Literal["ibet_wst_bridge"]
    network: Literal["avalanche"] = "avalanche"


class BridgeMessageBurn(BaseModel):
    """
    Message format for IbetWST burn operations.
    """

    message: Literal["ibet_wst_bridge"]


class BridgeMessageTransfer(BaseModel):
    """
    Message format for IbetWST transfer operations.
    """

    message: Literal["ibet_wst_bridge"]


class AvaWSTBridgeMonitoringProcessor:
    """
    Processor for handling Avalanche IbetWST bridge operations.
    """

    def __init__(self):
        # Key: wst_address, Value: AvaBridgeEventViewer
        self.wst_list: dict[str, AvaBridgeEventViewer] = {}

    async def run(self):
        """
        Main method to run the AVA WST bridge monitoring processor.
        """
        # Load the latest list of WST tokens
        await self.load_wst_list()
        # Process bridge events from ibetfin to avalanche
        await self.ibet_to_ava()
        # Process bridge events from avalanche to ibetfin
        await self.ava_to_ibet()

    async def load_wst_list(self):
        """
        Load the list of WST tokens from the database and initialize their contract events.
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            load_target_tokens: Sequence[Token] = (
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

            wst_address_set: set[str] = set()
            for token in load_target_tokens:
                if not token.is_ibet_wst_deployed(IbetWSTBlockchain.AVALANCHE):
                    continue
                wst_address = token.get_ibet_wst_address(IbetWSTBlockchain.AVALANCHE)
                if wst_address is None:
                    continue
                wst_address_set.add(wst_address)
            wst_address_all: tuple[str, ...] = tuple(wst_address_set)

            loaded_address_list: tuple[str, ...] = tuple(self.wst_list.keys())
            load_required_address_list = list(
                set(wst_address_all) ^ set(loaded_address_list)
            )

            if not load_required_address_list:
                # If there are no additional tokens to load, skip process
                return

            for _token in load_target_tokens:
                wst_address = _token.get_ibet_wst_address(IbetWSTBlockchain.AVALANCHE)
                if wst_address is None:
                    continue
                if wst_address not in load_required_address_list:
                    continue
                self.wst_list[wst_address] = AvaBridgeEventViewer(_token)
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    async def ibet_to_ava(self):
        """
        Detect events from ibetfin and operate IbetWST tokens on avalanche.
        - 1. Lock event of ibet token -> Execute mintWithAuthorization on IbetWST
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the latest block number to start monitoring
            latest_block = await self.get_latest_block_number("ibetfin")
            _block_from = await self.get_from_block_number(db_session, "ibetfin")
            # Calculate the block range to monitor
            _block_to = _block_from + IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE

            if _block_from >= latest_block:
                # Skip processing if the range exceeds the latest block
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

    async def ava_to_ibet(self):
        """
        Detect events from IbetWST on avalanche and operate tokens on ibetfin.
        - 1. Burn event of IbetWST -> Execute unlock on ibet token
        - 2. Transfer event of IbetWST -> Execute forceChangeLockedAccount on ibet token
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            # Get the latest block number to start monitoring
            latest_block = await self.get_latest_block_number("avalanche")
            _block_from = await self.get_from_block_number(db_session, "avalanche")
            # Calculate the block range to monitor
            _block_to = _block_from + IBET_WST_BRIDGE_BLOCK_LOT_MAX_SIZE

            if _block_from >= latest_block:
                # Skip processing if the range exceeds the latest block
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
                db_session, network="avalanche", block_number=latest_block
            )
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise
        finally:
            await db_session.close()

    @staticmethod
    async def get_latest_block_number(network: Literal["avalanche", "ibetfin"]) -> int:
        """
        Get the latest block number.
        """
        if network == "avalanche":
            block_number = await AvaAsyncContractUtils.get_finalized_block_number()
        else:
            block_number = await IbetWeb3.eth.block_number

        return block_number

    @staticmethod
    async def get_from_block_number(
        db_session: AsyncSession, network: Literal["avalanche", "ibetfin"]
    ) -> int:
        """
        Get the starting block number for monitoring bridge events.
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
            return synced_block.latest_block_number or 0

    @staticmethod
    async def set_synced_block_number(
        db_session: AsyncSession,
        network: Literal["avalanche", "ibetfin"],
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
                args = lock_event["args"]
                # Filter out events that do not match the issuer address
                if args["lockAddress"] != bridge_event_viewer.issuer_address:
                    continue
                try:
                    # Skip if the data is not a valid BridgeMessage
                    bridge_message_mint = BridgeMessageMint(**json.loads(args["data"]))
                except json.JSONDecodeError, ValidationError, TypeError:
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

                try:
                    # Issue mintWithAuthorization transaction for IbetWST
                    wst_contract = AvalancheIbetWST(wst_address)
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
                    signature = AvaWeb3.eth.account.unsafe_sign_hash(digest, issuer_pk)

                    tx_id = str(uuid.uuid4())
                    if bridge_message_mint.network == "avalanche":
                        # Insert transaction record
                        wst_tx = AvaIbetWSTTx()
                        wst_tx.tx_id = tx_id
                        wst_tx.tx_type = IbetWSTTxType.MINT
                        wst_tx.version = IbetWSTVersion.V_1
                        wst_tx.status = IbetWSTTxStatus.PENDING
                        wst_tx.ibet_wst_address = wst_address
                        wst_tx.tx_params = IbetWSTTxParamsMint(
                            to_address=args["accountAddress"],
                            value=args["value"],
                        )
                        assert AVA_MASTER_ACCOUNT_ADDRESS is not None
                        wst_tx.tx_sender = AVA_MASTER_ACCOUNT_ADDRESS
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
        for bridge_event_viewer in self.wst_list.values():
            # Get Burn events from IbetWST
            burn_events = await bridge_event_viewer.get_wst_event_logs(
                event_name="Burn", block_from=block_from, block_to=block_to
            )
            for burn_event in burn_events:
                args = burn_event["args"]
                # Issue unlock transaction for ibet token
                tx_id = str(uuid.uuid4())
                bridge_tx = AvaToIbetBridgeTx()
                bridge_tx.tx_id = tx_id
                bridge_tx.token_address = bridge_event_viewer.ibet_token_address
                bridge_tx.tx_type = ToIbetBridgeTxType.FORCE_UNLOCK
                bridge_tx.status = ToIbetBridgeTxStatus.PENDING
                bridge_tx.tx_params = IbetBridgeTxParamsForceUnlock(
                    lock_address=bridge_event_viewer.issuer_address,
                    account_address=args["from"],
                    recipient_address=args["from"],
                    value=args["value"],
                    data=BridgeMessageBurn(message="ibet_wst_bridge").model_dump(),
                )
                bridge_tx.tx_sender = bridge_event_viewer.issuer_address
                db_session.add(bridge_tx)

    async def __process_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """
        Process transfer events from IbetWST and issue forceChangeLockedAccount transactions for ibet tokens.
        """
        for bridge_event_viewer in self.wst_list.values():
            # Get Transfer events from IbetWST
            transfer_events = await bridge_event_viewer.get_wst_event_logs(
                event_name="Transfer", block_from=block_from, block_to=block_to
            )
            for transfer_event in transfer_events:
                args = transfer_event["args"]
                if args["from"] == ZERO_ADDRESS or args["to"] == ZERO_ADDRESS:
                    # Skip if the transfer is from or to the zero address
                    continue

                # Issue forceChangeLockedAccount transaction for ibet token
                tx_id = str(uuid.uuid4())
                bridge_tx = AvaToIbetBridgeTx()
                bridge_tx.tx_id = tx_id
                bridge_tx.token_address = bridge_event_viewer.ibet_token_address
                bridge_tx.tx_type = ToIbetBridgeTxType.FORCE_CHANGE_LOCKED_ACCOUNT
                bridge_tx.status = ToIbetBridgeTxStatus.PENDING
                bridge_tx.tx_params = IbetBridgeTxParamsForceChangeLockedAccount(
                    lock_address=bridge_event_viewer.issuer_address,
                    before_account_address=args["from"],
                    after_account_address=args["to"],
                    value=args["value"],
                    data=BridgeMessageTransfer(message="ibet_wst_bridge").model_dump(),
                )
                bridge_tx.tx_sender = bridge_event_viewer.issuer_address
                db_session.add(bridge_tx)


async def main():
    LOG.info("Service started successfully")
    bridge_processor = AvaWSTBridgeMonitoringProcessor()

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
