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

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import randint
from typing import List, TypeVar

from sqlalchemy import delete, desc, select
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError
from web3.datastructures import AttributeDict
from web3.exceptions import TimeExhausted

from app import log
from app.database import async_engine
from app.exceptions import (
    ContractRevertError,
    SendTransactionError,
    ServiceUnavailableError,
)
from app.model import EthereumAddress
from app.model.db import TokenAttrUpdate, TokenCache
from app.model.ibet import IbetExchangeInterface
from app.model.ibet.tx_params.ibet_security_token import (
    AdditionalIssueParams as IbetSecurityTokenAdditionalIssueParams,
    ApproveTransferParams as IbetSecurityTokenApproveTransfer,
    BulkTransferParams as IbetSecurityTokenBulkTransferParams,
    CancelTransferParams as IbetSecurityTokenCancelTransfer,
    ForceChangeLockedAccountParams as IbetSecurityTokenForceChangeLockedAccountParams,
    ForcedTransferParams as IbetSecurityTokenForcedTransferParams,
    ForceLockParams as IbetSecurityTokenForceLockParams,
    ForceUnlockParams as IbetSecurityTokenForceUnlockParams,
    LockParams as IbetSecurityTokenLockParams,
    RedeemParams as IbetSecurityTokenRedeemParams,
)
from app.model.ibet.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.ibet.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.ibet_contract_utils import AsyncContractUtils
from app.utils.ibet_web3_utils import Web3Wrapper
from config import (
    CHAIN_ID,
    DEFAULT_CURRENCY,
    TOKEN_CACHE,
    TOKEN_CACHE_TTL,
    TOKEN_CACHE_TTL_JITTER,
    TX_GAS_LIMIT,
    ZERO_ADDRESS,
)

LOG = log.get_logger()

web3 = Web3Wrapper()


class IbetStandardTokenInterface:
    issuer_address: str
    token_address: str
    name: str
    symbol: str
    total_supply: int
    contact_information: str
    privacy_policy: str
    tradable_exchange_contract_address: str
    status: bool

    def __init__(
        self,
        contract_address: str = ZERO_ADDRESS,
        contract_name: str = "IbetStandardTokenInterface",
    ):
        self.contract_name = contract_name
        self.token_address = contract_address

    async def check_attr_update(
        self, db_session: AsyncSession, base_datetime: datetime
    ):
        is_updated = False
        _token_attr_update = (
            await db_session.scalars(
                select(TokenAttrUpdate)
                .where(TokenAttrUpdate.token_address == self.token_address)
                .order_by(desc(TokenAttrUpdate.id))
                .limit(1)
            )
        ).first()
        if (
            _token_attr_update is not None
            and _token_attr_update.updated_datetime > base_datetime
        ):
            is_updated = True
        return is_updated

    async def record_attr_update(self, db_session: AsyncSession):
        _token_attr_update = TokenAttrUpdate()
        _token_attr_update.token_address = self.token_address
        _token_attr_update.updated_datetime = datetime.now(UTC).replace(tzinfo=None)
        db_session.add(_token_attr_update)

    async def create_cache(self, db_session: AsyncSession):
        token_cache = TokenCache()
        token_cache.token_address = self.token_address
        token_cache.attributes = self.__dict__
        token_cache.cached_datetime = datetime.now(UTC).replace(tzinfo=None)
        token_cache.expiration_datetime = datetime.now(UTC).replace(
            tzinfo=None
        ) + timedelta(
            seconds=randint(
                TOKEN_CACHE_TTL - TOKEN_CACHE_TTL_JITTER,
                TOKEN_CACHE_TTL + TOKEN_CACHE_TTL_JITTER,
            )
        )
        await db_session.merge(token_cache)

    async def delete_cache(self, db_session: AsyncSession):
        await db_session.execute(
            delete(TokenCache).where(TokenCache.token_address == self.token_address)
        )

    async def get_account_balance(self, account_address: str):
        """Get account balance"""
        contract = AsyncContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )
        balance = await AsyncContractUtils.call_function(
            contract=contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0,
        )
        tradable_exchange_address = await AsyncContractUtils.call_function(
            contract=contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS,
        )
        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = IbetExchangeInterface(tradable_exchange_address)
            exchange_balance = await exchange_contract.get_account_balance(
                account_address=account_address, token_address=self.token_address
            )
            balance = (
                balance + exchange_balance["balance"] + exchange_balance["commitment"]
            )

        return balance


