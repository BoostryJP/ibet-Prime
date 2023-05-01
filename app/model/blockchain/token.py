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
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.orm import Session
from web3.datastructures import AttributeDict
from web3.exceptions import TimeExhausted

from app import log
from app.database import engine
from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain import IbetExchangeInterface
from app.model.blockchain.tx_params.ibet_security_token import (
    AdditionalIssueParams as IbetSecurityTokenAdditionalIssueParams,
)
from app.model.blockchain.tx_params.ibet_security_token import (
    ApproveTransferParams as IbetSecurityTokenApproveTransfer,
)
from app.model.blockchain.tx_params.ibet_security_token import (
    CancelTransferParams as IbetSecurityTokenCancelTransfer,
)
from app.model.blockchain.tx_params.ibet_security_token import (
    ForceUnlockParams as IbetSecurityTokenForceUnlockParams,
)
from app.model.blockchain.tx_params.ibet_security_token import (
    LockParams as IbetSecurityTokenLockParams,
)
from app.model.blockchain.tx_params.ibet_security_token import (
    RedeemParams as IbetSecurityTokenRedeemParams,
)
from app.model.blockchain.tx_params.ibet_security_token import (
    TransferParams as IbetSecurityTokenTransferParams,
)
from app.model.blockchain.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams as IbetStraightBondUpdateParams,
)
from app.model.db import (
    TokenAttrUpdate,
    TokenCache,
    TokenType,
    UpdateToken,
    UpdateTokenTrigger,
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from config import CHAIN_ID, TOKEN_CACHE, TOKEN_CACHE_TTL, TX_GAS_LIMIT, ZERO_ADDRESS

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

    def check_attr_update(self, db_session: Session, base_datetime: datetime):
        is_updated = False
        _token_attr_update = (
            db_session.query(TokenAttrUpdate)
            .filter(TokenAttrUpdate.token_address == self.token_address)
            .order_by(desc(TokenAttrUpdate.id))
            .first()
        )
        if (
            _token_attr_update is not None
            and _token_attr_update.updated_datetime > base_datetime
        ):
            is_updated = True
        return is_updated

    def record_attr_update(self, db_session: Session):
        _token_attr_update = TokenAttrUpdate()
        _token_attr_update.token_address = self.token_address
        _token_attr_update.updated_datetime = datetime.utcnow()
        db_session.add(_token_attr_update)

    def create_history(
        self,
        db_session: Session,
        original_contents: dict,
        modified_contents: dict,
        token_type: str,
        trigger: UpdateTokenTrigger,
    ):
        update_token = UpdateToken()
        update_token.token_address = self.token_address
        update_token.issuer_address = self.issuer_address
        update_token.type = token_type
        update_token.arguments = modified_contents
        update_token.original_contents = original_contents
        update_token.status = 1  # succeeded
        update_token.trigger = trigger
        db_session.add(update_token)

    def create_cache(self, db_session: Session):
        token_cache = TokenCache()
        token_cache.token_address = self.token_address
        token_cache.attributes = self.__dict__
        token_cache.cached_datetime = datetime.utcnow()
        token_cache.expiration_datetime = datetime.utcnow() + timedelta(
            seconds=TOKEN_CACHE_TTL
        )
        db_session.merge(token_cache)

    def delete_cache(self, db_session: Session):
        db_session.query(TokenCache).filter(
            TokenCache.token_address == self.token_address
        ).delete()

    def get_account_balance(self, account_address: str):
        """Get account balance"""
        contract = ContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )
        balance = ContractUtils.call_function(
            contract=contract,
            function_name="balanceOf",
            args=(account_address,),
            default_returns=0,
        )
        tradable_exchange_address = ContractUtils.call_function(
            contract=contract,
            function_name="tradableExchange",
            args=(),
            default_returns=ZERO_ADDRESS,
        )
        if tradable_exchange_address != ZERO_ADDRESS:
            exchange_contract = IbetExchangeInterface(tradable_exchange_address)
            exchange_balance = exchange_contract.get_account_balance(
                account_address=account_address, token_address=self.token_address
            )
            balance = (
                balance + exchange_balance["balance"] + exchange_balance["commitment"]
            )

        return balance


