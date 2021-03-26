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
import asyncio
from unittest.mock import patch

import pytest
import json

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted
from eth_keyfile import decode_keyfile_json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.exceptions import SendTransactionError
from config import WEB3_HTTP_PROVIDER, CHAIN_ID, TX_GAS_LIMIT, DATABASE_URL
from app.model.blockchain.utils import ContractUtils
from app.model.db import TransactionLock
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


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

    contract_interface_list = [
        "ContractReceiver",
        "IbetStandardTokenInterface"
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self):
        for contract_name in self.contract_list:
            rtn_abi, rtn_bytecode, rtn_deploy_bytecode = ContractUtils.get_contract_code(
                contract_name=contract_name
            )
            expected_json = json.load(open(f"contracts/{contract_name}.json", "r"))
            assert rtn_abi == expected_json["abi"]
            assert rtn_bytecode == expected_json["bytecode"]
            assert rtn_deploy_bytecode == expected_json["deployedBytecode"]

    # <Normal_2>
    # ContractReceiver and IbetStandardTokenInterface does not have bytecode
    def test_normal_2(self):
        for contract_name in self.contract_interface_list:
            rtn = ContractUtils.get_contract_code(
                contract_name=contract_name
            )
            expected_json = json.load(open(f"contracts/{contract_name}.json", "r"))
            assert rtn == (expected_json["abi"], None, None)

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract name does not exist
    def test_error_1(self):
        with pytest.raises(FileNotFoundError):
            ContractUtils.get_contract_code(
                contract_name="NO_EXISTS"
            )


class TestDeployContract:
    account_list = [
        config_eth_account("user1"),
        config_eth_account("user2")
    ]

    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=account_list[0]["keyfile_json"],
        password=eoa_password.encode("utf-8")
    )

    test_contract_name = "IbetCoupon"
    test_arg = [
        "sample_coupon_name", "sample", 100, account_list[1]["address"], "details",
        "return_details", "memo", '20210531', True, "contractInformation",
        "PrivacyPolicy"
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    def test_normal_1(self):
        # mock
        ContractUtils_send_transaction = patch(
            target="app.model.blockchain.utils.ContractUtils.send_transaction",
            return_value=("tx_hash", {"status": 1})
        )

        with ContractUtils_send_transaction:
            rtn_contract_address, rtn_abi, rtn_tx_hash = ContractUtils.deploy_contract(
                contract_name=self.test_contract_name,
                args=self.test_arg,
                deployer=self.account_list[0]["address"],
                private_key=self.private_key
            )
            expected_abi = json.load(open(f"contracts/{self.test_contract_name}.json", 'r'))["abi"]
            assert rtn_abi == expected_abi
            assert rtn_tx_hash == "tx_hash"

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract name does not exist
    def test_error_1(self):
        # mock
        ContractConstructor_buildTransaction = patch(
            target="web3.contract.ContractConstructor.buildTransaction",
            side_effect=TimeExhausted("TIME EXHAUSTED")
        )

        with ContractConstructor_buildTransaction:
            with pytest.raises(SendTransactionError) as ex_info:
                ContractUtils.deploy_contract(
                    contract_name=self.test_contract_name,
                    args=self.test_arg,
                    deployer=self.account_list[0]["address"],
                    private_key=self.private_key
                )
            assert str(ex_info.typename) == "SendTransactionError"
            assert str(ex_info.value) == "TIME EXHAUSTED"

    # <Error_2>
    # Contract name does not exist
    def test_error_2(self):
        # mock
        ContractUtils_send_transaction = patch(
            target="app.model.blockchain.utils.ContractUtils.send_transaction",
            side_effect=ConnectionError("TEST ERROR")
        )

        with ContractUtils_send_transaction:
            with pytest.raises(SendTransactionError) as ex_info:
                ContractUtils.deploy_contract(
                    contract_name=self.test_contract_name,
                    args=self.test_arg,
                    deployer=self.account_list[0]["address"],
                    private_key=self.private_key
                )
        assert str(ex_info.typename) == "SendTransactionError"
        assert str(ex_info.value) == "TEST ERROR"


class TestGetContract:
    account_list = [
        config_eth_account("user1"),
        config_eth_account("user2")
    ]

    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=account_list[0]["keyfile_json"],
        password=eoa_password.encode("utf-8")
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
                contract_name=_contract_name,
                contract_address=test_address
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
                contract_address="0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6ZZZZ"  # too long
            )

    # <Error_2>
    # Contract does not exists
    def test_error_2(self):
        with pytest.raises(FileNotFoundError):
            ContractUtils.get_contract(
                contract_name="NoExistContract",
                contract_address="0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6"
            )


