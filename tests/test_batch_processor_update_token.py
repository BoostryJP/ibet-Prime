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
import pytest
from unittest.mock import patch, ANY, call

from config import TOKEN_LIST_CONTRACT_ADDRESS
from app.model.schema import (
    IbetShareUpdate,
    IbetStraightBondUpdate
)
from app.model.db import (
    Account,
    Token,
    TokenType,
    UpdateToken,
    IDXPosition,
    Notification,
    NotificationType
)
from app.utils.e2ee_utils import E2EEUtils
from app.exceptions import SendTransactionError
from batch.processor_update_token import (
    Sinks,
    DBSink,
    Processor
)
from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(db):
    _sink = Sinks()
    _sink.register(DBSink(db))
    return Processor(sink=_sink, db=db)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Issuing(IbetShare, IbetStraightBond)
    def test_normal_1(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test_1"
        _token_address_2 = "token_address_test_2"
        _token_address_3 = "token_address_test_3"  # not target
        _token_address_4 = "token_address_test_4"  # not target

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = _issuer_address
        _token_1.token_address = _token_address_1
        _token_1.abi = ""
        _token_1.token_status = 0
        db.add(_token_1)

        _update_token_1 = UpdateToken()
        _update_token_1.token_address = _token_address_1
        _update_token_1.issuer_address = _issuer_address
        _update_token_1.type = TokenType.IBET_SHARE
        _update_token_1.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "image_url": ["image_1"],  # update
            "transferable": False,  # update
            "status": False,  # update
            "offering_status": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": 1000,
            "is_canceled": True  # update
        }
        _update_token_1.status = 0
        _update_token_1.trigger = "Issue"
        db.add(_update_token_1)

        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = _issuer_address
        _token_2.token_address = _token_address_2
        _token_2.abi = ""
        _token_2.token_status = 0
        db.add(_token_2)

        _update_token_2 = UpdateToken()
        _update_token_2.token_address = _token_address_2
        _update_token_2.issuer_address = _issuer_address
        _update_token_2.type = TokenType.IBET_STRAIGHT_BOND
        _update_token_2.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 2000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        _update_token_2.status = 0
        _update_token_2.trigger = "Issue"
        db.add(_update_token_2)

        # not target
        _update_token_3 = UpdateToken()
        _update_token_3.token_address = _token_address_3
        _update_token_3.issuer_address = _issuer_address
        _update_token_3.type = TokenType.IBET_SHARE
        _update_token_3.arguments = {}
        _update_token_3.status = 1
        _update_token_3.trigger = "Issue"
        db.add(_update_token_3)

        # not target
        _update_token_4 = UpdateToken()
        _update_token_4.token_address = _token_address_4
        _update_token_4.issuer_address = _issuer_address
        _update_token_4.type = TokenType.IBET_SHARE
        _update_token_4.arguments = {}
        _update_token_4.status = 2
        _update_token_4.trigger = "Issue"
        db.add(_update_token_4)

        with patch(target="app.model.blockchain.token.IbetShareContract.update",
                   return_value=None) as IbetShareContract_update, \
                patch(target="app.model.blockchain.token.IbetStraightBondContract.update",
                      return_value=None) as IbetStraightBondContract_update, \
                patch(target="app.model.blockchain.token_list.TokenListContract.register",
                      return_value=None) as TokenListContract_register:
            # Execute batch
            processor.process()

            # assertion(contract)
            IbetShareContract_update.assert_called_with(
                contract_address=_token_address_1,
                data=IbetShareUpdate(
                    cancellation_date=None,
                    dividend_record_date=None,
                    dividend_payment_date=None,
                    dividends=None,
                    tradable_exchange_contract_address="0x0000000000000000000000000000000000000001",
                    personal_info_contract_address="0x0000000000000000000000000000000000000002",
                    image_url=["image_1"],
                    transferable=False,
                    status=False,
                    offering_status=True,
                    contact_information="contact info test",
                    privacy_policy="privacy policy test",
                    transfer_approval_required=True,
                    is_canceled=True
                ),
                tx_from=_issuer_address,
                private_key=ANY
            )

            IbetStraightBondContract_update.assert_called_with(
                contract_address=_token_address_2,
                data=IbetStraightBondUpdate(
                    interest_rate=0.0001,
                    interest_payment_date=["0331", "0930"],
                    transferable=False,
                    image_url=["image_1"],
                    status=False,
                    initial_offering_status=True,
                    is_redeemed=True,
                    tradable_exchange_contract_address="0x0000000000000000000000000000000000000001",
                    personal_info_contract_address="0x0000000000000000000000000000000000000002",
                    contact_information="contact info test",
                    privacy_policy="privacy policy test"
                ),
                tx_from=_issuer_address,
                private_key=ANY
            )

            TokenListContract_register.assert_has_calls([
                call(token_list_address=TOKEN_LIST_CONTRACT_ADDRESS,
                     token_address=_token_address_1,
                     token_template=TokenType.IBET_SHARE,
                     account_address=_issuer_address,
                     private_key=ANY),
                call(token_list_address=TOKEN_LIST_CONTRACT_ADDRESS,
                     token_address=_token_address_2,
                     token_template=TokenType.IBET_STRAIGHT_BOND,
                     account_address=_issuer_address,
                     private_key=ANY),
            ])

            # assertion(DB)
            _idx_position_list = db.query(IDXPosition).order_by(IDXPosition.id).all()
            assert len(_idx_position_list) == 2
            _idx_position = _idx_position_list[0]
            assert _idx_position.id == 1
            assert _idx_position.token_address == _token_address_1
            assert _idx_position.account_address == _issuer_address
            assert _idx_position.balance == 10000
            assert _idx_position.pending_transfer == 0
            _idx_position = _idx_position_list[1]
            assert _idx_position.id == 2
            assert _idx_position.token_address == _token_address_2
            assert _idx_position.account_address == _issuer_address
            assert _idx_position.balance == 2000
            assert _idx_position.exchange_balance == 0
            assert _idx_position.exchange_commitment == 0
            assert _idx_position.pending_transfer == 0

            _token_list = db.query(Token).order_by(Token.id).all()
            _token = _token_list[0]
            assert _token.token_status == 1
            _token = _token_list[1]
            assert _token.token_status == 1

            _update_token_list = db.query(UpdateToken).order_by(UpdateToken.id).all()
            _update_token = _update_token_list[0]
            assert _update_token.status == 1
            _update_token = _update_token_list[1]
            assert _update_token.status == 1
            _update_token = _update_token_list[2]
            assert _update_token.status == 1
            _update_token = _update_token_list[3]
            assert _update_token.status == 2

            _notification_list = db.query(Notification).order_by(Notification.id).all()
            assert len(_notification_list) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Issuing: Account does not exist
    def test_error_1(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test_1"
        _token_address_2 = "token_address_test_2"
        _token_address_3 = "token_address_test_3"  # not target
        _token_address_4 = "token_address_test_4"  # not target

        # prepare data
        account = Account()
        account.issuer_address = "test"  # not target
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = _issuer_address
        _token_1.token_address = _token_address_1
        _token_1.abi = ""
        _token_1.token_status = 0
        db.add(_token_1)

        _update_token_1 = UpdateToken()
        _update_token_1.token_address = _token_address_1
        _update_token_1.issuer_address = _issuer_address
        _update_token_1.type = TokenType.IBET_SHARE
        _update_token_1.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "image_url": ["image_1"],  # update
            "transferable": False,  # update
            "status": False,  # update
            "offering_status": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": 1000,
            "is_canceled": True  # update
        }
        _update_token_1.status = 0
        _update_token_1.trigger = "Issue"
        db.add(_update_token_1)

        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = _issuer_address
        _token_2.token_address = _token_address_2
        _token_2.abi = ""
        _token_2.token_status = 0
        db.add(_token_2)

        _update_token_2 = UpdateToken()
        _update_token_2.token_address = _token_address_2
        _update_token_2.issuer_address = _issuer_address
        _update_token_2.type = TokenType.IBET_STRAIGHT_BOND
        _update_token_2.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 2000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        _update_token_2.status = 0
        _update_token_2.trigger = "Issue"
        db.add(_update_token_2)

        # not target
        _update_token_3 = UpdateToken()
        _update_token_3.token_address = _token_address_3
        _update_token_3.issuer_address = _issuer_address
        _update_token_3.type = TokenType.IBET_SHARE
        _update_token_3.arguments = {}
        _update_token_3.status = 1
        _update_token_3.trigger = "Issue"
        db.add(_update_token_3)

        # not target
        _update_token_4 = UpdateToken()
        _update_token_4.token_address = _token_address_4
        _update_token_4.issuer_address = _issuer_address
        _update_token_4.type = TokenType.IBET_SHARE
        _update_token_4.arguments = {}
        _update_token_4.status = 2
        _update_token_4.trigger = "Issue"
        db.add(_update_token_4)

        # Execute batch
        processor.process()

        # assertion(DB)
        _idx_position_list = db.query(IDXPosition).order_by(IDXPosition.id).all()
        assert len(_idx_position_list) == 0

        _token_list = db.query(Token).order_by(Token.id).all()
        _token = _token_list[0]
        assert _token.token_status == 2
        _token = _token_list[1]
        assert _token.token_status == 2

        _update_token_list = db.query(UpdateToken).order_by(UpdateToken.id).all()
        _update_token = _update_token_list[0]
        assert _update_token.status == 2
        _update_token = _update_token_list[1]
        assert _update_token.status == 2
        _update_token = _update_token_list[2]
        assert _update_token.status == 1
        _update_token = _update_token_list[3]
        assert _update_token.status == 2

        _notification_list = db.query(Notification).order_by(Notification.id).all()
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.ISSUE_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_address": _token_address_1,
            "token_type": TokenType.IBET_SHARE,
            "arguments": {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "image_url": ["image_1"],  # update
                "transferable": False,  # update
                "status": False,  # update
                "offering_status": True,  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test",  # update
                "transfer_approval_required": True,  # update
                "principal_value": 1000,
                "is_canceled": True  # update
            }
        }
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.ISSUE_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {
            "token_address": _token_address_2,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "arguments": {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 2000,
                "face_value": 200,
                "redemption_date": "redemption_date_test1",
                "redemption_value": 4000,
                "return_date": "return_date_test1",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.0001,  # update
                "interest_payment_date": ["0331", "0930"],  # update
                "transferable": False,  # update
                "image_url": ["image_1"],  # update
                "status": False,  # update
                "initial_offering_status": True,  # update
                "is_redeemed": True,  # update
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test"  # update
            }
        }

    # <Error_2>
    # Issuing: Fail to get the private key
    def test_error_2(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test_1"
        _token_address_2 = "token_address_test_2"
        _token_address_3 = "token_address_test_3"  # not target
        _token_address_4 = "token_address_test_4"  # not target

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password_ng")  # invalid
        db.add(account)

        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = _issuer_address
        _token_1.token_address = _token_address_1
        _token_1.abi = ""
        _token_1.token_status = 0
        db.add(_token_1)

        _update_token_1 = UpdateToken()
        _update_token_1.token_address = _token_address_1
        _update_token_1.issuer_address = _issuer_address
        _update_token_1.type = TokenType.IBET_SHARE
        _update_token_1.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "image_url": ["image_1"],  # update
            "transferable": False,  # update
            "status": False,  # update
            "offering_status": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": 1000,
            "is_canceled": True  # update
        }
        _update_token_1.status = 0
        _update_token_1.trigger = "Issue"
        db.add(_update_token_1)

        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = _issuer_address
        _token_2.token_address = _token_address_2
        _token_2.abi = ""
        _token_2.token_status = 0
        db.add(_token_2)

        _update_token_2 = UpdateToken()
        _update_token_2.token_address = _token_address_2
        _update_token_2.issuer_address = _issuer_address
        _update_token_2.type = TokenType.IBET_STRAIGHT_BOND
        _update_token_2.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 2000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        _update_token_2.status = 0
        _update_token_2.trigger = "Issue"
        db.add(_update_token_2)

        # not target
        _update_token_3 = UpdateToken()
        _update_token_3.token_address = _token_address_3
        _update_token_3.issuer_address = _issuer_address
        _update_token_3.type = TokenType.IBET_SHARE
        _update_token_3.arguments = {}
        _update_token_3.status = 1
        _update_token_3.trigger = "Issue"
        db.add(_update_token_3)

        # not target
        _update_token_4 = UpdateToken()
        _update_token_4.token_address = _token_address_4
        _update_token_4.issuer_address = _issuer_address
        _update_token_4.type = TokenType.IBET_SHARE
        _update_token_4.arguments = {}
        _update_token_4.status = 2
        _update_token_4.trigger = "Issue"
        db.add(_update_token_4)

        # Execute batch
        processor.process()

        # assertion(DB)
        _idx_position_list = db.query(IDXPosition).order_by(IDXPosition.id).all()
        assert len(_idx_position_list) == 0

        _token_list = db.query(Token).order_by(Token.id).all()
        _token = _token_list[0]
        assert _token.token_status == 2
        _token = _token_list[1]
        assert _token.token_status == 2

        _update_token_list = db.query(UpdateToken).order_by(UpdateToken.id).all()
        _update_token = _update_token_list[0]
        assert _update_token.status == 2
        _update_token = _update_token_list[1]
        assert _update_token.status == 2
        _update_token = _update_token_list[2]
        assert _update_token.status == 1
        _update_token = _update_token_list[3]
        assert _update_token.status == 2

        _notification_list = db.query(Notification).order_by(Notification.id).all()
        _notification = _notification_list[0]
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.ISSUE_ERROR
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_address": _token_address_1,
            "token_type": TokenType.IBET_SHARE,
            "arguments": {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "issue_price": 1000,
                "total_supply": 10000,
                "dividends": 123.45,
                "dividend_record_date": "20211231",
                "dividend_payment_date": "20211231",
                "cancellation_date": "20221231",
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "image_url": ["image_1"],  # update
                "transferable": False,  # update
                "status": False,  # update
                "offering_status": True,  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test",  # update
                "transfer_approval_required": True,  # update
                "principal_value": 1000,
                "is_canceled": True  # update
            }
        }
        _notification = _notification_list[1]
        assert _notification.id == 2
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _issuer_address
        assert _notification.priority == 1
        assert _notification.type == NotificationType.ISSUE_ERROR
        assert _notification.code == 1
        assert _notification.metainfo == {
            "token_address": _token_address_2,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
            "arguments": {
                "name": "name_test1",
                "symbol": "symbol_test1",
                "total_supply": 2000,
                "face_value": 200,
                "redemption_date": "redemption_date_test1",
                "redemption_value": 4000,
                "return_date": "return_date_test1",
                "return_amount": "return_amount_test1",
                "purpose": "purpose_test1",
                "interest_rate": 0.0001,  # update
                "interest_payment_date": ["0331", "0930"],  # update
                "transferable": False,  # update
                "image_url": ["image_1"],  # update
                "status": False,  # update
                "initial_offering_status": True,  # update
                "is_redeemed": True,  # update
                "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                "contact_information": "contact info test",  # update
                "privacy_policy": "privacy policy test"  # update
            }
        }

    # <Error_3>
    # Issuing: Send transaction error(token update)
    def test_error_3(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test_1"
        _token_address_2 = "token_address_test_2"
        _token_address_3 = "token_address_test_3"  # not target
        _token_address_4 = "token_address_test_4"  # not target

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = _issuer_address
        _token_1.token_address = _token_address_1
        _token_1.abi = ""
        _token_1.token_status = 0
        db.add(_token_1)

        _update_token_1 = UpdateToken()
        _update_token_1.token_address = _token_address_1
        _update_token_1.issuer_address = _issuer_address
        _update_token_1.type = TokenType.IBET_SHARE
        _update_token_1.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "image_url": ["image_1"],  # update
            "transferable": False,  # update
            "status": False,  # update
            "offering_status": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": 1000,
            "is_canceled": True  # update
        }
        _update_token_1.status = 0
        _update_token_1.trigger = "Issue"
        db.add(_update_token_1)

        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = _issuer_address
        _token_2.token_address = _token_address_2
        _token_2.abi = ""
        _token_2.token_status = 0
        db.add(_token_2)

        _update_token_2 = UpdateToken()
        _update_token_2.token_address = _token_address_2
        _update_token_2.issuer_address = _issuer_address
        _update_token_2.type = TokenType.IBET_STRAIGHT_BOND
        _update_token_2.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 2000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        _update_token_2.status = 0
        _update_token_2.trigger = "Issue"
        db.add(_update_token_2)

        # not target
        _update_token_3 = UpdateToken()
        _update_token_3.token_address = _token_address_3
        _update_token_3.issuer_address = _issuer_address
        _update_token_3.type = TokenType.IBET_SHARE
        _update_token_3.arguments = {}
        _update_token_3.status = 1
        _update_token_3.trigger = "Issue"
        db.add(_update_token_3)

        # not target
        _update_token_4 = UpdateToken()
        _update_token_4.token_address = _token_address_4
        _update_token_4.issuer_address = _issuer_address
        _update_token_4.type = TokenType.IBET_SHARE
        _update_token_4.arguments = {}
        _update_token_4.status = 2
        _update_token_4.trigger = "Issue"
        db.add(_update_token_4)

        with patch(target="app.model.blockchain.token.IbetShareContract.update",
                   rside_effect=SendTransactionError()) as IbetShareContract_update, \
                patch(target="app.model.blockchain.token.IbetStraightBondContract.update",
                      side_effect=SendTransactionError()) as IbetStraightBondContract_update:
            # Execute batch
            processor.process()

            # assertion(DB)
            _idx_position_list = db.query(IDXPosition).order_by(IDXPosition.id).all()
            assert len(_idx_position_list) == 0

            _token_list = db.query(Token).order_by(Token.id).all()
            _token = _token_list[0]
            assert _token.token_status == 2
            _token = _token_list[1]
            assert _token.token_status == 2

            _update_token_list = db.query(UpdateToken).order_by(UpdateToken.id).all()
            _update_token = _update_token_list[0]
            assert _update_token.status == 2
            _update_token = _update_token_list[1]
            assert _update_token.status == 2
            _update_token = _update_token_list[2]
            assert _update_token.status == 1
            _update_token = _update_token_list[3]
            assert _update_token.status == 2

            _notification_list = db.query(Notification).order_by(Notification.id).all()
            _notification = _notification_list[0]
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.ISSUE_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "token_address": _token_address_1,
                "token_type": TokenType.IBET_SHARE,
                "arguments": {
                    "name": "name_test1",
                    "symbol": "symbol_test1",
                    "issue_price": 1000,
                    "total_supply": 10000,
                    "dividends": 123.45,
                    "dividend_record_date": "20211231",
                    "dividend_payment_date": "20211231",
                    "cancellation_date": "20221231",
                    "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                    "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                    "image_url": ["image_1"],  # update
                    "transferable": False,  # update
                    "status": False,  # update
                    "offering_status": True,  # update
                    "contact_information": "contact info test",  # update
                    "privacy_policy": "privacy policy test",  # update
                    "transfer_approval_required": True,  # update
                    "principal_value": 1000,
                    "is_canceled": True  # update
                }
            }
            _notification = _notification_list[1]
            assert _notification.id == 2
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.ISSUE_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "token_address": _token_address_2,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
                "arguments": {
                    "name": "name_test1",
                    "symbol": "symbol_test1",
                    "total_supply": 2000,
                    "face_value": 200,
                    "redemption_date": "redemption_date_test1",
                    "redemption_value": 4000,
                    "return_date": "return_date_test1",
                    "return_amount": "return_amount_test1",
                    "purpose": "purpose_test1",
                    "interest_rate": 0.0001,  # update
                    "interest_payment_date": ["0331", "0930"],  # update
                    "transferable": False,  # update
                    "image_url": ["image_1"],  # update
                    "status": False,  # update
                    "initial_offering_status": True,  # update
                    "is_redeemed": True,  # update
                    "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                    "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                    "contact_information": "contact info test",  # update
                    "privacy_policy": "privacy policy test"  # update
                }
            }

    # <Error_4>
    # Issuing: Send transaction error(TokenList register)
    def test_error_4(self, processor, db):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        _keyfile = test_account["keyfile_json"]
        _token_address_1 = "token_address_test_1"
        _token_address_2 = "token_address_test_2"
        _token_address_3 = "token_address_test_3"  # not target
        _token_address_4 = "token_address_test_4"  # not target

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token_1 = Token()
        _token_1.type = TokenType.IBET_SHARE
        _token_1.tx_hash = ""
        _token_1.issuer_address = _issuer_address
        _token_1.token_address = _token_address_1
        _token_1.abi = ""
        _token_1.token_status = 0
        db.add(_token_1)

        _update_token_1 = UpdateToken()
        _update_token_1.token_address = _token_address_1
        _update_token_1.issuer_address = _issuer_address
        _update_token_1.type = TokenType.IBET_SHARE
        _update_token_1.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "issue_price": 1000,
            "total_supply": 10000,
            "dividends": 123.45,
            "dividend_record_date": "20211231",
            "dividend_payment_date": "20211231",
            "cancellation_date": "20221231",
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "image_url": ["image_1"],  # update
            "transferable": False,  # update
            "status": False,  # update
            "offering_status": True,  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test",  # update
            "transfer_approval_required": True,  # update
            "principal_value": 1000,
            "is_canceled": True  # update
        }
        _update_token_1.status = 0
        _update_token_1.trigger = "Issue"
        db.add(_update_token_1)

        _token_2 = Token()
        _token_2.type = TokenType.IBET_STRAIGHT_BOND
        _token_2.tx_hash = ""
        _token_2.issuer_address = _issuer_address
        _token_2.token_address = _token_address_2
        _token_2.abi = ""
        _token_2.token_status = 0
        db.add(_token_2)

        _update_token_2 = UpdateToken()
        _update_token_2.token_address = _token_address_2
        _update_token_2.issuer_address = _issuer_address
        _update_token_2.type = TokenType.IBET_STRAIGHT_BOND
        _update_token_2.arguments = {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "total_supply": 2000,
            "face_value": 200,
            "redemption_date": "redemption_date_test1",
            "redemption_value": 4000,
            "return_date": "return_date_test1",
            "return_amount": "return_amount_test1",
            "purpose": "purpose_test1",
            "interest_rate": 0.0001,  # update
            "interest_payment_date": ["0331", "0930"],  # update
            "transferable": False,  # update
            "image_url": ["image_1"],  # update
            "status": False,  # update
            "initial_offering_status": True,  # update
            "is_redeemed": True,  # update
            "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
            "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
            "contact_information": "contact info test",  # update
            "privacy_policy": "privacy policy test"  # update
        }
        _update_token_2.status = 0
        _update_token_2.trigger = "Issue"
        db.add(_update_token_2)

        # not target
        _update_token_3 = UpdateToken()
        _update_token_3.token_address = _token_address_3
        _update_token_3.issuer_address = _issuer_address
        _update_token_3.type = TokenType.IBET_SHARE
        _update_token_3.arguments = {}
        _update_token_3.status = 1
        _update_token_3.trigger = "Issue"
        db.add(_update_token_3)

        # not target
        _update_token_4 = UpdateToken()
        _update_token_4.token_address = _token_address_4
        _update_token_4.issuer_address = _issuer_address
        _update_token_4.type = TokenType.IBET_SHARE
        _update_token_4.arguments = {}
        _update_token_4.status = 2
        _update_token_4.trigger = "Issue"
        db.add(_update_token_4)

        with patch(target="app.model.blockchain.token.IbetShareContract.update",
                   return_value=None) as IbetShareContract_update, \
                patch(target="app.model.blockchain.token.IbetStraightBondContract.update",
                      return_value=None) as IbetStraightBondContract_update, \
                patch(target="app.model.blockchain.token_list.TokenListContract.register",
                      side_effect=SendTransactionError()) as TokenListContract_register:
            # Execute batch
            processor.process()

            # assertion(contract)
            IbetShareContract_update.assert_called_with(
                contract_address=_token_address_1,
                data=IbetShareUpdate(
                    cancellation_date=None,
                    dividend_record_date=None,
                    dividend_payment_date=None,
                    dividends=None,
                    tradable_exchange_contract_address="0x0000000000000000000000000000000000000001",
                    personal_info_contract_address="0x0000000000000000000000000000000000000002",
                    image_url=["image_1"],
                    transferable=False,
                    status=False,
                    offering_status=True,
                    contact_information="contact info test",
                    privacy_policy="privacy policy test",
                    transfer_approval_required=True,
                    is_canceled=True
                ),
                tx_from=_issuer_address,
                private_key=ANY
            )

            IbetStraightBondContract_update.assert_called_with(
                contract_address=_token_address_2,
                data=IbetStraightBondUpdate(
                    interest_rate=0.0001,
                    interest_payment_date=["0331", "0930"],
                    transferable=False,
                    image_url=["image_1"],
                    status=False,
                    initial_offering_status=True,
                    is_redeemed=True,
                    tradable_exchange_contract_address="0x0000000000000000000000000000000000000001",
                    personal_info_contract_address="0x0000000000000000000000000000000000000002",
                    contact_information="contact info test",
                    privacy_policy="privacy policy test"
                ),
                tx_from=_issuer_address,
                private_key=ANY
            )

            # assertion(DB)
            _idx_position_list = db.query(IDXPosition).order_by(IDXPosition.id).all()
            assert len(_idx_position_list) == 0

            _token_list = db.query(Token).order_by(Token.id).all()
            _token = _token_list[0]
            assert _token.token_status == 2
            _token = _token_list[1]
            assert _token.token_status == 2

            _update_token_list = db.query(UpdateToken).order_by(UpdateToken.id).all()
            _update_token = _update_token_list[0]
            assert _update_token.status == 2
            _update_token = _update_token_list[1]
            assert _update_token.status == 2
            _update_token = _update_token_list[2]
            assert _update_token.status == 1
            _update_token = _update_token_list[3]
            assert _update_token.status == 2

            _notification_list = db.query(Notification).order_by(Notification.id).all()
            _notification = _notification_list[0]
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.ISSUE_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "token_address": _token_address_1,
                "token_type": TokenType.IBET_SHARE,
                "arguments": {
                    "name": "name_test1",
                    "symbol": "symbol_test1",
                    "issue_price": 1000,
                    "total_supply": 10000,
                    "dividends": 123.45,
                    "dividend_record_date": "20211231",
                    "dividend_payment_date": "20211231",
                    "cancellation_date": "20221231",
                    "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                    "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                    "image_url": ["image_1"],  # update
                    "transferable": False,  # update
                    "status": False,  # update
                    "offering_status": True,  # update
                    "contact_information": "contact info test",  # update
                    "privacy_policy": "privacy policy test",  # update
                    "transfer_approval_required": True,  # update
                    "principal_value": 1000,
                    "is_canceled": True  # update
                }
            }
            _notification = _notification_list[1]
            assert _notification.id == 2
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.ISSUE_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "token_address": _token_address_2,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
                "arguments": {
                    "name": "name_test1",
                    "symbol": "symbol_test1",
                    "total_supply": 2000,
                    "face_value": 200,
                    "redemption_date": "redemption_date_test1",
                    "redemption_value": 4000,
                    "return_date": "return_date_test1",
                    "return_amount": "return_amount_test1",
                    "purpose": "purpose_test1",
                    "interest_rate": 0.0001,  # update
                    "interest_payment_date": ["0331", "0930"],  # update
                    "transferable": False,  # update
                    "image_url": ["image_1"],  # update
                    "status": False,  # update
                    "initial_offering_status": True,  # update
                    "is_redeemed": True,  # update
                    "tradable_exchange_contract_address": "0x0000000000000000000000000000000000000001",  # update
                    "personal_info_contract_address": "0x0000000000000000000000000000000000000002",  # update
                    "contact_information": "contact info test",  # update
                    "privacy_policy": "privacy policy test"  # update
                }
            }
