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
from datetime import datetime
from typing import Sequence

import uvloop
from eth_utils import to_checksum_address
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.model.db import (
    Account,
    IDXPersonalInfo,
    IDXPersonalInfoBlockNumber,
    Token,
    TokenType,
)
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch import batch_log
from config import INDEXER_BLOCK_LOT_MAX_SIZE, INDEXER_SYNC_INTERVAL, ZERO_ADDRESS

process_name = "INDEXER-Personal-Info"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    def __init__(self):
        self.personal_info_contract_list = []

    async def process(self):
        db_session = BatchAsyncSessionLocal()
        try:
            await self.__refresh_personal_info_list(db_session=db_session)
            # most recent blockNumber that has been synchronized with DB
            latest_block = await web3.eth.block_number  # latest blockNumber
            _from_block = await self.__get_block_number(db_session=db_session)
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

            await self.__set_block_number(
                db_session=db_session, block_number=latest_block
            )
            await db_session.commit()
        finally:
            await db_session.close()
        LOG.info("Sync job has been completed")

    async def __refresh_personal_info_list(self, db_session: AsyncSession):
        self.personal_info_contract_list.clear()
        _tokens: Sequence[Token] = (
            await db_session.scalars(
                select(Token)
                .join(
                    Account,
                    and_(
                        Account.issuer_address == Token.issuer_address,
                        Account.is_deleted == False,
                    ),
                )
                .where(Token.token_status == 1)
            )
        ).all()
        tmp_list = []
        for _token in _tokens:
            personal_info_address = ZERO_ADDRESS
            if _token.type == TokenType.IBET_STRAIGHT_BOND.value:
                bond_token = IbetStraightBondContract(_token.token_address)
                await bond_token.get()
                personal_info_address = bond_token.personal_info_contract_address
            elif _token.type == TokenType.IBET_SHARE.value:
                share_token = IbetShareContract(_token.token_address)
                await share_token.get()
                personal_info_address = share_token.personal_info_contract_address

            if personal_info_address != ZERO_ADDRESS:
                tmp_list.append(
                    {
                        "issuer_address": _token.issuer_address,
                        "personal_info_address": personal_info_address,
                    }
                )

        # Remove duplicates from the list
        unique_list = list(map(json.loads, set(map(json.dumps, tmp_list))))
        # Get a list of PersonalInfoContracts
        for item in unique_list:
            issuer_account = (
                await db_session.scalars(
                    select(Account)
                    .where(Account.issuer_address == item["issuer_address"])
                    .limit(1)
                )
            ).first()
            personal_info_contract = PersonalInfoContract(
                issuer=issuer_account,
                contract_address=item["personal_info_address"],
            )
            self.personal_info_contract_list.append(personal_info_contract)

    @staticmethod
    async def __get_block_number(db_session: AsyncSession):
        """Get the most recent blockNumber"""
        block_number: IDXPersonalInfoBlockNumber | None = (
            await db_session.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        if block_number is None:
            return 0
        else:
            return block_number.latest_block_number

    @staticmethod
    async def __set_block_number(db_session: AsyncSession, block_number: int):
        """Setting the most recent blockNumber"""
        _block_number: IDXPersonalInfoBlockNumber | None = (
            await db_session.scalars(select(IDXPersonalInfoBlockNumber).limit(1))
        ).first()
        if _block_number is None:
            _block_number = IDXPersonalInfoBlockNumber()
            _block_number.latest_block_number = block_number
        else:
            _block_number.latest_block_number = block_number
        await db_session.merge(_block_number)

    async def __sync_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info(f"Syncing from={block_from}, to={block_to}")
        await self.__sync_personal_info_register(
            db_session=db_session, block_from=block_from, block_to=block_to
        )
        await self.__sync_personal_info_modify(
            db_session=db_session, block_from=block_from, block_to=block_to
        )

    async def __sync_personal_info_register(
        self, db_session: AsyncSession, block_from, block_to
    ):
        for _personal_info_contract in self.personal_info_contract_list:
            try:
                register_event_list = await _personal_info_contract.get_register_event(
                    block_from, block_to
                )
                for event in register_event_list:
                    args = event["args"]
                    account_address = args.get("account_address", ZERO_ADDRESS)
                    link_address = args.get("link_address", ZERO_ADDRESS)
                    if link_address == _personal_info_contract.issuer.issuer_address:
                        block = await web3.eth.get_block(event["blockNumber"])
                        timestamp = datetime.utcfromtimestamp(block["timestamp"])
                        decrypted_personal_info = (
                            await _personal_info_contract.get_info(
                                account_address=account_address, default_value=None
                            )
                        )
                        await self.__sink_on_personal_info(
                            db_session=db_session,
                            account_address=account_address,
                            issuer_address=link_address,
                            personal_info=decrypted_personal_info,
                            timestamp=timestamp,
                        )
                        await db_session.commit()
            except Exception:
                LOG.exception("An exception occurred during event synchronization")

    async def __sync_personal_info_modify(
        self, db_session: AsyncSession, block_from, block_to
    ):
        for _personal_info_contract in self.personal_info_contract_list:
            try:
                register_event_list = await _personal_info_contract.get_modify_event(
                    block_from, block_to
                )
                for event in register_event_list:
                    args = event["args"]
                    account_address = args.get("account_address", ZERO_ADDRESS)
                    link_address = args.get("link_address", ZERO_ADDRESS)
                    if link_address == _personal_info_contract.issuer.issuer_address:
                        block = await web3.eth.get_block(event["blockNumber"])
                        timestamp = datetime.utcfromtimestamp(block["timestamp"])
                        decrypted_personal_info = (
                            await _personal_info_contract.get_info(
                                account_address=account_address, default_value=None
                            )
                        )
                        await self.__sink_on_personal_info(
                            db_session=db_session,
                            account_address=account_address,
                            issuer_address=link_address,
                            personal_info=decrypted_personal_info,
                            timestamp=timestamp,
                        )
                        await db_session.commit()
            except Exception:
                LOG.exception("An exception occurred during event synchronization")

    @staticmethod
    async def __sink_on_personal_info(
        db_session: AsyncSession,
        account_address: str,
        issuer_address: str,
        personal_info: dict,
        timestamp: datetime,
    ):
        _personal_info: IDXPersonalInfo | None = (
            await db_session.scalars(
                select(IDXPersonalInfo)
                .where(
                    and_(
                        IDXPersonalInfo.account_address
                        == to_checksum_address(account_address),
                        IDXPersonalInfo.issuer_address
                        == to_checksum_address(issuer_address),
                    )
                )
                .limit(1)
            )
        ).first()
        if _personal_info is not None:
            _personal_info.personal_info = personal_info
            _personal_info.modified = timestamp
            await db_session.merge(_personal_info)
            LOG.debug(
                f"Modify: account_address={account_address}, issuer_address={issuer_address}"
            )
        else:
            _personal_info = IDXPersonalInfo()
            _personal_info.account_address = account_address
            _personal_info.issuer_address = issuer_address
            _personal_info.personal_info = personal_info
            _personal_info.created = timestamp
            _personal_info.modified = timestamp
            db_session.add(_personal_info)
            LOG.debug(
                f"Register: account_address={account_address}, issuer_address={issuer_address}"
            )


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
