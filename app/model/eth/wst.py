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
    def generate_add_account_whitelist_digest(
        domain_separator: bytes,
        account_address: str,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for adding an account to the whitelist.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param account_address: Address of the account to add to the whitelist
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the add whitelist operation
        """

        type_hash = keccak(
            text="AddAccountWhiteListWithAuthorization(address accountAddress,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # account
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(account_address),
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
        account_address: str,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for deleting an account from the whitelist.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param account_address: Address of the account to delete from the whitelist
        :param nonce: Nonce for the operation, used to prevent replay attacks
        :return: EIP-712 digest for the delete whitelist operation
        """

        type_hash = keccak(
            text="DeleteAccountWhiteListWithAuthorization(address accountAddress,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # account
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(account_address),
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
        _from: str,
        _to: str,
        value: int,
        valid_after: int,
        valid_before: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for transfer with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param _from: from address
        :param _to: to address
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
                    to_checksum_address(_from),
                    to_checksum_address(_to),
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
        _from: str,
        _to: str,
        value: int,
        valid_after: int,
        valid_before: int,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for receive with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param _from: from address
        :param _to: to address
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
                    to_checksum_address(_from),
                    to_checksum_address(_to),
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
        seller_st_account_address: str,
        buyer_st_account_address: str,
        sc_token_address: str,
        seller_sc_account_address: str,
        buyer_sc_account_address: str,
        st_value: int,
        sc_value: int,
        memo: str,
        nonce: bytes,
    ) -> bytes:
        """
        Generate the EIP-712 digest for request trade with authorization.

        :param domain_separator: EIP-712 DOMAIN_SEPARATOR
        :param seller_st_account_address: Seller's ST account address
        :param buyer_st_account_address: Buyer's ST account address
        :param sc_token_address: SC contract address
        :param seller_sc_account_address: Seller's SC account address
        :param buyer_sc_account_address: Buyer's SC account address
        :param st_value: Value of ST to trade
        :param sc_value: Value of SC to trade
        :param memo: Optional memo for the trade request
        :param nonce: Nonce for the trade, used to prevent replay attacks
        :return: EIP-712 digest for the trade request
        """

        type_hash = keccak(
            text="RequestTradeWithAuthorization(address sellerSTAccountAddress,address buyerSTAccountAddress,address SCTokenAddress,address sellerSCAccountAddress,address buyerSCAccountAddress,uint256 STValue,uint256 SCValue,string memory memo,bytes32 nonce)"
        )

        struct_hash = keccak(
            encode(
                [
                    "bytes32",  # typeHash
                    "address",  # sellerSTAccountAddress
                    "address",  # buyerSTAccountAddress
                    "address",  # SCTokenAddress
                    "address",  # sellerSCAccountAddress
                    "address",  # buyerSCAccountAddress
                    "uint256",  # STValue
                    "uint256",  # SCValue
                    "string",  # memo
                    "bytes32",  # nonce
                ],
                [
                    type_hash,
                    to_checksum_address(seller_st_account_address),
                    to_checksum_address(buyer_st_account_address),
                    to_checksum_address(sc_token_address),
                    to_checksum_address(seller_sc_account_address),
                    to_checksum_address(buyer_sc_account_address),
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
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Add account to white list with authorization

        :param account: Account address
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to add the account to the whitelist
            tx = await self.contract.functions.addAccountWhiteListWithAuthorization(
                account,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
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
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Delete account from white list with authorization

        :param account: Account address
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
            # Build the transaction to delete the account from the whitelist
            tx = await self.contract.functions.deleteAccountWhiteListWithAuthorization(
                account,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
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
                to_address,
                value,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
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
                from_address,
                value,
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
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
        authorization: IbetWSTAuthorization,
        tx_sender: EthereumAddress,
        tx_sender_key: bytes,
    ) -> str:
        """
        Request a trade with authorization

        :param trade: Trade information
        :param authorization: Authorization data containing nonce, v, r, s
        :param tx_sender: Address of the transaction sender
        :param tx_sender_key: Private key of the transaction sender
        :return: Transaction hash
        """
        try:
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
                authorization.nonce,
                authorization.v,
                authorization.r,
                authorization.s,
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
                    "from": tx_sender,
                    "gas": ETH_TX_GAS_LIMIT,
                }
            )
            # Send the transaction
            return await EthAsyncContractUtils.send_transaction(tx, tx_sender_key)
        except Exception as err:
            raise SendTransactionError(err)
