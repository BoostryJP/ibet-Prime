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

from unittest import mock
from unittest.mock import MagicMock

import pytest
from eth_keyfile import decode_keyfile_json
from web3 import Web3
from web3.exceptions import ContractLogicError, TimeExhausted
from web3.middleware import ExtraDataToPOAMiddleware

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.ibet import IbetSecurityTokenEscrow, IbetStraightBondContract
from app.model.ibet.tx_params.ibet_security_token_escrow import (
    ApproveTransferParams,
)
from app.utils.ibet_contract_utils import ContractUtils
from config import CHAIN_ID, TX_GAS_LIMIT, WEB3_HTTP_PROVIDER
from tests.account_config import default_eth_account

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def deploy_security_token_escrow_contract():
    deployer = default_eth_account("user1")
    private_key = decode_keyfile_json(
        raw_keyfile_json=deployer["keyfile_json"],
        password=deployer["password"].encode("utf-8"),
    )

    # deploy
    escrow_storage_address, _, _ = ContractUtils.deploy_contract(
        contract_name="EscrowStorage",
        args=[],
        deployer=deployer["address"],
        private_key=private_key,
    )

    escrow_contract_address, _, _ = ContractUtils.deploy_contract(
        contract_name="IbetSecurityTokenEscrow",
        args=[escrow_storage_address],
        deployer=deployer["address"],
        private_key=private_key,
    )
    escrow_contract = ContractUtils.get_contract(
        contract_name="IbetSecurityTokenEscrow",
        contract_address=escrow_contract_address,
    )

    # update storage
    storage_contract = ContractUtils.get_contract(
        contract_name="EscrowStorage", contract_address=escrow_storage_address
    )
    tx = storage_contract.functions.upgradeVersion(
        escrow_contract_address
    ).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": deployer["address"],
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=private_key)

    return escrow_contract


async def issue_bond_token(issuer: dict, exchange_address: str):
    issuer_address = issuer["address"]
    issuer_pk = decode_keyfile_json(
        raw_keyfile_json=issuer.get("keyfile_json"),
        password=issuer.get("password").encode("utf-8"),
    )

    # deploy token
    arguments = [
        "テスト債券",
        "TEST",
        2**256 - 1,
        10000,
        "JPY",
        "20211231",
        10000,
        "JPY",
        "20211231",
        "リターン内容",
        "発行目的",
    ]
    token_contract_address, _, _ = await IbetStraightBondContract().create(
        args=arguments, tx_from=issuer_address, private_key=issuer_pk
    )
    token_contract = ContractUtils.get_contract(
        contract_name="IbetStraightBond", contract_address=token_contract_address
    )
    tx = token_contract.functions.setTransferable(True).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=issuer_pk)

    # set tradable exchange address
    tx = token_contract.functions.setTradableExchange(
        exchange_address
    ).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=issuer_pk)

    # set personal info address
    personal_info_contract_address, _, _ = ContractUtils.deploy_contract(
        "PersonalInfo", [], issuer_address, issuer_pk
    )
    tx = token_contract.functions.setPersonalInfoAddress(
        personal_info_contract_address
    ).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=issuer_pk)

    # set transfer approval required
    tx = token_contract.functions.setTransferApprovalRequired(True).build_transaction(
        {
            "chainId": CHAIN_ID,
            "from": issuer_address,
            "gas": TX_GAS_LIMIT,
            "gasPrice": 0,
        }
    )
    ContractUtils.send_transaction(transaction=tx, private_key=issuer_pk)

    return token_contract


