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

import pytest

from app.model.eth import ERC20
from app.utils.eth_contract_utils import EthAsyncContractUtils
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account


async def deploy_token(
    name: str,
    deployer: dict,
    owner: dict,
) -> str:
    """
    Deploy an ERC20 token contract.

    :param name: Name of the contract to deploy.
    :param deployer: Address of the deployer.
    :param owner: Address of the owner of the contract.
    :return: Transaction hash of the deployment.
    """
    tx_hash, _ = await EthAsyncContractUtils.deploy_contract(
        contract_name="IbetERC20",
        args=[
            name,
            owner["address"],
        ],
        deployer=deployer["address"],
        private_key=bytes.fromhex(deployer["private_key"]),
    )
    tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.get("contractAddress")
    return contract_address


async def mint_token(
    contract_address: str,
    to: str,
    value: int,
    tx_from: dict,
) -> None:
    """
    Mint tokens to a specified recipient.

    :param contract_address: Address of the ERC20 contract.
    :param to: Address of the recipient.
    :param value: Value of tokens to mint.
    :param tx_from: Owner of the contract.
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="IbetERC20",
        contract_address=contract_address,
    )

    # Mint tokens
    tx = await contract.functions.mint(to, value).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash, _ = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


async def approve_token(
    contract_address: str,
    spender: str,
    value: int,
    tx_from: dict,
) -> None:
    """
    Approve a spender to spend tokens on behalf of the owner.

    :param contract_address: Address of the ERC20 contract.
    :param spender: Address of the spender.
    :param value: Value of tokens to approve.
    :param tx_from: Owner of the contract.
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="IbetERC20",
        contract_address=contract_address,
    )

    # Approve spender
    tx = await contract.functions.approve(spender, value).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash, _ = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


@pytest.mark.asyncio
class TestName:
    """
    Test ERC20 contract name
    """

    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that the name function returns the correct token name after deploying the contract.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_token("Test Token", self.deployer, self.issuer)

        # Generate contract instance
        contract = ERC20(contract_address)

        # Call name function
        name = await contract.name()

        # Assert that the name is correct
        assert name == "Test Token"

    # Normal_2
    # - Test that the name function returns an empty string when called on a contract at the zero address.
    async def test_normal_2(self):
        # Generate contract instance
        contract = ERC20(ZERO_ADDRESS)

        # Call name function
        name = await contract.name()

        # Assert that the name is an empty string
        assert name == ""


@pytest.mark.asyncio
class TestBalanceOf:
    """
    Test ERC20 contract balanceOf function
    """

    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")
    user1 = default_eth_account("user3")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that the balanceOf function returns the correct balance
    #   after deploying the contract and transferring tokens.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_token("Test Token", self.deployer, self.issuer)

        # Mint tokens to user1
        await mint_token(
            contract_address=contract_address,
            to=self.user1["address"],
            value=1000,
            tx_from=self.issuer,
        )

        # Generate contract instance
        contract = ERC20(contract_address)

        # Call balanceOf function
        balance = await contract.balance_of(self.user1["address"])

        # Assert that the balance is correct
        assert balance == 1000

    # Normal_2
    # - Test that the balanceOf function returns zero
    #   when called on a contract which has not been deployed.
    async def test_normal_2(self):
        # Generate contract instance
        contract = ERC20(ZERO_ADDRESS)

        # Call balanceOf function
        balance = await contract.balance_of(self.user1["address"])

        # Assert that the balance is correct
        assert balance == 0


@pytest.mark.asyncio
class TestAllowance:
    """
    Test ERC20 contract allowance function
    """

    deployer = default_eth_account("user1")
    issuer = default_eth_account("user2")
    user1 = default_eth_account("user3")
    user2 = default_eth_account("user4")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that the allowance function returns the correct allowance
    #   after deploying the contract and approving a spender.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_token("Test Token", self.deployer, self.issuer)

        # Mint tokens to user1
        await mint_token(
            contract_address=contract_address,
            to=self.user1["address"],
            value=1000,
            tx_from=self.issuer,
        )

        # Approve user2 to spend tokens on behalf of user1
        await approve_token(
            contract_address=contract_address,
            spender=self.user2["address"],
            value=500,
            tx_from=self.user1,
        )

        # Generate contract instance
        contract = ERC20(contract_address)

        # Call allowance function
        allowance = await contract.allowance(
            self.user1["address"], self.user2["address"]
        )

        # Assert that the allowance is correct
        assert allowance == 500

    # Normal_2
    # - Test that the allowance function returns zero
    #   when called on a contract which has not been deployed.
    async def test_normal_2(self):
        # Generate contract instance
        contract = ERC20(ZERO_ADDRESS)

        # Call allowance function
        allowance = await contract.allowance(
            self.user1["address"], self.user2["address"]
        )

        # Assert that the allowance is correct
        assert allowance == 0
