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
from unittest.mock import patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.orm import Session
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception
from web3.middleware import geth_poa_middleware

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import TransactionLock
from app.utils.contract_utils import ContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class TestGetContractCode:
    contract_list = [
        "IbetCoupon",
        "IbetMembership",
        "IbetShare",
        "IbetStraightBond",
        "Ownable",
        "PersonalInfo",
        "SafeMath",
        "TokenList",
    ]

    contract_interface_list = ["ContractReceiver", "IbetStandardTokenInterface"]

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self):
        for contract_name in self.contract_list:
            (
                rtn_abi,
                rtn_bytecode,
                rtn_deploy_bytecode,
            ) = ContractUtils.get_contract_code(contract_name=contract_name)
            expected_json = json.load(open(f"contracts/{contract_name}.json", "r"))
            assert rtn_abi == expected_json["abi"]
            assert rtn_bytecode == expected_json["bytecode"]
            assert rtn_deploy_bytecode == expected_json["deployedBytecode"]

    # <Normal_2>
    # ContractReceiver and IbetStandardTokenInterface does not have bytecode
    def test_normal_2(self):
        for contract_name in self.contract_interface_list:
            rtn = ContractUtils.get_contract_code(contract_name=contract_name)
            expected_json = json.load(open(f"contracts/{contract_name}.json", "r"))
            assert rtn == (expected_json["abi"], None, None)

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract name does not exist
    def test_error_1(self):
        with pytest.raises(FileNotFoundError):
            ContractUtils.get_contract_code(contract_name="NO_EXISTS")


class TestDeployContract:
    test_account = config_eth_account("user1")
    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=test_account["keyfile_json"],
        password=eoa_password.encode("utf-8"),
    )

    test_contract_name = "IbetCoupon"
    test_arg = [
        "test_coupon_name",
        "TEST",
        100,
        ZERO_ADDRESS,
        "test_details",
        "test_return_details",
        "test_memo",
        "20210531",
        True,
        "test_contract_information",
        "test_privacy_policy",
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self, db):
        rtn_contract_address, rtn_abi, rtn_tx_hash = ContractUtils.deploy_contract(
            contract_name=self.test_contract_name,
            args=self.test_arg,
            deployer=self.test_account["address"],
            private_key=self.private_key,
        )
        expected_abi = json.load(
            open(f"contracts/{self.test_contract_name}.json", "r")
        )["abi"]
        assert rtn_abi == expected_abi

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract name does not exist
    def test_error_1(self):
        with pytest.raises(SendTransactionError) as ex_info:
            ContractUtils.deploy_contract(
                contract_name="NOT_EXIST_CONTRACT",
                args=self.test_arg,
                deployer=self.test_account["address"],
                private_key=self.private_key,
            )
        assert str(ex_info.typename) == "SendTransactionError"

    # <Error_2>
    # Send transaction error
    def test_error_2(self):
        # mock
        ContractUtils_send_transaction = patch(
            target="app.utils.contract_utils.ContractUtils.send_transaction",
            side_effect=SendTransactionError,
        )

        with ContractUtils_send_transaction:
            with pytest.raises(SendTransactionError) as ex_info:
                ContractUtils.deploy_contract(
                    contract_name=self.test_contract_name,
                    args=self.test_arg,
                    deployer=self.test_account["address"],
                    private_key=self.private_key,
                )
        assert str(ex_info.typename) == "SendTransactionError"


class TestGetContract:
    test_account = config_eth_account("user1")
    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=test_account["keyfile_json"],
        password=eoa_password.encode("utf-8"),
    )

    contract_list = [
        "IbetCoupon",
        "IbetMembership",
        "IbetShare",
        "IbetStraightBond",
        "Ownable",
        "PersonalInfo",
        "SafeMath",
        "TokenList",
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self):
        test_address = "0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6"
        for _contract_name in self.contract_list:
            contract = ContractUtils.get_contract(
                contract_name=_contract_name, contract_address=test_address
            )
            assert contract.abi == ContractUtils.get_contract_code(_contract_name)[0]
            assert contract.bytecode is None
            assert contract.bytecode_runtime is None
            assert contract.address == test_address

    # <Error_1>
    # Contract address is not address
    def test_error_1(self):
        with pytest.raises(ValueError):
            ContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address="0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6ZZZZ",  # too long
            )

    # <Error_2>
    # Contract does not exists
    def test_error_2(self):
        with pytest.raises(FileNotFoundError):
            ContractUtils.get_contract(
                contract_name="NotExistContract",
                contract_address="0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6",
            )


