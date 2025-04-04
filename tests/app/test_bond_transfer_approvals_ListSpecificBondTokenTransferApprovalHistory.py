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

from datetime import datetime

import pytest
from pytz import timezone

import config
from app.model.db import (
    IDXPersonalInfo,
    IDXTransferApproval,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
    TransferApprovalHistory,
    TransferApprovalOperationType,
)

local_tz = timezone(config.TZ)


class TestListSpecificBondTokenTransferApprovalHistory:
    # target API endpoint
    base_url = "/bond/transfer_approvals/{}"

    test_transaction_hash = "test_transaction_hash"

    test_issuer_address = "test_issuer_address"
    test_token_address = "test_token_address"
    test_exchange_address = "test_exchange_address"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
    test_application_datetime = datetime(year=2019, month=9, day=1)
    test_application_datetime_str = (
        timezone("UTC")
        .localize(test_application_datetime)
        .astimezone(local_tz)
        .isoformat()
    )
    test_application_datetime_2 = datetime(year=2019, month=10, day=1)
    test_application_datetime_str_2 = (
        timezone("UTC")
        .localize(test_application_datetime_2)
        .astimezone(local_tz)
        .isoformat()
    )
    test_application_blocktimestamp = datetime(year=2019, month=9, day=2)
    test_application_blocktimestamp_str = (
        timezone("UTC")
        .localize(test_application_blocktimestamp)
        .astimezone(local_tz)
        .isoformat()
    )
    test_approval_datetime = datetime(year=2019, month=9, day=3)
    test_approval_datetime_str = (
        timezone("UTC")
        .localize(test_approval_datetime)
        .astimezone(local_tz)
        .isoformat()
    )
    test_approval_datetime_2 = datetime(year=2019, month=10, day=3)
    test_approval_datetime_str_2 = (
        timezone("UTC")
        .localize(test_approval_datetime_2)
        .astimezone(local_tz)
        .isoformat()
    )
    test_approval_blocktimestamp = datetime(year=2019, month=9, day=4)
    test_approval_blocktimestamp_str = (
        timezone("UTC")
        .localize(test_approval_blocktimestamp)
        .astimezone(local_tz)
        .isoformat()
    )
    test_cancellation_blocktimestamp = datetime(year=2019, month=9, day=5)
    test_cancellation_blocktimestamp_str = (
        timezone("UTC")
        .localize(test_cancellation_blocktimestamp)
        .astimezone(local_tz)
        .isoformat()
    )

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # no data
    @pytest.mark.asyncio
    async def test_normal_1_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 0, "offset": None, "limit": None, "total": 0},
            "transfer_approval_history": [],
        }
        assert resp.json() == assumed_response

    # <Normal_1_2>
    # exist data
    @pytest.mark.asyncio
    async def test_normal_1_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = None
            _idx_transfer_approval.approval_blocktimestamp = None
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_approval_history": [
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_2>
    # offset, limit
    @pytest.mark.asyncio
    async def test_normal_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address) + "?offset=1&limit=1"
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": 1, "limit": 1, "total": 3},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_3>
    # set exchange_address
    @pytest.mark.asyncio
    async def test_normal_3(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            if i == 1:
                _idx_transfer_approval.exchange_address = (
                    self.test_exchange_address + "0"
                )
            else:
                _idx_transfer_approval.exchange_address = (
                    self.test_exchange_address + "1"
                )
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_approval_history": [
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address + "1",
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address + "0",
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address + "1",
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_1>
    # filter
    # from_address
    @pytest.mark.asyncio
    async def test_normal_4_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address + str(i)
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"from_address": self.test_from_address + "1"},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address + "1",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_2>
    # filter
    # to_address
    @pytest.mark.asyncio
    async def test_normal_4_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address + str(i)
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"to_address": self.test_to_address + "1"},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 3},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address + "1",
                    "to_address_personal_information": None,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_1>
    # filter
    # status
    # 0: unapproved
    @pytest.mark.asyncio
    async def test_normal_4_3_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 5):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i == 0:  # unapproved
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            elif i == 1:  # escrow_finished
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = None
            elif i == 2:  # transferred_1
                _idx_transfer_approval.exchange_address = "test_exchange_address"
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = True
            elif i == 3:  # transferred_2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = True
            elif i == 4:  # canceled
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = (
                    self.test_cancellation_blocktimestamp
                )
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"status": 0}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 5},
            "transfer_approval_history": [
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_2>
    # filter
    # status
    # 1: escrow_finished
    @pytest.mark.asyncio
    async def test_normal_4_3_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 5):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i == 0:  # unapproved
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            elif i == 1:  # escrow_finished
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = None
            elif i == 2:  # transferred_1
                _idx_transfer_approval.exchange_address = "test_exchange_address"
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = True
            elif i == 3:  # transferred_2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = True
            elif i == 4:  # canceled
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = (
                    self.test_cancellation_blocktimestamp
                )
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"status": 1}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 1, "offset": None, "limit": None, "total": 5},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 1,
                    "issuer_cancelable": True,
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_3>
    # filter
    # status
    # 2: transferred
    @pytest.mark.asyncio
    async def test_normal_4_3_3(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXTransferApproval
        for i in range(0, 7):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i == 0:  # unapproved
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            elif i == 1:  # escrow_finished
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = None
            elif i == 2:  # transferred_1
                _idx_transfer_approval.exchange_address = "test_exchange_address"
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = True
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.approval_blocktimestamp = (
                    self.test_approval_blocktimestamp
                )
            elif i == 3:  # transferred_2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
                _transfer_approval_history = TransferApprovalHistory()
                _transfer_approval_history.token_address = self.test_token_address
                _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
                _transfer_approval_history.application_id = i
                _transfer_approval_history.operation_type = (
                    TransferApprovalOperationType.APPROVE
                )
                _transfer_approval_history.from_address_personal_info = {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                _transfer_approval_history.to_address_personal_info = {
                    "key_manager": "key_manager_test2",
                    "name": "name_test2",
                    "postal_code": "postal_code_test2",
                    "address": "address_test2",
                    "email": "email_test2",
                    "birth": "birth_test2",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                async_db.add(_transfer_approval_history)
            elif i == 4:  # transferred_3
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = True
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.approval_blocktimestamp = (
                    self.test_approval_blocktimestamp
                )
            elif i == 5:  # canceled-1
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
                _transfer_approval_history = TransferApprovalHistory()
                _transfer_approval_history.token_address = self.test_token_address
                _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
                _transfer_approval_history.application_id = i
                _transfer_approval_history.operation_type = (
                    TransferApprovalOperationType.CANCEL
                )
                _transfer_approval_history.from_address_personal_info = {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                _transfer_approval_history.to_address_personal_info = {
                    "key_manager": "key_manager_test2",
                    "name": "name_test2",
                    "postal_code": "postal_code_test2",
                    "address": "address_test2",
                    "email": "email_test2",
                    "birth": "birth_test2",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                async_db.add(_transfer_approval_history)
            elif i == 6:  # canceled-2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = (
                    self.test_cancellation_blocktimestamp
                )
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"status": 2}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 7},
            "transfer_approval_history": [
                {
                    "id": 5,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 4,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": None,
                    "amount": 4,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": True,
                    "status": 2,
                    "issuer_cancelable": True,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": True,
                    "status": 2,
                    "issuer_cancelable": True,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": "test_exchange_address",
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": None,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": True,
                    "transfer_approved": True,
                    "status": 2,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_4>
    # filter
    # status
    # 3: canceled
    @pytest.mark.asyncio
    async def test_normal_4_3_4(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 6):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i == 0:  # unapproved
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            elif i == 1:  # escrow_finished
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = None
            elif i == 2:  # transferred_1
                _idx_transfer_approval.exchange_address = "test_exchange_address"
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = True
            elif i == 3:  # transferred_2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = True
            elif i == 4:  # canceled-1
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
                _transfer_approval_history = TransferApprovalHistory()
                _transfer_approval_history.token_address = self.test_token_address
                _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
                _transfer_approval_history.application_id = i
                _transfer_approval_history.operation_type = (
                    TransferApprovalOperationType.CANCEL
                )
                _transfer_approval_history.from_address_personal_info = {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                _transfer_approval_history.to_address_personal_info = {
                    "key_manager": "key_manager_test2",
                    "name": "name_test2",
                    "postal_code": "postal_code_test2",
                    "address": "address_test2",
                    "email": "email_test2",
                    "birth": "birth_test2",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                async_db.add(_transfer_approval_history)
            elif i == 5:  # canceled-2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = (
                    self.test_cancellation_blocktimestamp
                )
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None

            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"status": 3}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 6},
            "transfer_approval_history": [
                {
                    "id": 6,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 5,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 5,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": self.test_cancellation_blocktimestamp_str,
                    "cancelled": True,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 3,
                    "issuer_cancelable": True,
                },
                {
                    "id": 5,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 4,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test1",
                        "birth": "birth_test1",
                        "email": "email_test1",
                        "is_corporate": False,
                        "key_manager": "key_manager_test1",
                        "name": "name_test1",
                        "postal_code": "postal_code_test1",
                        "tax_category": 10,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test2",
                        "birth": "birth_test2",
                        "email": "email_test2",
                        "is_corporate": False,
                        "key_manager": "key_manager_test2",
                        "name": "name_test2",
                        "postal_code": "postal_code_test2",
                        "tax_category": 10,
                    },
                    "amount": 4,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": True,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 3,
                    "issuer_cancelable": True,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_4_3_5>
    # filter
    # status
    # multi specify
    @pytest.mark.asyncio
    async def test_normal_4_3_5(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 7):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i == 0:  # unapproved
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            elif i == 1:  # escrow_finished
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = None
            elif i == 2:  # transferred_1
                _idx_transfer_approval.exchange_address = "test_exchange_address"
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = True
            elif i == 3:  # transferred_2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
                _transfer_approval_history = TransferApprovalHistory()
                _transfer_approval_history.token_address = self.test_token_address
                _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
                _transfer_approval_history.application_id = i
                _transfer_approval_history.operation_type = (
                    TransferApprovalOperationType.APPROVE
                )
                _transfer_approval_history.from_address_personal_info = {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                _transfer_approval_history.to_address_personal_info = {
                    "key_manager": "key_manager_test2",
                    "name": "name_test2",
                    "postal_code": "postal_code_test2",
                    "address": "address_test2",
                    "email": "email_test2",
                    "birth": "birth_test2",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                async_db.add(_transfer_approval_history)
            elif i == 4:  # transferred_3
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = True
            elif i == 5:  # canceled-1
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
                _transfer_approval_history = TransferApprovalHistory()
                _transfer_approval_history.token_address = self.test_token_address
                _transfer_approval_history.exchange_address = config.ZERO_ADDRESS
                _transfer_approval_history.application_id = i
                _transfer_approval_history.operation_type = (
                    TransferApprovalOperationType.CANCEL
                )
                _transfer_approval_history.from_address_personal_info = {
                    "key_manager": "key_manager_test1",
                    "name": "name_test1",
                    "postal_code": "postal_code_test1",
                    "address": "address_test1",
                    "email": "email_test1",
                    "birth": "birth_test1",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                _transfer_approval_history.to_address_personal_info = {
                    "key_manager": "key_manager_test2",
                    "name": "name_test2",
                    "postal_code": "postal_code_test2",
                    "address": "address_test2",
                    "email": "email_test2",
                    "birth": "birth_test2",
                    "is_corporate": False,
                    "tax_category": 10,
                }  # snapshot
                async_db.add(_transfer_approval_history)
            elif i == 6:  # canceled-2
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = (
                    self.test_cancellation_blocktimestamp
                )
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address), params={"status": [0, 1]}
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 2, "offset": None, "limit": None, "total": 7},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 1,
                    "issuer_cancelable": True,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_1>
    # sort
    # id
    @pytest.mark.asyncio
    async def test_normal_5_1(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 3):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "id", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 3},
            "transfer_approval_history": [
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_2>
    # sort
    # exchange_address
    @pytest.mark.asyncio
    async def test_normal_5_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            if i % 2 == 0:
                _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "exchange_address", "sort_order": 1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_3>
    # sort
    # application_id
    @pytest.mark.asyncio
    async def test_normal_5_3(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            if i % 2 == 0:
                _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = int(i / 2)
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "application_id", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_4>
    # sort
    # from_address
    @pytest.mark.asyncio
    async def test_normal_5_4(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address + str(
                int((3 - i) / 2)
            )
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "from_address", "sort_order": 1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address + "1",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address + "1",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 3,
                    "from_address": self.test_from_address + "0",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address + "0",
                    "from_address_personal_information": None,
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_5>
    # sort
    # to_address
    @pytest.mark.asyncio
    async def test_normal_5_5(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address + str(int(i / 2))
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "to_address", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address + "0",
                    "to_address_personal_information": None,
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address + "0",
                    "to_address_personal_information": None,
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address + "1",
                    "to_address_personal_information": None,
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address + "1",
                    "to_address_personal_information": None,
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_6>
    # sort
    # amount
    @pytest.mark.asyncio
    async def test_normal_5_6(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = int((3 - i) / 2)
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "amount", "sort_order": 1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_7>
    # sort
    # application_datetime
    @pytest.mark.asyncio
    async def test_normal_5_7(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            if i % 2 == 0:
                _idx_transfer_approval.application_datetime = (
                    self.test_application_datetime
                )
            else:
                _idx_transfer_approval.application_datetime = (
                    self.test_application_datetime_2
                )
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "application_datetime", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str_2,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str_2,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_8>
    # sort
    # approval_datetime
    @pytest.mark.asyncio
    async def test_normal_5_8(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 4):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.exchange_address = self.test_exchange_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i % 2 == 0:
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
            else:
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime_2
            _idx_transfer_approval.approval_blocktimestamp = (
                self.test_approval_blocktimestamp
            )
            _idx_transfer_approval.cancellation_blocktimestamp = None
            _idx_transfer_approval.cancelled = False
            _idx_transfer_approval.transfer_approved = False
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "approval_datetime", "sort_order": 1},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 4, "offset": None, "limit": None, "total": 4},
            "transfer_approval_history": [
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str_2,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str_2,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": self.test_exchange_address,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": False,
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Normal_5_9>
    # sort
    # status
    @pytest.mark.asyncio
    async def test_normal_5_9(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        # prepare data: IDXPersonalInfo
        _from_personal_info = IDXPersonalInfo()
        _from_personal_info.account_address = self.test_from_address
        _from_personal_info.issuer_address = self.test_issuer_address
        _from_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _from_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_from_personal_info)

        # prepare data: IDXPersonalInfo
        _to_personal_info = IDXPersonalInfo()
        _to_personal_info.account_address = self.test_to_address
        _to_personal_info.issuer_address = self.test_issuer_address
        _to_personal_info._personal_info = {
            "key_manager": "key_manager_test",
            "name": "name_test",
            "postal_code": "postal_code_test",
            "address": "address_test",
            "email": "email_test",
            "birth": "birth_test",
            "is_corporate": False,
        }
        _to_personal_info.data_source = PersonalInfoDataSource.ON_CHAIN
        async_db.add(_to_personal_info)

        # prepare data: IDXTransferApproval
        for i in range(0, 8):
            _idx_transfer_approval = IDXTransferApproval()
            _idx_transfer_approval.token_address = self.test_token_address
            _idx_transfer_approval.application_id = i
            _idx_transfer_approval.from_address = self.test_from_address
            _idx_transfer_approval.to_address = self.test_to_address
            _idx_transfer_approval.amount = i
            _idx_transfer_approval.application_datetime = self.test_application_datetime
            _idx_transfer_approval.application_blocktimestamp = (
                self.test_application_blocktimestamp
            )
            if i == 0 or i == 1:
                # unapproved
                _idx_transfer_approval.approval_datetime = None
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            elif i == 2 or i == 3:
                # escrow_finished
                _idx_transfer_approval.approval_datetime = None
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = True
                _idx_transfer_approval.transfer_approved = None
            elif i == 4 or i == 5:
                # transferred
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = None
                _idx_transfer_approval.cancelled = None
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = True
                _idx_transfer_approval.approval_datetime = self.test_approval_datetime
                _idx_transfer_approval.approval_blocktimestamp = (
                    self.test_approval_blocktimestamp
                )
            else:
                # canceled
                _idx_transfer_approval.approval_datetime = None
                _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
                _idx_transfer_approval.cancellation_blocktimestamp = (
                    self.test_cancellation_blocktimestamp
                )
                _idx_transfer_approval.cancelled = True
                _idx_transfer_approval.escrow_finished = None
                _idx_transfer_approval.transfer_approved = None
            async_db.add(_idx_transfer_approval)

        await async_db.commit()

        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={"sort_item": "status", "sort_order": 0},
        )

        # assertion
        assert resp.status_code == 200
        assumed_response = {
            "result_set": {"count": 8, "offset": None, "limit": None, "total": 8},
            "transfer_approval_history": [
                {
                    "id": 2,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 1,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 1,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 1,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 0,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 0,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 0,
                    "issuer_cancelable": True,
                },
                {
                    "id": 4,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 3,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 3,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 1,
                    "issuer_cancelable": True,
                },
                {
                    "id": 3,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 2,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 2,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 1,
                    "issuer_cancelable": True,
                },
                {
                    "id": 6,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 5,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 5,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": True,
                    "status": 2,
                    "issuer_cancelable": True,
                },
                {
                    "id": 5,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 4,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 4,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": self.test_approval_datetime_str,
                    "approval_blocktimestamp": self.test_approval_blocktimestamp_str,
                    "cancellation_blocktimestamp": None,
                    "cancelled": False,
                    "escrow_finished": False,
                    "transfer_approved": True,
                    "status": 2,
                    "issuer_cancelable": True,
                },
                {
                    "id": 8,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 7,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 7,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": self.test_cancellation_blocktimestamp_str,
                    "cancelled": True,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 3,
                    "issuer_cancelable": True,
                },
                {
                    "id": 7,
                    "token_address": self.test_token_address,
                    "exchange_address": config.ZERO_ADDRESS,
                    "application_id": 6,
                    "from_address": self.test_from_address,
                    "from_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "to_address": self.test_to_address,
                    "to_address_personal_information": {
                        "address": "address_test",
                        "birth": "birth_test",
                        "email": "email_test",
                        "is_corporate": False,
                        "key_manager": "key_manager_test",
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "tax_category": None,
                    },
                    "amount": 6,
                    "application_datetime": self.test_application_datetime_str,
                    "application_blocktimestamp": self.test_application_blocktimestamp_str,
                    "approval_datetime": None,
                    "approval_blocktimestamp": None,
                    "cancellation_blocktimestamp": self.test_cancellation_blocktimestamp_str,
                    "cancelled": True,
                    "escrow_finished": False,
                    "transfer_approved": False,
                    "status": 3,
                    "issuer_cancelable": True,
                },
            ],
        }
        assert resp.json() == assumed_response

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # validation error
    # type_error
    @pytest.mark.asyncio
    async def test_error_1_1(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "status": ["a"],
                "offset": "c",
                "limit": "d",
            },
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "int_parsing",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "c",
                },
                {
                    "type": "int_parsing",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "d",
                },
                {
                    "type": "enum",
                    "loc": ["query", "status", 0],
                    "msg": "Input should be 0, 1, 2 or 3",
                    "input": "a",
                    "ctx": {"expected": "0, 1, 2 or 3"},
                },
            ],
        }
        assert resp.json() == assumed_response

    # <Error_1_2>
    # validation error
    # min value
    @pytest.mark.asyncio
    async def test_error_1_2(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "status": -1,
            },
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "0, 1, 2 or 3"},
                    "input": "-1",
                    "loc": ["query", "status", 0],
                    "msg": "Input should be 0, 1, 2 or 3",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Error_1_3>
    # validation error
    # max value
    @pytest.mark.asyncio
    async def test_error_1_3(self, async_client, async_db):
        # request target API
        resp = await async_client.get(
            self.base_url.format(self.test_token_address),
            params={
                "status": 4,
            },
        )

        # assertion
        assert resp.status_code == 422
        assumed_response = {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "0, 1, 2 or 3"},
                    "input": "4",
                    "loc": ["query", "status", 0],
                    "msg": "Input should be 0, 1, 2 or 3",
                    "type": "enum",
                }
            ],
        }
        assert resp.json() == assumed_response

    # <Error_2>
    # token not found
    @pytest.mark.asyncio
    async def test_error_1(self, async_client, async_db):
        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 404
        assumed_response = {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
        }
        assert resp.json() == assumed_response

    # <Error_3>
    # processing token
    @pytest.mark.asyncio
    async def test_error_2(self, async_client, async_db):
        # prepare data: Token
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = self.test_issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_25_06
        async_db.add(_token)

        await async_db.commit()

        # request target API
        resp = await async_client.get(self.base_url.format(self.test_token_address))

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
        }