class IbetSecurityTokenInterface(IbetStandardTokenInterface):
    personal_info_contract_address: str
    require_personal_info_registered: bool
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool

    def __init__(
        self,
        contract_address: str = ZERO_ADDRESS,
        contract_name: str = "IbetSecurityTokenInterface",
    ):
        super().__init__(contract_address, contract_name)

    async def forced_transfer(
        self,
        tx_params: IbetSecurityTokenForcedTransferParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Transfer ownership

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            _from = tx_params.from_address
            _to = tx_params.to_address
            _amount = tx_params.amount
            tx = await contract.functions.transferFrom(
                _from, _to, _amount
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        return tx_hash

    async def bulk_forced_transfer(
        self,
        tx_params: list[IbetSecurityTokenForcedTransferParams],
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Bulk transfer ownership

        :param tx_params: List of transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        from_list = []
        to_list = []
        amounts = []

        for _d in tx_params:
            from_list.append(_d.from_address)
            to_list.append(_d.to_address)
            amounts.append(_d.amount)

        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.bulkTransferFrom(
                from_list, to_list, amounts
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        return tx_hash

    async def bulk_transfer(
        self,
        tx_params: IbetSecurityTokenBulkTransferParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Transfer ownership

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.bulkTransfer(
                tx_params.to_address_list, tx_params.amount_list
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        return tx_hash

    async def additional_issue(
        self,
        tx_params: IbetSecurityTokenAdditionalIssueParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Additional issue

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            _target_address = tx_params.account_address
            _amount = tx_params.amount
            tx = await contract.functions.issueFrom(
                _target_address, ZERO_ADDRESS, _amount
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        # Delete Cache
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            await self.record_attr_update(db_session)
            await self.delete_cache(db_session)
            await db_session.commit()
        except Exception:
            LOG.exception("Failed to update database")
            pass
        finally:
            await db_session.close()

        return tx_hash

    async def bulk_additional_issue(
        self,
        tx_params: list[IbetSecurityTokenAdditionalIssueParams],
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Bulk additional issue

        :param tx_params: List of transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        target_address_list = []
        lock_address_list = []
        amounts = []

        for _d in tx_params:
            target_address_list.append(_d.account_address)
            lock_address_list.append(ZERO_ADDRESS)
            amounts.append(_d.amount)

        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.bulkIssueFrom(
                target_address_list, lock_address_list, amounts
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        # Delete Cache
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            await self.record_attr_update(db_session)
            await self.delete_cache(db_session)
            await db_session.commit()
        except Exception:
            LOG.exception("Failed to update database")
            pass
        finally:
            await db_session.close()

        return tx_hash

    async def redeem(
        self,
        tx_params: IbetSecurityTokenRedeemParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Redeem a token

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            _target_address = tx_params.account_address
            _amount = tx_params.amount
            tx = await contract.functions.redeemFrom(
                _target_address, ZERO_ADDRESS, _amount
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        # Delete Cache
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            await self.record_attr_update(db_session)
            await self.delete_cache(db_session)
            await db_session.commit()
        except Exception:
            LOG.exception("Failed to update database")
            pass
        finally:
            await db_session.close()

        return tx_hash

    async def bulk_redeem(
        self,
        tx_params: list[IbetSecurityTokenRedeemParams],
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Redeem a token

        :param tx_params: List of transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        target_address_list = []
        lock_address_list = []
        amounts = []

        for _d in tx_params:
            target_address_list.append(_d.account_address)
            lock_address_list.append(ZERO_ADDRESS)
            amounts.append(_d.amount)

        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.bulkRedeemFrom(
                target_address_list, lock_address_list, amounts
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        # Delete Cache
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            await self.record_attr_update(db_session)
            await self.delete_cache(db_session)
            await db_session.commit()
        except Exception:
            LOG.exception("Failed to update database")
            pass
        finally:
            await db_session.close()

        return tx_hash

    async def approve_transfer(
        self,
        tx_params: IbetSecurityTokenApproveTransfer,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Approve Transfer

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.approveTransfer(
                tx_params.application_id, tx_params.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def cancel_transfer(
        self,
        tx_params: IbetSecurityTokenCancelTransfer,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Cancel Transfer

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.cancelTransfer(
                tx_params.application_id, tx_params.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def lock(
        self,
        tx_params: IbetSecurityTokenLockParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Lock

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.lock(
                tx_params.lock_address, tx_params.value, tx_params.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def force_lock(
        self,
        tx_params: IbetSecurityTokenForceLockParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Force Lock

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.forceLock(
                tx_params.lock_address,
                tx_params.account_address,
                tx_params.value,
                tx_params.data,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def force_unlock(
        self,
        tx_params: IbetSecurityTokenForceUnlockParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Force Unlock

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.forceUnlock(
                tx_params.lock_address,
                tx_params.account_address,
                tx_params.recipient_address,
                tx_params.value,
                tx_params.data,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    async def force_change_locked_account(
        self,
        tx_params: IbetSecurityTokenForceChangeLockedAccountParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Force Change Locked Account

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        try:
            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = await contract.functions.forceChangeLockedAccount(
                tx_params.lock_address,
                tx_params.before_account_address,
                tx_params.after_account_address,
                tx_params.value,
                tx_params.data,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=tx_sender_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)


class IbetStraightBondContract(IbetSecurityTokenInterface):
    """IbetStraightBond contract"""

    face_value: int
    face_value_currency: str
    interest_rate: float
    interest_payment_date: List[str]
    interest_payment_currency: str
    redemption_date: str
    redemption_value: int
    redemption_value_currency: str
    base_fx_rate: float
    return_date: str
    return_amount: str
    purpose: str
    memo: str
    is_redeemed: bool

    def __init__(self, contract_address: str = ZERO_ADDRESS):
        super().__init__(contract_address, "IbetStraightBond")

    async def create(
        self, args: list, tx_sender: EthereumAddress, tx_sender_key: bytes
    ):
        """
        Deploy token

        :param args: deploy arguments
        :param tx_sender: contract deployer
        :param tx_sender_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        if self.token_address == ZERO_ADDRESS:
            contract_address, abi, tx_hash = await AsyncContractUtils.deploy_contract(
                contract_name="IbetStraightBond",
                args=args,
                deployer=tx_sender,
                private_key=tx_sender_key,
            )
            self.contract_name = "IbetStraightBond"
            self.token_address = contract_address
            return contract_address, abi, tx_hash
        else:
            raise SendTransactionError("contract is already deployed")

    T = TypeVar("T")

    async def get(self) -> T:
        """Get token attributes"""
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            # When using the cache
            if TOKEN_CACHE:
                token_cache: TokenCache | None = (
                    await db_session.scalars(
                        select(TokenCache)
                        .where(TokenCache.token_address == self.token_address)
                        .limit(1)
                    )
                ).first()
                if token_cache is not None:
                    is_updated = await self.check_attr_update(
                        db_session=db_session, base_datetime=token_cache.cached_datetime
                    )
                    if (
                        is_updated is False
                        and token_cache.expiration_datetime
                        > datetime.now(UTC).replace(tzinfo=None)
                    ):
                        # Get data from cache
                        for k, v in token_cache.attributes.items():
                            setattr(self, k, v)
                        await db_session.close()
                        return AttributeDict(self.__dict__)

            # When cache is not used
            # Or, if there is no data in the cache
            # Or, if the cache has expired

            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )

            try:
                tasks = await SemaphoreTaskGroup.run(
                    # IbetStandardTokenInterface attribute
                    AsyncContractUtils.call_function(
                        contract, "owner", (), ZERO_ADDRESS
                    ),
                    AsyncContractUtils.call_function(contract, "name", (), ""),
                    AsyncContractUtils.call_function(contract, "symbol", (), ""),
                    AsyncContractUtils.call_function(contract, "totalSupply", (), 0),
                    AsyncContractUtils.call_function(
                        contract, "tradableExchange", (), ZERO_ADDRESS
                    ),
                    AsyncContractUtils.call_function(
                        contract, "contactInformation", (), ""
                    ),
                    AsyncContractUtils.call_function(contract, "privacyPolicy", (), ""),
                    AsyncContractUtils.call_function(contract, "status", (), True),
                    # IbetSecurityTokenInterface attribute
                    AsyncContractUtils.call_function(
                        contract, "personalInfoAddress", (), ZERO_ADDRESS
                    ),
                    AsyncContractUtils.call_function(
                        contract, "requirePersonalInfoRegistered", (), True
                    ),
                    AsyncContractUtils.call_function(
                        contract, "transferable", (), False
                    ),
                    AsyncContractUtils.call_function(contract, "isOffering", (), False),
                    AsyncContractUtils.call_function(
                        contract, "transferApprovalRequired", (), False
                    ),
                    # IbetStraightBondToken attribute
                    AsyncContractUtils.call_function(contract, "faceValue", (), 0),
                    AsyncContractUtils.call_function(
                        contract, "faceValueCurrency", (), DEFAULT_CURRENCY
                    ),
                    AsyncContractUtils.call_function(contract, "interestRate", (), 0),
                    AsyncContractUtils.call_function(
                        contract, "interestPaymentCurrency", (), ""
                    ),
                    AsyncContractUtils.call_function(
                        contract, "interestPaymentDate", (), ""
                    ),
                    AsyncContractUtils.call_function(
                        contract, "redemptionDate", (), ""
                    ),
                    AsyncContractUtils.call_function(
                        contract, "redemptionValue", (), 0
                    ),
                    AsyncContractUtils.call_function(
                        contract, "redemptionValueCurrency", (), ""
                    ),
                    AsyncContractUtils.call_function(contract, "returnDate", (), ""),
                    AsyncContractUtils.call_function(contract, "returnAmount", (), ""),
                    AsyncContractUtils.call_function(contract, "baseFXRate", (), ""),
                    AsyncContractUtils.call_function(contract, "purpose", (), ""),
                    AsyncContractUtils.call_function(contract, "memo", (), ""),
                    AsyncContractUtils.call_function(contract, "isRedeemed", (), False),
                    max_concurrency=3,
                )
                (
                    self.issuer_address,
                    self.name,
                    self.symbol,
                    self.total_supply,
                    self.tradable_exchange_contract_address,
                    self.contact_information,
                    self.privacy_policy,
                    self.status,
                    self.personal_info_contract_address,
                    self.require_personal_info_registered,
                    self.transferable,
                    self.is_offering,
                    self.transfer_approval_required,
                    self.face_value,
                    self.face_value_currency,
                    _interest_rate,
                    self.interest_payment_currency,
                    _interest_payment_date,
                    self.redemption_date,
                    self.redemption_value,
                    self.redemption_value_currency,
                    self.return_date,
                    self.return_amount,
                    _base_fx_rate,
                    self.purpose,
                    self.memo,
                    self.is_redeemed,
                ) = [task.result() for task in tasks]
            except ExceptionGroup:
                LOG.warning("Failed to get ibet token attributes")
                raise ServiceUnavailableError from None

            self.interest_rate = float(Decimal(str(_interest_rate)) * Decimal("0.0001"))
            try:
                if _base_fx_rate is not None and _base_fx_rate != "":
                    self.base_fx_rate = float(_base_fx_rate)
                else:
                    self.base_fx_rate = 0.0
            except ValueError:
                self.base_fx_rate = 0.0

            interest_payment_date_list = []
            interest_payment_date_string = _interest_payment_date.replace("'", '"')
            interest_payment_date = {}
            try:
                if interest_payment_date_string != "":
                    interest_payment_date = json.loads(interest_payment_date_string)
            except Exception as err:
                LOG.warning("Failed to load interestPaymentDate: ", err)
            for i in range(1, 13):
                interest_payment_date_list.append(
                    interest_payment_date.get(f"interestPaymentDate{str(i)}", "")
                )
            self.interest_payment_date = interest_payment_date_list

            if TOKEN_CACHE:
                # Create token cache
                try:
                    await self.create_cache(db_session)
                    await db_session.commit()
                except (SAIntegrityError, StaleDataError):
                    await db_session.rollback()
        finally:
            await db_session.close()

        return AttributeDict(self.__dict__)

    async def update(
        self,
        tx_params: IbetStraightBondUpdateParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Update token

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        contract = AsyncContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )

        if tx_params.face_value is not None:
            tx = await contract.functions.setFaceValue(
                tx_params.face_value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.face_value_currency is not None:
            tx = await contract.functions.setFaceValueCurrency(
                tx_params.face_value_currency
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.purpose is not None:
            tx = await contract.functions.setPurpose(
                tx_params.purpose
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.interest_rate is not None:
            _interest_rate = int(
                Decimal(str(tx_params.interest_rate)) * Decimal("10000")
            )
            tx = await contract.functions.setInterestRate(
                _interest_rate
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.interest_payment_date is not None:
            _interest_payment_date = {}
            for i, item in enumerate(tx_params.interest_payment_date):
                _interest_payment_date[f"interestPaymentDate{i + 1}"] = item
            _interest_payment_date_string = json.dumps(_interest_payment_date)
            tx = await contract.functions.setInterestPaymentDate(
                _interest_payment_date_string
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.interest_payment_currency is not None:
            tx = await contract.functions.setInterestPaymentCurrency(
                tx_params.interest_payment_currency
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.redemption_value is not None:
            tx = await contract.functions.setRedemptionValue(
                tx_params.redemption_value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.redemption_value_currency is not None:
            tx = await contract.functions.setRedemptionValueCurrency(
                tx_params.redemption_value_currency
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.redemption_date is not None:
            tx = await contract.functions.setRedemptionDate(
                tx_params.redemption_date
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.base_fx_rate is not None:
            tx = await contract.functions.setBaseFXRate(
                str(tx_params.base_fx_rate)
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.transferable is not None:
            tx = await contract.functions.setTransferable(
                tx_params.transferable
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.status is not None:
            tx = await contract.functions.setStatus(tx_params.status).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.is_offering is not None:
            tx = await contract.functions.changeOfferingStatus(
                tx_params.is_offering
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.is_redeemed is not None and tx_params.is_redeemed:
            tx = await contract.functions.changeToRedeemed().build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.tradable_exchange_contract_address is not None:
            tx = await contract.functions.setTradableExchange(
                tx_params.tradable_exchange_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.personal_info_contract_address is not None:
            tx = await contract.functions.setPersonalInfoAddress(
                tx_params.personal_info_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.require_personal_info_registered is not None:
            tx = await contract.functions.setRequirePersonalInfoRegistered(
                tx_params.require_personal_info_registered
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.contact_information is not None:
            tx = await contract.functions.setContactInformation(
                tx_params.contact_information
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.privacy_policy is not None:
            tx = await contract.functions.setPrivacyPolicy(
                tx_params.privacy_policy
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.transfer_approval_required is not None:
            tx = await contract.functions.setTransferApprovalRequired(
                tx_params.transfer_approval_required
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.memo is not None:
            tx = await contract.functions.setMemo(tx_params.memo).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        # Delete Cache
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            await self.record_attr_update(db_session)
            await self.delete_cache(db_session)
            await db_session.commit()
        except Exception:
            LOG.exception("Failed to update database")
            pass
        finally:
            await db_session.close()


class IbetShareContract(IbetSecurityTokenInterface):
    """IbetShare contract"""

    issue_price: int
    cancellation_date: str
    memo: str
    principal_value: int
    is_canceled: bool
    dividends: float
    dividend_record_date: str
    dividend_payment_date: str

    def __init__(self, contract_address: str = ZERO_ADDRESS):
        super().__init__(contract_address, "IbetShare")

    async def create(
        self, args: list, tx_sender: EthereumAddress, tx_sender_key: bytes
    ):
        """
        Deploy token

        :param args: deploy arguments
        :param tx_sender: contract deployer
        :param tx_sender_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        if self.token_address == ZERO_ADDRESS:
            contract_address, abi, tx_hash = await AsyncContractUtils.deploy_contract(
                contract_name="IbetShare",
                args=args,
                deployer=tx_sender,
                private_key=tx_sender_key,
            )
            self.contract_name = "IbetShare"
            self.token_address = contract_address
            return contract_address, abi, tx_hash
        else:
            raise SendTransactionError("contract is already deployed")

    T = TypeVar("T")

    async def get(self) -> T:
        """Get token attributes"""
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            # When using the cache
            if TOKEN_CACHE:
                token_cache: TokenCache | None = (
                    await db_session.scalars(
                        select(TokenCache)
                        .where(TokenCache.token_address == self.token_address)
                        .limit(1)
                    )
                ).first()
                if token_cache is not None:
                    is_updated = await self.check_attr_update(
                        db_session=db_session, base_datetime=token_cache.cached_datetime
                    )
                    if (
                        is_updated is False
                        and token_cache.expiration_datetime
                        > datetime.now(UTC).replace(tzinfo=None)
                    ):
                        # Get data from cache
                        for k, v in token_cache.attributes.items():
                            setattr(self, k, v)
                        await db_session.close()
                        return AttributeDict(self.__dict__)

            # When cache is not used
            # Or, if there is no data in the cache
            # Or, if the cache has expired

            contract = AsyncContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )

            try:
                tasks = await SemaphoreTaskGroup.run(
                    # IbetStandardTokenInterface attribute
                    AsyncContractUtils.call_function(
                        contract, "owner", (), ZERO_ADDRESS
                    ),
                    AsyncContractUtils.call_function(contract, "name", (), ""),
                    AsyncContractUtils.call_function(contract, "symbol", (), ""),
                    AsyncContractUtils.call_function(contract, "totalSupply", (), 0),
                    AsyncContractUtils.call_function(
                        contract, "tradableExchange", (), ZERO_ADDRESS
                    ),
                    AsyncContractUtils.call_function(
                        contract, "contactInformation", (), ""
                    ),
                    AsyncContractUtils.call_function(contract, "privacyPolicy", (), ""),
                    AsyncContractUtils.call_function(contract, "status", (), True),
                    # IbetSecurityTokenInterface attribute
                    AsyncContractUtils.call_function(
                        contract, "personalInfoAddress", (), ZERO_ADDRESS
                    ),
                    AsyncContractUtils.call_function(
                        contract, "requirePersonalInfoRegistered", (), True
                    ),
                    AsyncContractUtils.call_function(
                        contract, "transferable", (), False
                    ),
                    AsyncContractUtils.call_function(contract, "isOffering", (), False),
                    AsyncContractUtils.call_function(
                        contract, "transferApprovalRequired", (), False
                    ),
                    # IbetShareToken attribute
                    AsyncContractUtils.call_function(contract, "issuePrice", (), 0),
                    AsyncContractUtils.call_function(
                        contract, "cancellationDate", (), ""
                    ),
                    AsyncContractUtils.call_function(contract, "memo", (), ""),
                    AsyncContractUtils.call_function(contract, "principalValue", (), 0),
                    AsyncContractUtils.call_function(contract, "isCanceled", (), False),
                    AsyncContractUtils.call_function(
                        contract, "dividendInformation", (), (0, "", "")
                    ),
                    max_concurrency=3,
                )
                (
                    self.issuer_address,
                    self.name,
                    self.symbol,
                    self.total_supply,
                    self.tradable_exchange_contract_address,
                    self.contact_information,
                    self.privacy_policy,
                    self.status,
                    self.personal_info_contract_address,
                    self.require_personal_info_registered,
                    self.transferable,
                    self.is_offering,
                    self.transfer_approval_required,
                    self.issue_price,
                    self.cancellation_date,
                    self.memo,
                    self.principal_value,
                    self.is_canceled,
                    _dividend_info,
                ) = [task.result() for task in tasks]
            except ExceptionGroup:
                LOG.warning("Failed to get ibet token attributes")
                raise ServiceUnavailableError from None

            self.dividends = float(
                Decimal(str(_dividend_info[0])) * Decimal("0.0000000000001")
            )
            self.dividend_record_date = _dividend_info[1]
            self.dividend_payment_date = _dividend_info[2]

            if TOKEN_CACHE:
                # Create token cache
                try:
                    await self.create_cache(db_session)
                    await db_session.commit()
                except (SAIntegrityError, StaleDataError):
                    await db_session.rollback()
        finally:
            await db_session.close()

        return AttributeDict(self.__dict__)

    async def update(
        self,
        tx_params: IbetShareUpdateParams,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ):
        """
        Update token

        :param tx_params: Transaction parameters
        :param tx_sender: Transaction sender address
        :param tx_sender_key: Transaction sender private key
        """
        contract = AsyncContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )

        if tx_params.tradable_exchange_contract_address is not None:
            tx = await contract.functions.setTradableExchange(
                tx_params.tradable_exchange_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.personal_info_contract_address is not None:
            tx = await contract.functions.setPersonalInfoAddress(
                tx_params.personal_info_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.require_personal_info_registered is not None:
            tx = await contract.functions.setRequirePersonalInfoRegistered(
                tx_params.require_personal_info_registered
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.dividends is not None:
            _dividends = int(
                Decimal(str(tx_params.dividends)) * Decimal("10000000000000")
            )
            tx = await contract.functions.setDividendInformation(
                _dividends,
                tx_params.dividend_record_date,
                tx_params.dividend_payment_date,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.cancellation_date is not None:
            tx = await contract.functions.setCancellationDate(
                tx_params.cancellation_date
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.contact_information is not None:
            tx = await contract.functions.setContactInformation(
                tx_params.contact_information
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.privacy_policy is not None:
            tx = await contract.functions.setPrivacyPolicy(
                tx_params.privacy_policy
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.status is not None:
            tx = await contract.functions.setStatus(tx_params.status).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.transferable is not None:
            tx = await contract.functions.setTransferable(
                tx_params.transferable
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.is_offering is not None:
            tx = await contract.functions.changeOfferingStatus(
                tx_params.is_offering
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.transfer_approval_required is not None:
            tx = await contract.functions.setTransferApprovalRequired(
                tx_params.transfer_approval_required
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.principal_value is not None:
            tx = await contract.functions.setPrincipalValue(
                tx_params.principal_value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.is_canceled is not None and tx_params.is_canceled:
            tx = await contract.functions.changeToCanceled().build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if tx_params.memo is not None:
            tx = await contract.functions.setMemo(tx_params.memo).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_sender,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=tx_sender_key
                )
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        # Delete Cache
        db_session = AsyncSession(autocommit=False, autoflush=True, bind=async_engine)
        try:
            await self.record_attr_update(db_session)
            await self.delete_cache(db_session)
            await db_session.commit()
        except Exception:
            LOG.exception("Failed to update database")
            pass
        finally:
            await db_session.close()
