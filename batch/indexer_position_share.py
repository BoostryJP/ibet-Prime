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
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)

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
import batch_log
from config import (
    DATABASE_URL,
    ZERO_ADDRESS,
    INDEXER_SYNC_INTERVAL
)

process_name = "INDEXER-Position-Share"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, _sink):
        self.sinks.append(_sink)

    def on_position(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_position(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_position(self, token_address: str,
                    account_address: str,
                    balance: Optional[int] = None,
                    exchange_balance: Optional[int] = None,
                    exchange_commitment: Optional[int] = None,
                    pending_transfer: Optional[int] = None):
        """Update balance data

        :param token_address: token address
        :param account_address: account address
        :param balance: balance
        :param exchange_balance: exchange balance
        :param exchange_commitment: exchange commitment
        :param pending_transfer: pending transfer
        :return: None
        """
        position = self.db.query(IDXPosition). \
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

        self.db.merge(position)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []
        self.exchange_address_list = []

    def sync_new_logs(self):
        self.__get_contract_list()

        # Get from_block_number and to_block_number for contract event filter
        idx_position_block_number = self.__get_idx_position_block_number()
        latest_block = web3.eth.blockNumber

        if idx_position_block_number >= latest_block:
            LOG.debug("skip process")
            pass
        else:
            self.__sync_all(idx_position_block_number + 1, latest_block)

    def __get_contract_list(self):
        self.token_list = []
        self.exchange_address_list = []

        issued_token_list = self.db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE). \
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

    def __get_idx_position_block_number(self):
        _idx_position_block_number = self.db.query(IDXPositionShareBlockNumber). \
            first()
        if _idx_position_block_number is None:
            return 0
        else:
            return _idx_position_block_number.latest_block_number

    def __set_idx_position_block_number(self, block_number: int):
        _idx_position_block_number = self.db.query(IDXPositionShareBlockNumber). \
            first()
        if _idx_position_block_number is None:
            _idx_position_block_number = IDXPositionShareBlockNumber()

        _idx_position_block_number.latest_block_number = block_number
        self.db.merge(_idx_position_block_number)

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_issuer()
        self.__sync_issue(block_from, block_to)
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__sync_redeem(block_from, block_to)
        self.__sync_apply_for_transfer(block_from, block_to)
        self.__sync_cancel_transfer(block_from, block_to)
        self.__sync_approve_transfer(block_from, block_to)
        self.__sync_exchange(block_from, block_to)
        self.__sync_escrow(block_from, block_to)
        self.__set_idx_position_block_number(block_to)
        self.sink.flush()

    def __sync_issuer(self):
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
                self.sink.on_position(
                    token_address=to_checksum_address(token.address),
                    account_address=issuer_address,
                    balance=balance,
                    pending_transfer=pending_transfer
                )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, block_from: int, block_to: int):
        """Synchronize Issue events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Issue.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_transfer(self, block_from: int, block_to: int):
        """Synchronize Transfer events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                # Get "Transfer" events from token contract
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )

                # Get exchange contract address
                exchange_contract_address = ContractUtils.call_function(
                    contract=token,
                    function_name="tradableExchange",
                    args=(),
                    default_returns=ZERO_ADDRESS
                )
                for event in events:
                    args = event["args"]
                    for account in [args.get("from", ZERO_ADDRESS), args.get("to", ZERO_ADDRESS)]:
                        if account != exchange_contract_address:
                            balance, pending_transfer, exchange_balance, exchange_commitment = \
                                self.__get_account_balance_all(token, account)
                            self.sink.on_position(
                                token_address=to_checksum_address(token.address),
                                account_address=account,
                                balance=balance,
                                exchange_balance=exchange_balance,
                                exchange_commitment=exchange_commitment,
                                pending_transfer=pending_transfer
                            )
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, block_from: int, block_to: int):
        """Synchronize Lock events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Lock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("accountAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, block_from: int, block_to: int):
        """Synchronize Unlock events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Unlock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("recipientAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, block_from: int, block_to: int):
        """Synchronize Redeem events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.Redeem.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("targetAddress", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_apply_for_transfer(self, block_from: int, block_to: int):
        """Sync ApplyForTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_transfer(self, block_from: int, block_to: int):
        """Sync CancelTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance, pending_transfer = self.__get_account_balance_token(token, account)
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance,
                        pending_transfer=pending_transfer
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_approve_transfer(self, block_from: int, block_to: int):
        """Sync ApproveTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    for account in [args.get("from", ZERO_ADDRESS), args.get("to", ZERO_ADDRESS)]:
                        balance, pending_transfer = self.__get_account_balance_token(token, account)
                        self.sink.on_position(
                            token_address=to_checksum_address(token.address),
                            account_address=account,
                            balance=balance,
                            pending_transfer=pending_transfer
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange(self, block_from: int, block_to: int):
        """Sync Events from IbetExchange

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                exchange = ContractUtils.get_contract("IbetExchange", exchange_address)

                account_list_tmp = []

                # NewOrder event
                _event_list = exchange.events.NewOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # CancelOrder event
                _event_list = exchange.events.CancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # ForceCancelOrder event
                _event_list = exchange.events.ForceCancelOrder.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("accountAddress", ZERO_ADDRESS)
                    })

                # Agree event
                _event_list = exchange.events.Agree.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("tokenAddress", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sellAddress", ZERO_ADDRESS)  # only seller has changed
                    })

                # SettlementOK event
                _event_list = exchange.events.SettlementOK.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
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
                _event_list = exchange.events.SettlementNG.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
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
                    self.sink.on_position(
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_escrow(self, block_from: int, block_to: int):
        """Sync Events from IbetSecurityTokenEscrow

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        for exchange_address in self.exchange_address_list:
            try:
                escrow = ContractUtils.get_contract("IbetSecurityTokenEscrow", exchange_address)

                account_list_tmp = []

                # EscrowCreated event
                _event_list = escrow.events.EscrowCreated.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)  # only sender has changed
                    })

                # EscrowCanceled event
                _event_list = escrow.events.EscrowCanceled.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for _event in _event_list:
                    account_list_tmp.append({
                        "token_address": _event["args"].get("token", ZERO_ADDRESS),
                        "account_address": _event["args"].get("sender", ZERO_ADDRESS)  # only sender has changed
                    })

                # EscrowFinished event
                _event_list = escrow.events.EscrowFinished.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
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
                    self.sink.on_position(
                        token_address=token_address,
                        account_address=account_address,
                        exchange_balance=exchange_balance,
                        exchange_commitment=exchange_commitment
                    )
            except Exception as e:
                LOG.exception(e)

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


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
