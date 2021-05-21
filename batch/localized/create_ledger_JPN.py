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
from datetime import datetime

import pytz

path = os.path.join(os.path.dirname(__file__), '../../')
sys.path.append(path)

from config import TZ

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


def get_ledger_keys():
    return "原簿作成日", "原簿名称", "項目", "権利", "権利名称", "明細"


def convert_details_item(details: list):
    convert_details = []
    for detail in details:
        # Convert key language
        convert_detail = {
            "アカウントアドレス": detail["account_address"],
            "氏名または名称": detail["name"],
            "住所": detail["address"],
            "保有口数": detail["amount"],
            "一口あたりの金額": detail["price"],
            "保有残高": detail["balance"],
            "取得日": detail["acquisition_date"],
        }

        # Set other key
        tmp_details = detail.copy()
        tmp_details.pop("account_address")
        tmp_details.pop("name")
        tmp_details.pop("address")
        tmp_details.pop("amount")
        tmp_details.pop("price")
        tmp_details.pop("balance")
        tmp_details.pop("acquisition_date")
        for k, v in tmp_details.items():
            convert_detail[k] = v

        convert_details.append(convert_detail)

    return convert_details


def get_default_corporate_bond_ledger(details: list):
    created_key, ledger_name_key, item_key, rights_key, rights_name_key, details_key = get_ledger_keys()

    ledger = {
        "原簿作成日": "",
        "原簿名称": "",
        "項目": {
            "社債の説明": "",
            "社債の総額": None,
            "各社債の金額": None,
            "払込情報": {
                "払込金額": None,
                "払込日": "",
                "払込状況": None
            },
            "社債の種類": "",
            "社債原簿管理人": {
                "氏名または名称": "",
                "住所": "",
                "事務取扱場所": ""
            },
        },
        "権利": [
            {
                "権利名称": "社債",
                "項目": {},
                "明細": []
            }
        ]
    }

    created_ymd = utc_tz.localize(datetime.utcnow()).astimezone(local_tz).strftime("%Y/%m/%d")
    ledger[created_key] = created_ymd

    convert_details = convert_details_item(details)
    ledger_details = ledger[rights_key][0][details_key]
    for detail in convert_details:
        detail.update({
            "金銭以外の財産給付情報": {
                "財産の価格": "-",
                "給付日": "-",
            },
            "債権相殺情報": {
                "相殺する債権額": "-",
                "相殺日": "-",
            },
            "質権情報": {
                "質権者の氏名または名称": "-",
                "質権者の住所": "-",
                "質権の目的である債券": "-",
            },
            "備考": "-",
        })
        ledger_details.append(detail)

    return ledger
