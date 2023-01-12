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
import secrets

import boto3
from Crypto.Cipher import (
    AES,
    PKCS1_OAEP
)
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from web3.exceptions import TimeExhausted

from config import (
    CHAIN_ID,
    TX_GAS_LIMIT,
    AWS_KMS_GENERATE_RANDOM_ENABLED,
    AWS_REGION_NAME
)
from app.utils.contract_utils import ContractUtils
from app.exceptions import SendTransactionError, ContractRevertError


class E2EMessaging:
    """E2EMessaging model"""

    def __init__(self, contract_address: str):
        self.contract_address = contract_address

    def send_message(self,
                     to_address: str, message: str,
                     tx_from: str, private_key: str):
        """Send Message"""
        contract = ContractUtils.get_contract(
            contract_name="E2EMessaging",
            contract_address=self.contract_address
        )
        try:
            tx = contract.functions.sendMessage(
                to_address,
                message
            ).build_transaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            tx_hash, tx_receipt = ContractUtils.send_transaction(tx, private_key)
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)

    def send_message_external(self,
                              to_address: str, _type: str, message_org: str, to_rsa_public_key: str,
                              tx_from: str, private_key: str):
        """Send Message(Format message for external system)"""

        # Encrypt message with AES-256-CBC
        if AWS_KMS_GENERATE_RANDOM_ENABLED:
            kms = boto3.client(service_name="kms", region_name=AWS_REGION_NAME)
            result = kms.generate_random(NumberOfBytes=AES.block_size * 2)
            aes_key = result["Plaintext"]
            result = kms.generate_random(NumberOfBytes=AES.block_size)
            aes_iv = result["Plaintext"]
        else:
            aes_key = secrets.token_bytes(AES.block_size * 2)
            aes_iv = secrets.token_bytes(AES.block_size)
        aes_cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        pad_message = pad(message_org.encode("utf-8"), AES.block_size)
        encrypted_message = base64.b64encode(aes_iv + aes_cipher.encrypt(pad_message)).decode()

        # Encrypt AES key with RSA
        rsa_key = RSA.import_key(to_rsa_public_key)
        rsa_cipher = PKCS1_OAEP.new(rsa_key)
        cipher_key = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode()

        # Create formatted message
        message_dict = {
            "type": _type,
            "text": {
                "cipher_key": cipher_key,
                "message": encrypted_message,
            },
        }
        message = json.dumps(message_dict)

        # Send message
        tx_hash, tx_receipt = E2EMessaging(self.contract_address).send_message(
            to_address=to_address,
            message=message,
            tx_from=tx_from,
            private_key=private_key
        )
        return tx_hash, tx_receipt

    def set_public_key(self,
                       public_key: str, key_type: str,
                       tx_from: str, private_key: str):
        """Set Public Key"""
        contract = ContractUtils.get_contract(
            contract_name="E2EMessaging",
            contract_address=self.contract_address
        )
        try:
            tx = contract.functions.setPublicKey(
                public_key,
                key_type
            ).build_transaction({
                "chainId": CHAIN_ID,
                "from": tx_from,
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0
            })
            tx_hash, tx_receipt = ContractUtils.send_transaction(tx, private_key)
            return tx_hash, tx_receipt
        except ContractRevertError:
            raise
        except TimeExhausted as timeout_error:
            raise SendTransactionError(timeout_error)
        except Exception as err:
            raise SendTransactionError(err)
