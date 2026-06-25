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
import secrets
import uuid

from eth_keyfile.keyfile import decode_keyfile_json
from eth_utils.address import to_checksum_address
from fastapi import APIRouter, HTTPException
from sqlalchemy import and_, select
from starlette.requests import Request

from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError
from app.model.db import (
    Account,
    IbetWSTAuthorization,
    IbetWSTBlockchain,
    IbetWSTTxStatus,
    IbetWSTTxType,
    IbetWSTVersion,
    IbetWSTWhitelistKYCDelegatedEoa,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
    Token,
    TokenHolderExtraInfo,
    TokenStatus,
)
from app.model.db.ibet_wst import (
    AvaIbetWSTTx,
    EthIbetWSTTx,
    IbetWSTTxParamsAddAccountWhiteList,
    IbetWSTTxParamsDeleteAccountWhiteList,
)
from app.model.schema import (
    IbetWSTTransactionResponse,
    SealedTxAddIbetWSTWhitelistRequest,
    SealedTxDeleteIbetWSTWhitelistRequest,
    SealedTxRegisterHolderExtraInfoRequest,
    SealedTxRegisterPersonalInfoRequest,
)
from app.model.wst import AvalancheIbetWST, EthereumIbetWST, IbetWSTDigestHelper
from app.utils.ava_contract_utils import AvaWeb3
from app.utils.docs_utils import get_routers_responses
from app.utils.e2ee_utils import E2EEUtils
from app.utils.eth_contract_utils import EthWeb3
from app.utils.sealedtx_utils import (
    RawRequestBody,
    SealedTxSignatureHeader,
    VerifySealedTxSignature,
)
from avalanche_config import AVA_MASTER_ACCOUNT_ADDRESS
from config import IBET_WST_AVA_FEATURE_ENABLED, IBET_WST_ETH_FEATURE_ENABLED
from eth_config import ETH_MASTER_ACCOUNT_ADDRESS

router = APIRouter(prefix="/sealed_tx", tags=["[misc] sealed_tx"])


def _ensure_ibet_wst_feature_enabled(blockchain_platform: IbetWSTBlockchain) -> None:
    is_enabled = (
        IBET_WST_AVA_FEATURE_ENABLED
        if blockchain_platform == IbetWSTBlockchain.AVALANCHE
        else IBET_WST_ETH_FEATURE_ENABLED
    )
    if is_enabled is False:
        raise HTTPException(
            status_code=404,
            detail="This URL is not available in the current settings",
        )


def _get_ibet_wst_address(
    token: Token, blockchain_platform: IbetWSTBlockchain
) -> str | None:
    return token.get_ibet_wst_address(blockchain_platform)


def _get_wst_contract(
    ibet_wst_address: str, blockchain_platform: IbetWSTBlockchain
) -> EthereumIbetWST | AvalancheIbetWST:
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvalancheIbetWST(ibet_wst_address)
    return EthereumIbetWST(ibet_wst_address)


def _get_signer_web3(blockchain_platform: IbetWSTBlockchain):
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvaWeb3
    return EthWeb3


def _get_master_account(blockchain_platform: IbetWSTBlockchain) -> str:
    account = (
        AVA_MASTER_ACCOUNT_ADDRESS
        if blockchain_platform == IbetWSTBlockchain.AVALANCHE
        else ETH_MASTER_ACCOUNT_ADDRESS
    )
    if account is None:
        raise HTTPException(
            status_code=503,
            detail="Master account is not configured for the selected blockchain platform",
        )
    return account


def _get_wst_tx_model(blockchain_platform: IbetWSTBlockchain):
    if blockchain_platform == IbetWSTBlockchain.AVALANCHE:
        return AvaIbetWSTTx
    return EthIbetWSTTx


async def _get_ibet_wst_token(
    db: DBAsyncSession,
    token_address: str,
    blockchain_platform: IbetWSTBlockchain,
    reject_pending_token: bool = False,
) -> Token:
    token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.token_address == to_checksum_address(token_address),
                    Token.token_status != TokenStatus.FAILED,
                )
            )
            .limit(1)
        )
    ).first()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if _get_ibet_wst_address(token, blockchain_platform) is None:
        raise HTTPException(status_code=404, detail="Token not found")
    if reject_pending_token and token.token_status == TokenStatus.PENDING:
        raise InvalidParameterError("This token is temporarily unavailable")
    return token


