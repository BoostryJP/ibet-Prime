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

import base64
import json
import os
import sys
import logging
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from datetime import timezone, timedelta

JST = timezone(timedelta(hours=+9), "JST")

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted
from eth_keyfile import decode_keyfile_json

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import WEB3_HTTP_PROVIDER, CHAIN_ID, TX_GAS_LIMIT
from app.model.blockchain.utils import ContractUtils
from app.model.db import Account
from app.model.utils import SecureValueUtils
from app.exceptions import SendTransactionError

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class PersonalInfoContract:
    """PersonalInfo contract model"""

    def __init__(self, db, issuer_address: str, contract_address=None):
        self.personal_info_contract = ContractUtils.get_contract(
            contract_name="PersonalInfo",
            contract_address=contract_address
        )
        self.issuer = db.query(Account). \
            filter(Account.issuer_address == issuer_address). \
            first()

    def get_info(self, account_address: str, default_value=None):
        """Get personal information

        :param account_address: Token holder account address
        :param default_value: Default value for items for which no value is set. (If not specified: None)
        :return: Personal info
        """

        # Get issuer's RSA private key
        cipher = None
        try:
            passphrase = SecureValueUtils.decrypt(self.issuer.rsa_passphrase)
            key = RSA.importKey(self.issuer.rsa_private_key, passphrase)
            cipher = PKCS1_OAEP.new(key)
        except Exception as err:
            logging.error(f"Cannot open the private key: {err}")

        # Set default value
        personal_info = {
            "key_manager": default_value,
            "name": default_value,
            "postal_code": default_value,
            "address": default_value,
            "email": default_value,
            "birth": default_value
        }

        # Get encrypted personal information
        personal_info_state = self.personal_info_contract.functions. \
            personal_info(account_address, self.issuer.issuer_address). \
            call()
        encrypted_info = personal_info_state[2]

        if encrypted_info == "" or cipher is None:
            return personal_info  # default
        else:
            try:
                ciphertext = base64.decodebytes(encrypted_info.encode("utf-8"))
                # NOTE:
                # When using JavaScript to encrypt RSA, if the first character is 0x00,
                # the data is requested with the 00 character removed.
                # Since decrypting this data will result in a ValueError (Ciphertext with incorrect length),
                # decrypt the data with 00 added to the beginning.
                if len(ciphertext) == 1279:
                    hex_fixed = "00" + ciphertext.hex()
                    ciphertext = base64.b16decode(hex_fixed.upper())
                decrypted_info = json.loads(cipher.decrypt(ciphertext))

                personal_info["key_manager"] = decrypted_info.get("key_manager", default_value)
                personal_info["name"] = decrypted_info.get("name", default_value)
                personal_info["address"] = decrypted_info.get("address", default_value)
                personal_info["postal_code"] = decrypted_info.get("postal_code", default_value)
                personal_info["email"] = decrypted_info.get("email", default_value)
                personal_info["birth"] = decrypted_info.get("birth", default_value)
                return personal_info
            except Exception as err:
                logging.error(f"Failed to decrypt: {err}")
                return personal_info  # default

    def modify_info(self, account_address: str, data: dict, default_value=None):
        """Modify personal information

        :param account_address: Token holder account address
        :param password: Token holder account address's password
        :param data: Modify data
        :param default_value: Default value for items for which no value is set. (If not specified: None)
        :return: None
        """

        # Set default value
        personal_info = {
            "key_manager": data.get("key_manager", default_value),
            "name": data.get("name", default_value),
            "postal_code": data.get("postal_code", default_value),
            "address": data.get("address", default_value),
            "email": data.get("email", default_value),
            "birth": data.get("birth", default_value)
        }

        # Encrypt personal info
        passphrase = SecureValueUtils.decrypt(self.issuer.rsa_passphrase)
        rsa_key = RSA.importKey(self.issuer.rsa_public_key, passphrase=passphrase)
        cipher = PKCS1_OAEP.new(rsa_key)
        ciphertext = base64.encodebytes(cipher.encrypt(json.dumps(personal_info).encode('utf-8')))

        try:
            password = SecureValueUtils.decrypt(self.issuer.eoa_password)
            private_key = decode_keyfile_json(
                raw_keyfile_json=self.issuer.keyfile,
                password=password.encode("utf-8")
            )
            tx = self.personal_info_contract.functions.modify(account_address, ciphertext). \
                buildTransaction({
                    "nonce": web3.eth.getTransactionCount(self.issuer.issuer_address),
                    "chainId": CHAIN_ID,
                    "from": self.issuer.issuer_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0
                })
            ContractUtils.send_transaction(transaction=tx, private_key=private_key)
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            logging.exception(f"{err}")
            raise SendTransactionError(err)

    def get_register_event(self, block_from, block_to):
        """Get Register event

        :param block_from: block from
        :param block_to: block to
        :return: event entries
        """
        event_filter = self.personal_info_contract.events.Register.createFilter(
            fromBlock=block_from,
            toBlock=block_to
        )
        return event_filter.get_all_entries()

    def get_modify_event(self, block_from, block_to):
        """Get Modify event

        :param block_from: block from
        :param block_to: block to
        :return: event entries
        """
        event_filter = self.personal_info_contract.events.Modify.createFilter(
            fromBlock=block_from,
            toBlock=block_to
        )
        return event_filter.get_all_entries()
