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
import json
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from aiohttp import ClientTimeout
from eth_keyfile.keyfile import decode_keyfile_json
from hexbytes import HexBytes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import ContractLogicError, TimeExhausted, Web3Exception
from web3.middleware import ExtraDataToPOAMiddleware

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import TransactionLock
from app.utils import ibet_contract_utils as contract_module
from app.utils.ibet_contract_utils import AsyncContractUtils
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper
from app.utils.web3_provider_utils import KeepAliveHTTPSessionManager
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


async def _get_web3(wrapper: AsyncWeb3Wrapper) -> AsyncWeb3[AsyncHTTPProvider]:
    return wrapper.get_web3()


# Test for get_contract_code
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
    @pytest.mark.asyncio
    async def test_normal_1(self):
        for contract_name in self.contract_list:
            (
                rtn_abi,
                rtn_bytecode,
                rtn_deploy_bytecode,
            ) = AsyncContractUtils.get_contract_code(contract_name=contract_name)
            expected_json = json.load(open(f"contracts/ibet/{contract_name}.json", "r"))
            assert rtn_abi == expected_json["abi"]
            assert rtn_bytecode == expected_json["bytecode"]
            assert rtn_deploy_bytecode == expected_json["deployedBytecode"]

    # <Normal_2>
    # ContractReceiver and IbetStandardTokenInterface does not have bytecode
    @pytest.mark.asyncio
    async def test_normal_2(self):
        for contract_name in self.contract_interface_list:
            rtn = AsyncContractUtils.get_contract_code(contract_name=contract_name)
            expected_json = json.load(open(f"contracts/ibet/{contract_name}.json", "r"))
            assert rtn == (expected_json["abi"], None, None)

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract name does not exist
    @pytest.mark.asyncio
    async def test_error_1(self):
        with pytest.raises(FileNotFoundError):
            AsyncContractUtils.get_contract_code(contract_name="NO_EXISTS")


# Test for deploy_contract
class TestDeployContract:
    test_account = default_eth_account("user1")
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
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db: AsyncSession):
        (
            _,
            rtn_abi,
            _,
        ) = await AsyncContractUtils.deploy_contract(
            contract_name=self.test_contract_name,
            args=self.test_arg,
            deployer=self.test_account["address"],
            private_key=self.private_key,
        )
        expected_abi = json.load(
            open(f"contracts/ibet/{self.test_contract_name}.json", "r")
        )["abi"]
        assert rtn_abi == expected_abi

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract name does not exist
    @pytest.mark.asyncio
    async def test_error_1(self):
        with pytest.raises(SendTransactionError) as ex_info:
            await AsyncContractUtils.deploy_contract(
                contract_name="NOT_EXIST_CONTRACT",
                args=self.test_arg,
                deployer=self.test_account["address"],
                private_key=self.private_key,
            )
        assert ex_info.typename == "SendTransactionError"

    # <Error_2>
    # Send transaction error
    @pytest.mark.asyncio
    async def test_error_2(self):
        # mock
        ContractUtils_send_transaction = patch(
            target="app.utils.ibet_contract_utils.AsyncContractUtils.send_transaction",
            side_effect=SendTransactionError,
        )

        with ContractUtils_send_transaction:
            with pytest.raises(SendTransactionError) as ex_info:
                await AsyncContractUtils.deploy_contract(
                    contract_name=self.test_contract_name,
                    args=self.test_arg,
                    deployer=self.test_account["address"],
                    private_key=self.private_key,
                )
        assert ex_info.typename == "SendTransactionError"