# POST: /sealed_tx/personal_info
@router.post(
    "/personal_info",
    operation_id="SealedTxRegisterPersonalInfo",
    response_model=None,
    responses=get_routers_responses(InvalidParameterError),
)
async def sealed_tx_register_personal_info(
    db: DBAsyncSession,
    raw_request_body: RawRequestBody,
    request: Request,
    sealed_tx_sig: SealedTxSignatureHeader,
    register_data: SealedTxRegisterPersonalInfoRequest,
):
    # Verify sealed tx signature
    account_address = VerifySealedTxSignature(
        req=request, body=json.loads(raw_request_body.decode()), signature=sealed_tx_sig
    )

    # Insert/Update offchain personal information
    # NOTE: Overwrite if a record for the same account already exists.
    personal_info = register_data.personal_information.model_dump()
    _off_personal_info = IDXPersonalInfo()
    _off_personal_info.issuer_address = register_data.link_address
    _off_personal_info.account_address = account_address
    _off_personal_info.personal_info = personal_info
    _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
    await db.merge(_off_personal_info)

    # Insert personal information history
    _personal_info_history = IDXPersonalInfoHistory()
    _personal_info_history.issuer_address = register_data.link_address
    _personal_info_history.account_address = account_address
    _personal_info_history.event_type = PersonalInfoEventType.REGISTER
    _personal_info_history.personal_info = personal_info
    db.add(_personal_info_history)

    await db.commit()

    return


# POST: /sealed_tx/holder_extra_info
@router.post(
    "/holder_extra_info",
    operation_id="SealedTxRegisterHolderExtraInfo",
    response_model=None,
    responses=get_routers_responses(InvalidParameterError),
)
async def sealed_tx_register_holder_extra_info(
    db: DBAsyncSession,
    raw_request_body: RawRequestBody,
    request: Request,
    sealed_tx_sig: SealedTxSignatureHeader,
    extra_info: SealedTxRegisterHolderExtraInfoRequest,
):
    # Verify sealed tx signature
    account_address = VerifySealedTxSignature(
        req=request, body=json.loads(raw_request_body.decode()), signature=sealed_tx_sig
    )

    # Insert/Update token holder's extra information
    # NOTE: Overwrite if a same record already exists.
    _holder_extra_info = TokenHolderExtraInfo()
    _holder_extra_info.token_address = extra_info.token_address
    _holder_extra_info.account_address = account_address
    _holder_extra_info.external_id1_type = extra_info.external_id1_type
    _holder_extra_info.external_id1 = extra_info.external_id1
    _holder_extra_info.external_id2_type = extra_info.external_id2_type
    _holder_extra_info.external_id2 = extra_info.external_id2
    _holder_extra_info.external_id3_type = extra_info.external_id3_type
    _holder_extra_info.external_id3 = extra_info.external_id3
    await db.merge(_holder_extra_info)
    await db.commit()

    return


