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

from app.model.eth import IbetWST, IbetWSTTrade
from app.utils.eth_contract_utils import EthAsyncContractUtils
from config import ZERO_ADDRESS
from tests.account_config import default_eth_account


async def deploy_wst_token(
    name: str,
    deployer: dict,
    owner: dict,
) -> str:
    """
    Deploy an AuthIbetWST token contract.

    :param name: Name of the contract to deploy.
    :param deployer: Address of the deployer.
    :param owner: Address of the owner of the contract.
    :return: Transaction hash of the deployment.
    """
    tx_hash = await EthAsyncContractUtils.deploy_contract(
        contract_name="AuthIbetWST",
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


async def mint_wst_token(
    contract_address: str,
    to: str,
    amount: int,
    tx_from: dict,
) -> None:
    """
    Mint WST tokens to a specified recipient.

    :param contract_address: Address of the ERC20 contract.
    :param to: Address of the recipient.
    :param amount: Amount of tokens to mint.
    :param tx_from: Transaction sender (owner of the contract).
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="AuthIbetWST",
        contract_address=contract_address,
    )

    # Mint tokens
    tx = await contract.functions.mint(to, amount).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


async def wst_add_account_to_whitelist(
    contract_address: str,
    account: str,
    tx_from: dict,
) -> None:
    """
    Add an account to the WST whitelist.

    :param contract_address: Address of the AuthIbetWST contract.
    :param account: Address of the account to add to the whitelist.
    :param tx_from: Transaction sender (owner of the contract).
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="AuthIbetWST",
        contract_address=contract_address,
    )

    # Add account to whitelist
    tx = await contract.functions.addAccountWhiteList(account).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


async def wst_request_trade(
    contract_address: str,
    buyer_st_account: str,
    sc_token_address: str,
    seller_sc_account: str,
    buyer_sc_account: str,
    st_value: int,
    sc_value: int,
    memo: str,
    tx_from: dict,
) -> None:
    """
    Request a trade on the AuthIbetWST contract.

    :param contract_address: Address of the AuthIbetWST contract.
    :param buyer_st_account: Buyer's ST account address.
    :param sc_token_address: SC token address.
    :param seller_sc_account: Seller's SC account address.
    :param buyer_sc_account: Buyer's SC account address.
    :param st_value: ST value for the trade.
    :param sc_value: SC value for the trade.
    :param memo: Memo for the trade.
    :param tx_from: Transaction sender.
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="AuthIbetWST",
        contract_address=contract_address,
    )

    # Request trade
    tx = await contract.functions.requestTrade(
        buyer_st_account,
        sc_token_address,
        seller_sc_account,
        buyer_sc_account,
        st_value,
        sc_value,
        memo,
    ).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


async def deploy_erc20_token(
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
    tx_hash = await EthAsyncContractUtils.deploy_contract(
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


async def mint_erc20_token(
    contract_address: str,
    to: str,
    amount: int,
    tx_from: dict,
) -> None:
    """
    Mint ERC20 tokens to a specified recipient.

    :param contract_address: Address of the ERC20 contract.
    :param to: Address of the recipient.
    :param amount: Amount of tokens to mint.
    :param tx_from: Transaction sender (owner of the contract).
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="IbetERC20",
        contract_address=contract_address,
    )

    # Mint tokens
    tx = await contract.functions.mint(to, amount).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


async def erc20_approve_token(
    contract_address: str,
    spender: str,
    amount: int,
    tx_from: dict,
) -> None:
    """
    Approve a spender to spend ERC20 tokens on behalf of the owner.

    :param contract_address: Address of the ERC20 contract.
    :param spender: Address of the spender.
    :param amount: Amount of tokens to approve.
    :param tx_from: Transaction sender.
    """
    # Get contract
    contract = EthAsyncContractUtils.get_contract(
        contract_name="IbetERC20",
        contract_address=contract_address,
    )

    # Approve tokens
    tx = await contract.functions.approve(spender, amount).build_transaction(
        {
            "from": tx_from["address"],
            "gas": 2000000,
        }
    )
    tx_hash = await EthAsyncContractUtils.send_transaction(
        transaction=tx,
        private_key=bytes.fromhex(tx_from["private_key"]),
    )
    await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)


