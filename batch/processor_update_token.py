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
from asyncio import Event
from datetime import UTC, datetime
from typing import Sequence

import uvloop
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import (
    ContractRevertError,
    SendTransactionError,
    ServiceUnavailableError,
)
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    TokenListContract,
)
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    UTXO,
    Account,
    IDXPosition,
    Notification,
    NotificationType,
    Token,
    TokenType,
    UpdateToken,
)
from app.utils.contract_utils import AsyncContractUtils
from app.utils.e2ee_utils import E2EEUtils
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler
from config import TOKEN_LIST_CONTRACT_ADDRESS, UPDATE_TOKEN_INTERVAL

"""
[PROCESSOR-Update-token]

Processor for asynchronous updating of update items when issuing new tokens
"""

process_name = "PROCESSOR-Update-token"
LOG = batch_log.get_logger(process_name=process_name)


class Processor:
    def __init__(self, is_shutdown: Event):
        self.is_shutdown = is_shutdown

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            _update_token_list = await self.__get_update_token_list(
                db_session=db_session
            )
            for _update_token in _update_token_list:
                if self.is_shutdown.is_set():
                    return

                LOG.info(f"Process start: upload_id={_update_token.token_address}")

                notice_type = ""
                if _update_token.trigger == "Issue":
                    notice_type = NotificationType.ISSUE_ERROR

                # Get issuer's private key
                try:
                    _account: Account | None = (
                        await db_session.scalars(
                            select(Account)
                            .where(
                                Account.issuer_address == _update_token.issuer_address
                            )
                            .limit(1)
                        )
                    ).first()
                    if (
                        _account is None
                    ):  # If issuer does not exist, update the status of the upload to ERROR
                        LOG.warning(
                            f"Issuer of the event_id:{_update_token.id} does not exist"
                        )
                        await self.__sink_on_finish_update_process(
                            db_session=db_session, record_id=_update_token.id, status=2
                        )
                        await self.__sink_on_error_notification(
                            db_session=db_session,
                            issuer_address=_update_token.issuer_address,
                            notice_type=notice_type,
                            code=0,
                            token_address=_update_token.token_address,
                            token_type=_update_token.type,
                            arguments=_update_token.arguments,
                        )
                        await db_session.commit()
                        continue
                    keyfile_json = _account.keyfile
                    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                    private_key = decode_keyfile_json(
                        raw_keyfile_json=keyfile_json,
                        password=decrypt_password.encode("utf-8"),
                    )
                except Exception as err:
                    LOG.exception(
                        f"Could not get the private key of the issuer of id:{_update_token.id}",
                        err,
                    )
                    await self.__sink_on_finish_update_process(
                        db_session=db_session, record_id=_update_token.id, status=2
                    )
                    await self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_update_token.issuer_address,
                        notice_type=notice_type,
                        code=1,
                        token_address=_update_token.token_address,
                        token_type=_update_token.type,
                        arguments=_update_token.arguments,
                    )
                    await db_session.commit()
                    continue

                try:
                    # Token Update
                    token_template = ""
                    if _update_token.type == TokenType.IBET_SHARE.value:
                        _update_data = self.__create_update_data(
                            trigger=_update_token.trigger,
                            token_type=TokenType.IBET_SHARE.value,
                            arguments=_update_token.arguments,
                        )
                        await IbetShareContract(_update_token.token_address).update(
                            data=_update_data,
                            tx_from=_update_token.issuer_address,
                            private_key=private_key,
                        )
                        token_template = TokenType.IBET_SHARE.value

                    elif _update_token.type == TokenType.IBET_STRAIGHT_BOND.value:
                        _update_data = self.__create_update_data(
                            trigger=_update_token.trigger,
                            token_type=TokenType.IBET_STRAIGHT_BOND.value,
                            arguments=_update_token.arguments,
                        )
                        await IbetStraightBondContract(
                            _update_token.token_address
                        ).update(
                            data=_update_data,
                            tx_from=_update_token.issuer_address,
                            private_key=private_key,
                        )
                        token_template = TokenType.IBET_STRAIGHT_BOND.value

                    if _update_token.trigger == "Issue":
                        # Register token_address token list
                        await TokenListContract(TOKEN_LIST_CONTRACT_ADDRESS).register(
                            token_address=_update_token.token_address,
                            token_template=token_template,
                            tx_from=_update_token.issuer_address,
                            private_key=private_key,
                        )

                        # Insert initial position data
                        _position = IDXPosition()
                        _position.token_address = _update_token.token_address
                        _position.account_address = _update_token.issuer_address
                        _position.balance = _update_token.arguments.get("total_supply")
                        _position.exchange_balance = 0
                        _position.exchange_commitment = 0
                        _position.pending_transfer = 0
                        db_session.add(_position)

                        # Insert issuer's UTXO data
                        _token: Token = (
                            await db_session.scalars(
                                select(Token)
                                .where(
                                    Token.token_address == _update_token.token_address
                                )
                                .limit(1)
                            )
                        ).first()
                        block = await AsyncContractUtils.get_block_by_transaction_hash(
                            _token.tx_hash
                        )
                        _utxo = UTXO()
                        _utxo.transaction_hash = _token.tx_hash
                        _utxo.account_address = _update_token.issuer_address
                        _utxo.token_address = _update_token.token_address
                        _utxo.amount = _update_token.arguments.get("total_supply")
                        _utxo.block_number = block["number"]
                        _utxo.block_timestamp = datetime.fromtimestamp(
                            block["timestamp"], UTC
                        ).replace(tzinfo=None)
                        db_session.add(_utxo)

                    await self.__sink_on_finish_update_process(
                        db_session=db_session, record_id=_update_token.id, status=1
                    )
                except ContractRevertError as e:
                    LOG.warning(
                        f"Transaction reverted: id=<{_update_token.id}> error_code:<{e.code}> error_msg:<{e.message}>"
                    )
                    await self.__sink_on_finish_update_process(
                        db_session=db_session, record_id=_update_token.id, status=2
                    )
                    await self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_update_token.issuer_address,
                        notice_type=notice_type,
                        code=2,
                        token_address=_update_token.token_address,
                        token_type=_update_token.type,
                        arguments=_update_token.arguments,
                    )
                except SendTransactionError as tx_err:
                    LOG.warning(f"Failed to send transaction: id=<{_update_token.id}>")
                    LOG.exception(tx_err)
                    await self.__sink_on_finish_update_process(
                        db_session=db_session, record_id=_update_token.id, status=2
                    )
                    await self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_update_token.issuer_address,
                        notice_type=notice_type,
                        code=2,
                        token_address=_update_token.token_address,
                        token_type=_update_token.type,
                        arguments=_update_token.arguments,
                    )

                await db_session.commit()
                LOG.info(f"Process end: upload_id={_update_token.token_address}")
        finally:
            await db_session.close()

    @staticmethod
    async def __get_update_token_list(db_session: AsyncSession):
        _update_token_list: Sequence[UpdateToken] = (
            await db_session.scalars(
                select(UpdateToken)
                .where(UpdateToken.status == 0)
                .order_by(UpdateToken.id)
            )
        ).all()
        return _update_token_list

    @staticmethod
    def __create_update_data(trigger, token_type, arguments: dict):
        if trigger == "Issue":
            # NOTE: Items set at the time of issue do not need to be updated.
            if token_type == TokenType.IBET_SHARE.value:
                return IbetShareUpdateParams(
                    tradable_exchange_contract_address=arguments.get(
                        "tradable_exchange_contract_address"
                    ),
                    personal_info_contract_address=arguments.get(
                        "personal_info_contract_address"
                    ),
                    require_personal_info_registered=arguments.get(
                        "require_personal_info_registered"
                    ),
                    transferable=arguments.get("transferable"),
                    status=arguments.get("status"),
                    is_offering=arguments.get("is_offering"),
                    contact_information=arguments.get("contact_information"),
                    privacy_policy=arguments.get("privacy_policy"),
                    transfer_approval_required=arguments.get(
                        "transfer_approval_required"
                    ),
                    is_canceled=arguments.get("is_canceled"),
                )
            elif token_type == TokenType.IBET_STRAIGHT_BOND.value:
                return IbetStraightBondUpdateParams(
                    face_value_currency=arguments.get("face_value_currency"),
                    redemption_value_currency=arguments.get(
                        "redemption_value_currency"
                    ),
                    interest_rate=arguments.get("interest_rate"),
                    interest_payment_date=arguments.get("interest_payment_date"),
                    interest_payment_currency=arguments.get(
                        "interest_payment_currency"
                    ),
                    base_fx_rate=arguments.get("base_fx_rate"),
                    transferable=arguments.get("transferable"),
                    status=arguments.get("status"),
                    is_offering=arguments.get("is_offering"),
                    is_redeemed=arguments.get("is_redeemed"),
                    tradable_exchange_contract_address=arguments.get(
                        "tradable_exchange_contract_address"
                    ),
                    personal_info_contract_address=arguments.get(
                        "personal_info_contract_address"
                    ),
                    require_personal_info_registered=arguments.get(
                        "require_personal_info_registered"
                    ),
                    contact_information=arguments.get("contact_information"),
                    privacy_policy=arguments.get("privacy_policy"),
                    transfer_approval_required=arguments.get(
                        "transfer_approval_required"
                    ),
                )
        return

    @staticmethod
    async def __sink_on_finish_update_process(
        db_session: AsyncSession, record_id: int, status: int
    ):
        _update_token: UpdateToken | None = (
            await db_session.scalars(
                select(UpdateToken).where(UpdateToken.id == record_id).limit(1)
            )
        ).first()
        if _update_token is not None:
            _update_token.status = status
            await db_session.merge(_update_token)

            if _update_token.trigger == "Issue":
                await db_session.execute(
                    update(Token)
                    .where(Token.token_address == _update_token.token_address)
                    .values(token_status=status)
                )

    @staticmethod
    async def __sink_on_error_notification(
        db_session: AsyncSession,
        issuer_address: str,
        notice_type: str,
        code: int,
        token_address: str,
        token_type: str,
        arguments: dict,
    ):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = notice_type
        notification.code = code
        notification.metainfo = {
            "token_address": token_address,
            "token_type": token_type,
            "arguments": arguments,
        }
        db_session.add(notification)


async def main():
    LOG.info("Service started successfully")

    is_shutdown = asyncio.Event()
    setup_signal_handler(logger=LOG, is_shutdown=is_shutdown)

    processor = Processor(is_shutdown)

    try:
        while not is_shutdown.is_set():
            try:
                await processor.process()
            except ServiceUnavailableError:
                LOG.warning("An external service was unavailable")
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )
            except Exception as ex:
                LOG.error(ex)

            await asyncio.sleep(UPDATE_TOKEN_INTERVAL)
    finally:
        LOG.info("Service is shutdown")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