# Test for deploy_contract
class TestGetContract:
    test_account = default_eth_account("user1")
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
    @pytest.mark.asyncio
    async def test_normal_1(self):
        test_address = "0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6"
        for _contract_name in self.contract_list:
            contract = AsyncContractUtils.get_contract(
                contract_name=_contract_name, contract_address=test_address
            )
            assert (
                contract.abi == AsyncContractUtils.get_contract_code(_contract_name)[0]
            )
            assert contract.bytecode is None
            assert contract.bytecode_runtime is None
            assert contract.address == test_address

    # <Normal_2>
    # Contract factory cache is scoped by AsyncWeb3 instance
    @pytest.mark.asyncio
    async def test_normal_2(self, monkeypatch: pytest.MonkeyPatch):
        web3_1 = AsyncWeb3(AsyncHTTPProvider("http://127.0.0.1:8545"))
        web3_2 = AsyncWeb3(AsyncHTTPProvider("http://127.0.0.1:8545"))

        contract_module.AsyncContractUtils.factory_map.clear()

        monkeypatch.setattr(contract_module.async_web3, "get_web3", lambda: web3_1)
        contract_1 = AsyncContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address="0x0000000000000000000000000000000000000001",
        )

        monkeypatch.setattr(contract_module.async_web3, "get_web3", lambda: web3_2)
        contract_2 = AsyncContractUtils.get_contract(
            contract_name="IbetShare",
            contract_address="0x0000000000000000000000000000000000000002",
        )

        assert cast(Any, contract_1).w3 is web3_1
        assert cast(Any, contract_2).w3 is web3_2
        assert len(contract_module.AsyncContractUtils.factory_map) == 2
        assert len(contract_module.AsyncContractUtils.factory_map[web3_1]) == 1
        assert len(contract_module.AsyncContractUtils.factory_map[web3_2]) == 1

        contract_module.AsyncContractUtils.factory_map.clear()

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Contract address is not address
    @pytest.mark.asyncio
    async def test_error_1(self):
        with pytest.raises(ValueError):
            AsyncContractUtils.get_contract(
                contract_name="IbetShare",
                contract_address="0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6ZZZZ",  # too long
            )

    # <Error_2>
    # Contract does not exist
    @pytest.mark.asyncio
    async def test_error_2(self):
        with pytest.raises(FileNotFoundError):
            AsyncContractUtils.get_contract(
                contract_name="NotExistContract",
                contract_address="0x986eBe386b1D04C8d57387b60628fD8BBeEFF1b6",
            )


# Test for AsyncWeb3 scope
class TestAsyncWeb3Wrapper:
    # <Normal_1>
    # Request timeout is normalized to ClientTimeout
    def test_normal_1(self):
        loop = asyncio.new_event_loop()
        wrapper = AsyncWeb3Wrapper(5)

        try:
            async_web3 = loop.run_until_complete(_get_web3(wrapper))
        finally:
            loop.close()

        timeout = cast(Any, async_web3.provider)._request_kwargs["timeout"]
        assert isinstance(timeout, ClientTimeout)
        assert timeout.total == 5

    # <Normal_2>
    # AsyncWeb3 instance is scoped by event loop
    def test_normal_2(self):
        wrapper = AsyncWeb3Wrapper()
        loops: list[asyncio.AbstractEventLoop] = []

        def get_web3_for_new_loop() -> AsyncWeb3[AsyncHTTPProvider]:
            loop = asyncio.new_event_loop()
            loops.append(loop)
            return loop.run_until_complete(_get_web3(wrapper))

        async_web3_1 = get_web3_for_new_loop()
        async_web3_2 = get_web3_for_new_loop()

        try:
            assert async_web3_1 is not async_web3_2
        finally:
            for loop in loops:
                loop.close()

    # <Normal_3>
    # Async provider uses the shared keep-alive session manager
    def test_normal_3(self):
        loop = asyncio.new_event_loop()
        wrapper = AsyncWeb3Wrapper()

        try:
            async_web3 = loop.run_until_complete(_get_web3(wrapper))
        finally:
            loop.close()

        session_manager = cast(Any, async_web3.provider)._request_session_manager
        assert isinstance(session_manager, KeepAliveHTTPSessionManager)


