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

from binascii import Error
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from eth_keyfile import decode_keyfile_json
from web3 import Web3
from web3.exceptions import ContractLogicError, InvalidAddress, ValidationError
from web3.middleware import ExtraDataToPOAMiddleware

import config
from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.token_list import TokenListContract
from app.model.db import TokenType
from app.utils.contract_utils import ContractUtils
from config import WEB3_HTTP_PROVIDER, ZERO_ADDRESS
from tests.account_config import config_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


@pytest.fixture
def contract_list(db):
    test_account = config_eth_account("user1")
    deployer_address = test_account.get("address")
    private_key = decode_keyfile_json(
        raw_keyfile_json=test_account.get("keyfile_json"),
        password=test_account.get("password").encode("utf-8"),
    )
    contract_address, _, _ = ContractUtils.deploy_contract(
        contract_name="TokenList",
        args=[],
        deployer=deployer_address,
        private_key=private_key,
    )
    config.TOKEN_LIST_CONTRACT_ADDRESS = contract_address


class TestRegisterTokenList:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1> token_template is IbetShare
    @pytest.mark.asyncio
    async def test_normal_1(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # execute the function
        arguments = [
            "テスト株式",
            "TEST",
            10000,
            20000,
            1,
            "20211231",
            "20211231",
            "20221231",
            10000,
        ]
        share_contract = IbetShareContract()
        share_token_address, _, _ = await share_contract.create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
            token_address=share_token_address,
            token_template=TokenType.IBET_SHARE.value,
            tx_from=issuer_address,
            private_key=private_key,
        )

        # assertion : list length
        token_list_contract = ContractUtils.get_contract(
            contract_name="TokenList",
            contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
        )
        assert token_list_contract.functions.getListLength().call() == 1

        # execute the function : IbetStraightBondContract
        arguments = [
            "テスト債券",
            "TEST",
            10000,
            20000,
            "JPY",
            "20211231",
            30000,
            "JPY",
            "20211231",
            "リターン内容",
            "発行目的",
        ]
        bond_token_address, _, _ = await IbetStraightBondContract().create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )

        await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
            token_address=bond_token_address,
            token_template=TokenType.IBET_STRAIGHT_BOND.value,
            tx_from=issuer_address,
            private_key=private_key,
        )

        # assertion
        token_list_contract = ContractUtils.get_contract(
            contract_name="TokenList",
            contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
        )
        assert token_list_contract.functions.getListLength().call() == 2
        _share_token = token_list_contract.functions.getTokenByAddress(
            share_token_address
        ).call()
        assert _share_token[0] == share_token_address
        assert _share_token[1] == TokenType.IBET_SHARE.value
        assert _share_token[2] == issuer_address
        _bond_token = token_list_contract.functions.getTokenByAddress(
            bond_token_address
        ).call()
        assert _bond_token[0] == bond_token_address
        assert _bond_token[1] == TokenType.IBET_STRAIGHT_BOND.value
        assert _bond_token[2] == issuer_address

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1> Invalid argument: token_address
    @pytest.mark.asyncio
    async def test_error_1(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        with pytest.raises(SendTransactionError) as exc_info:
            await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address="dummy_token_address",
                token_template=TokenType.IBET_SHARE.value,
                tx_from=issuer_address,
                private_key=private_key,
            )
        assert isinstance(exc_info.value.args[0], ValidationError)

    # <Error_2> Invalid argument: token_list_address
    @pytest.mark.asyncio
    async def test_error_2(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        with pytest.raises(SendTransactionError) as exc_info:
            await TokenListContract("dummy_token_list_address").register(
                token_address=ZERO_ADDRESS,
                token_template=TokenType.IBET_STRAIGHT_BOND.value,
                tx_from=issuer_address,
                private_key=private_key,
            )
        assert isinstance(exc_info.value.args[0], ValueError)

    # <Error_3> Invalid argument: account_address
    @pytest.mark.asyncio
    async def test_error_3(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        with pytest.raises(SendTransactionError) as exc_info:
            await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address=ZERO_ADDRESS,
                token_template=TokenType.IBET_SHARE.value,
                tx_from=issuer_address[:-1],
                private_key=private_key,
            )
        assert isinstance(exc_info.value.args[0], InvalidAddress)

    # <Error_4> Invalid argument: private_key
    @pytest.mark.asyncio
    async def test_error_4(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")

        with pytest.raises(SendTransactionError) as exc_info:
            await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address=ZERO_ADDRESS,
                token_template=TokenType.IBET_SHARE.value,
                tx_from=issuer_address,
                private_key="not private key",
            )
        assert isinstance(exc_info.value.args[0], Error)

    # <Error_5> SendTransactionError : ContractUtils
    @pytest.mark.asyncio
    async def test_error_5(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # mock
        ContractUtils_send_transaction = patch(
            target="app.utils.contract_utils.AsyncContractUtils.send_transaction",
            side_effect=SendTransactionError(),
        )

        # execute the function
        with ContractUtils_send_transaction:
            with pytest.raises(SendTransactionError):
                await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                    token_address=ZERO_ADDRESS,
                    token_template=TokenType.IBET_SHARE.value,
                    tx_from=issuer_address,
                    private_key=private_key,
                )

    # <Error_6> Transaction REVERT(token address is zero)
    @pytest.mark.asyncio
    async def test_error_6(self, db, contract_list):
        test_account = config_eth_account("user1")
        issuer_address = test_account.get("address")
        private_key = decode_keyfile_json(
            raw_keyfile_json=test_account.get("keyfile_json"),
            password=test_account.get("password").encode("utf-8"),
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted: 100001")),
        )

        # execute the function
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address=ZERO_ADDRESS,
                token_template=TokenType.IBET_SHARE.value,
                tx_from=issuer_address,
                private_key=private_key,
            )

        # assertion
        assert exc_info.value.args[0] == "The address has already been registered."
