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

from typing import Literal

from eth_abi import encode
from eth_abi.packed import encode_packed
from eth_utils import keccak, to_checksum_address
from pydantic import BaseModel, Field
from web3.contract import AsyncContract

from app.exceptions import SendTransactionError
from app.model import EthereumAddress
from app.utils.eth_contract_utils import EthAsyncContractUtils
from config import ZERO_ADDRESS
from eth_config import ETH_CHAIN_ID


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
            args=(to_checksum_address(account),),
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
            args=(to_checksum_address(account), to_checksum_address(spender)),
            default_returns=0,
        )


class IbetWSTWhiteList(BaseModel):
    """
    IbetWST White List information
    """

    st_account: EthereumAddress = Field(default=ZERO_ADDRESS)
    sc_account_in: EthereumAddress = Field(default=ZERO_ADDRESS)
    sc_account_out: EthereumAddress = Field(default=ZERO_ADDRESS)
    listed: bool = Field(default=False)


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
    state: Literal["Pending", "Executed", "Cancelled", "Rejected"] = Field(
        default="Pending"
    )
    memo: str = Field(default="")


class IbetWSTAuthorization(BaseModel):
    """
    Authorization data for IbetWST contract operations.
    """

    nonce: bytes
    v: int
    r: bytes
    s: bytes