class TestApproveTransfer:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # balance = 0, commitment = 0
    # Default value
    @pytest.mark.asyncio
    async def test_normal_1(self, async_db):
        user1_account = default_eth_account("user1")
        user1_account_pk = decode_keyfile_json(
            raw_keyfile_json=user1_account["keyfile_json"],
            password=user1_account["password"].encode("utf-8"),
        )
        user2_account = default_eth_account("user2")
        user2_account_pk = decode_keyfile_json(
            raw_keyfile_json=user2_account["keyfile_json"],
            password=user2_account["password"].encode("utf-8"),
        )
        user3_account = default_eth_account("user3")

        # deploy contract
        escrow_contract = deploy_security_token_escrow_contract()
        token_contract = await issue_bond_token(
            issuer=user1_account, exchange_address=escrow_contract.address
        )

        # Pre transfer
        personal_info_contract_address = (
            token_contract.functions.personalInfoAddress().call()
        )
        personal_info_contract = ContractUtils.get_contract(
            "PersonalInfo", personal_info_contract_address
        )
        tx = personal_info_contract.functions.register(
            user1_account["address"], "test"
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)
        tx = token_contract.functions.transferFrom(
            user1_account["address"], user2_account["address"], 100
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user1_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user1_account_pk)

        # Deposit escrow
        tx = token_contract.functions.transfer(
            escrow_contract.address, 100
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)

        # Apply for transfer
        tx = escrow_contract.functions.createEscrow(
            token_contract.address,
            user3_account["address"],
            10,
            user2_account["address"],
            "test",
            "test",
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)

        # Finish Escrow
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()
        tx = escrow_contract.functions.finishEscrow(latest_escrow_id).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)

        # test IbetSecurityTokenEscrow.approve_transfer
        security_token_escrow = IbetSecurityTokenEscrow(escrow_contract.address)
        tx_hash, tx_receipt = await security_token_escrow.approve_transfer(
            data=ApproveTransferParams(escrow_id=1, data="test"),
            tx_from=user1_account["address"],
            private_key=user1_account_pk,
        )

        # assertion
        assert isinstance(tx_hash, str) and int(tx_hash, 16) > 0
        assert tx_receipt["status"] == 1

        user2_balance = await security_token_escrow.get_account_balance(
            user2_account["address"], token_contract.address
        )
        assert user2_balance["balance"] == 90
        assert user2_balance["commitment"] == 0

        user3_balance = await security_token_escrow.get_account_balance(
            user3_account["address"], token_contract.address
        )
        assert user3_balance["balance"] == 10
        assert user3_balance["commitment"] == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Send Transaction Failed with HTTP Connection Error
    @pytest.mark.asyncio
    async def test_error_1(self, async_db):
        user1_account = default_eth_account("user1")
        user1_account_pk = decode_keyfile_json(
            raw_keyfile_json=user1_account["keyfile_json"],
            password=user1_account["password"].encode("utf-8"),
        )
        user2_account = default_eth_account("user2")
        user2_account_pk = decode_keyfile_json(
            raw_keyfile_json=user2_account["keyfile_json"],
            password=user2_account["password"].encode("utf-8"),
        )
        user3_account = default_eth_account("user3")

        # deploy contract
        escrow_contract = deploy_security_token_escrow_contract()
        token_contract = await issue_bond_token(
            issuer=user1_account, exchange_address=escrow_contract.address
        )

        # Pre transfer
        personal_info_contract_address = (
            token_contract.functions.personalInfoAddress().call()
        )
        personal_info_contract = ContractUtils.get_contract(
            "PersonalInfo", personal_info_contract_address
        )
        tx = personal_info_contract.functions.register(
            user1_account["address"], "test"
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)
        tx = token_contract.functions.transferFrom(
            user1_account["address"], user2_account["address"], 100
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user1_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user1_account_pk)

        # Deposit escrow
        tx = token_contract.functions.transfer(
            escrow_contract.address, 100
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)

        # Apply for transfer
        tx = escrow_contract.functions.createEscrow(
            token_contract.address,
            user3_account["address"],
            10,
            user2_account["address"],
            "test",
            "test",
        ).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)

        # Finish Escrow
        latest_escrow_id = escrow_contract.functions.latestEscrowId().call()
        tx = escrow_contract.functions.finishEscrow(latest_escrow_id).build_transaction(
            {
                "chainId": CHAIN_ID,
                "from": user2_account["address"],
                "gas": TX_GAS_LIMIT,
                "gasPrice": 0,
            }
        )
        ContractUtils.send_transaction(transaction=tx, private_key=user2_account_pk)

        # mock
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.wait_for_transaction_receipt",
            MagicMock(side_effect=ConnectionError),
        )
        # test IbetSecurityTokenEscrow.approve_transfer
        with InspectionMock, pytest.raises(SendTransactionError) as exc_info:
            security_token_escrow = IbetSecurityTokenEscrow(escrow_contract.address)
            await security_token_escrow.approve_transfer(
                data=ApproveTransferParams(escrow_id=1, data="test"),
                tx_from=user1_account["address"],
                private_key=user1_account_pk,
            )

        cause = exc_info.value.args[0]
        assert isinstance(cause, ConnectionError)

    # <Error_2>
    # Timeout Error
    @pytest.mark.asyncio
    async def test_error_2(self, async_db):
        user1_account = default_eth_account("user1")
        user1_account_pk = decode_keyfile_json(
            raw_keyfile_json=user1_account["keyfile_json"],
            password=user1_account["password"].encode("utf-8"),
        )

        # deploy contract
        exchange_contract = deploy_security_token_escrow_contract()
        _ = await issue_bond_token(
            issuer=user1_account, exchange_address=exchange_contract.address
        )

        # test IbetSecurityTokenEscrow.approve_transfer
        with pytest.raises(SendTransactionError) as exc_info:
            with mock.patch(
                "app.utils.ibet_contract_utils.AsyncContractUtils.send_transaction",
                MagicMock(side_effect=TimeExhausted("Timeout Error test")),
            ):
                security_token_escrow = IbetSecurityTokenEscrow(
                    exchange_contract.address
                )
                await security_token_escrow.approve_transfer(
                    data=ApproveTransferParams(escrow_id=0, data="test"),
                    tx_from=user1_account["address"],
                    private_key=user1_account_pk,
                )

        cause = exc_info.value.args[0]
        assert isinstance(cause, TimeExhausted)
        assert "Timeout Error test" in str(cause)

    # <Error_3>
    # Transaction REVERT
    # Not apply
    @pytest.mark.asyncio
    async def test_error_3(self, async_db):
        user1_account = default_eth_account("user1")
        user1_account_pk = decode_keyfile_json(
            raw_keyfile_json=user1_account["keyfile_json"],
            password=user1_account["password"].encode("utf-8"),
        )

        # deploy contract
        exchange_contract = deploy_security_token_escrow_contract()
        _ = await issue_bond_token(
            issuer=user1_account, exchange_address=exchange_contract.address
        )

        # mock
        #   hardhatがrevertする際にweb3.pyからraiseされるExceptionはGethと異なるためモック化する。
        #   geth: ContractLogicError("execution reverted: ")
        InspectionMock = mock.patch(
            "web3.eth.async_eth.AsyncEth.call",
            MagicMock(side_effect=ContractLogicError("execution reverted")),
        )

        # test IbetSecurityTokenEscrow.approve_transfer
        with InspectionMock, pytest.raises(ContractRevertError) as exc_info:
            security_token_escrow = IbetSecurityTokenEscrow(exchange_contract.address)
            await security_token_escrow.approve_transfer(
                data=ApproveTransferParams(escrow_id=0, data="test"),
                tx_from=user1_account["address"],
                private_key=user1_account_pk,
            )

        assert exc_info.value.args[0] == "execution reverted"
