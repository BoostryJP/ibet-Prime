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

from sqlalchemy import select

from app.model.db import TokenHolderExtraInfo
from tests.app.utils.generate_signature import generate_sealed_tx_signature


class TestSealedTxRegisterHolderExtraInfo:
    test_token_address = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"

    test_account_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    test_account_pk = "0000000000000000000000000000000000000000000000000000000000000001"

    # Target API endpoint
    url = "/sealed_tx/holder_extra_info"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # Register token holder's extra information
    def test_normal_1(self, client, db):
        # Derive a signature
        _params = {
            "token_address": self.test_token_address,
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        extra_info = db.scalars(select(TokenHolderExtraInfo).limit(1)).first()
        assert extra_info.json() == {
            "token_address": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
            "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }

    # <Normal_2>
    # Optional input parameters
    def test_normal_2(self, client, db):
        # Derive a signature
        _params = {
            "token_address": self.test_token_address,
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        extra_info = db.scalars(select(TokenHolderExtraInfo).limit(1)).first()
        assert extra_info.json() == {
            "token_address": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
            "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
            "external_id_1_type": None,
            "external_id_1": None,
            "external_id_2_type": None,
            "external_id_2": None,
            "external_id_3_type": None,
            "external_id_3": None,
        }

    # <Normal_3>
    # Overwrite the already registered data
    def test_normal_3(self, client, db):
        extra_info_bf = TokenHolderExtraInfo()
        extra_info_bf.token_address = self.test_token_address
        extra_info_bf.account_address = self.test_account_address
        extra_info_bf.external_id_1_type = "test_id_type_1_bf"
        extra_info_bf.external_id_1 = "test_id_1_bf"
        extra_info_bf.external_id_2_type = "test_id_type_2_bf"
        extra_info_bf.external_id_2 = "test_id_2_bf"
        extra_info_bf.external_id_3_type = "test_id_type_3_bf"
        extra_info_bf.external_id_3 = "test_id_3_bf"
        db.add(extra_info_bf)
        db.commit()

        # Derive a signature
        _params = {
            "token_address": self.test_token_address,
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        extra_info = db.scalars(select(TokenHolderExtraInfo).limit(1)).first()
        assert extra_info.json() == {
            "token_address": "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
            "account_address": "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf",
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # - Missing X-SealedTx-Signature header
    def test_error_1(self, client, db):
        _params = {
            "token_address": self.test_token_address,
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }

        # Call API
        resp = client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "X-SealedTx-Signature"],
                    "msg": "Field required",
                    "input": None,
                }
            ],
        }

    # <Error_2>
    # RequestValidationError
    # - Missing required field: token_address
    def test_error_2(self, client, db):
        # Derive a signature
        _params = {
            "external_id_1_type": "test_id_type_1",
            "external_id_1": "test_id_1",
            "external_id_2_type": "test_id_type_2",
            "external_id_2": "test_id_2",
            "external_id_3_type": "test_id_type_3",
            "external_id_3": "test_id_3",
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "token_address"],
                    "msg": "Field required",
                    "input": {
                        "external_id_1_type": "test_id_type_1",
                        "external_id_1": "test_id_1",
                        "external_id_2_type": "test_id_type_2",
                        "external_id_2": "test_id_2",
                        "external_id_3_type": "test_id_type_3",
                        "external_id_3": "test_id_3",
                    },
                }
            ],
        }

    # <Error_3>
    # RequestValidationError
    # - external_id: string_too_long
    def test_error_3(self, client, db):
        # Derive a signature
        _params = {
            "token_address": self.test_token_address,
            "external_id_1_type": "a" * 51,
            "external_id_1": "a" * 51,
            "external_id_2_type": "a" * 51,
            "external_id_2": "a" * 51,
            "external_id_3_type": "a" * 51,
            "external_id_3": "a" * 51,
        }
        _sealed_tx_sig = generate_sealed_tx_signature(
            "POST",
            self.url,
            private_key=self.test_account_pk,
            json=_params,
        )

        # Call API
        resp = client.post(
            self.url,
            json=_params,
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": _sealed_tx_sig,
            },
        )

        # Assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_1_type"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_1"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_2_type"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_2"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_3_type"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
                {
                    "type": "string_too_long",
                    "loc": ["body", "external_id_3"],
                    "msg": "String should have at most 50 characters",
                    "input": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "ctx": {"max_length": 50},
                },
            ],
        }
