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
import os
import sys
import time
from typing import Optional
from itertools import groupby

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.model.blockchain import IbetExchangeInterface
from app.model.db import (
    Token,
    TokenType,
    IDXPosition,
    IDXPositionShareBlockNumber
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import ServiceUnavailableError
import batch_log
from config import (
    DATABASE_URL,
    ZERO_ADDRESS,
    INDEXER_SYNC_INTERVAL
)

process_name = "INDEXER-Position-Share"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def __init__(self):
        self.latest_block = web3.eth.blockNumber
        self.token_list = []
        self.exchange_address_list = []

    def sync_new_logs(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            self.__get_contract_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            idx_position_block_number = self.__get_idx_position_block_number(db_session=db_session)
            latest_block = web3.eth.blockNumber

            if idx_position_block_number >= latest_block:
                LOG.debug("skip process")
                pass
            else:
                self.__sync_all(
                    db_session=db_session,
                    block_from=idx_position_block_number + 1,
                    block_to=latest_block
                )
                self.__set_idx_position_block_number(
                    db_session=db_session,
                    block_number=latest_block
                )
                db_session.commit()
        finally:
            db_session.close()

    def __get_contract_list(self, db_session: Session):
        self.token_list = []
        self.exchange_address_list = []

        issued_token_list = db_session.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE.value). \
            filter(Token.token_status == 1). \
            all()
        _exchange_list_tmp = []
        for issued_token in issued_token_list:
            token_contract = web3.eth.contract(
                address=issued_token.token_address,
                abi=issued_token.abi
            )
            self.token_list.append(token_contract)

            tradable_exchange_address = ContractUtils.call_function(
                contract=token_contract,
                function_name="tradableExchange",
                args=(),
                default_returns=ZERO_ADDRESS
            )
            if tradable_exchange_address != ZERO_ADDRESS:
                _exchange_list_tmp.append(tradable_exchange_address)

        # Remove duplicate exchanges from a list
        self.exchange_address_list = list(set(_exchange_list_tmp))

    def __get_idx_position_block_number(self, db_session: Session):
        _idx_position_block_number = db_session.query(IDXPositionShareBlockNumber). \
            first()
        if _idx_position_block_number is None:
            return 0
        else:
            return _idx_position_block_number.latest_block_number

    def __set_idx_position_block_number(self, db_session: Session, block_number: int):
        _idx_position_block_number = db_session.query(IDXPositionShareBlockNumber). \
            first()
        if _idx_position_block_number is None:
            _idx_position_block_number = IDXPositionShareBlockNumber()

        _idx_position_block_number.latest_block_number = block_number
        db_session.merge(_idx_position_block_number)

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_issuer(db_session)
        self.__sync_issue(db_session, block_from, block_to)
        self.__sync_transfer(db_session, block_from, block_to)
        self.__sync_lock(db_session, block_from, block_to)
        self.__sync_unlock(db_session, block_from, block_to)
        self.__sync_redeem(db_session, block_from, block_to)
        self.__sync_apply_for_transfer(db_session, block_from, block_to)
        self.__sync_cancel_transfer(db_session, block_from, block_to)
        self.__sync_approve_transfer(db_session, block_from, block_to)
        self.__sync_exchange(db_session, block_from, block_to)
        self.__sync_escrow(db_session, block_from, block_to)

    def __sync_issuer(self, db_session: Session):
        """Synchronize issuer position"""
        for token in self.token_list:
            try:
                issuer_address = ContractUtils.call_function(
                    contract=token,
                    function_name="owner",
                    args=(),
                    default_returns=ZERO_ADDRESS
                )
                balance, pending_transfer = self.__get_account_balance_token(token, issuer_address)
                self.__sink_on_position(
                    db_session=db_session,
                    token_address=to_checksum_address(token.address),
                    account_address=issuer_address,
                    balance=balance,
                    pending_transfer=pending_transfer
                )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Issue events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="Issue",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Transfer events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                # Get "Transfer" events from token contract
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="Transfer",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event["args"]
                    for account in [args.get("from", ZERO_ADDRESS), args.get("to", ZERO_ADDRESS)]:
                        if web3.eth.getCode(account).hex() == "0x":
                            balance, pending_transfer, exchange_balance, exchange_commitment = \
                                self.__get_account_balance_all(token, account)
                            self.__sink_on_position(
                                db_session=db_session,
                                token_address=to_checksum_address(token.address),
                                account_address=account,
                                balance=balance,
                                exchange_balance=exchange_balance,
                                exchange_commitment=exchange_commitment,
                                pending_transfer=pending_transfer
                            )
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Lock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="Lock",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("accountAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Unlock events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="Unlock",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("recipientAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Redeem events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="Redeem",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_apply_for_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync ApplyForTransfer Events

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="ApplyForTransfer",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync CancelTransfer Events

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="CancelTransfer",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_approve_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Sync ApproveTransfer Events

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="ApproveTransfer",
                    block_from=block_from,
                    block_to=block_to
                )
                for event in events:
                    args = event["args"]
                    for account in [args.get("from", ZERO_ADDRESS), args.get("to", ZERO_ADDRESS)]:
                        balance, pending_transfer = self.__get_account_balance_token(token, account)
                        self.__sink_on_position(
                            db_session=db_session,
                            token_address=to_checksum_address(token.address),
                            account_address=account,
                            balance=balance,
                            pending_transfer=pending_transfer
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange(self, db_session: Session, block_from: int, block_to: int):
        """Sync Events from IbetExchange

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                exchange = ContractUtils.get_contract("IbetExchange", exchange_address)

                account_list_tmp = []

                # NewOrder event
                _event_list = ContractUtils.get_event_logs(
                    contract=exchange,
                    event="NewOrder",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # CancelOrder event
                _event_list = ContractUtils.get_event_logs(
                    contract=exchange,
                    event="CancelOrder",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # ForceCancelOrder event
                _event_list = ContractUtils.get_event_logs(
                    contract=exchange,
                    event="ForceCancelOrder",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # Agree event
                _event_list = ContractUtils.get_event_logs(
                    contract=exchange,
                    event="Agree",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)  # only seller has changed
                    })

                # SettlementOK event
                _event_list = ContractUtils.get_event_logs(
                    contract=exchange,
                    event="SettlementOK",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("buyAddress", ZERO_ADDRESS)
                    })
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)
                    })

                # SettlementNG event
                _event_list = ContractUtils.get_event_logs(
                    contract=exchange,
                    event="SettlementNG",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)  # only seller has changed
                    })

                # Make temporary list unique
                account_list_tmp.sort(key=lambda x: (x["token_address"], x["account_address"]))
                account_list = []
                for k, g in groupby(account_list_tmp, lambda x: (x["token_address"], x["account_address"])):
                    account_list.append({"token_address": k[0], "account_address": k[1]})

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    account_address = _account["account_address"]
                    exchange_balance, exchange_commitment = self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address
                    )
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_escrow(self, db_session: Session, block_from: int, block_to: int):
        """Sync Events from IbetSecurityTokenEscrow

        :param db_session: database session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                escrow = ContractUtils.get_contract("IbetSecurityTokenEscrow", exchange_address)

                account_list_tmp = []

                # EscrowCreated event
                _event_list = ContractUtils.get_event_logs(
                    contract=escrow,
                    event="EscrowCreated",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)  # only sender has changed
                    })

                # EscrowCanceled event
                _event_list = ContractUtils.get_event_logs(
                    contract=escrow,
                    event="EscrowCanceled",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)  # only sender has changed
                    })

                # EscrowFinished event
                _event_list = ContractUtils.get_event_logs(
                    contract=escrow,
                    event="EscrowFinished",
                    block_from=block_from,
                    block_to=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)
                    })
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("recipient", ZERO_ADDRESS)
                    })

                # Make temporary list unique
                account_list_tmp.sort(key=lambda x: (x["token_address"], x["account_address"]))
                account_list = []
                for k, g in groupby(account_list_tmp, lambda x: (x["token_address"], x["account_address"])):
                    account_list.append({"token_address": k[0], "account_address": k[1]})

                # Update position
                for _account in account_list:
                    token_address = _account["token_address"]
                    account_address = _account["account_address"]
                    exchange_balance, exchange_commitment = self.__get_account_balance_exchange(
                        exchange_address=exchange_address,
                        token_address=token_address,
                        account_address=account_address
                    )
                    self.__sink_on_position(
                        db_session=db_session,
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    @staticmethod
    def __sink_on_position(db_session: Session,
                           token_address: str,
                           account_address: str,
                           balance: Optional[int] = None,
                           exchange_balance: Optional[int] = None,
                           exchange_commitment: Optional[int] = None,
                           pending_transfer: Optional[int] = None):
        """Update balance data

        :param db_session: database session
        :param token_address: token address
        :param account_address: account address
        :param balance: balance
        :param exchange_balance: exchange balance
        :param exchange_commitment: exchange commitment
        :param pending_transfer: pending transfer
        :return: None
        """
        position = db_session.query(IDXPosition). \
            filter(IDXPosition.token_address == token_address). \
            filter(IDXPosition.account_address == account_address). \
            first()
        if position is not None:
            if balance is not None:
                position.balance = balance
            if pending_transfer is not None:
                position.pending_transfer = pending_transfer
            if exchange_balance is not None:
                position.exchange_balance = exchange_balance
            if exchange_commitment is not None:
                position.exchange_commitment = exchange_commitment
            db_session.merge(position)
        elif any(value is not None and value > 0
                 for value in [balance, pending_transfer, exchange_balance, exchange_commitment]):
            LOG.debug(f"Position created (Share): token_address={token_address}, account_address={account_address}")
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance or 0
            position.pending_transfer = pending_transfer or 0
            position.exchange_balance = exchange_balance or 0
            position.exchange_commitment = exchange_commitment or 0
            db_session.add(position)

    @staticmethod
    def __get_account_balance_all(token_contract, account_address: str):
        """Get balance"""

        balance = ContractUtils.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0
        )
        pending_transfer = ContractUtils.call_function(
            contract=token_contract,
            function_name="pendingTransfer",
            args=(account_address,),
            default_returns=0
        )
        exchange_balance = 0
        exchange_commitment = 0
        tradable_exchange_address = ContractUtils.call_function(
            contract=token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS
        )
        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = IbetExchangeInterface(tradable_exchange_address)
            exchange_contract_balance = exchange_contract.get_account_balance(
                account_address=account_address,
                token_address=token_contract.address
            )
            exchange_balance = exchange_contract_balance["balance"]
            exchange_commitment = exchange_contract_balance["commitment"]

        return balance, pending_transfer, exchange_balance, exchange_commitment

    @staticmethod
    def __get_account_balance_token(token_contract, account_address: str):
        """Get balance on token"""

        balance = ContractUtils.call_function(
            contract=token_contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0
        )
        pending_transfer = ContractUtils.call_function(
            contract=token_contract,
            function_name="pendingTransfer",
            args=(account_address,),
            default_returns=0
        )
        return balance, pending_transfer

    @staticmethod
    def __get_account_balance_exchange(exchange_address: str, token_address: str, account_address: str):
        """Get balance on exchange"""

        exchange_contract = IbetExchangeInterface(exchange_address)
        exchange_contract_balance = exchange_contract.get_account_balance(
            account_address=account_address,
            token_address=token_address
        )
        return exchange_contract_balance["balance"], exchange_contract_balance["commitment"]


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