class TestSendTransaction:
    account_list = [
        config_eth_account("user1"),
        config_eth_account("user2")
    ]

    eoa_password = "password"
    private_key = decode_keyfile_json(
        raw_keyfile_json=account_list[0]["keyfile_json"],
        password=eoa_password.encode("utf-8")
    )

    test_contract_name = "IbetCoupon"
    test_arg = [
        "sample_coupon_name", "sample", 100, account_list[1]["address"], "details",
        "return_details", "memo", '20210531', True, "contractInformation",
        "PrivacyPolicy"
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
        tx = contract.constructor(*self.test_arg).buildTransaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.account_list[0]["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        rtn_tx_hash, rtn_receipt = ContractUtils.send_transaction(
            transaction=tx,
            private_key=self.private_key
        )

        assert rtn_tx_hash == rtn_receipt["transactionHash"].hex()
        assert rtn_receipt["status"] == 1
        assert rtn_receipt["to"] is None
        assert rtn_receipt["from"] == self.account_list[0]["address"]
        assert web3.isAddress(rtn_receipt["contractAddress"])

    ###########################################################################
    # Error Case
    ###########################################################################
    def test_error_1(self, db: Session):
        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).buildTransaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.account_list[0]["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            return_value={
                "dummy": "hoge",
                "status": 0
            }
        )

        with Web3_sendRawTransaction:
            with pytest.raises(SendTransactionError):
                ContractUtils.send_transaction(
                    transaction=tx,
                    private_key=self.private_key
                )

    def test_error_2(self, db: Session):
        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).buildTransaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.account_list[0]["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        # mock
        Web3_sendRawTransaction = patch(
            target="web3.eth.Eth.waitForTransactionReceipt",
            side_effect=ValueError
        )

        with Web3_sendRawTransaction:
            with pytest.raises(ValueError):
                ContractUtils.send_transaction(
                    transaction=tx,
                    private_key=self.private_key
                )

    async def send_transaction(self, tx: dict):
        ContractUtils.send_transaction(
            transaction=tx,
            private_key=self.private_key
        )

    @staticmethod
    async def tx_lock_record(tx_from: str):
        DB_URI = DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        # 10-sec timeout
        db_engine = create_engine(
            DB_URI,
            connect_args={'options': '-c lock_timeout=10000'},
            echo=False
        )
        local_session = Session(autocommit=False, autoflush=True, bind=db_engine)

        # exclusive control within transaction execution address
        # lock record
        try:
            _tm = local_session.query(TransactionLock). \
                filter(TransactionLock.tx_from == tx_from). \
                populate_existing(). \
                with_for_update(). \
                first()
            await asyncio.sleep(10)
        finally:
            local_session.close()

    def test_error_3(self, db: Session):
        # prepare data : TX
        _tx_mng = TransactionLock()
        _tx_mng.tx_from = self.account_list[0]["address"]
        db.add(_tx_mng)
        db.commit()

        # Contract
        contract = web3.eth.contract(
            abi=self.contract_json["abi"],
            bytecode=self.contract_json["bytecode"],
            bytecode_runtime=self.contract_json["deployedBytecode"],
        )

        # Build transaction
        tx = contract.constructor(*self.test_arg).buildTransaction(
            transaction={
                "chainId": CHAIN_ID,
                "from": self.account_list[0]["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )

        loop = asyncio.get_event_loop()
        gather = asyncio.gather(
            self.tx_lock_record(self.account_list[0]["address"]),
            self.send_transaction(tx)
        )
        with pytest.raises(TimeExhausted) as ex_info:
            loop.run_until_complete(gather)
        assert ex_info.typename == "TimeExhausted"
