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
from datetime import datetime
from unittest.mock import ANY

from _decimal import Decimal
from eth_keyfile import decode_keyfile_json
from pytz import timezone
from starlette.testclient import TestClient
from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware

import config
from app.model.blockchain import IbetStraightBondContract
from app.model.db import (
    Account,
    Token,
    TokenType,
    TokenUpdateOperationCategory,
    TokenUpdateOperationLog,
)
from app.model.schema import IbetStraightBondCreate
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def deploy_bond_token_contract(
    session,
    address,
    private_key,
    personal_info_contract_address,
    tradable_exchange_contract_address=config.ZERO_ADDRESS,
    transfer_approval_required=True,
    created: datetime | None = None,
) -> (Contract, dict):
    arguments = [
        "token.name",  # name
        "token.symbol",  # symbol
        100,  # total_supply
        20,  # face_value
        "20230501",  # redemption_date
        30,  # redemption_value
        "20230501",  # return_date
        "token.return_amount",  # return_amount
        "token.purpose",  # purpose
    ]
    bond_contrat = IbetStraightBondContract()
    token_address, _, _ = bond_contrat.create(arguments, address, private_key)
    contract = ContractUtils.get_contract("IbetStraightBond", token_address)
    token_create_param = IbetStraightBondCreate(
        name="token.name",
        total_supply=100,
        face_value=20,
        purpose="token.purpose",
        symbol="token.symbol",
        redemption_date="20230501",
        redemption_value=30,
        return_date="20230501",
        return_amount="token.return_amount",
        interest_rate=0.0001,  # update
        interest_payment_date=["0331", "0930"],  # update
        transferable=True,  # update
        is_redeemed=False,
        status=False,  # update
        is_offering=True,  # update
        tradable_exchange_contract_address=tradable_exchange_contract_address,  # update
        personal_info_contract_address=personal_info_contract_address,  # update
        image_url=None,
        contact_information="contact info test",  # update
        privacy_policy="privacy policy test",  # update
        transfer_approval_required=transfer_approval_required,  # update
        face_value_currency="JPY",  # update
        redemption_value_currency="JPY",  # update
        interest_payment_currency="JPY",  # update
        base_fx_rate=123.456789,  # update
    ).__dict__

    token_create_param.pop("image_url")
    token_update_operation_log = TokenUpdateOperationLog()
    token_update_operation_log.issuer_address = address
    token_update_operation_log.token_address = token_address
    token_update_operation_log.type = TokenType.IBET_STRAIGHT_BOND.value
    token_update_operation_log.issuer_address = address
    token_update_operation_log.arguments = token_create_param
    token_update_operation_log.original_contents = None
    token_update_operation_log.operation_category = (
        TokenUpdateOperationCategory.ISSUE.value
    )
    if created:
        token_update_operation_log.created = created
    session.add(token_update_operation_log)

    build_tx_param = {
        "chainId": config.CHAIN_ID,
        "from": address,
        "gas": config.TX_GAS_LIMIT,
        "gasPrice": 0,
    }
    tx = contract.functions.setInterestRate(
        int(Decimal(str(token_create_param["interest_rate"])) * Decimal("10000"))
    ).build_transaction(build_tx_param)
    _interest_payment_date = {}
    for i, item in enumerate(token_create_param["interest_payment_date"]):
        _interest_payment_date[f"interestPaymentDate{i + 1}"] = item
    _interest_payment_date_string = json.dumps(_interest_payment_date)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setInterestPaymentDate(
        _interest_payment_date_string
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setTransferable(
        token_create_param["transferable"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setStatus(token_create_param["status"]).build_transaction(
        build_tx_param
    )
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.changeOfferingStatus(
        token_create_param["is_offering"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setTradableExchange(
        token_create_param["tradable_exchange_contract_address"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setPersonalInfoAddress(
        token_create_param["personal_info_contract_address"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setContactInformation(
        token_create_param["contact_information"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setPrivacyPolicy(
        token_create_param["privacy_policy"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setTransferApprovalRequired(
        token_create_param["transfer_approval_required"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setFaceValueCurrency(
        token_create_param["face_value_currency"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setInterestPaymentCurrency(
        token_create_param["interest_payment_currency"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setRedemptionValueCurrency(
        token_create_param["redemption_value_currency"]
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)
    tx = contract.functions.setBaseFXRate(
        str(token_create_param["base_fx_rate"])
    ).build_transaction(build_tx_param)
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    return contract, token_create_param


class TestAppRoutersBondTokensTokenAddressHistoryGET:
    # target API endpoint
    base_url = "/bond/tokens/{}/history"

    @staticmethod
    def create_history_by_api(
        client: TestClient, token_address: str, issuer_address: str
    ):
        client.post(
            f"/bond/tokens/{token_address}",
            json={"face_value": 10000, "memo": None},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )
        client.post(
            f"/bond/tokens/{token_address}",
            json={"interest_rate": 0.5, "memo": None},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )
        client.post(
            f"/bond/tokens/{token_address}",
            json={"interest_payment_date": ["0101", "0701"], "memo": None},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

    @staticmethod
    def expected_original_after_issue(
        create_token_param: dict, issuer_address: str, token_address: str
    ):
        interest_payment_date = [
            create_token_param["interest_payment_date"][i]
            if len(create_token_param["interest_payment_date"]) > i
            else ""
            for i in range(12)
        ]

        return {
            **create_token_param,
            "contract_name": "IbetStraightBond",
            "interest_payment_date": interest_payment_date,
            "issuer_address": issuer_address,
            "memo": "",
            "token_address": token_address,
        }

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    def test_normal_1(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # prepare data: Token
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = "no_record_address"
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)

        # request target api
        resp = client.get(
            self.base_url.format(_token.token_address),
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 0,
                "offset": None,
                "limit": None,
                "total": 0,
            },
            "history": [],
        }

    # <Normal_2>
    # Multiple record
    def test_normal_2(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
        )
        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_1>
    # Search filter: trigger
    def test_normal_3_1(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "operation_category": "Update",
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 3,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_2>
    # Search filter: modified_contents
    def test_normal_3_2(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "modified_contents": "face_value",
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_3>
    # Search filter: created_from
    def test_normal_3_3(self, client, db, personal_info_contract, monkeypatch):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db,
            _issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            created=datetime(2023, 5, 1, tzinfo=timezone("UTC")),
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)

        _operation_log_1 = TokenUpdateOperationLog()
        _operation_log_1.created = datetime(2023, 5, 2, tzinfo=timezone("UTC"))
        _operation_log_1.issuer_address = _issuer_address
        _operation_log_1.token_address = _token_address
        _operation_log_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _operation_log_1.arguments = {"memo": "20230502"}
        _operation_log_1.original_contents = {}
        _operation_log_1.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db.add(_operation_log_1)
        _operation_log_2 = TokenUpdateOperationLog()
        _operation_log_2.created = datetime(2023, 5, 3, tzinfo=timezone("UTC"))
        _operation_log_2.issuer_address = _issuer_address
        _operation_log_2.token_address = _token_address
        _operation_log_2.type = TokenType.IBET_STRAIGHT_BOND.value
        _operation_log_2.arguments = {"memo": "20230503"}
        _operation_log_2.original_contents = {}
        _operation_log_2.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db.add(_operation_log_2)
        _operation_log_3 = TokenUpdateOperationLog()
        _operation_log_3.created = datetime(2023, 5, 4, tzinfo=timezone("UTC"))
        _operation_log_3.issuer_address = _issuer_address
        _operation_log_3.token_address = _token_address
        _operation_log_3.type = TokenType.IBET_STRAIGHT_BOND.value
        _operation_log_3.arguments = {"memo": "20230504"}
        _operation_log_3.original_contents = {}
        _operation_log_3.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db.add(_operation_log_3)
        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "created_from": str(datetime(2023, 5, 3, 8, 0, 0)),
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 2,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {},
                    "modified_contents": {"memo": "20230504"},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {},
                    "modified_contents": {"memo": "20230503"},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_3_4>
    # Search filter: created_to
    def test_normal_3_4(self, client, db, personal_info_contract, monkeypatch):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db,
            _issuer_address,
            issuer_private_key,
            personal_info_contract.address,
            created=datetime(2023, 5, 1, tzinfo=timezone("UTC")),
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)

        _operation_log_1 = TokenUpdateOperationLog()
        _operation_log_1.created = datetime(2023, 5, 2, tzinfo=timezone("UTC"))
        _operation_log_1.issuer_address = _issuer_address
        _operation_log_1.token_address = _token_address
        _operation_log_1.type = TokenType.IBET_STRAIGHT_BOND.value
        _operation_log_1.arguments = {"memo": "20230502"}
        _operation_log_1.original_contents = {}
        _operation_log_1.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db.add(_operation_log_1)
        _operation_log_2 = TokenUpdateOperationLog()
        _operation_log_2.created = datetime(2023, 5, 3, tzinfo=timezone("UTC"))
        _operation_log_2.issuer_address = _issuer_address
        _operation_log_2.token_address = _token_address
        _operation_log_2.type = TokenType.IBET_STRAIGHT_BOND.value
        _operation_log_2.arguments = {"memo": "20230503"}
        _operation_log_2.original_contents = {}
        _operation_log_2.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db.add(_operation_log_2)
        _operation_log_3 = TokenUpdateOperationLog()
        _operation_log_3.created = datetime(2023, 5, 4, tzinfo=timezone("UTC"))
        _operation_log_3.issuer_address = _issuer_address
        _operation_log_3.token_address = _token_address
        _operation_log_3.type = TokenType.IBET_STRAIGHT_BOND.value
        _operation_log_3.arguments = {"memo": "20230504"}
        _operation_log_3.original_contents = {}
        _operation_log_3.operation_category = TokenUpdateOperationCategory.UPDATE.value
        db.add(_operation_log_3)
        db.commit()

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "created_to": str(datetime(2023, 5, 2, 0, 0, 0)),
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_4_1>
    # Sort Order
    def test_normal_4_1(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "sort_order": 0,
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE.value,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_4_2>
    # Sort Item
    def test_normal_4_2(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "sort_order": 0,
                "sort_item": "operation_category",
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": None,
                    "modified_contents": create_param,
                    "operation_category": TokenUpdateOperationCategory.ISSUE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                        **{"interest_rate": 0.5},
                    },
                    "modified_contents": {"interest_payment_date": ["0101", "0701"]},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_5_1>
    # Pagination
    def test_normal_5_1(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "limit": 2,
                "offset": 1,
            },
        )

        original_after_issue = self.expected_original_after_issue(
            create_param, _issuer_address, _token_address
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": 1,
                "limit": 2,
                "total": 4,
            },
            "history": [
                {
                    "original_contents": {
                        **original_after_issue,
                        **{"face_value": 10000},
                    },
                    "modified_contents": {"interest_rate": 0.5},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
                {
                    "original_contents": original_after_issue,
                    "modified_contents": {"face_value": 10000},
                    "operation_category": TokenUpdateOperationCategory.UPDATE.value,
                    "created": ANY,
                },
            ],
        }

    # <Normal_5_2>
    # Pagination (over offset)
    def test_normal_5_2(self, client, db, personal_info_contract):
        test_account = config_eth_account("user1")
        _issuer_address = test_account["address"]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=test_account["keyfile_json"],
            password="password".encode("utf-8"),
        )
        _keyfile = test_account["keyfile_json"]

        # Prepare data : Token
        token_contract, create_param = deploy_bond_token_contract(
            db, _issuer_address, issuer_private_key, personal_info_contract.address
        )
        _token_address = token_contract.address

        # prepare data
        account = Account()
        account.issuer_address = _issuer_address
        account.keyfile = _keyfile
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.token_address = token_contract.address
        _token.issuer_address = _issuer_address
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = ""
        _token.abi = ""
        db.add(_token)
        db.commit()

        # create history
        self.create_history_by_api(client, _token_address, _issuer_address)

        # request target API
        resp = client.get(
            self.base_url.format(_token_address),
            params={
                "limit": 1,
                "offset": 4,
            },
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "result_set": {
                "count": 4,
                "offset": 4,
                "limit": 1,
                "total": 4,
            },
            "history": [],
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # query(invalid value)
    def test_error_1(self, client, db):
        token_address = "0x0123456789012345678901234567890123456789"

        # request target api
        resp = client.get(
            self.base_url.format(token_address),
            params={
                "operation_category": "test",
                "sort_order": "test",
                "sort_item": "test",
                "offset": "test",
                "limit": "test",
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "'Issue' or 'Update'"},
                    "input": "test",
                    "loc": ["query", "operation_category"],
                    "msg": "Input should be 'Issue' or 'Update'",
                    "type": "enum",
                },
                {
                    "ctx": {"expected": "'created' or 'operation_category'"},
                    "input": "test",
                    "loc": ["query", "sort_item"],
                    "msg": "Input should be 'created' or 'operation_category'",
                    "type": "enum",
                },
                {
                    "input": "test",
                    "loc": ["query", "sort_order"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse string "
                    "as an integer",
                    "type": "int_parsing",
                },
            ],
        }
