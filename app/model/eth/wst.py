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

import secrets
from typing import Literal

from eth_abi import encode
from eth_abi.packed import encode_packed
from eth_utils import keccak, to_checksum_address
from pydantic import BaseModel, Field
from web3.contract import AsyncContract

from app.exceptions import SendTransactionError
from app.model import EthereumAddress
from app.utils.eth_contract_utils import EthAsyncContractUtils, EthWeb3
from config import ZERO_ADDRESS
from eth_config import ETH_CHAIN_ID, ETH_TX_GAS_LIMIT


class ERC20:
    """
    ERC20 contract
    """

    contract_name = "IbetERC20"
    contract: AsyncContract

    def __init__(
        self,
        contract_address: str = ZERO_ADDRESS,
    ):
        self.contract = EthAsyncContractUtils.get_contract(
            contract_name=self.contract_name, contract_address=contract_address
        )

    async def name(self) -> str:
        """
        Get token name

        :return: Token name
        """
        return await EthAsyncContractUtils.call_function(
            contract=self.contract, function_name="name", args=(), default_returns=""
        )

    async def balance_of(self, account: EthereumAddress) -> int:
        """
        Get balance of account

        :param account: Account address
        :return: Account balance
        """
        return await EthAsyncContractUtils.call_function(
            contract=self.contract,
            function_name="balanceOf",
            args=(account,),
            default_returns=0,
        )

    async def allowance(
        self, account: EthereumAddress, spender: EthereumAddress
    ) -> int:
        """
        Get allowance of spender by owner

        :param account: Token holder address
        :param spender: Spender address
        :return: Allowance amount
        """
        return await EthAsyncContractUtils.call_function(
            contract=self.contract,
            function_name="allowance",
            args=(account, spender),
            default_returns=0,
        )


class IbetWSTTrade(BaseModel):
    """
    IbetWST Trade information
    """

    seller_st_account: EthereumAddress = Field(default=ZERO_ADDRESS)
    buyer_st_account: EthereumAddress = Field(default=ZERO_ADDRESS)
    sc_token_address: EthereumAddress = Field(default=ZERO_ADDRESS)
    seller_sc_account: EthereumAddress = Field(default=ZERO_ADDRESS)
    buyer_sc_account: EthereumAddress = Field(default=ZERO_ADDRESS)
    st_value: int = Field(default=0)
    sc_value: int = Field(default=0)
    state: Literal["Pending", "Executed", "Cancelled"] = Field(default="Pending")
    memo: str = Field(default="")