class IbetWSTDigestHelper:
    """
    Helper class for generating EIP-712 digests for IbetWST contract operations.
    """

    @staticmethod
    def generate_mint_digest(
        domain_separator: bytes,
        to_address: str,
        value: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for minting tokens with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param to_address: Address to mint tokens to
        :param value: Value of tokens to mint
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the mint operation
        """

        type_hash = keccak(
            text="MintWithAuthorization(address to,uint256 value,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # to
                    "uint256",  # value
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(to_address),
                    value,
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
        return digest

    @staticmethod
    def generate_burn_digest(
        domain_separator: bytes,
        from_address: str,
        value: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for burning tokens with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param from_address: Address to burn tokens from
        :param value: Value of tokens to burn
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the burn operation
        """

        type_hash = keccak(
            text="BurnWithAuthorization(address from,uint256 value,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # from
                    "uint256",  # value
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(from_address),
                    value,
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
        return digest

    @staticmethod
    def generate_force_burn_from_digest(
        domain_separator: bytes,
        account_address: str,
        value: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for force burning tokens from an account with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param account_address: Address to burn tokens from
        :param value: Value of tokens to burn
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the force burn operation
        """

        type_hash = keccak(
            text="ForceBurnFromWithAuthorization(address account,uint256 value,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # account
                    "uint256",  # value
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(account_address),
                    value,
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
        return digest

    @staticmethod
    def generate_add_account_whitelist_digest(
        domain_separator: bytes,
        st_account: str,
        sc_account_in: str,
        sc_account_out: str,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for adding an account to the whitelist.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param st_account: ST account address
        :param sc_account_in: SC account address for deposits
        :param sc_account_out: SC account address for withdrawals
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the add whitelist operation
        """

        type_hash = keccak(
            text="AddAccountWhiteListWithAuthorization(address STAccountAddress,address SCAccountAddressIn,address SCAccountAddressOut,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # STAccountAddress
                    "address",  # SCAccountAddressIn
                    "address",  # SCAccountAddressOut
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(st_account),
                    to_checksum_address(sc_account_in),
                    to_checksum_address(sc_account_out),
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
        return digest

    @staticmethod
    def generate_delete_account_whitelist_digest(
        domain_separator: bytes,
        st_account: str,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for deleting an account from the whitelist.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param st_account: Address of the ST account to delete from the whitelist
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the delete whitelist operation
        """

        type_hash = keccak(
            text="DeleteAccountWhiteListWithAuthorization(address STAccountAddress,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # STAccountAddress
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(st_account),
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
        return digest

    @staticmethod
    def generate_transfer_digest(
        domain_separator: bytes,
        from_address: str,
        to_address: str,
        value: int,
        nonce: bytes,
        valid_after: int = 1,
        valid_before: int = 2**64 - 1,
    ) -> bytes:
        """
        Generate the EIP-712 digest for transfer with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param from_address: from address
        :param to_address: to address
        :param value: value to transfer
        :param valid_after: block timestamp after which the transfer is valid
        :param valid_before: block timestamp before which the transfer is valid
        :param nonce: nonce for the transfer, used to prevent replay attacks
        :return: EIP-712 digest for the transfer
        """

        type_hash = keccak(
            text="TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # from
                    "address",  # to
                    "uint256",  # value
                    "uint256",  # validAfter
                    "uint256",  # validBefore
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(from_address),
                    to_checksum_address(to_address),
                    value,
                    valid_after,
                    valid_before,
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
        return digest

    @staticmethod
    def generate_receive_digest(
        domain_separator: bytes,
        from_address: str,
        to_address: str,
        value: int,
        valid_after: int,
        valid_before: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for receive with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param from_address: from address
        :param to_address: to address
        :param value: value to transfer
        :param valid_after: block timestamp after which the transfer is valid
        :param valid_before: block timestamp before which the transfer is valid
        :param nonce: nonce for the transfer, used to prevent replay attacks
        :return: EIP-712 digest for the transfer
        """

        type_hash = keccak(
            text="ReceiveWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # from
                    "address",  # to
                    "uint256",  # value
                    "uint256",  # validAfter
                    "uint256",  # validBefore
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(from_address),
                    to_checksum_address(to_address),
                    value,
                    valid_after,
                    valid_before,
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
        return digest

    @staticmethod
    def generate_request_trade_digest(
        domain_separator: bytes,
        seller_st_account: str,
        buyer_st_account: str,
        sc_token_address: str,
        st_value: int,
        sc_value: int,
        memo: str,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for request trade with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param seller_st_account: Seller's ST account address
        :param buyer_st_account: Buyer's ST account address
        :param sc_token_address: SC contract address
        :param st_value: Value of ST to trade
        :param sc_value: Value of SC to trade
        :param memo: Optional memo for the trade request
        :param nonce: Nonce for the trade, used to prevent replay attacks
        :return: EIP-712 digest for the trade request
        """

        type_hash = keccak(
            text="RequestTradeWithAuthorization(address sellerSTAccountAddress,address buyerSTAccountAddress,address SCTokenAddress,uint256 STValue,uint256 SCValue,string memory memo,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # sellerSTAccountAddress
                    "address",  # buyerSTAccountAddress
                    "address",  # SCTokenAddress
                    "uint256",  # STValue
                    "uint256",  # SCValue
                    "string",  # memo
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(seller_st_account),
                    to_checksum_address(buyer_st_account),
                    to_checksum_address(sc_token_address),
                    st_value,
                    sc_value,
                    memo,
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
        return digest

    @staticmethod
    def generate_cancel_trade_digest(
        domain_separator: bytes,
        index: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for cancel trade with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param index: Index of the trade to cancel
        :param nonce: Nonce for the trade, used to prevent replay attacks
        :return: EIP-712 digest for the trade cancellation
        """

        type_hash = keccak(
            text="CancelTradeWithAuthorization(uint256 index,bytes32 nonce)"
        )

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
        return digest

    @staticmethod
    def generate_accept_trade_digest(
        domain_separator: bytes,
        index: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for accept trade with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param index: Index of the trade to accept
        :param nonce: Nonce for the trade, used to prevent replay attacks
        :return: EIP-712 digest for the trade acceptance
        """

        type_hash = keccak(
            text="AcceptTradeWithAuthorization(uint256 index,bytes32 nonce)"
        )

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
        return digest

    @staticmethod
    def generate_reject_trade_digest(
        domain_separator: bytes,
        index: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for reject trade with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param index: Index of the trade to reject
        :param nonce: Nonce for the trade, used to prevent replay attacks
        :return: EIP-712 digest for the trade cancellation
        """

        type_hash = keccak(
            text="RejectTradeWithAuthorization(uint256 index,bytes32 nonce)"
        )

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
        return digest


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

    async def account_white_list(self, account: EthereumAddress) -> IbetWSTWhiteList:
        """
        Check if account is in white list

        :param account: Account address
        :return: True if account is in white list, False otherwise
        """
        whitelist = await EthAsyncContractUtils.call_function(
            contract=self.contract,
            function_name="accountWhiteList",
            args=(to_checksum_address(account),),
            default_returns=(
                ZERO_ADDRESS,  # st_account
                ZERO_ADDRESS,  # sc_account_in
                ZERO_ADDRESS,  # sc_account_out
                False,  # listed
            ),
        )
        return IbetWSTWhiteList(
            st_account=to_checksum_address(whitelist[0]),
            sc_account_in=to_checksum_address(whitelist[1]),
            sc_account_out=to_checksum_address(whitelist[2]),
            listed=whitelist[3],
        )

    async def add_account_white_list_with_authorization(
        self,
        st_account: EthereumAddress,
        sc_account_in: EthereumAddress,
        sc_account_out: EthereumAddress,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Add account to white list with authorization

        :param st_account: ST account address
        :param sc_account_in: SC account address for deposits
        :param sc_account_out: SC account address for withdrawals
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to add the account to the whitelist
            tx = await self.contract.functions.addAccountWhiteListWithAuthorization(
                to_checksum_address(st_account),
                to_checksum_address(sc_account_in),
                to_checksum_address(sc_account_out),
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 150000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def delete_account_white_list_with_authorization(
        self,
        st_account: EthereumAddress,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Delete account from white list with authorization

        :param st_account: Account address for ST
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to delete the account from the whitelist
            tx = await self.contract.functions.deleteAccountWhiteListWithAuthorization(
                to_checksum_address(st_account),
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 80000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def mint_with_authorization(
        self,
        to_address: EthereumAddress,
        value: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Mint tokens with authorization

        :param to_address: Address to mint tokens to
        :param value: Value of tokens to mint
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to mint tokens
            tx = await self.contract.functions.mintWithAuthorization(
                to_checksum_address(to_address),
                value,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 125000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def burn_with_authorization(
        self,
        from_address: EthereumAddress,
        value: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Burn tokens with authorization

        :param from_address: Address to burn tokens from
        :param value: Value of tokens to burn
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to burn tokens
            tx = await self.contract.functions.burnWithAuthorization(
                to_checksum_address(from_address),
                value,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 82000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def force_burn_from_with_authorization(
        self,
        account_address: EthereumAddress,
        value: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Force burn tokens from an account with authorization

        :param account_address: Address to burn tokens from
        :param value: Value of tokens to burn
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to force burn tokens
            tx = await self.contract.functions.forceBurnFromWithAuthorization(
                to_checksum_address(account_address),
                value,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 82000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def transfer_with_authorization(
        self,
        from_address: EthereumAddress,
        to_address: EthereumAddress,
        value: int,
        valid_after: int,
        valid_before: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Transfer tokens with authorization

        :param from_address: Address to transfer tokens from
        :param to_address: Address to transfer tokens to
        :param value: Value of tokens to transfer
        :param valid_after: Block timestamp after which the transfer is valid
        :param valid_before: Block timestamp before which the transfer is valid
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to transfer tokens
            tx = await self.contract.functions.transferWithAuthorization(
                to_checksum_address(from_address),
                to_checksum_address(to_address),
                value,
                valid_after,
                valid_before,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 108000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def receive_with_authorization(
        self,
        from_address: EthereumAddress,
        to_address: EthereumAddress,
        value: int,
        valid_after: int,
        valid_before: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Receive tokens with authorization

        :param from_address: Address to receive tokens from
        :param to_address: Address to receive tokens to
        :param value: Value of tokens to receive
        :param valid_after: Block timestamp after which the receive is valid
        :param valid_before: Block timestamp before which the receive is valid
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to receive tokens
            tx = await self.contract.functions.receiveWithAuthorization(
                to_checksum_address(from_address),
                to_checksum_address(to_address),
                value,
                valid_after,
                valid_before,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 500000,
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
            case 3:
                _state = "Rejected"

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
        seller_st_account: EthereumAddress,
        buyer_st_account: EthereumAddress,
        sc_token_address: EthereumAddress,
        st_value: int,
        sc_value: int,
        memo: str,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Request a trade with authorization

        :param seller_st_account: Seller's ST account address
        :param buyer_st_account: Buyer's ST account address
        :param sc_token_address: SC contract address
        :param st_value: Value of ST to trade
        :param sc_value: Value of SC to trade
        :param memo: Optional memo for the trade request
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction
            tx = await self.contract.functions.requestTradeWithAuthorization(
                to_checksum_address(seller_st_account),
                to_checksum_address(buyer_st_account),
                to_checksum_address(sc_token_address),
                st_value,
                sc_value,
                memo,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 324000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def cancel_trade_with_authorization(
        self,
        index: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Cancel a trade with authorization

        :param index: Trade ID (index)
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to cancel the trade
            tx = await self.contract.functions.cancelTradeWithAuthorization(
                index,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 113000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def accept_trade_with_authorization(
        self,
        index: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Accept a trade with authorization

        :param index: Trade ID (index)
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to accept the trade
            tx = await self.contract.functions.acceptTradeWithAuthorization(
                index,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 182000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)

    async def reject_trade_with_authorization(
        self,
        index: int,
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Reject a trade with authorization

        :param index: Trade ID (index)
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to reject the trade
            tx = await self.contract.functions.rejectTradeWithAuthorization(
                index,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
            ).build_transaction(
                {
                    "chainId": ETH_CHAIN_ID,
                    "from": to_checksum_address(tx_sender),
                    "gas": 113000,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)
