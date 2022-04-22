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
from typing import Optional, Dict, List

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from web3.contract import Contract
import config
from app.model.db import TokenHolder, TokenHoldersList, TokenHolderBatchStatus

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.model.db import TokenType
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import ServiceUnavailableError
import batch_log
from config import DATABASE_URL, ZERO_ADDRESS, INDEXER_SYNC_INTERVAL

process_name = "INDEXER-Position-Bond"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for collecting Token Holders at given block number and token."""

    class BalanceBook:
        pages: Dict[str, TokenHolder]

        def __init__(self):
            self.pages = {}

        def store(
            self,
            account_address: str,
            balance: int = 0,
            pending_transfer: int = 0,
            exchange_balance: int = 0,
            exchange_commitment: int = 0,
        ):
            if account_address not in self.pages:
                token_holder = TokenHolder()
                token_holder.balance = balance
                token_holder.pending_transfer = pending_transfer
                token_holder.exchange_balance = exchange_balance
                token_holder.exchange_commitment = exchange_commitment
                token_holder.account_address = account_address
                self.pages[account_address] = token_holder
            else:
                self.pages[account_address].balance += balance
                self.pages[account_address].pending_transfer += pending_transfer
                self.pages[account_address].exchange_balance += exchange_balance
                self.pages[account_address].exchange_commitment += exchange_commitment

    target: Optional[TokenHoldersList]
    balance_book: BalanceBook

    tradable_exchange_address: str
    token_owner_address: str

    block_from: int
    block_to: int
    checkpoint_used: bool

    token_contract: Optional[Contract]
    exchange_contract: Optional[Contract]
    escrow_contract: Optional[Contract]

    def __init__(self):
        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""
        self.checkpoint_used = False

    @staticmethod
    def __get_db_session() -> Session:
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def __load_target(self, db_session: Session) -> bool:
        self.target: TokenHoldersList = (
            db_session.query(TokenHoldersList)
            .filter(
                TokenHoldersList.batch_status == TokenHolderBatchStatus.PENDING.value
            )
            .first()
        )
        return True if self.target else False

    def __load_token_info(self) -> bool:
        # Fetch token list information from TokenList Contract
        list_contract = ContractUtils.get_contract(
            contract_name="TokenList",
            contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
        )
        token_info: List[str, 3] = ContractUtils.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(self.target.token_address,),
            default_returns=(ZERO_ADDRESS, "", ZERO_ADDRESS),
        )
        self.token_owner_address = token_info[2]
        # Store token contract.
        if token_info[1] == TokenType.IBET_STRAIGHT_BOND.value:
            self.token_contract = ContractUtils.get_contract(
                "IbetStraightBond", self.target.token_address
            )
        elif token_info[1] == TokenType.IBET_SHARE.value:
            self.token_contract = ContractUtils.get_contract(
                "IbetShare", self.target.token_address
            )
        else:
            return False

        # Fetch current tradable exchange to store exchange contract.
        self.tradable_exchange_address = ContractUtils.call_function(
            contract=self.token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS,
        )
        self.exchange_contract = ContractUtils.get_contract(
            contract_name="IbetExchange",
            contract_address=self.tradable_exchange_address,
        )

        # Store escrow contract.
        # if token_info[1] in ["IbetStraightBond", "IbetShare"]:
        #     self.escrow_contract = ContractUtils.get_contract(
        #         "IbetSecurityTokenEscrow", self.tradable_exchange_address
        #     )
        # else:
        self.escrow_contract = ContractUtils.get_contract(
            "IbetSecurityTokenEscrow", self.tradable_exchange_address
        )
        return True

    def __load_checkpoint(self, local_session: Session) -> bool:
        _checkpoint: Optional[TokenHoldersList] = (
            local_session.query(TokenHoldersList)
            .filter(TokenHoldersList.token_address == self.target.token_address)
            .filter(TokenHoldersList.block_number < self.target.block_number)
            .filter(TokenHoldersList.batch_status == TokenHolderBatchStatus.DONE.value)
            .order_by(TokenHoldersList.block_number.desc())
            .first()
        )
        if _checkpoint:
            _holders: List[TokenHolder] = (
                local_session.query(TokenHolder)
                .filter(TokenHolder.holder_list_id == _checkpoint.id)
                .all()
            )
            for holder in _holders:
                self.balance_book.store(
                    account_address=holder.account_address,
                    balance=holder.balance,
                    pending_transfer=holder.pending_transfer,
                    exchange_balance=holder.exchange_balance,
                    exchange_commitment=holder.exchange_commitment,
                )
            self.block_from = _checkpoint.block_number + 1
            self.checkpoint_used = True
        return True

    def collect(self):
        local_session = self.__get_db_session()
        try:
            if not self.__load_target(local_session):
                LOG.debug(f"There are no pending collect batch")
                return
            if not self.__load_token_info():
                LOG.debug(f"Token contract must be listed to TokenList contract.")
                self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
                local_session.commit()
                return
            self.block_from = 0
            self.block_to = self.target.block_number
            self.__load_checkpoint(local_session)
            self.__sync_all(local_session, self.block_from, self.block_to)
            self.__update_status(local_session, TokenHolderBatchStatus.DONE)
            local_session.commit()
        except Exception as e:
            local_session.rollback()
            self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
            local_session.commit()
        finally:
            local_session.close()
            LOG.info(f"<{process_name}> Collect job has been completed")

    def __update_status(self, local_session: Session, status: TokenHolderBatchStatus):
        self.target.batch_status = status.value
        local_session.merge(self.target)
        LOG.info(
            f"Token holder list({self.target.list_id}) status changes to be {status.value}."
        )

        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""
        self.token_owner_address = ""
        self.block_from = 0
        self.checkpoint_used = False
        self.token_contract = None
        self.exchange_contract = None
        self.escrow_contract = None

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))

        self.__sync_transfer(block_from, block_to)
        self.__sync_exchange(block_from, block_to)
        self.__sync_escrow(block_from, block_to)
        self.__sync_issue(block_from, block_to)
        self.__sync_redeem(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__sync_apply_for_transfer(block_from, block_to)
        self.__sync_cancel_transfer(block_from, block_to)
        self.__sync_approve_transfer(block_from, block_to)

        self.__save_holders(
            db_session,
            self.balance_book,
            self.target.id,
            self.target.token_address,
            self.token_owner_address,
        )

    def __sync_transfer(self, block_from: int, block_to: int):
        """Sync Transfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            token = self.token_contract
            events = token.events.Transfer.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for event in events:
                args = event["args"]
                _from = args.get("from", ZERO_ADDRESS)
                _to = args.get("to", ZERO_ADDRESS)
                _value = args.get("value", 0)

                _from_exchange = _from == self.tradable_exchange_address
                _to_exchange = _to == self.tradable_exchange_address
                if _from_exchange and not _to_exchange:
                    # exchange_address -> token_address => withdraw from exchange
                    self.balance_book.store(
                        account_address=_to, balance=+_value, exchange_balance=-_value
                    )
                elif not _from_exchange and _to_exchange:
                    # token_address -> exchange_address => deposit to exchange
                    self.balance_book.store(
                        account_address=_from, balance=-_value, exchange_balance=+_value
                    )
                else:
                    # token_address -> token_address => transfer
                    self.balance_book.store(
                        account_address=_from,
                        balance=-_value,
                    )
                    self.balance_book.store(
                        account_address=_to,
                        balance=+_value,
                    )
        except Exception as e:
            LOG.exception(e)

    def __sync_lock(self, block_from: int, block_to: int):
        """Sync Lock Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """

        try:
            token = self.token_contract
            events = token.events.Lock.getLogs(fromBlock=block_from, toBlock=block_to)
            for event in events:
                # event Lock(
                #     address indexed accountAddress,
                #     address indexed lockAddress,
                #     uint256 value
                # );
                # accountAddress
                #   tokenBalance.sub(value)
                #   lockedTokenBalance.add(value)
                args = event["args"]
                _account_address = args.get("accountAddress", ZERO_ADDRESS)
                _lock_address = args.get("lockAddress", ZERO_ADDRESS)
                _value = args.get("value", 0)
                self.balance_book.store(
                    account_address=_account_address,
                    balance=-_value,
                )
        except Exception as e:
            LOG.exception(e)

    def __sync_unlock(self, block_from: int, block_to: int):
        """Sync Unlock Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """

        try:
            token = self.token_contract
            events = token.events.Unlock.getLogs(fromBlock=block_from, toBlock=block_to)
            for event in events:
                args = event["args"]
                _account_address = args.get("accountAddress", ZERO_ADDRESS)
                _lock_address = args.get("lockAddress", ZERO_ADDRESS)
                _recipient_address = args.get("recipientAddress", ZERO_ADDRESS)
                _value = args.get("value", 0)
                self.balance_book.store(
                    account_address=_recipient_address,
                    balance=+_value,
                )
        except Exception as e:
            LOG.exception(e)

    def __sync_issue(self, block_from: int, block_to: int):
        """Sync Issue Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            token = self.token_contract
            events = token.events.Issue.getLogs(fromBlock=block_from, toBlock=block_to)
            for event in events:
                args = event["args"]
                _from = args.get("from", ZERO_ADDRESS)
                _target_address = args.get("targetAddress", ZERO_ADDRESS)
                _lock_address = args.get("lockAddress", ZERO_ADDRESS)
                _amount = args.get("amount", 0)
                if _target_address == self.token_owner_address:
                    pass
                elif _lock_address == ZERO_ADDRESS:
                    self.balance_book.store(
                        account_address=_target_address,
                        balance=+_amount,
                    )
        except Exception as e:
            LOG.exception(e)

    def __sync_redeem(self, block_from: int, block_to: int):
        """Sync Redeem Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            token = self.token_contract
            events = token.events.Redeem.getLogs(fromBlock=block_from, toBlock=block_to)

            for event in events:
                args = event["args"]
                _from = args.get("from", ZERO_ADDRESS)
                _target_address = args.get("targetAddress", ZERO_ADDRESS)
                _lock_address = args.get("lockAddress", ZERO_ADDRESS)
                _amount = args.get("amount", 0)
                if _target_address == self.token_owner_address:
                    pass
                elif _lock_address == ZERO_ADDRESS:
                    self.balance_book.store(
                        account_address=_target_address,
                        balance=-_amount,
                    )
        except Exception as e:
            LOG.exception(e)

    def __sync_apply_for_transfer(self, block_from: int, block_to: int):
        """Sync ApplyForTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            token = self.token_contract
            events = token.events.ApplyForTransfer.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for event in events:
                args = event["args"]
                _from = args.get("from", ZERO_ADDRESS)
                _to = args.get("to", ZERO_ADDRESS)
                _value = int(args.get("value", 0))
                self.balance_book.store(
                    account_address=_from, balance=-_value, pending_transfer=+_value
                )
        except Exception as e:
            LOG.exception(e)

    def __sync_cancel_transfer(self, block_from: int, block_to: int):
        """Sync CancelTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            token = self.token_contract
            events = token.events.CancelTransfer.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for event in events:
                args = event["args"]
                _index = args.get("index", ZERO_ADDRESS)
                _from = args.get("from", ZERO_ADDRESS)
                _to = args.get("to", ZERO_ADDRESS)
                _, _, _value, _ = ContractUtils.call_function(
                    contract=token,
                    function_name="applicationsForTransfer",
                    args=(_index,),
                )
                self.balance_book.store(
                    account_address=_from, balance=+_value, pending_transfer=-_value
                )
        except Exception as e:
            LOG.exception(e)

    def __sync_approve_transfer(self, block_from: int, block_to: int):
        """Sync ApproveTransfer Events

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            token = self.token_contract
            events = token.events.ApproveTransfer.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for event in events:
                args = event["args"]
                _from = args.get("from", ZERO_ADDRESS)
                _to = args.get("to", ZERO_ADDRESS)
                _index = args.get("index", 0)
                _, _, _value, _ = ContractUtils.call_function(
                    contract=token,
                    function_name="applicationsForTransfer",
                    args=(_index,),
                )
                self.balance_book.store(
                    account_address=_from, balance=+_value, pending_transfer=-_value
                )
        except Exception as e:
            LOG.exception(e)

    def __sync_exchange(self, block_from: int, block_to: int):
        """Sync Events from IbetExchange

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        exchange_address = self.tradable_exchange_address
        try:
            token = self.token_contract
            exchange = ContractUtils.get_contract(
                contract_name="IbetExchange", contract_address=exchange_address
            )
            # NewOrder event
            _event_list = exchange.events.NewOrder.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("tokenAddress", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    _account_address = args.get("accountAddress", ZERO_ADDRESS)
                    _is_buy = args.get("isBuy", False)
                    _amount = args.get("amount", 0)
                    if not _is_buy:
                        # If order is made by sell side, seller assets must be committed.
                        self.balance_book.store(
                            account_address=_account_address,
                            exchange_balance=-_amount,
                            exchange_commitment=+_amount,
                        )

            # CancelOrder event
            _event_list = exchange.events.CancelOrder.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("tokenAddress", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    _account_address = args.get("accountAddress", ZERO_ADDRESS)
                    _is_buy = args.get("isBuy", False)
                    _amount = args.get("amount", 0)
                    if not _is_buy:
                        # If order made by sell side is cancelled, seller commitment must be released.
                        self.balance_book.store(
                            account_address=_account_address,
                            exchange_balance=+_amount,
                            exchange_commitment=-_amount,
                        )
            # ForceCancelOrder event
            _event_list = exchange.events.ForceCancelOrder.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("tokenAddress", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    _account_address = args.get("accountAddress", ZERO_ADDRESS)
                    _is_buy = args.get("isBuy", False)
                    _amount = args.get("amount", 0)
                    if not _is_buy:
                        # If order made by sell side is cancelled, seller commitment must be released.
                        self.balance_book.store(
                            account_address=_account_address,
                            exchange_balance=+_amount,
                            exchange_commitment=-_amount,
                        )
            # Agree event
            _event_list = exchange.events.Agree.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("tokenAddress", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    _sell_address = args.get("sellAddress", ZERO_ADDRESS)
                    _amount = args.get("amount", 0)
                    _order_id = args.get("orderId", 0)
                    _, _, _, _, _order_is_buy, _, _ = ContractUtils.call_function(
                        contract=exchange, function_name="getOrder", args=(_order_id,)
                    )
                    if _order_is_buy:
                        # If order is taken by sell side, seller assets must be committed.
                        self.balance_book.store(
                            account_address=_sell_address,
                            exchange_balance=-_amount,
                            exchange_commitment=+_amount,
                        )
            # SettlementOK event
            _event_list = exchange.events.SettlementOK.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("tokenAddress", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    # If settlementOK is emitted, seller commitment must be subtracted.
                    _buy_address = args.get("buyAddress", ZERO_ADDRESS)
                    _sell_address = args.get("sellAddress", ZERO_ADDRESS)
                    _amount = args.get("amount", 0)
                    self.balance_book.store(
                        account_address=_sell_address,
                        exchange_commitment=-_amount,
                    )
                    self.balance_book.store(
                        account_address=_buy_address,
                        exchange_balance=+_amount,
                    )
            # SettlementNG event
            _event_list = exchange.events.SettlementNG.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("tokenAddress", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    _order_id = args.get("orderId", ZERO_ADDRESS)
                    (
                        _maker_address,
                        _token_address,
                        _,
                        _,
                        _order_is_buy,
                        _,
                        _,
                    ) = ContractUtils.call_function(
                        contract=exchange, function_name="getOrder", args=(_order_id,)
                    )
                    if _order_is_buy:
                        # If settlementNG is emitted, seller commitment must be released.
                        _sell_address = args.get("sellAddress", ZERO_ADDRESS)
                        _buy_address = args.get("buyAddress", ZERO_ADDRESS)
                        _amount = args.get("amount", 0)
                        self.balance_book.store(
                            account_address=_sell_address,
                            exchange_balance=+_amount,
                            exchange_commitment=-_amount,
                        )
        except Exception as e:
            LOG.exception(e)

    def __sync_escrow(self, block_from: int, block_to: int):
        """Sync Events from IbetSecurityTokenEscrow/IbetEscrow

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        escrow_contract = self.escrow_contract
        try:
            # EscrowCreated event
            _event_list = escrow_contract.events.EscrowCreated.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("token", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    # If EscrowCreated is emitted, sender seller assets must be committed.
                    _account_address = args.get("sender", ZERO_ADDRESS)
                    _amount = args.get("amount", 0)
                    self.balance_book.store(
                        account_address=_account_address,
                        exchange_balance=-_amount,
                        exchange_commitment=+_amount,
                    )
            # EscrowCanceled event
            _event_list = escrow_contract.events.EscrowCanceled.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("token", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    # If EscrowCanceled is emitted, sender commitment must be released.
                    _account_address = args.get("sender", ZERO_ADDRESS)
                    _amount = args.get("amount", 0)
                    self.balance_book.store(
                        account_address=_account_address,
                        exchange_balance=+_amount,
                        exchange_commitment=-_amount,
                    )
            # EscrowFinished event
            _event_list = escrow_contract.events.EscrowFinished.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("token", ZERO_ADDRESS)
                if _token_address == self.target.token_address:
                    _transfer_approval_required = args.get(
                        "transferApprovalRequired", False
                    )
                    if not _transfer_approval_required:
                        # If the finished escrow need no approval, sender commitment must be transferred to recipient.
                        _sender = args.get("sender", ZERO_ADDRESS)
                        _recipient = args.get("recipient", ZERO_ADDRESS)
                        _amount = args.get("amount", 0)
                        self.balance_book.store(
                            account_address=_recipient,
                            exchange_balance=+_amount,
                        )
                        self.balance_book.store(
                            account_address=_sender, exchange_commitment=-_amount
                        )
            # ApproveTransfer event
            _event_list = escrow_contract.events.ApproveTransfer.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
            for _event in _event_list:
                args = _event["args"]
                _token_address = args.get("token", ZERO_ADDRESS)
                _escrow_id = args.get("escrowId", ZERO_ADDRESS)
                _, _sender, _recipient, _amount, _, _ = ContractUtils.call_function(
                    contract=escrow_contract,
                    function_name="getEscrow",
                    args=(_escrow_id,),
                )
                if _token_address == self.target.token_address:
                    # If ApproveTransfer is emitted, sender commitment must be transferred to recipient.
                    self.balance_book.store(
                        account_address=_recipient,
                        exchange_balance=+_amount,
                    )
                    self.balance_book.store(
                        account_address=_sender, exchange_commitment=-_amount
                    )
        except Exception as e:
            LOG.exception(e)

    @staticmethod
    def __save_holders(
        db_session: Session,
        balance_book: BalanceBook,
        holder_list_id: int,
        token_address: str,
        token_owner_address: str,
    ):
        for account_address, page in zip(
            balance_book.pages.keys(), balance_book.pages.values()
        ):
            if page.account_address == token_owner_address:
                continue
            token_holder: TokenHolder = (
                db_session.query(TokenHolder)
                .filter(TokenHolder.holder_list_id == holder_list_id)
                .filter(TokenHolder.account_address == account_address)
                .first()
            )
            if token_holder is not None:
                if page.balance is not None:
                    token_holder.balance += page.balance
                if page.pending_transfer is not None:
                    token_holder.pending_transfer += page.pending_transfer
                if page.exchange_balance is not None:
                    token_holder.exchange_balance += page.exchange_balance
                if page.exchange_commitment is not None:
                    token_holder.exchange_commitment += page.exchange_commitment
                db_session.merge(token_holder)
            elif any(
                value is not None and value > 0
                for value in [
                    page.balance,
                    page.pending_transfer,
                    page.exchange_balance,
                    page.exchange_commitment,
                ]
            ):
                LOG.debug(
                    f"Collection record created : token_address={token_address}, account_address={account_address}"
                )
                page.holder_list_id = holder_list_id
                db_session.add(page)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.collect()
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