@pytest.mark.asyncio
class TestAccountWhitelist:
    """
    Test cases for the account_white_list function of the AuthIbetWST contract.
    """

    deployer = default_eth_account("user1")
    owner = default_eth_account("user2")
    user1 = default_eth_account("user3")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that an account can be added to the whitelist and checked successfully.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address, self.user1["address"], self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Call account_white_list function
        is_white_listed = await contract.account_white_list(self.user1["address"])

        # Assert that the address is whitelisted
        assert is_white_listed is True

    # Normal_2
    # - Test that an address not in the whitelist returns false.
    async def test_normal_2(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Call name function
        is_white_listed = await contract.account_white_list(ZERO_ADDRESS)

        # Assert that the address is not whitelisted
        assert is_white_listed is False


@pytest.mark.asyncio
class TestAddAccountWhiteListWithAuthorization:
    """
    Test cases for the add_account_white_list_with_authorization function of the AuthIbetWST contract.
    """

    deployer = default_eth_account("user1")
    relayer = deployer
    owner = default_eth_account("user2")
    user1 = default_eth_account("user3")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that an account can be added to the whitelist with authorization.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to add account to whitelist with invalid authorization
        tx_hash = await contract.add_account_white_list_with_authorization(
            account=self.user1["address"],
            authorizer_key=bytes.fromhex(self.owner["private_key"]),
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check if the account is whitelisted
        is_white_listed = await contract.account_white_list(self.user1["address"])
        assert is_white_listed is True

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to add an account to the whitelist
    #   with invalid authorization.
    async def test_error_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to add account to whitelist with invalid authorization
        tx_hash = await contract.add_account_white_list_with_authorization(
            account=self.user1["address"],
            authorizer_key=bytes.fromhex(
                self.user1["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0  # Transaction failed

        # Check if the account is whitelisted
        is_white_listed = await contract.account_white_list(self.user1["address"])
        assert is_white_listed is False


@pytest.mark.asyncio
class TestDeleteAccountWhiteListWithAuthorization:
    """
    Test cases for the delete_account_white_list_with_authorization function of the AuthIbetWST contract.
    """

    deployer = default_eth_account("user1")
    relayer = deployer
    owner = default_eth_account("user2")
    user1 = default_eth_account("user3")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that an account can be removed from the whitelist with authorization.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=contract_address,
            account=self.user1["address"],
            tx_from=self.owner,
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to remove account from whitelist with valid authorization
        tx_hash = await contract.delete_account_white_list_with_authorization(
            account=self.user1["address"],
            authorizer_key=bytes.fromhex(self.owner["private_key"]),
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check if the account is deleted from the whitelist
        is_white_listed = await contract.account_white_list(self.user1["address"])
        assert is_white_listed is False

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to remove an account from the whitelist
    #   with invalid authorization.
    async def test_error_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address, self.user1["address"], self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to remove account from whitelist with invalid authorization
        tx_hash = await contract.delete_account_white_list_with_authorization(
            account=self.user1["address"],
            authorizer_key=bytes.fromhex(
                self.user1["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0  # Transaction failed

        # Check if the account is still whitelisted
        is_white_listed = await contract.account_white_list(self.user1["address"])
        assert is_white_listed is True


@pytest.mark.asyncio
class TestMintWithAuthorization:
    """
    Test cases for the mint_with_authorization function of the AuthIbetWST contract.
    """

    deployer = default_eth_account("user1")
    relayer = deployer
    owner = default_eth_account("user2")
    user1 = default_eth_account("user3")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that tokens can be minted with authorization.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to mint tokens with valid authorization
        tx_hash = await contract.mint_with_authorization(
            to_address=self.user1["address"],
            amount=1000,
            authorizer_key=bytes.fromhex(self.owner["private_key"]),
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check the balance of the user
        balance = await contract.balance_of(self.user1["address"])
        assert balance == 1000

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to mint tokens with invalid authorization.
    async def test_error_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to mint tokens with invalid authorization
        tx_hash = await contract.mint_with_authorization(
            to_address=self.user1["address"],
            amount=1000,
            authorizer_key=bytes.fromhex(
                self.user1["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0  # Transaction failed

        # Check the balance of the user
        balance = await contract.balance_of(self.user1["address"])
        assert balance == 0


@pytest.mark.asyncio
class TestBurnWithAuthorization:
    """
    Test cases for the burn_with_authorization function of the AuthIbetWST contract.
    """

    deployer = default_eth_account("user1")
    relayer = deployer
    owner = default_eth_account("user2")
    user1 = default_eth_account("user3")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that tokens can be burned with authorization.
    async def test_normal_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Mint tokens to user1
        await mint_wst_token(
            contract_address=contract_address,
            to=self.user1["address"],
            amount=1000,
            tx_from=self.owner,
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to burn tokens with valid authorization
        tx_hash = await contract.burn_with_authorization(
            from_address=self.user1["address"],
            amount=500,
            authorizer_key=bytes.fromhex(self.owner["private_key"]),
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check the balance of the user
        balance = await contract.balance_of(self.user1["address"])
        assert balance == 500

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to burn tokens with invalid authorization.
    async def test_error_1(self):
        # Deploy contract
        contract_address = await deploy_wst_token(
            "Test Token", self.deployer, self.owner
        )

        # Mint tokens to user1
        await mint_wst_token(
            contract_address=contract_address,
            to=self.user1["address"],
            amount=1000,
            tx_from=self.owner,
        )

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Attempt to burn tokens with invalid authorization
        tx_hash = await contract.burn_with_authorization(
            from_address=self.user1["address"],
            amount=500,
            authorizer_key=bytes.fromhex(
                self.user1["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.relayer["address"],
            tx_sender_key=bytes.fromhex(self.relayer["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0  # Transaction failed

        # Check the balance of the user
        balance = await contract.balance_of(self.user1["address"])
        assert balance == 1000


@pytest.mark.asyncio
class TestGetTrade:
    """
    Test cases for the get_trade function of the AuthIbetWST contract.
    """

    owner = default_eth_account("user1")
    seller_st = default_eth_account("user2")
    seller_sc = default_eth_account("user3")
    buyer_st = default_eth_account("user4")
    buyer_sc = default_eth_account("user5")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that the get_trade function returns the correct trade information after a trade is requested.
    async def test_normal_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Request a trade
        await wst_request_trade(
            contract_address=st_token_address,
            buyer_st_account=self.buyer_st["address"],
            sc_token_address=sc_token_address,
            seller_sc_account=self.seller_sc["address"],
            buyer_sc_account=self.buyer_sc["address"],
            st_value=100,
            sc_value=200,
            memo="Test Trade",
            tx_from=self.seller_st,
        )

        # Call get_trade function
        trade_info = await token_st.get_trade(1)

        # Assert that the trade information is correct
        assert trade_info.model_dump() == {
            "seller_st_account": self.seller_st["address"],
            "buyer_st_account": self.buyer_st["address"],
            "sc_token_address": sc_token_address,
            "seller_sc_account": self.seller_sc["address"],
            "buyer_sc_account": self.buyer_sc["address"],
            "st_value": 100,
            "sc_value": 200,
            "state": "Pending",
            "memo": "Test Trade",
        }

    # Normal_2
    # - Test that the get_trade function returns default values for a trade that does not exist.
    async def test_normal_2(self):
        # Deploy contract
        contract_address = await deploy_wst_token("Test Token", self.owner, self.owner)

        # Generate contract instance
        contract = IbetWST(contract_address)

        # Call get_trade function
        trade_info = await contract.get_trade(1)

        # Assert that the trade information is correct
        assert trade_info.model_dump() == {
            "seller_st_account": "0x0000000000000000000000000000000000000000",
            "buyer_st_account": "0x0000000000000000000000000000000000000000",
            "sc_token_address": "0x0000000000000000000000000000000000000000",
            "seller_sc_account": "0x0000000000000000000000000000000000000000",
            "buyer_sc_account": "0x0000000000000000000000000000000000000000",
            "st_value": 0,
            "sc_value": 0,
            "state": "Pending",
            "memo": "",
        }


@pytest.mark.asyncio
class TestRequestTradeWithAuthorization:
    """
    Test cases for the wst_request_trade_with_authorization function of the AuthIbetWST contract.
    """

    owner = default_eth_account("user1")
    seller_st = default_eth_account("user2")
    seller_sc = default_eth_account("user3")
    buyer_st = default_eth_account("user4")
    buyer_sc = default_eth_account("user5")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that a trade can be requested with authorization.
    async def test_normal_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Attempt to request trade with valid authorization
        tx_hash = await token_st.request_trade_with_authorization(
            trade=IbetWSTTrade(
                seller_st_account=self.seller_st["address"],
                buyer_st_account=self.buyer_st["address"],
                sc_token_address=sc_token_address,
                seller_sc_account=self.seller_sc["address"],
                buyer_sc_account=self.buyer_sc["address"],
                st_value=1000,
                sc_value=2000,
                memo="Test Trade",
            ),
            authorizer_key=bytes.fromhex(self.seller_st["private_key"]),
            tx_sender=self.owner["address"],
            tx_sender_key=bytes.fromhex(self.owner["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check the trade information
        trade_info = await token_st.get_trade(1)
        assert trade_info.model_dump() == {
            "seller_st_account": self.seller_st["address"],
            "buyer_st_account": self.buyer_st["address"],
            "sc_token_address": sc_token_address,
            "seller_sc_account": self.seller_sc["address"],
            "buyer_sc_account": self.buyer_sc["address"],
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",
            "memo": "Test Trade",
        }

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to request a trade with invalid authorization.
    async def test_error_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Attempt to request trade with invalid authorization
        tx_hash = await token_st.request_trade_with_authorization(
            trade=IbetWSTTrade(
                seller_st_account=self.seller_st["address"],
                buyer_st_account=self.buyer_st["address"],
                sc_token_address=sc_token_address,
                seller_sc_account=self.seller_sc["address"],
                buyer_sc_account=self.buyer_sc["address"],
                st_value=1000,
                sc_value=2000,
                memo="Test Trade",
            ),
            authorizer_key=bytes.fromhex(
                self.buyer_st["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.owner["address"],
            tx_sender_key=bytes.fromhex(self.owner["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0

        # Check that the trade was not created
        trade_info = await token_st.get_trade(1)
        assert trade_info.model_dump() == {
            "seller_st_account": "0x0000000000000000000000000000000000000000",
            "buyer_st_account": "0x0000000000000000000000000000000000000000",
            "sc_token_address": "0x0000000000000000000000000000000000000000",
            "seller_sc_account": "0x0000000000000000000000000000000000000000",
            "buyer_sc_account": "0x0000000000000000000000000000000000000000",
            "st_value": 0,
            "sc_value": 0,
            "state": "Pending",
            "memo": "",
        }


@pytest.mark.asyncio
class TestCancelTradeWithAuthorization:
    """
    Test cases for the cancel_trade_with_authorization function of the AuthIbetWST contract.
    """

    owner = default_eth_account("user1")
    seller_st = default_eth_account("user2")
    seller_sc = default_eth_account("user3")
    buyer_st = default_eth_account("user4")
    buyer_sc = default_eth_account("user5")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that a trade can be canceled with authorization.
    async def test_normal_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Request a trade
        await wst_request_trade(
            contract_address=st_token_address,
            buyer_st_account=self.buyer_st["address"],
            sc_token_address=sc_token_address,
            seller_sc_account=self.seller_sc["address"],
            buyer_sc_account=self.buyer_sc["address"],
            st_value=1000,
            sc_value=2000,
            memo="Test Trade",
            tx_from=self.seller_st,
        )

        # Attempt to cancel trade with valid authorization
        tx_hash = await token_st.cancel_trade_with_authorization(
            index=1,
            authorizer_key=bytes.fromhex(self.seller_st["private_key"]),
            tx_sender=self.owner["address"],
            tx_sender_key=bytes.fromhex(self.owner["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check the trade information
        trade_info = await token_st.get_trade(1)
        assert trade_info.model_dump() == {
            "seller_st_account": self.seller_st["address"],
            "buyer_st_account": self.buyer_st["address"],
            "sc_token_address": sc_token_address,
            "seller_sc_account": self.seller_sc["address"],
            "buyer_sc_account": self.buyer_sc["address"],
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Cancelled",
            "memo": "Test Trade",
        }

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to cancel a trade with invalid authorization.
    async def test_error_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Request a trade
        await wst_request_trade(
            contract_address=st_token_address,
            buyer_st_account=self.buyer_st["address"],
            sc_token_address=sc_token_address,
            seller_sc_account=self.seller_sc["address"],
            buyer_sc_account=self.buyer_sc["address"],
            st_value=1000,
            sc_value=2000,
            memo="Test Trade",
            tx_from=self.seller_st,
        )

        # Attempt to cancel trade with invalid authorization
        tx_hash = await token_st.cancel_trade_with_authorization(
            index=1,
            authorizer_key=bytes.fromhex(
                self.buyer_st["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.owner["address"],
            tx_sender_key=bytes.fromhex(self.owner["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0

        # Check that the trade was not canceled
        trade_info = await token_st.get_trade(1)
        assert trade_info.model_dump() == {
            "seller_st_account": self.seller_st["address"],
            "buyer_st_account": self.buyer_st["address"],
            "sc_token_address": sc_token_address,
            "seller_sc_account": self.seller_sc["address"],
            "buyer_sc_account": self.buyer_sc["address"],
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",  # Trade should still be pending
            "memo": "Test Trade",
        }


@pytest.mark.asyncio
class TestAcceptTradeWithAuthorization:
    """
    Test cases for the accept_trade_with_authorization function of the AuthIbetWST contract.
    """

    owner = default_eth_account("user1")
    seller_st = default_eth_account("user2")
    seller_sc = default_eth_account("user3")
    buyer_st = default_eth_account("user4")
    buyer_sc = default_eth_account("user5")

    #################################################################
    # Normal
    #################################################################

    # Normal_1
    # - Test that a trade can be accepted with authorization.
    async def test_normal_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        await mint_wst_token(
            st_token_address, self.seller_st["address"], 1000, self.owner
        )
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )
        await mint_erc20_token(
            sc_token_address, self.buyer_sc["address"], 2000, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Approve the SC token for ST token contract
        await erc20_approve_token(
            contract_address=sc_token_address,
            spender=st_token_address,
            amount=2000,
            tx_from=self.buyer_sc,
        )

        # Request a trade
        await wst_request_trade(
            contract_address=st_token_address,
            buyer_st_account=self.buyer_st["address"],
            sc_token_address=sc_token_address,
            seller_sc_account=self.seller_sc["address"],
            buyer_sc_account=self.buyer_sc["address"],
            st_value=1000,
            sc_value=2000,
            memo="Test Trade",
            tx_from=self.seller_st,
        )

        # Attempt to accept trade with valid authorization
        tx_hash = await token_st.accept_trade_with_authorization(
            index=1,
            authorizer_key=bytes.fromhex(self.buyer_st["private_key"]),
            tx_sender=self.owner["address"],
            tx_sender_key=bytes.fromhex(self.owner["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 1  # Transaction was successful

        # Check the trade information
        trade_info = await token_st.get_trade(1)
        assert trade_info.model_dump() == {
            "seller_st_account": self.seller_st["address"],
            "buyer_st_account": self.buyer_st["address"],
            "sc_token_address": sc_token_address,
            "seller_sc_account": self.seller_sc["address"],
            "buyer_sc_account": self.buyer_sc["address"],
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Executed",
            "memo": "Test Trade",
        }

    #################################################################
    # Error
    #################################################################

    # Error_1
    # - Test that an error is raised when trying to accept a trade with invalid authorization.
    async def test_error_1(self):
        # Deploy contract (WST)
        st_token_address = await deploy_wst_token("Test Token", self.owner, self.owner)
        await mint_wst_token(
            st_token_address, self.seller_st["address"], 1000, self.owner
        )
        token_st = IbetWST(st_token_address)

        # Deploy contract (SC token)
        sc_token_address = await deploy_erc20_token(
            "Test Token", self.owner, self.owner
        )
        await mint_erc20_token(
            sc_token_address, self.buyer_sc["address"], 2000, self.owner
        )

        # Add account to whitelist
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.seller_st["address"],
            tx_from=self.owner,
        )
        await wst_add_account_to_whitelist(
            contract_address=st_token_address,
            account=self.buyer_st["address"],
            tx_from=self.owner,
        )

        # Approve the SC token for ST token contract
        await erc20_approve_token(
            contract_address=sc_token_address,
            spender=st_token_address,
            amount=2000,
            tx_from=self.buyer_sc,
        )

        # Request a trade
        await wst_request_trade(
            contract_address=st_token_address,
            buyer_st_account=self.buyer_st["address"],
            sc_token_address=sc_token_address,
            seller_sc_account=self.seller_sc["address"],
            buyer_sc_account=self.buyer_sc["address"],
            st_value=1000,
            sc_value=2000,
            memo="Test Trade",
            tx_from=self.seller_st,
        )

        # Attempt to accept trade with invalid authorization
        tx_hash = await token_st.accept_trade_with_authorization(
            index=1,
            authorizer_key=bytes.fromhex(
                self.seller_st["private_key"]
            ),  # Invalid authorizer key
            tx_sender=self.owner["address"],
            tx_sender_key=bytes.fromhex(self.owner["private_key"]),
        )

        # Wait for transaction receipt
        tx_receipt = await EthAsyncContractUtils.wait_for_transaction_receipt(tx_hash)
        assert tx_receipt["status"] == 0  # Transaction failed

        # Check that the trade was not accepted
        trade_info = await token_st.get_trade(1)
        assert trade_info.model_dump() == {
            "seller_st_account": self.seller_st["address"],
            "buyer_st_account": self.buyer_st["address"],
            "sc_token_address": sc_token_address,
            "seller_sc_account": self.seller_sc["address"],
            "buyer_sc_account": self.buyer_sc["address"],
            "st_value": 1000,
            "sc_value": 2000,
            "state": "Pending",  # Trade should still be pending
            "memo": "Test Trade",
        }
