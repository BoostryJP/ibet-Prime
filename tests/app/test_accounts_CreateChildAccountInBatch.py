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

import secrets

from coincurve import PublicKey
from eth_utils import keccak, to_checksum_address
from sqlalchemy import select

from app.model.db import (
    Account,
    ChildAccountIndex,
    TmpChildAccountBatchCreate,
)


class TestCreateChildAccountInBatch:
    sk_1 = secrets.token_bytes(32)
    pk_1 = PublicKey.from_valid_secret(sk_1)

    issuer_pub_key = pk_1.format().hex()
    issuer_address = to_checksum_address(
        keccak(pk_1.format(compressed=False)[1:])[-20:]
    )

    # Target API endpoint
    base_url = "/accounts/{}/child_accounts/batch"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Successfully generated the child key
    def test_normal_1_1(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 1
        db.add(_child_index)

        db.commit()

        _personal_info_list = []
        for i in range(10):
            _personal_info = {
                "name": f"name_test_{i}",
                "postal_code": f"postal_code_test_{i}",
                "address": f"address_test_{i}",
                "email": f"email_test_{i}",
                "birth": f"birth_test_{i}",
                "is_corporate": False,
                "tax_category": i,
            }
            _personal_info_list.append(_personal_info)

        # Call API
        resp = client.post(
            self.base_url.format(self.issuer_address),
            json={"personal_information_list": _personal_info_list},
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {
            "child_account_index_list": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        }

        _child_account = db.scalars(
            select(TmpChildAccountBatchCreate).where(
                TmpChildAccountBatchCreate.issuer_address == self.issuer_address
            )
        ).all()
        assert len(_child_account) == 10
        for i in range(10):
            assert _child_account[i].issuer_address == self.issuer_address
            assert _child_account[i].child_account_index == i + 1
            _personal_info = _personal_info_list[i]
            _personal_info["key_manager"] = "SELF"
            assert _child_account[i].personal_info == _personal_info

        _child_index = db.scalars(
            select(ChildAccountIndex)
            .where(ChildAccountIndex.issuer_address == self.issuer_address)
            .limit(1)
        ).first()
        assert _child_index.next_index == 11

    # <Normal_1_2>
    # Personal information is blank
    def test_normal_1_2(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 1
        db.add(_child_index)

        db.commit()

        # Call API
        resp = client.post(
            self.base_url.format(self.issuer_address),
            json={"personal_information_list": [{}]},
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() == {"child_account_index_list": [1]}

        _child_account = db.scalars(
            select(TmpChildAccountBatchCreate).where(
                TmpChildAccountBatchCreate.issuer_address == self.issuer_address
            )
        ).all()
        assert len(_child_account) == 1
        assert _child_account[0].issuer_address == self.issuer_address
        assert _child_account[0].child_account_index == 1
        assert _child_account[0].personal_info == {
            "key_manager": "SELF",
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }

        _child_index = db.scalars(
            select(ChildAccountIndex)
            .where(ChildAccountIndex.issuer_address == self.issuer_address)
            .limit(1)
        ).first()
        assert _child_index.next_index == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # RequestValidationError
    # - Missing body
    def test_error_1(self, client, db):
        # Call API
        resp = client.post(self.base_url.format(self.issuer_address), json={})

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "type": "missing",
                    "loc": ["body", "personal_information_list"],
                    "msg": "Field required",
                    "input": {},
                }
            ],
        }

    # <Error_2>
    # 404: Issuer does not exist
    def test_error_2(self, client, db):
        # Call API
        resp = client.post(
            self.base_url.format(self.issuer_address),
            json={
                "personal_information_list": [
                    {
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "address": "address_test",
                        "email": "email_test",
                        "birth": "birth_test",
                        "is_corporate": False,
                        "tax_category": 10,
                    }
                ]
            },
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "issuer does not exist",
        }

    # <Error_3>
    # OperationNotPermittedForOlderIssuers
    def test_error_3(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = None  # public-key is not set
        db.add(_account)
        db.commit()

        # Call API
        resp = client.post(
            self.base_url.format(self.issuer_address),
            json={
                "personal_information_list": [
                    {
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "address": "address_test",
                        "email": "email_test",
                        "birth": "birth_test",
                        "is_corporate": False,
                        "tax_category": 10,
                    }
                ]
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 10, "title": "OperationNotPermittedForOlderIssuers"}
        }

    # <Error_4>
    # ServiceUnavailableError
    # - Lock timeout for index table
    def test_error_4(self, client, db):
        # Prepare data
        _account = Account()
        _account.issuer_address = self.issuer_address
        _account.issuer_public_key = self.issuer_pub_key
        db.add(_account)

        _child_index = ChildAccountIndex()
        _child_index.issuer_address = self.issuer_address
        _child_index.next_index = 2
        db.add(_child_index)

        db.commit()

        # Lock child account index table
        _child_index = db.scalars(
            select(ChildAccountIndex)
            .where(ChildAccountIndex.issuer_address == self.issuer_address)
            .limit(1)
            .with_for_update(nowait=True)
        ).first()

        # Call API
        resp = client.post(
            self.base_url.format(self.issuer_address),
            json={
                "personal_information_list": [
                    {
                        "name": "name_test",
                        "postal_code": "postal_code_test",
                        "address": "address_test",
                        "email": "email_test",
                        "birth": "birth_test",
                        "is_corporate": False,
                        "tax_category": 10,
                    }
                ]
            },
        )

        # Assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 1, "title": "ServiceUnavailableError"},
            "detail": "Creation of child accounts for this issuer is temporarily unavailable",
        }

        db.rollback()
        db.close()