class IbetWST(ERC20):
    """
    IbetWST contract
    """

    contract_name = "AuthIbetWST"

    def __init__(self, contract_address: str = ZERO_ADDRESS):
        super().__init__(contract_address)

    async def domain_separator(self) -> bytes:
        """
        Get domain separator

        :return: Domain separator
        """
        name = await EthAsyncContractUtils.call_function(
            contract=self.contract, function_name="name", args=(), default_returns=""
        )
        return keccak(
            encode(
                [
                    "bytes32",  # EIP712Domain type
                    "bytes32",  # name type
                    "bytes32",  # version type
                    "uint256",  # chainId type
                    "address",  # verifyingContract type
                ],
                [
                    keccak(
                        text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
                    ),
                    keccak(name.encode()),
                    keccak("1".encode()),
                    ETH_CHAIN_ID,
                    to_checksum_address(self.contract.address),
                ],
            )
        )

    async def account_white_list(self, account: EthereumAddress) -> bool:
        """
        Check if account is in white list

        :param account: Account address
        :return: True if account is in white list, False otherwise
        """
        return await EthAsyncContractUtils.call_function(
            contract=self.contract,
            function_name="accountWhiteList",
            args=(account,),
            default_returns=False,
        )

    async def add_account_white_list_with_authorization(
        self,
        account: EthereumAddress,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Add account to white list with authorization

        :param account: Account address
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="AddAccountWhiteListWithAuthorization(address accountAddress,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "address",  # account
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        to_checksum_address(account),
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction to add the account to the whitelist
            tx = await self.contract.functions.addAccountWhiteListWithAuthorization(
                account,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def delete_account_white_list_with_authorization(
        self,
        account: EthereumAddress,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Delete account from white list with authorization

        :param account: Account address
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="DeleteAccountWhiteListWithAuthorization(address accountAddress,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "address",  # account
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        to_checksum_address(account),
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction to delete the account from the whitelist
            tx = await self.contract.functions.deleteAccountWhiteListWithAuthorization(
                account,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def mint_with_authorization(
        self,
        to_address: EthereumAddress,
        amount: int,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Mint tokens with authorization

        :param to_address: Address to mint tokens to
        :param amount: Amount of tokens to mint
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="MintWithAuthorization(address to,uint256 amount,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "address",  # to
                        "uint256",  # amount
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        to_checksum_address(to_address),
                        amount,
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction to mint tokens
            tx = await self.contract.functions.mintWithAuthorization(
                to_address,
                amount,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def burn_with_authorization(
        self,
        from_address: EthereumAddress,
        amount: int,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Burn tokens with authorization

        :param from_address: Address to burn tokens from
        :param amount: Amount of tokens to burn
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="BurnWithAuthorization(address from,uint256 amount,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "address",  # from
                        "uint256",  # amount
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        to_checksum_address(from_address),
                        amount,
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction to burn tokens
            tx = await self.contract.functions.burnWithAuthorization(
                from_address,
                amount,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def get_trade(self, index: int) -> IbetWSTTrade:
        """
        Get trade information by trade ID

        :param index: Trade ID (index)
        :return: Trade information
        """
        trade = await EthAsyncContractUtils.call_function(
            contract=self.contract,
            function_name="getTrade",
            args=(index,),
            default_returns=IbetWSTTrade(),
        )

        match trade[7]:
            case 0:
                _state = "Pending"
            case 1:
                _state = "Executed"
            case 2:
                _state = "Cancelled"

        return IbetWSTTrade(
            seller_st_account=to_checksum_address(trade[0]),
            buyer_st_account=to_checksum_address(trade[1]),
            sc_token_address=to_checksum_address(trade[2]),
            seller_sc_account=to_checksum_address(trade[3]),
            buyer_sc_account=to_checksum_address(trade[4]),
            st_value=trade[5],
            sc_value=trade[6],
            state=_state,
            memo=trade[8],
        )

    async def request_trade_with_authorization(
        self,
        trade: IbetWSTTrade,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Request a trade with authorization

        :param trade: Trade information
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="RequestTradeWithAuthorization(address sellerSTAccountAddress,address buyerSTAccountAddress,address SCTokenAddress,address sellerSCAccountAddress,address buyerSCAccountAddress,uint256 STValue,uint256 SCValue,string memory memo,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "address",  # sellerStAccount
                        "address",  # buyerStAccount
                        "address",  # scTokenAddress
                        "address",  # sellerScAccount
                        "address",  # buyerScAccount
                        "uint256",  # stValue
                        "uint256",  # scValue
                        "string",  # memo
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        to_checksum_address(trade.seller_st_account),
                        to_checksum_address(trade.buyer_st_account),
                        to_checksum_address(trade.sc_token_address),
                        to_checksum_address(trade.seller_sc_account),
                        to_checksum_address(trade.buyer_sc_account),
                        trade.st_value,
                        trade.sc_value,
                        trade.memo,
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction
            tx = await self.contract.functions.requestTradeWithAuthorization(
                trade.seller_st_account,
                trade.buyer_st_account,
                trade.sc_token_address,
                trade.seller_sc_account,
                trade.buyer_sc_account,
                trade.st_value,
                trade.sc_value,
                trade.memo,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def cancel_trade_with_authorization(
        self,
        index: int,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Cancel a trade with authorization

        :param index: Trade ID (index)
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="CancelTradeWithAuthorization(uint256 index,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "uint256",  # index
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        index,
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction to cancel the trade
            tx = await self.contract.functions.cancelTradeWithAuthorization(
                index,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def accept_trade_with_authorization(
        self,
        index: int,
        authorizer_key: bytes,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Accept a trade with authorization

        :param index: Trade ID (index)
        :param authorizer_key: Private key of the authorizer
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Type hash
            type_hash = keccak(
                text="AcceptTradeWithAuthorization(uint256 index,bytes32 nonce)"
            )

            # Generate nonce
            nonce = secrets.token_bytes(32)

            # Generate domain separator
            domain_separator = await self.domain_separator()

            # Generate authorization digest
            struct_hash = keccak(
                encode(
                    [
                        "bytes32",  # typeHash
                        "uint256",  # index
                        "bytes32",  # nonce
                    ],
                    [
                        type_hash,
                        index,
                        nonce,
                    ],
                )
            )
            digest = keccak(
                encode_packed(
                    [
                        "bytes2",  # EIP-712 prefix
                        "bytes32",  # domainSeparator
                        "bytes32",  # structHash
                    ],
                    [
                        "\x19\x01".encode(),
                        domain_separator,
                        struct_hash,
                    ],
                )
            )

            # Sign the digest from the authorizer's private key
            signature = EthWeb3.eth.account.unsafe_sign_hash(digest, authorizer_key)

            # Build the transaction to accept the trade
            tx = await self.contract.functions.acceptTradeWithAuthorization(
                index,
                nonce,
                signature.v,
                EthWeb3.to_bytes(signature.r),
                EthWeb3.to_bytes(signature.s),
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )

            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)