class TestSendTransaction:
    test_account = config_eth_account("user1")
    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=test_account["keyfile_json"],
        password=eoa_password.encode("utf-8"),
    )

    test_contract_name = "IbetCoupon"
    test_arg = [
        "test_coupon_name",
        "TEST",
        100,
        ZERO_ADDRESS,
        "test_details",
        "test_return_details",
        "test_memo",
        "20210531",
        True,
        "test_contract_information",
        "test_privacy_policy",
    ]
    contract_file = f"contracts/{test_contract_name}.json"
    contract_json = json.load(open(contract_file, "r"))

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self, db: Session):
        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).build_transaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.test_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        rtn_tx_hash, rtn_receipt = ContractUtils.send_transaction(
            transaction=tx, private_key=self.private_key
        )

        assert rtn_tx_hash == rtn_receipt["transactionHash"].hex()
        assert rtn_receipt["status"] == 1
        assert rtn_receipt["to"] is None
        assert rtn_receipt["from"] == self.test_account["address"]
        assert web3.is_address(rtn_receipt["contractAddress"])

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Transaction REVERT(Deploying invalid bytecode)
    def test_error_1(self, db: Session):
        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            # add "0000" to make invalid bytecode
            bytecode=self.contract_json["bytecode"] + "0000",
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).build_transaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.test_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            return_value={"dummy": "hoge", "status": 0},
        )
        InspectionMock = patch(
            target="web3.eth.Eth.call",
            side_effect=ContractLogicError("execution reverted"),
        )

        with Web3_send_raw_transaction, InspectionMock:
            with pytest.raises(ContractRevertError):
                ContractUtils.send_transaction(
                    transaction=tx, private_key=self.private_key
                )

    # <Error_2>
    # Value Error
    def test_error_2(self, db: Session):
        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).build_transaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.test_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        # mock
        Web3_send_raw_transaction = patch(
            target="web3.eth.Eth.wait_for_transaction_receipt",
            side_effect=Web3Exception,
        )

        with Web3_send_raw_transaction:
            with pytest.raises(Web3Exception):
                ContractUtils.send_transaction(
                    transaction=tx, private_key=self.private_key
                )

    # <Error_3>
    # Timeout waiting for lock release
    def test_error_3(self, db: Session):
        # prepare data : TX lock
        _tx_mng = TransactionLock()
        _tx_mng.tx_from = self.test_account["address"]
        db.add(_tx_mng)
        db.commit()

        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).build_transaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.test_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        # Transaction Lock
        db.scalars(
            select(TransactionLock)
            .where(TransactionLock.tx_from == self.test_account["address"])
            .limit(1)
            .with_for_update()
        ).first()

        with pytest.raises(SendTransactionError) as ex_info:
            ContractUtils.send_transaction(transaction=tx, private_key=self.private_key)
        assert ex_info.typename == "SendTransactionError"

        db.rollback()


class TestGetBlockByTransactionHash:
    test_account = config_eth_account("user1")
    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=test_account["keyfile_json"],
        password=eoa_password.encode("utf-8"),
    )

    test_contract_name = "IbetCoupon"
    test_arg = [
        "test_coupon_name",
        "TEST",
        100,
        ZERO_ADDRESS,
        "test_details",
        "test_return_details",
        "test_memo",
        "20210531",
        True,
        "test_contract_information",
        "test_privacy_policy",
    ]
    contract_file = f"contracts/{test_contract_name}.json"
    contract_json = json.load(open(contract_file, "r"))

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self, db: Session):
        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).build_transaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.test_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        nonce = web3.eth.get_transaction_count(self.test_account["address"])
        tx["nonce"] = nonce
        signed_tx = web3.eth.account.sign_transaction(
            transaction_dict=tx, private_key=self.private_key
        )

        # Send Transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction.hex())
        tx_receipt = web3.eth.wait_for_transaction_receipt(
            transaction_hash=tx_hash, timeout=10
        )

        block = ContractUtils.get_block_by_transaction_hash(tx_hash)

        assert block["number"] == tx_receipt["blockNumber"]
        assert block["timestamp"] > 0

    ###########################################################################
    # Error Case
    ###########################################################################
