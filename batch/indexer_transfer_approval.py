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
import uuid
from datetime import UTC, datetime
from typing import Optional, Sequence

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
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType,
    Token,
    TokenStatus,
    TokenType,
)
from app.utils.contract_utils import AsyncContractEventsView, AsyncContractUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import free_malloc
from batch.utils import batch_log
from config import INDEXER_BLOCK_LOT_MAX_SIZE, INDEXER_SYNC_INTERVAL, ZERO_ADDRESS

process_name = "INDEXER-TransferApproval"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


"""
Batch process for indexing security token transfer approval events

ibetSecurityToken
  - ApplyForTransfer: 'ApplyFor'
  - CancelTransfer: 'Cancel'
  - ApproveTransfer: 'Approve'

ibetSecurityTokenEscrow
  - ApplyForTransfer: 'ApplyFor'
  - CancelTransfer: 'Cancel'
  - EscrowFinished: 'EscrowFinish'
  - ApproveTransfer: 'Approve'

"""


class Processor:
    def __init__(self):
        self.token_list: dict[str, AsyncContractEventsView] = {}
        self.exchange_list: list[AsyncContract] = []
        self.token_type_map: dict[str, TokenType] = {}

    async def sync_new_logs(self):
        db_session = BatchAsyncSessionLocal()
        try:
            await self.__get_contract_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            latest_block = await web3.eth.block_number
            _from_block = await self.__get_idx_transfer_approval_block_number(
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

            await self.__set_idx_transfer_approval_block_number(
                db_session=db_session, block_number=latest_block
            )
            await db_session.commit()
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")

    async def __get_contract_list(self, db_session: AsyncSession):
        self.exchange_list = []

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
            self.token_type_map[load_required_token.token_address] = (
                load_required_token.type
            )

        _exchange_list_tmp = []
        for token_contract in self.token_list.values():
            tradable_exchange_address = ZERO_ADDRESS
            if (
                self.token_type_map.get(token_contract.address)
                == TokenType.IBET_STRAIGHT_BOND.value
            ):
                bond_token = IbetStraightBondContract(token_contract.address)
                await bond_token.get()
                tradable_exchange_address = (
                    bond_token.tradable_exchange_contract_address
                )
            elif (
                self.token_type_map.get(token_contract.address)
                == TokenType.IBET_SHARE.value
            ):
                share_token = IbetShareContract(token_contract.address)
                await share_token.get()
                tradable_exchange_address = (
                    share_token.tradable_exchange_contract_address
                )

            if tradable_exchange_address != ZERO_ADDRESS:
                _exchange_list_tmp.append(tradable_exchange_address)

        # Remove duplicate exchanges from a list
        for _exchange_address in list(set(_exchange_list_tmp)):
            exchange_contract = AsyncContractUtils.get_contract(
                contract_name="IbetSecurityTokenEscrow",
                contract_address=_exchange_address,
            )
            self.exchange_list.append(exchange_contract)

    @staticmethod
    async def __get_idx_transfer_approval_block_number(db_session: AsyncSession):
        _idx_transfer_approval_block_number: IDXTransferApprovalBlockNumber | None = (
            await db_session.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        if _idx_transfer_approval_block_number is None:
            return 0
        else:
            return _idx_transfer_approval_block_number.latest_block_number

    @staticmethod
    async def __set_idx_transfer_approval_block_number(
        db_session: AsyncSession, block_number: int
    ):
        _idx_transfer_approval_block_number: IDXTransferApprovalBlockNumber | None = (
            await db_session.scalars(select(IDXTransferApprovalBlockNumber).limit(1))
        ).first()
        if _idx_transfer_approval_block_number is None:
            _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()

        _idx_transfer_approval_block_number.latest_block_number = block_number
        await db_session.merge(_idx_transfer_approval_block_number)

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info(f"Syncing from={block_from}, to={block_to}")
        await self.__sync_token_apply_for_transfer(db_session, block_from, block_to)
        await self.__sync_token_cancel_transfer(db_session, block_from, block_to)
        await self.__sync_token_approve_transfer(db_session, block_from, block_to)
        await self.__sync_exchange_apply_for_transfer(db_session, block_from, block_to)
        await self.__sync_exchange_cancel_transfer(db_session, block_from, block_to)
        await self.__sync_exchange_escrow_finished(db_session, block_from, block_to)
        await self.__sync_exchange_approve_transfer(db_session, block_from, block_to)

    async def __sync_token_apply_for_transfer(
        self, db_session: AsyncSession, block_from, block_to
    ):
        """Sync ApplyForTransfer Events of Tokens

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
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
                    value = args.get("value", 0)
                    if value > sys.maxsize:  # suppress overflow
                        pass
                    else:
                        block_timestamp = await self.__get_block_timestamp(event=event)
                        await self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=token.address,
                            exchange_address=ZERO_ADDRESS,
                            application_id=args.get("index"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            amount=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp,
                        )
                        await self.__register_notification(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"],
                            token_address=token.address,
                            exchange_address=ZERO_ADDRESS,
                            application_id=args.get("index"),
                            notice_code=0,
                        )
            except Exception:
                raise

    async def __sync_token_cancel_transfer(
        self, db_session: AsyncSession, block_from, block_to
    ):
        """Sync CancelTransfer Events of Tokens

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
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
                    block_timestamp = await self.__get_block_timestamp(event=event)
                    await self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Cancel",
                        token_address=token.address,
                        exchange_address=ZERO_ADDRESS,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        block_timestamp=block_timestamp,
                    )
                    await self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=token.address,
                        exchange_address=ZERO_ADDRESS,
                        application_id=args.get("index"),
                        notice_code=1,
                    )
            except Exception:
                raise

    async def __sync_token_approve_transfer(
        self, db_session: AsyncSession, block_from, block_to
    ):
        """Sync ApproveTransfer Events of Tokens

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
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
                    block_timestamp = await self.__get_block_timestamp(event=event)
                    await self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Approve",
                        token_address=token.address,
                        exchange_address=ZERO_ADDRESS,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp,
                    )
                    await self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=token.address,
                        exchange_address=ZERO_ADDRESS,
                        application_id=args.get("index"),
                        notice_code=2,
                    )
            except Exception:
                raise

    async def __sync_exchange_apply_for_transfer(
        self, db_session: AsyncSession, block_from, block_to
    ):
        """Sync ApplyForTransfer events of exchanges

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="ApplyForTransfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:  # suppress overflow
                        pass
                    else:
                        block_timestamp = await self.__get_block_timestamp(event=event)
                        await self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=args.get("token", ZERO_ADDRESS),
                            exchange_address=exchange.address,
                            application_id=args.get("escrowId"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            amount=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp,
                        )
                        await self.__register_notification(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"],
                            token_address=args.get("token", ZERO_ADDRESS),
                            exchange_address=exchange.address,
                            application_id=args.get("escrowId"),
                            notice_code=0,
                        )
            except Exception:
                raise

    async def __sync_exchange_cancel_transfer(
        self, db_session: AsyncSession, block_from, block_to
    ):
        """Sync CancelTransfer events of exchanges

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="CancelTransfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    block_timestamp = await self.__get_block_timestamp(event=event)
                    await self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Cancel",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        block_timestamp=block_timestamp,
                    )
                    await self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        notice_code=1,
                    )
            except Exception:
                raise

    async def __sync_exchange_escrow_finished(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync EscrowFinished events of exchanges

        :param db_session: ORM session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="EscrowFinished",
                    block_from=block_from,
                    block_to=block_to,
                    argument_filters={"transferApprovalRequired": True},
                )
                for event in events:
                    args = event["args"]
                    await self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="EscrowFinish",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("sender", ZERO_ADDRESS),
                        to_address=args.get("recipient", ZERO_ADDRESS),
                    )
                    await self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        notice_code=3,
                    )
            except Exception:
                raise

    async def __sync_exchange_approve_transfer(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        """Sync ApproveTransfer events of exchanges

        :param db_session: ORM session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = await AsyncContractUtils.get_event_logs(
                    contract=exchange,
                    event="ApproveTransfer",
                    block_from=block_from,
                    block_to=block_to,
                )
                for event in events:
                    args = event["args"]
                    block_timestamp = await self.__get_block_timestamp(event=event)
                    await self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Approve",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp,
                    )
                    await self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        notice_code=2,
                    )
            except Exception:
                raise

    async def __register_notification(
        self,
        db_session: AsyncSession,
        transaction_hash,
        token_address,
        exchange_address,
        application_id,
        notice_code,
    ):
        # Get IDXTransferApproval's Sequence Id
        transfer_approval: IDXTransferApproval | None = (
            await db_session.scalars(
                select(IDXTransferApproval)
                .where(
                    and_(
                        IDXTransferApproval.token_address == token_address,
                        IDXTransferApproval.exchange_address == exchange_address,
                        IDXTransferApproval.application_id == application_id,
                    )
                )
                .limit(1)
            )
        ).first()
        if transfer_approval is not None:
            # Get issuer address
            token: Token | None = (
                await db_session.scalars(
                    select(Token).where(Token.token_address == token_address).limit(1)
                )
            ).first()
            sender = (await web3.eth.get_transaction(transaction_hash))["from"]
            if token is not None:
                if token.issuer_address != sender:  # Operate from other than issuer
                    if notice_code == 0:  # ApplyForTransfer
                        await self.__sink_on_info_notification(
                            db_session=db_session,
                            issuer_address=token.issuer_address,
                            code=notice_code,
                            token_address=token_address,
                            token_type=token.type,
                            id=transfer_approval.id,
                        )
                    elif (
                        notice_code == 1 or notice_code == 3
                    ):  # CancelTransfer or EscrowFinished
                        await self.__sink_on_info_notification(
                            db_session=db_session,
                            issuer_address=token.issuer_address,
                            code=notice_code,
                            token_address=token_address,
                            token_type=token.type,
                            id=transfer_approval.id,
                        )
                else:  # Operate from issuer
                    if notice_code == 2:  # ApproveTransfer
                        await self.__sink_on_info_notification(
                            db_session=db_session,
                            issuer_address=token.issuer_address,
                            code=notice_code,
                            token_address=token_address,
                            token_type=token.type,
                            id=transfer_approval.id,
                        )

    @staticmethod
    async def __get_block_timestamp(event) -> int:
        block_timestamp = (await web3.eth.get_block(event["blockNumber"]))["timestamp"]
        return block_timestamp

    @staticmethod
    async def __sink_on_transfer_approval(
        db_session: AsyncSession,
        event_type: str,
        token_address: str,
        exchange_address: Optional[str],
        application_id: int,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        amount: Optional[int] = None,
        optional_data_applicant: Optional[str] = None,
        optional_data_approver: Optional[str] = None,
        block_timestamp: Optional[int] = None,
    ):
        """Update Transfer Approval data in DB

        :param db_session: database session
        :param event_type: event type [ApplyFor, Cancel, Approve, Finish]
        :param token_address: token address
        :param exchange_address: exchange address (value is set if the event is from exchange)
        :param application_id: application id
        :param from_address: transfer from
        :param to_address: transfer to
        :param amount: transfer amount
        :param optional_data_applicant: optional data (ApplyForTransfer)
        :param optional_data_approver: optional data (ApproveTransfer)
        :param block_timestamp: block timestamp
        :return: None
        """
        transfer_approval: IDXTransferApproval | None = (
            await db_session.scalars(
                select(IDXTransferApproval)
                .where(
                    and_(
                        IDXTransferApproval.token_address == token_address,
                        IDXTransferApproval.exchange_address == exchange_address,
                        IDXTransferApproval.application_id == application_id,
                    )
                )
                .limit(1)
            )
        ).first()
        if event_type == "ApplyFor":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.exchange_address = exchange_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            transfer_approval.amount = amount
            try:
                transfer_approval.application_datetime = datetime.fromtimestamp(
                    float(optional_data_applicant), tz=UTC
                ).replace(tzinfo=None)
            except ValueError:
                transfer_approval.application_datetime = None
            transfer_approval.application_blocktimestamp = datetime.fromtimestamp(
                block_timestamp, tz=UTC
            ).replace(tzinfo=None)
        elif event_type == "Cancel":
            if transfer_approval is not None:
                transfer_approval.cancellation_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                ).replace(tzinfo=None)
                transfer_approval.cancelled = True
        elif event_type == "EscrowFinish":
            if transfer_approval is not None:
                transfer_approval.escrow_finished = True
        elif event_type == "Approve":
            if transfer_approval is not None:
                try:
                    transfer_approval.approval_datetime = datetime.fromtimestamp(
                        float(optional_data_approver), tz=UTC
                    ).replace(tzinfo=None)
                except ValueError:
                    transfer_approval.approval_datetime = None
                transfer_approval.approval_blocktimestamp = datetime.fromtimestamp(
                    block_timestamp, tz=UTC
                ).replace(tzinfo=None)
                transfer_approval.transfer_approved = True
        await db_session.merge(transfer_approval)

    @staticmethod
    async def __sink_on_info_notification(
        db_session: AsyncSession,
        issuer_address: str,
        code: int,
        token_address: str,
        token_type: str,
        id: int,
    ):
        notification = Notification()
        notification.notice_id = str(uuid.uuid4())
        notification.issuer_address = issuer_address
        notification.priority = 0  # Low
        notification.type = NotificationType.TRANSFER_APPROVAL_INFO
        notification.code = code
        notification.metainfo = {
            "token_address": token_address,
            "token_type": token_type,
            "id": id,
        }
        db_session.add(notification)


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
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
