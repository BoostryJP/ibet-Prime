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
import logging
from typing import Final

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from eth_keyfile import decode_keyfile_json
from pydantic import BaseModel
from web3.contract import AsyncContract
from web3.exceptions import TimeExhausted

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import Account
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from app.utils.ibet_web3_utils import Web3Wrapper
from config import CHAIN_ID, TX_GAS_LIMIT, ZERO_ADDRESS

web3 = Web3Wrapper()


class ContractPersonalInfoType(BaseModel):
    key_manager: str | None = None
    name: str | None = None
    address: str | None = None
    postal_code: str | None = None
    email: str | None = None
    birth: str | None = None
    is_corporate: bool | None = None
    tax_category: int | None = None


class PersonalInfoContract:
    """PersonalInfo contract"""

    personal_info_contract: AsyncContract
    issuer: Final[Account]
    private_key: bytes | None

    def __init__(self, logger: logging.Logger, issuer: Account, contract_address=None):
        self.logger = logger
        self.personal_info_contract = AsyncContractUtils.get_contract(
            contract_name="PersonalInfo", contract_address=contract_address
        )
        self.issuer = issuer
        self.cipher = None
        self.private_key = None

    async def get_info(self, account_address: str, default_value=None):
        """Get personal information from contract storage

        :param account_address: Token holder account address
        :param default_value: Default value for items for which no value is set. (If not specified: None)
        :return: Personal info
        """

        # Get encrypted personal information
        personal_info_state = await AsyncContractUtils.call_function(
            contract=self.personal_info_contract,
            function_name="personal_info",
            args=(
                account_address,
                self.issuer.issuer_address,
            ),
            default_returns=[ZERO_ADDRESS, ZERO_ADDRESS, ""],
        )
        encrypted_info = personal_info_state[2]

        if encrypted_info == "":
            return ContractPersonalInfoType(
                key_manager=default_value,
                name=default_value,
                address=default_value,
                postal_code=default_value,
                email=default_value,
                birth=default_value,
            ).model_dump()
        else:
            # Get issuer's RSA private key
            try:
                if self.cipher is None:
                    passphrase = E2EEUtils.decrypt(self.issuer.rsa_passphrase)
                    key = RSA.importKey(self.issuer.rsa_private_key, passphrase)
                    self.cipher = PKCS1_OAEP.new(key)
            except Exception as err:
                self.logger.error(f"Cannot open the private key: {err}")
                return ContractPersonalInfoType(
                    key_manager=default_value,
                    name=default_value,
                    address=default_value,
                    postal_code=default_value,
                    email=default_value,
                    birth=default_value,
                ).model_dump()
            if self.cipher is not None:
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
                    decrypted_info = json.loads(self.cipher.decrypt(ciphertext))

                    return ContractPersonalInfoType(
                        key_manager=decrypted_info.get("key_manager", default_value),
                        name=decrypted_info.get("name", default_value),
                        address=decrypted_info.get("address", default_value),
                        postal_code=decrypted_info.get("postal_code", default_value),
                        email=decrypted_info.get("email", default_value),
                        birth=decrypted_info.get("birth", default_value),
                        is_corporate=decrypted_info.get("is_corporate", None),
                        tax_category=decrypted_info.get("tax_category", None),
                    ).model_dump()
                except Exception as err:
                    self.logger.error(
                        f"Failed to decrypt: issuer_address={self.issuer.issuer_address}, account_address={account_address}: {err}"
                    )
                    return ContractPersonalInfoType(
                        key_manager=default_value,
                        name=default_value,
                        address=default_value,
                        postal_code=default_value,
                        email=default_value,
                        birth=default_value,
                    ).model_dump()

    async def register_info(
        self, account_address: str, data: dict, default_value=None
    ) -> str:
        """Register personal information

        :param account_address: Token holder account address
        :param data: Register data
        :param default_value: Default value for items for which no value is set. (If not specified: None)
        :return: tx_hash
        """

        # Set default value
        personal_info = {
            "key_manager": data.get("key_manager", default_value),
            "name": data.get("name", default_value),
            "postal_code": data.get("postal_code", default_value),
            "address": data.get("address", default_value),
            "email": data.get("email", default_value),
            "birth": data.get("birth", default_value),
            "is_corporate": data.get("is_corporate", default_value),
            "tax_category": data.get("tax_category", default_value),
        }

        # Encrypt personal info
        passphrase = E2EEUtils.decrypt(self.issuer.rsa_passphrase)
        rsa_key = RSA.importKey(self.issuer.rsa_public_key, passphrase=passphrase)
        cipher = PKCS1_OAEP.new(rsa_key)
        ciphertext = base64.encodebytes(
            cipher.encrypt(json.dumps(personal_info).encode("utf-8"))
        )

        try:
            if self.private_key is None:
                password = E2EEUtils.decrypt(self.issuer.eoa_password)
                self.private_key = decode_keyfile_json(
                    raw_keyfile_json=self.issuer.keyfile,
                    password=password.encode("utf-8"),
                )
            tx = await self.personal_info_contract.functions.forceRegister(
                account_address, ciphertext.decode("utf-8")
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": self.issuer.issuer_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            tx_hash, _ = await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=self.private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            self.logger.exception(f"{err}")
            raise SendTransactionError(err)
        return tx_hash

    async def modify_info(self, account_address: str, data: dict, default_value=None):
        """Modify personal information

        :param account_address: Token holder account address
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
            "birth": data.get("birth", default_value),
            "is_corporate": data.get("is_corporate", default_value),
            "tax_category": data.get("tax_category", default_value),
        }

        # Encrypt personal info
        passphrase = E2EEUtils.decrypt(self.issuer.rsa_passphrase)
        rsa_key = RSA.importKey(self.issuer.rsa_public_key, passphrase=passphrase)
        cipher = PKCS1_OAEP.new(rsa_key)
        ciphertext = base64.encodebytes(
            cipher.encrypt(json.dumps(personal_info).encode("utf-8"))
        )

        try:
            if self.private_key is None:
                password = E2EEUtils.decrypt(self.issuer.eoa_password)
                self.private_key = decode_keyfile_json(
                    raw_keyfile_json=self.issuer.keyfile,
                    password=password.encode("utf-8"),
                )
            tx = await self.personal_info_contract.functions.modify(
                account_address, ciphertext.decode("utf-8")
            ).build_transaction(
                {
                    "chainId": CHAIN_ID,
                    "from": self.issuer.issuer_address,
                    "gas": TX_GAS_LIMIT,
                    "gasPrice": 0,
                }
            )
            await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=self.private_key
            )
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            self.logger.exception(f"{err}")
            raise SendTransactionError(err)

    async def get_register_event(self, block_from, block_to):
        """Get Register event

        :param block_from: block from
        :param block_to: block to
        :return: event entries
        """
        events = await AsyncContractUtils.get_event_logs(
            contract=self.personal_info_contract,
            event="Register",
            block_from=block_from,
            block_to=block_to,
        )
        return events

    async def get_modify_event(self, block_from, block_to):
        """Get Modify event

        :param block_from: block from
        :param block_to: block to
        :return: event entries
        """
        events = await AsyncContractUtils.get_event_logs(
            contract=self.personal_info_contract,
            event="Modify",
            block_from=block_from,
            block_to=block_to,
        )
        return events