class IbetSecurityTokenInterface(IbetStandardTokenInterface):
    personal_info_contract_address: str
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool

    def __init__(
        self,
        contract_address: str = ZERO_ADDRESS,
        contract_name: str = "IbetSecurityTokenInterface",
    ):
        super().__init__(contract_address, contract_name)

    def transfer(
        self, data: IbetSecurityTokenTransferParams, tx_from: str, private_key: str
    ):
        """Transfer ownership"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            _from = data.from_address
            _to = data.to_address
            _amount = data.amount
            tx = contract.functions.transferFrom(_from, _to, _amount).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        return tx_hash

    def additional_issue(
        self,
        data: IbetSecurityTokenAdditionalIssueParams,
        tx_from: str,
        private_key: str,
    ):
        """Additional issue"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            _target_address = data.account_address
            _amount = data.amount
            tx = contract.functions.issueFrom(
                _target_address, ZERO_ADDRESS, _amount
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        # Delete Cache
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            self.record_attr_update(db_session)
            self.delete_cache(db_session)
            db_session.commit()
        except Exception as err:
            raise SendTransactionError(err)
        finally:
            db_session.close()

        return tx_hash

    def redeem(
        self, data: IbetSecurityTokenRedeemParams, tx_from: str, private_key: str
    ):
        """Redeem a token"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            _target_address = data.account_address
            _amount = data.amount
            tx = contract.functions.redeemFrom(
                _target_address, ZERO_ADDRESS, _amount
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

        # Delete Cache
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            self.record_attr_update(db_session)
            self.delete_cache(db_session)
            db_session.commit()
        except Exception as err:
            raise SendTransactionError(err)
        finally:
            db_session.close()

        return tx_hash

    def approve_transfer(
        self, data: IbetSecurityTokenApproveTransfer, tx_from: str, private_key: str
    ):
        """Approve Transfer"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = contract.functions.approveTransfer(
                data.application_id, data.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    def cancel_transfer(
        self, data: IbetSecurityTokenCancelTransfer, tx_from: str, private_key: str
    ):
        """Cancel Transfer"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = contract.functions.cancelTransfer(
                data.application_id, data.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    def lock(self, data: IbetSecurityTokenLockParams, tx_from: str, private_key: str):
        """Lock"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = contract.functions.lock(
                data.lock_address, data.value, data.data
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    def force_unlock(
        self, data: IbetSecurityTokenForceUnlockParams, tx_from: str, private_key: str
    ):
        """Force Unlock"""
        try:
            contract = ContractUtils.get_contract(
                contract_name=self.contract_name, contract_address=self.token_address
            )
            tx = contract.functions.forceUnlock(
                data.lock_address,
                data.account_address,
                data.recipient_address,
                data.value,
                data.data,
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, tx_receipt = ContractUtils.send_transaction(
                transaction=tx, private_key=private_key
            )
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)


class IbetStraightBondContract(IbetSecurityTokenInterface):
    face_value: int
    interest_rate: float
    interest_payment_date: List[str]
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    memo: str
    is_redeemed: bool

    def __init__(self, contract_address: str = ZERO_ADDRESS):
        super().__init__(contract_address, "IbetStraightBond")

    def create(self, args: list, tx_from: str, private_key: str):
        """Deploy token

        :param args: deploy arguments
        :param tx_from: contract deployer
        :param private_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        if self.token_address == ZERO_ADDRESS:
            contract_address, abi, tx_hash = ContractUtils.deploy_contract(
                contract_name="IbetStraightBond",
                args=args,
                deployer=tx_from,
                private_key=private_key,
            )
            self.contract_name = "IbetStraightBond"
            self.token_address = contract_address
            return contract_address, abi, tx_hash
        else:
            raise SendTransactionError("contract is already deployed")

    def get(self):
        """Get token attributes"""
        db_session = Session(autocommit=False, autoflush=True, bind=engine)

        # When using the cache
        if TOKEN_CACHE:
            token_cache: TokenCache | None = (
                db_session.query(TokenCache)
                .filter(TokenCache.token_address == self.token_address)
                .first()
            )
            if token_cache is not None:
                is_updated = self.check_attr_update(
                    db_session=db_session, base_datetime=token_cache.cached_datetime
                )
                if (
                    is_updated is False
                    and token_cache.expiration_datetime > datetime.utcnow()
                ):
                    # Get data from cache
                    for k, v in token_cache.attributes.items():
                        setattr(self, k, v)
                    db_session.close()
                    return AttributeDict(self.__dict__)

        # When cache is not used
        # Or, if there is no data in the cache
        # Or, if the cache has expired

        contract = ContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )

        # Set IbetStandardTokenInterface attribute
        self.issuer_address = ContractUtils.call_function(
            contract, "owner", (), ZERO_ADDRESS
        )
        self.name = ContractUtils.call_function(contract, "name", (), "")
        self.symbol = ContractUtils.call_function(contract, "symbol", (), "")
        self.total_supply = ContractUtils.call_function(contract, "totalSupply", (), 0)
        self.tradable_exchange_contract_address = ContractUtils.call_function(
            contract, "tradableExchange", (), ZERO_ADDRESS
        )
        self.contact_information = ContractUtils.call_function(
            contract, "contactInformation", (), ""
        )
        self.privacy_policy = ContractUtils.call_function(
            contract, "privacyPolicy", (), ""
        )
        self.status = ContractUtils.call_function(contract, "status", (), True)

        # Set IbetSecurityTokenInterface attribute
        self.personal_info_contract_address = ContractUtils.call_function(
            contract, "personalInfoAddress", (), ZERO_ADDRESS
        )
        self.transferable = ContractUtils.call_function(
            contract, "transferable", (), False
        )
        self.is_offering = ContractUtils.call_function(
            contract, "isOffering", (), False
        )
        self.transfer_approval_required = ContractUtils.call_function(
            contract, "transferApprovalRequired", (), False
        )

        # Set IbetStraightBondToken attribute
        self.face_value = ContractUtils.call_function(contract, "faceValue", (), 0)
        self.interest_rate = float(
            Decimal(str(ContractUtils.call_function(contract, "interestRate", (), 0)))
            * Decimal("0.0001")
        )
        self.redemption_date = ContractUtils.call_function(
            contract, "redemptionDate", (), ""
        )
        self.redemption_value = ContractUtils.call_function(
            contract, "redemptionValue", (), 0
        )
        self.return_date = ContractUtils.call_function(contract, "returnDate", (), "")
        self.return_amount = ContractUtils.call_function(
            contract, "returnAmount", (), ""
        )
        self.purpose = ContractUtils.call_function(contract, "purpose", (), "")
        self.memo = ContractUtils.call_function(contract, "memo", (), "")
        self.is_redeemed = ContractUtils.call_function(
            contract, "isRedeemed", (), False
        )

        interest_payment_date_list = []
        interest_payment_date_string = ContractUtils.call_function(
            contract, "interestPaymentDate", (), ""
        ).replace("'", '"')
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
                self.create_cache(db_session)
                db_session.commit()
            except SAIntegrityError:
                db_session.rollback()

        db_session.close()

        return AttributeDict(self.__dict__)

    def update(
        self, data: IbetStraightBondUpdateParams, tx_from: str, private_key: str
    ):
        """Update token"""
        if data.dict(exclude_none=True) == {}:
            return

        original_contents = self.get().__dict__

        contract = ContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )

        if data.face_value is not None:
            tx = contract.functions.setFaceValue(data.face_value).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.interest_rate is not None:
            _interest_rate = int(Decimal(str(data.interest_rate)) * Decimal("10000"))
            tx = contract.functions.setInterestRate(_interest_rate).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.interest_payment_date is not None:
            _interest_payment_date = {}
            for i, item in enumerate(data.interest_payment_date):
                _interest_payment_date[f"interestPaymentDate{i + 1}"] = item
            _interest_payment_date_string = json.dumps(_interest_payment_date)
            tx = contract.functions.setInterestPaymentDate(
                _interest_payment_date_string
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.redemption_value is not None:
            tx = contract.functions.setRedemptionValue(
                data.redemption_value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transferable is not None:
            tx = contract.functions.setTransferable(
                data.transferable
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.status is not None:
            tx = contract.functions.setStatus(data.status).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_offering is not None:
            tx = contract.functions.changeOfferingStatus(
                data.is_offering
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_redeemed is not None and data.is_redeemed:
            tx = contract.functions.changeToRedeemed().build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.tradable_exchange_contract_address is not None:
            tx = contract.functions.setTradableExchange(
                data.tradable_exchange_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.personal_info_contract_address is not None:
            tx = contract.functions.setPersonalInfoAddress(
                data.personal_info_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.contact_information is not None:
            tx = contract.functions.setContactInformation(
                data.contact_information
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.privacy_policy is not None:
            tx = contract.functions.setPrivacyPolicy(
                data.privacy_policy
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transfer_approval_required is not None:
            tx = contract.functions.setTransferApprovalRequired(
                data.transfer_approval_required
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.memo is not None:
            tx = contract.functions.setMemo(data.memo).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        # Delete Cache
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            self.record_attr_update(db_session)
            self.create_history(
                db_session,
                original_contents=original_contents,
                modified_contents=data.dict(exclude_none=True),
                token_type=TokenType.IBET_STRAIGHT_BOND.value,
                trigger=UpdateTokenTrigger.UPDATE,
            )
            self.delete_cache(db_session)
            db_session.commit()
        except Exception as err:
            raise SendTransactionError(err)
        finally:
            db_session.close()


class IbetShareContract(IbetSecurityTokenInterface):
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

    def create(self, args: list, tx_from: str, private_key: str):
        """Deploy token

        :param args: deploy arguments
        :param tx_from: contract deployer
        :param private_key: deployer's private key
        :return: contract address, ABI, transaction hash
        """
        if self.token_address == ZERO_ADDRESS:
            contract_address, abi, tx_hash = ContractUtils.deploy_contract(
                contract_name="IbetShare",
                args=args,
                deployer=tx_from,
                private_key=private_key,
            )
            self.contract_name = "IbetShare"
            self.token_address = contract_address
            return contract_address, abi, tx_hash
        else:
            raise SendTransactionError("contract is already deployed")

    def get(self):
        """Get token attributes"""
        db_session = Session(autocommit=False, autoflush=True, bind=engine)

        # When using the cache
        if TOKEN_CACHE:
            token_cache: TokenCache | None = (
                db_session.query(TokenCache)
                .filter(TokenCache.token_address == self.token_address)
                .first()
            )
            if token_cache is not None:
                is_updated = self.check_attr_update(
                    db_session=db_session, base_datetime=token_cache.cached_datetime
                )
                if (
                    is_updated is False
                    and token_cache.expiration_datetime > datetime.utcnow()
                ):
                    # Get data from cache
                    for k, v in token_cache.attributes.items():
                        setattr(self, k, v)
                    db_session.close()
                    return AttributeDict(self.__dict__)

        # When cache is not used
        # Or, if there is no data in the cache
        # Or, if the cache has expired

        contract = ContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )

        # Set IbetStandardTokenInterface attribute
        self.issuer_address = ContractUtils.call_function(
            contract, "owner", (), ZERO_ADDRESS
        )
        self.name = ContractUtils.call_function(contract, "name", (), "")
        self.symbol = ContractUtils.call_function(contract, "symbol", (), "")
        self.total_supply = ContractUtils.call_function(contract, "totalSupply", (), 0)
        self.tradable_exchange_contract_address = ContractUtils.call_function(
            contract, "tradableExchange", (), ZERO_ADDRESS
        )
        self.contact_information = ContractUtils.call_function(
            contract, "contactInformation", (), ""
        )
        self.privacy_policy = ContractUtils.call_function(
            contract, "privacyPolicy", (), ""
        )
        self.status = ContractUtils.call_function(contract, "status", (), True)

        # Set IbetSecurityTokenInterface attribute
        self.personal_info_contract_address = ContractUtils.call_function(
            contract, "personalInfoAddress", (), ZERO_ADDRESS
        )
        self.transferable = ContractUtils.call_function(
            contract, "transferable", (), False
        )
        self.is_offering = ContractUtils.call_function(
            contract, "isOffering", (), False
        )
        self.transfer_approval_required = ContractUtils.call_function(
            contract, "transferApprovalRequired", (), False
        )

        # Set IbetShareToken attribute
        self.issue_price = ContractUtils.call_function(contract, "issuePrice", (), 0)
        self.cancellation_date = ContractUtils.call_function(
            contract, "cancellationDate", (), ""
        )
        self.memo = ContractUtils.call_function(contract, "memo", (), "")
        self.principal_value = ContractUtils.call_function(
            contract, "principalValue", (), 0
        )
        self.is_canceled = ContractUtils.call_function(
            contract, "isCanceled", (), False
        )
        _dividend_info = ContractUtils.call_function(
            contract, "dividendInformation", (), (0, "", "")
        )
        self.dividends = float(
            Decimal(str(_dividend_info[0])) * Decimal("0.0000000000001")
        )
        self.dividend_record_date = _dividend_info[1]
        self.dividend_payment_date = _dividend_info[2]

        if TOKEN_CACHE:
            # Create token cache
            try:
                self.create_cache(db_session)
                db_session.commit()
            except SAIntegrityError:
                db_session.rollback()

        db_session.close()

        return AttributeDict(self.__dict__)

    def update(self, data: IbetShareUpdateParams, tx_from: str, private_key: str):
        """Update token"""
        if data.dict(exclude_none=True) == {}:
            return

        original_contents = self.get().__dict__

        contract = ContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=self.token_address
        )

        if data.tradable_exchange_contract_address is not None:
            tx = contract.functions.setTradableExchange(
                data.tradable_exchange_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.personal_info_contract_address is not None:
            tx = contract.functions.setPersonalInfoAddress(
                data.personal_info_contract_address
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.dividends is not None:
            _dividends = int(Decimal(str(data.dividends)) * Decimal("10000000000000"))
            tx = contract.functions.setDividendInformation(
                _dividends, data.dividend_record_date, data.dividend_payment_date
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.cancellation_date is not None:
            tx = contract.functions.setCancellationDate(
                data.cancellation_date
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.contact_information is not None:
            tx = contract.functions.setContactInformation(
                data.contact_information
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.privacy_policy is not None:
            tx = contract.functions.setPrivacyPolicy(
                data.privacy_policy
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.status is not None:
            tx = contract.functions.setStatus(data.status).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transferable is not None:
            tx = contract.functions.setTransferable(
                data.transferable
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_offering is not None:
            tx = contract.functions.changeOfferingStatus(
                data.is_offering
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.transfer_approval_required is not None:
            tx = contract.functions.setTransferApprovalRequired(
                data.transfer_approval_required
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.principal_value is not None:
            tx = contract.functions.setPrincipalValue(
                data.principal_value
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.is_canceled is not None and data.is_canceled:
            tx = contract.functions.changeToCanceled().build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        if data.memo is not None:
            tx = contract.functions.setMemo(data.memo).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": tx_from,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            try:
                ContractUtils.send_transaction(transaction=tx, private_key=private_key)
            except ContractRevertError:
                raise
            except TimeExhausted as timeout_error:
                raise SendTransactionError(timeout_error)
            except Exception as err:
                raise SendTransactionError(err)

        # Delete Cache
        db_session = Session(autocommit=False, autoflush=True, bind=engine)
        try:
            self.record_attr_update(db_session)
            self.create_history(
                db_session,
                original_contents=original_contents,
                modified_contents=data.dict(exclude_none=True),
                token_type=TokenType.IBET_SHARE.value,
                trigger=UpdateTokenTrigger.UPDATE,
            )
            self.delete_cache(db_session)
            db_session.commit()
        except Exception as err:
            raise SendTransactionError(err)
        finally:
            db_session.close()
