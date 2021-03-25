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

from app.model.db import Token, TokenType, BondLedger
from tests.account_config import config_eth_account


class TestAppBondLedgerTokenAddressHistoryGETJPN:
    # target API endpoint
    base_url = "/bond_ledger/{}/history"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, db):
        user = config_eth_account("user1")
        issuer_address = user["address"]
        token_address = "0xABCdeF1234567890abcdEf123456789000000000"

        # prepare data
        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND
        _token.tx_hash = ""
        _token.issuer_address = issuer_address
        _token.token_address = token_address
        _token.abi = {}
        db.add(_token)

        _bond_ledger_1 = BondLedger()
        _bond_ledger_1.token_address = token_address
        _bond_ledger_1.ledger = {}
        _bond_ledger_1.country_code = "JPN"
        _bond_ledger_1.bond_ledger_created = \
            datetime.strptime("2021/12/31 01:20:30", '%Y/%m/%d %H:%M:%S')  # UTC
        db.add(_bond_ledger_1)
        _bond_ledger_2 = BondLedger()
        _bond_ledger_2.token_address = token_address
        _bond_ledger_2.ledger = {}
        _bond_ledger_2.country_code = "JPN"
        _bond_ledger_2.bond_ledger_created = \
            datetime.strptime("2021/12/31 11:30:40", '%Y/%m/%d %H:%M:%S')  # UTC
        db.add(_bond_ledger_2)

        # request target API
        resp = client.get(
            self.base_url.format(token_address),
            headers={
                "country-code": "jpn",
                "issuer-address": issuer_address,
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json() == [
            {
                "id": 1,
                "token_address": token_address,
                "country_code": "JPN",
                "created": "2021/12/31 10:20:30 +0900",
            },
            {
                "id": 2,
                "token_address": token_address,
                "country_code": "JPN",
                "created": "2021/12/31 20:30:40 +0900",
            }
        ]

    ###########################################################################
    # Error Case
    ###########################################################################