# POST: /sealed_tx/ibet_wst/whitelists/add
@router.post(
    "/ibet_wst/whitelists/add",
    operation_id="SealedTxAddIbetWSTWhitelist",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
async def sealed_tx_add_ibet_wst_whitelist(
    db: DBAsyncSession,
    raw_request_body: RawRequestBody,
    request: Request,
    sealed_tx_sig: SealedTxSignatureHeader,
    data: SealedTxAddIbetWSTWhitelistRequest,
):
    """
    Add an account to the IbetWST whitelist by sealed tx

    - This endpoint allows an issuer's delegated EOA to instruct whitelist registration by sealed tx.
    """

    # Verify sealed tx signature
    account_address = VerifySealedTxSignature(
        req=request, body=json.loads(raw_request_body.decode()), signature=sealed_tx_sig
    )

    blockchain_platform = IbetWSTBlockchain(data.blockchain_platform)
    _ensure_ibet_wst_feature_enabled(blockchain_platform)

    # Get token
    token = await _get_ibet_wst_token(
        db=db,
        token_address=data.token_address,
        blockchain_platform=blockchain_platform,
    )

    # Check if the signed EOA is delegated for IbetWST whitelist KYC operations.
    delegate = (
        await db.scalars(
            select(IbetWSTWhitelistKYCDelegatedEoa)
            .where(
                and_(
                    IbetWSTWhitelistKYCDelegatedEoa.key_manager == token.issuer_address,
                    IbetWSTWhitelistKYCDelegatedEoa.account_address == account_address,
                )
            )
            .limit(1)
        )
    ).first()
    if delegate is None:
        raise InvalidParameterError("delegated EOA is not authorized")

    issuer_account = (
        await db.scalars(
            select(Account)
            .where(
                and_(
                    Account.issuer_address == token.issuer_address,
                    Account.is_deleted.is_(False),
                )
            )
            .limit(1)
        )
    ).first()
    if issuer_account is None:
        raise HTTPException(status_code=404, detail="Issuer account not found")

    # Get issuer private key and create an issuer-authorized transaction record.
    decrypt_password = E2EEUtils.decrypt(issuer_account.eoa_password)
    issuer_pk = decode_keyfile_json(
        raw_keyfile_json=issuer_account.keyfile,
        password=decrypt_password.encode("utf-8"),
    )

    ibet_wst_address = _get_ibet_wst_address(token, blockchain_platform)
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")
    contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    nonce = secrets.token_bytes(32)
    domain_separator = await contract.domain_separator()
    digest = IbetWSTDigestHelper.generate_add_account_whitelist_digest(
        domain_separator=domain_separator,
        st_account=data.st_account_address,
        sc_account_in=data.sc_account_address_in,
        sc_account_out=data.sc_account_address_out,
        nonce=nonce,
    )
    signature = _get_signer_web3(blockchain_platform).eth.account.unsafe_sign_hash(
        digest, issuer_pk
    )

    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.ADD_WHITELIST
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsAddAccountWhiteList(
        st_account=data.st_account_address,
        sc_account_in=data.sc_account_address_in,
        sc_account_out=data.sc_account_address_out,
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = token.issuer_address
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=nonce.hex(),
        v=signature.v,
        r=signature.r.to_bytes(32).hex(),
        s=signature.s.to_bytes(32).hex(),
    )
    db.add(wst_tx)
    await db.commit()

    return {"tx_id": tx_id}


# POST: /sealed_tx/ibet_wst/whitelists/delete
@router.post(
    "/ibet_wst/whitelists/delete",
    operation_id="SealedTxDeleteIbetWSTWhitelist",
    response_model=IbetWSTTransactionResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
async def sealed_tx_delete_ibet_wst_whitelist(
    db: DBAsyncSession,
    raw_request_body: RawRequestBody,
    request: Request,
    sealed_tx_sig: SealedTxSignatureHeader,
    data: SealedTxDeleteIbetWSTWhitelistRequest,
):
    """
    Delete an account from the IbetWST whitelist by sealed tx

    - This endpoint allows an issuer's delegated EOA to instruct whitelist deletion by sealed tx.
    """

    # Verify sealed tx signature
    account_address = VerifySealedTxSignature(
        req=request, body=json.loads(raw_request_body.decode()), signature=sealed_tx_sig
    )

    blockchain_platform = IbetWSTBlockchain(data.blockchain_platform)
    _ensure_ibet_wst_feature_enabled(blockchain_platform)

    # Get token
    token = await _get_ibet_wst_token(
        db=db,
        token_address=data.token_address,
        blockchain_platform=blockchain_platform,
        reject_pending_token=True,
    )

    # Check if the signed EOA is delegated for IbetWST whitelist KYC operations.
    delegate = (
        await db.scalars(
            select(IbetWSTWhitelistKYCDelegatedEoa)
            .where(
                and_(
                    IbetWSTWhitelistKYCDelegatedEoa.key_manager == token.issuer_address,
                    IbetWSTWhitelistKYCDelegatedEoa.account_address == account_address,
                )
            )
            .limit(1)
        )
    ).first()
    if delegate is None:
        raise InvalidParameterError("delegated EOA is not authorized")

    issuer_account = (
        await db.scalars(
            select(Account)
            .where(
                and_(
                    Account.issuer_address == token.issuer_address,
                    Account.is_deleted.is_(False),
                )
            )
            .limit(1)
        )
    ).first()
    if issuer_account is None:
        raise HTTPException(status_code=404, detail="Issuer account not found")

    # Get issuer private key and create an issuer-authorized transaction record.
    decrypt_password = E2EEUtils.decrypt(issuer_account.eoa_password)
    issuer_pk = decode_keyfile_json(
        raw_keyfile_json=issuer_account.keyfile,
        password=decrypt_password.encode("utf-8"),
    )

    ibet_wst_address = _get_ibet_wst_address(token, blockchain_platform)
    if ibet_wst_address is None:
        raise HTTPException(status_code=404, detail="Token not found")
    contract = _get_wst_contract(ibet_wst_address, blockchain_platform)
    nonce = secrets.token_bytes(32)
    domain_separator = await contract.domain_separator()
    digest = IbetWSTDigestHelper.generate_delete_account_whitelist_digest(
        domain_separator=domain_separator,
        st_account=data.st_account_address,
        nonce=nonce,
    )
    signature = _get_signer_web3(blockchain_platform).eth.account.unsafe_sign_hash(
        digest, issuer_pk
    )

    wst_tx_model = _get_wst_tx_model(blockchain_platform)
    tx_id = str(uuid.uuid4())
    wst_tx = wst_tx_model()
    wst_tx.tx_id = tx_id
    wst_tx.tx_type = IbetWSTTxType.DELETE_WHITELIST
    wst_tx.version = IbetWSTVersion.V_1
    wst_tx.status = IbetWSTTxStatus.PENDING
    wst_tx.ibet_wst_address = ibet_wst_address
    wst_tx.tx_params = IbetWSTTxParamsDeleteAccountWhiteList(
        st_account=data.st_account_address,
    )
    wst_tx.tx_sender = _get_master_account(blockchain_platform)
    wst_tx.authorizer = token.issuer_address
    wst_tx.authorization = IbetWSTAuthorization(
        nonce=nonce.hex(),
        v=signature.v,
        r=signature.r.to_bytes(32).hex(),
        s=signature.s.to_bytes(32).hex(),
    )
    db.add(wst_tx)
    await db.commit()

    return {"tx_id": tx_id}