# Test for send_transaction
class TestSendTransaction:
    test_account = default_eth_account("user1")
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
    contract_file = f"contracts/ibet/{test_contract_name}.json"
    contract_json = json.load(open(contract_file, "r"))

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db: AsyncSession):
        # Contract
        contract: Any = web3.eth.contract(
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

        rtn_tx_hash, rtn_receipt = await AsyncContractUtils.send_transaction(
            transaction=tx, private_key=self.private_key
        )

        assert rtn_tx_hash == rtn_receipt["transactionHash"].to_0x_hex()
        assert rtn_receipt["status"] == 1
        assert rtn_receipt["to"] is None
        assert rtn_receipt["from"] == self.test_account["address"]
        assert web3.is_address(rtn_receipt["contractAddress"])

    # <Normal_2>
    # Pending nonce is used for signing and engine is disposed after sending
    @pytest.mark.asyncio
    async def test_normal_2(self):
        fake_engine = MagicMock()
        fake_engine.dispose = AsyncMock()
        fake_session = MagicMock()
        fake_session.scalars = AsyncMock(
            return_value=MagicMock(first=MagicMock(return_value=None))
        )
        fake_session.rollback = AsyncMock()
        fake_session.close = AsyncMock()
        fake_signed_tx = MagicMock()
        fake_signed_tx.raw_transaction.to_0x_hex.return_value = "0xsigned"
        fake_tx_hash = MagicMock()
        fake_tx_hash.to_0x_hex.return_value = "0xhash"
        fake_receipt = {"status": 1, "transactionHash": fake_tx_hash}

        with (
            patch(
                "app.utils.ibet_contract_utils.create_async_engine",
                return_value=fake_engine,
            ),
            patch(
                "app.utils.ibet_contract_utils.AsyncSession", return_value=fake_session
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction_count",
                AsyncMock(return_value=7),
            ) as get_transaction_count,
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.account.sign_transaction",
                return_value=fake_signed_tx,
            ) as sign_transaction,
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.send_raw_transaction",
                AsyncMock(return_value=fake_tx_hash),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.wait_for_transaction_receipt",
                AsyncMock(return_value=fake_receipt),
            ),
        ):
            rtn_tx_hash, rtn_receipt = await AsyncContractUtils.send_transaction(
                transaction={"from": self.test_account["address"]},
                private_key=self.private_key,
            )

        get_transaction_count.assert_awaited_once_with(
            self.test_account["address"], block_identifier="pending"
        )
        sign_transaction.assert_called_once_with(
            transaction_dict={"from": self.test_account["address"], "nonce": 7},
            private_key=self.private_key,
        )
        assert rtn_tx_hash == "0xhash"
        assert rtn_receipt == fake_receipt
        fake_session.scalars.assert_awaited_once()
        fake_session.rollback.assert_awaited_once()
        fake_session.close.assert_awaited_once()
        fake_engine.dispose.assert_awaited_once()

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Transaction REVERT(Deploying invalid bytecode)
    @pytest.mark.asyncio
    async def test_error_1(self, async_db: AsyncSession):
        # Contract
        contract: Any = web3.eth.contract(
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
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            return_value={"dummy": "hoge", "status": 0},
        )
        InspectionMock = patch(
            target="web3.eth.async_eth.AsyncEth.call",
            side_effect=ContractLogicError("execution reverted"),
        )

        with Web3_send_raw_transaction, InspectionMock:
            with pytest.raises(ContractRevertError):
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=self.private_key
                )

    # <Error_2>
    # Value Error
    @pytest.mark.asyncio
    async def test_error_2(self, async_db: AsyncSession):
        # Contract
        contract: Any = web3.eth.contract(
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
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=Web3Exception,
        )

        with Web3_send_raw_transaction:
            with pytest.raises(Web3Exception):
                await AsyncContractUtils.send_transaction(
                    transaction=tx, private_key=self.private_key
                )

    # <Error_3>
    # Timeout waiting for lock release
    @pytest.mark.asyncio
    async def test_error_3(self, async_db: AsyncSession):
        # prepare data : TX lock
        _tx_mng = TransactionLock()
        _tx_mng.tx_from = self.test_account["address"]
        async_db.add(_tx_mng)
        await async_db.commit()

        # Contract
        contract: Any = web3.eth.contract(
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
        (
            await async_db.scalars(
                select(TransactionLock)
                .where(TransactionLock.tx_from == self.test_account["address"])
                .limit(1)
                .with_for_update()
            )
        ).first()

        with pytest.raises(SendTransactionError) as ex_info:
            await AsyncContractUtils.send_transaction(
                transaction=tx, private_key=self.private_key
            )
        assert ex_info.typename == "SendTransactionError"

        await async_db.rollback()

    # <Error_4>
    # Transaction REVERT when revert replay unexpectedly succeeds
    @pytest.mark.asyncio
    async def test_error_4(self):
        fake_engine = MagicMock()
        fake_engine.dispose = AsyncMock()
        fake_session = MagicMock()
        fake_session.scalars = AsyncMock(
            return_value=MagicMock(first=MagicMock(return_value=None))
        )
        fake_session.rollback = AsyncMock()
        fake_session.close = AsyncMock()
        fake_signed_tx = MagicMock()
        fake_signed_tx.raw_transaction.to_0x_hex.return_value = "0xsigned"
        fake_tx_hash = MagicMock()
        fake_tx_hash.to_0x_hex.return_value = "0xhash"
        fake_receipt = {"status": 0, "transactionHash": fake_tx_hash}
        fake_tx = {
            "to": ZERO_ADDRESS,
            "from": self.test_account["address"],
            "value": 0,
            "input": HexBytes("0x1234"),
            "blockNumber": 10,
        }

        with (
            patch(
                "app.utils.ibet_contract_utils.create_async_engine",
                return_value=fake_engine,
            ),
            patch(
                "app.utils.ibet_contract_utils.AsyncSession", return_value=fake_session
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction_count",
                AsyncMock(return_value=7),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.account.sign_transaction",
                return_value=fake_signed_tx,
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.send_raw_transaction",
                AsyncMock(return_value=fake_tx_hash),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.wait_for_transaction_receipt",
                AsyncMock(return_value=fake_receipt),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                AsyncMock(return_value=fake_tx),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.call",
                AsyncMock(return_value=HexBytes("0x")),
            ),
        ):
            with pytest.raises(ContractRevertError) as exc_info:
                await AsyncContractUtils.send_transaction(
                    transaction={"from": self.test_account["address"]},
                    private_key=self.private_key,
                )

        assert exc_info.value.code == 0
        assert exc_info.value.message == ""


# Test for send_transaction_no_wait and wait_for_transaction_receipt
class TestSendTransactionNoWait:
    test_account = default_eth_account("user1")
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
    contract_file = f"contracts/ibet/{test_contract_name}.json"
    contract_json = json.load(open(contract_file, "r"))

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db: AsyncSession):
        # Contract
        contract: Any = web3.eth.contract(
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

        # Call send_transaction_no_wait
        rtn_tx_hash = await AsyncContractUtils.send_transaction_no_wait(
            transaction=tx, private_key=self.private_key
        )
        assert rtn_tx_hash is not None

        # Call wait_for_transaction_receipt
        rtn_receipt = await AsyncContractUtils.wait_for_transaction_receipt(rtn_tx_hash)
        assert rtn_tx_hash == rtn_receipt["transactionHash"].to_0x_hex()
        assert rtn_receipt["status"] == 1
        assert rtn_receipt["to"] is None
        assert rtn_receipt["from"] == self.test_account["address"]
        assert web3.is_address(rtn_receipt["contractAddress"])

    # <Normal_2>
    # Consecutive sends use fresh pending nonces and dispose their engines
    @pytest.mark.asyncio
    async def test_normal_2(self):
        fake_engine = MagicMock()
        fake_engine.dispose = AsyncMock()
        fake_session = MagicMock()
        fake_session.scalars = AsyncMock(
            return_value=MagicMock(first=MagicMock(return_value=None))
        )
        fake_session.rollback = AsyncMock()
        fake_session.close = AsyncMock()
        fake_signed_tx = MagicMock()
        fake_signed_tx.raw_transaction.to_0x_hex.return_value = "0xsigned"
        fake_tx_hash = MagicMock()
        fake_tx_hash.to_0x_hex.return_value = "0xhash"

        with (
            patch(
                "app.utils.ibet_contract_utils.create_async_engine",
                return_value=fake_engine,
            ),
            patch(
                "app.utils.ibet_contract_utils.AsyncSession", return_value=fake_session
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction_count",
                AsyncMock(side_effect=[7, 8]),
            ) as get_transaction_count,
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.account.sign_transaction",
                return_value=fake_signed_tx,
            ) as sign_transaction,
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.send_raw_transaction",
                AsyncMock(return_value=fake_tx_hash),
            ),
        ):
            for nonce in (7, 8):
                rtn_tx_hash = await AsyncContractUtils.send_transaction_no_wait(
                    transaction={"from": self.test_account["address"]},
                    private_key=self.private_key,
                )
                assert rtn_tx_hash == "0xhash"
                sign_transaction.assert_called_with(
                    transaction_dict={
                        "from": self.test_account["address"],
                        "nonce": nonce,
                    },
                    private_key=self.private_key,
                )

        assert get_transaction_count.await_args_list == [
            call(self.test_account["address"], block_identifier="pending"),
            call(self.test_account["address"], block_identifier="pending"),
        ]
        assert sign_transaction.call_count == 2
        assert fake_session.scalars.await_count == 2
        assert fake_session.rollback.await_count == 2
        assert fake_session.close.await_count == 2
        assert fake_engine.dispose.await_count == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # send_transaction_no_wait
    # Lock timeout
    @pytest.mark.asyncio
    async def test_error_1(self, async_db: AsyncSession):
        # prepare data : TX lock
        _tx_mng = TransactionLock()
        _tx_mng.tx_from = self.test_account["address"]
        async_db.add(_tx_mng)
        await async_db.commit()

        # Contract
        contract: Any = web3.eth.contract(
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
        (
            await async_db.scalars(
                select(TransactionLock)
                .where(TransactionLock.tx_from == self.test_account["address"])
                .limit(1)
                .with_for_update()
            )
        ).first()

        # Call send_transaction_no_wait
        with pytest.raises(SendTransactionError):
            await AsyncContractUtils.send_transaction_no_wait(
                transaction=tx, private_key=self.private_key
            )

        await async_db.rollback()

    # <Error_2>
    # wait_for_transaction_receipt
    # TimeExhausted
    @pytest.mark.asyncio
    async def test_error_2(self, async_db: AsyncSession):
        # prepare data : TX lock
        _tx_mng = TransactionLock()
        _tx_mng.tx_from = self.test_account["address"]
        async_db.add(_tx_mng)
        await async_db.commit()

        # Contract
        contract: Any = web3.eth.contract(
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

        # Call send_transaction_no_wait
        rtn_tx_hash = await AsyncContractUtils.send_transaction_no_wait(
            transaction=tx, private_key=self.private_key
        )
        assert rtn_tx_hash is not None

        mocked_wait_for_tx = patch(
            target="web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            side_effect=TimeExhausted(),
        )

        # Call wait_for_transaction_receipt
        with mocked_wait_for_tx:
            with pytest.raises(TimeExhausted):
                await AsyncContractUtils.wait_for_transaction_receipt(rtn_tx_hash)


# Test for get_block_by_transaction_hash
class TestGetBlockByTransactionHash:
    test_account = default_eth_account("user1")
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
    contract_file = f"contracts/ibet/{test_contract_name}.json"
    contract_json = json.load(open(contract_file, "r"))

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db: AsyncSession):
        # Contract
        contract: Any = web3.eth.contract(
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
        nonce = web3.eth.get_transaction_count(
            Web3.to_checksum_address(self.test_account["address"])
        )
        tx["nonce"] = nonce
        signed_tx = web3.eth.account.sign_transaction(
            transaction_dict=tx, private_key=self.private_key
        )

        # Send Transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction.to_0x_hex())
        tx_receipt = web3.eth.wait_for_transaction_receipt(
            transaction_hash=tx_hash, timeout=10
        )

        block = await AsyncContractUtils.get_block_by_transaction_hash(tx_hash)
        block_number = block.get("number")
        block_timestamp = block.get("timestamp")
        assert block_number == tx_receipt["blockNumber"]
        assert block_timestamp is not None
        assert block_timestamp > 0


# Test for inspect_tx_failure
class TestInspectTxFailure:
    tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    base_tx: dict[str, Any] = {
        "to": ZERO_ADDRESS,
        "from": default_eth_account("user1")["address"],
        "value": 0,
        "input": HexBytes("0xdeadbeef"),
        "blockNumber": 10,
    }

    ###########################################################################
    # Normal Case
    ###########################################################################
    # <Normal_1>
    # Extract revert code or message (including contract creation with to=None)
    @pytest.mark.asyncio
    async def test_normal_1(self):
        with (
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                AsyncMock(return_value=self.base_tx),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.call",
                AsyncMock(side_effect=ContractLogicError("execution reverted: 110902")),
            ) as eth_call,
        ):
            assert await AsyncContractUtils.inspect_tx_failure(self.tx_hash) == "110902"

        eth_call.assert_awaited_once_with(
            {
                "from": self.base_tx["from"],
                "value": 0,
                "data": b"\xde\xad\xbe\xef",
                "to": ZERO_ADDRESS,
            },
            9,
        )

        deploy_tx = {**self.base_tx, "to": None}
        with (
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                AsyncMock(return_value=deploy_tx),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.call",
                AsyncMock(side_effect=ContractLogicError("execution reverted")),
            ) as deploy_call,
        ):
            assert (
                await AsyncContractUtils.inspect_tx_failure(self.tx_hash)
                == "execution reverted"
            )

        deploy_call.assert_awaited_once_with(
            {
                "from": self.base_tx["from"],
                "value": 0,
                "data": b"\xde\xad\xbe\xef",
            },
            9,
        )

    ###########################################################################
    # Error Case
    ###########################################################################
    # <Error_1>
    # Unavailable or unmined transaction state returns None
    @pytest.mark.asyncio
    async def test_error_1(self):
        for invalid_tx in (
            None,
            {**self.base_tx, "blockNumber": None},
            {**self.base_tx, "blockNumber": 0},
            {**self.base_tx, "from": None},
        ):
            with patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                AsyncMock(return_value=invalid_tx),
            ):
                assert await AsyncContractUtils.inspect_tx_failure(self.tx_hash) is None

    # <Error_2>
    # Transaction lookup RPC error logs warning and returns None
    @pytest.mark.asyncio
    async def test_error_2(self):
        with (
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                AsyncMock(side_effect=Web3Exception("RPC unavailable")),
            ),
            patch.object(contract_module.LOG, "warning") as log_warning,
        ):
            assert await AsyncContractUtils.inspect_tx_failure(self.tx_hash) is None

        log_warning.assert_called_once()
        assert (
            "Failed to get transaction for revert inspection:"
            in log_warning.call_args.args[0]
        )

    # <Error_3>
    # Replay RPC error or empty ContractLogicError logs warning and returns None
    @pytest.mark.asyncio
    async def test_error_3(self):
        for exc, expected_log in (
            (
                Web3Exception("missing trie node"),
                "Failed to replay transaction revert:",
            ),
            (
                ContractLogicError(),
                "Failed to inspect transaction revert:",
            ),
        ):
            with (
                patch(
                    "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                    AsyncMock(return_value=self.base_tx),
                ),
                patch(
                    "app.utils.ibet_contract_utils.async_web3.eth.call",
                    AsyncMock(side_effect=exc),
                ),
                patch.object(contract_module.LOG, "warning") as log_warning,
            ):
                assert await AsyncContractUtils.inspect_tx_failure(self.tx_hash) is None

            log_warning.assert_called_once()
            assert expected_log in log_warning.call_args.args[0]

    # <Error_4>
    # Unexpectedly successful replay logs warning and returns None
    @pytest.mark.asyncio
    async def test_error_4(self):
        with (
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.get_transaction",
                AsyncMock(return_value=self.base_tx),
            ),
            patch(
                "app.utils.ibet_contract_utils.async_web3.eth.call",
                AsyncMock(return_value=HexBytes("0x")),
            ),
            patch.object(contract_module.LOG, "warning") as log_warning,
        ):
            assert await AsyncContractUtils.inspect_tx_failure(self.tx_hash) is None

        log_warning.assert_called_once()
        assert (
            "Transaction replay unexpectedly succeeded:"
            in log_warning.call_args.args[0]
        )
