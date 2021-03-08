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
from typing import Dict
import base64
import binascii
import json
from datetime import datetime, timedelta

import boto3
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper
from web3 import Web3

from config import E2EE_RSA_RESOURCE_MODE, E2EE_RSA_RESOURCE, E2EE_RSA_PASSPHRASE, AWS_REGION_NAME


class E2EEUtils:
    """End to End Encryption Utilities

    This class is used for E2E encryption or decryption between client side and server side.
    The values encrypted on the client side are directly stored in the DB, etc.
    in an encrypted state, and decrypted for use.
    """

    cache = {
        "private_key": None,
        "public_key": None,
        "encrypted_length": None,
        "expiration_datetime": datetime.min
    }

    @staticmethod
    def encrypt(data: str):
        """Encrypt data

        :param data: Data to encrypt
        :return: Base64-decoded encrypted data
        """
        crypto_data = E2EEUtils.__get_crypto_data()
        if crypto_data.get("public_key") is None:
            return data

        rsa_key = RSA.importKey(crypto_data.get("public_key"), passphrase=E2EE_RSA_PASSPHRASE)
        cipher = PKCS1_OAEP.new(rsa_key)
        encrypt_data = cipher.encrypt(data.encode("utf-8"))
        base64_data = base64.encodebytes(encrypt_data)
        return base64_data.decode().replace("\n", "").replace(" ", "")

    @staticmethod
    def decrypt(base64_encrypt_data: str):
        """Decrypt data

        :param base64_encrypt_data: Base64-decoded encrypted data
        :return: Decrypted data
        """
        crypto_data = E2EEUtils.__get_crypto_data()
        if crypto_data.get("private_key") is None:
            return base64_encrypt_data

        rsa_key = RSA.importKey(crypto_data.get("private_key"), passphrase=E2EE_RSA_PASSPHRASE)
        cipher = PKCS1_OAEP.new(rsa_key)

        try:
            encrypt_data = base64.decodebytes(base64_encrypt_data.encode("utf-8"))
        except binascii.Error as err:
            raise ValueError(err.args[0] + " for base64 string.")

        # NOTE:
        # When using JavaScript to encrypt RSA, if the first character is 0x00,
        # the data is requested with the 00 character removed.
        # Since decrypting this data will result in a ValueError (Ciphertext with incorrect length),
        # decrypt the data with 00 added to the beginning.
        if len(encrypt_data) == (crypto_data.get("encrypted_length") - 1):
            hex_fixed = "00" + encrypt_data.hex()
            encrypt_data = base64.b16decode(hex_fixed.upper())

        decrypt_data = cipher.decrypt(encrypt_data)
        return decrypt_data.decode()

    @staticmethod
    def get_key():
        """Get crypt keys

        :return: Private Key, Public Key
        """
        crypto_data = E2EEUtils.__get_crypto_data()
        return crypto_data.get("private_key"), crypto_data.get("public_key")

    @staticmethod
    def __get_crypto_data() -> Dict:

        # Use Cache
        if E2EEUtils.cache.get("expiration_datetime") > datetime.utcnow():
            return E2EEUtils.cache

        # Get Private Key
        private_key = None
        if E2EE_RSA_RESOURCE_MODE == 0:
            with open(E2EE_RSA_RESOURCE, "r") as f:
                private_key = f.read()
        elif E2EE_RSA_RESOURCE_MODE == 1:
            secrets_manager = boto3.client(
                service_name="secretsmanager",
                region_name=AWS_REGION_NAME
            )
            result = secrets_manager.get_secret_value(SecretId=E2EE_RSA_RESOURCE)
            private_key = json.loads(result.get("SecretString"))

        # Get Public Key
        rsa_key = RSA.importKey(private_key, passphrase=E2EE_RSA_PASSPHRASE)

        public_key = rsa_key.publickey().exportKey().decode()

        # Calculate Encrypted Length
        cipher = PKCS1_OAEP.new(rsa_key)
        encrypted_length = len(cipher.encrypt(b''))

        # Update Cache(expiration for 1 hour)
        E2EEUtils.cache = {
            "private_key": private_key,
            "public_key": public_key,
            "encrypted_length": encrypted_length,
            "expiration_datetime": datetime.utcnow() + timedelta(hours=1)
        }

        return E2EEUtils.cache


def headers_validate(validators: list):
    errors = []
    for v in validators:
        name = v.get("name")
        value = v.get("value")
        validator = v.get("validator")

        try:
            validator(name, value)
        except Exception as err:
            errors.append(ErrorWrapper(exc=err, loc=("header", name)))

    if len(errors) > 0:
        raise RequestValidationError(errors)


def address_is_valid_address(name, value):
    if value:
        if not Web3.isAddress(value):
            raise ValueError(f"{name} is not a valid address")


def check_value_is_encrypted(name, value):
    if value:
        try:
            E2EEUtils.decrypt(value)
        except ValueError:
            raise ValueError(f"{name} is not a Base64-decoded encrypted data")
