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
import uuid
from datetime import UTC, datetime
from typing import Annotated, List, Optional, Sequence

import pytz
from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Header, Path, Query, Request
from fastapi.exceptions import HTTPException
from sqlalchemy import (
    String,
    and_,
    asc,
    case,
    cast,
    column,
    desc,
    distinct,
    func,
    literal,
    literal_column,
    null,
    or_,
    select,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import coalesce

import config
from app import log
from app.database import DBAsyncSession
from app.exceptions import (
    AuthorizationError,
    BatchPersonalInfoRegistrationValidationError,
    ContractRevertError,
    InvalidParameterError,
    InvalidUploadErrorDetail,
    MultipleTokenTransferNotAllowedError,
    NonTransferableTokenError,
    OperationNotAllowedStateError,
    OperationNotSupportedVersionError,
    PersonalInfoExceedsSizeLimit,
    RecordErrorDetail,
    SendTransactionError,
    TokenNotExistError,
)
from app.model.blockchain import (
    IbetSecurityTokenEscrow,
    IbetStraightBondContract,
    PersonalInfoContract,
    TokenListContract,
)
from app.model.blockchain.tx_params.ibet_security_token_escrow import (
    ApproveTransferParams as EscrowApproveTransferParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    AdditionalIssueParams,
    ApproveTransferParams,
    CancelTransferParams,
    ForcedTransferParams,
    RedeemParams,
    UpdateParams,
)
from app.model.db import (
    UTXO,
    Account,
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeemUpload,
    BatchRegisterPersonalInfo,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    BulkTransfer,
    BulkTransferUpload,
    IDXIssueRedeem,
    IDXIssueRedeemEventType,
    IDXIssueRedeemSortItem,
    IDXLock,
    IDXLockedPosition,
    IDXPersonalInfo,
    IDXPosition,
    IDXTransfer,
    IDXTransferApproval,
    IDXTransferApprovalsSortItem,
    IDXUnlock,
    ScheduledEvents,
    Token,
    TokenHolderExtraInfo,
    TokenType,
    TokenUpdateOperationCategory,
    TokenUpdateOperationLog,
    TokenVersion,
    TransferApprovalHistory,
    TransferApprovalOperationType,
    UpdateToken,
)
from app.model.schema import (
    BatchIssueRedeemUploadIdResponse,
    BatchRegisterPersonalInfoUploadResponse,
    BulkTransferUploadIdResponse,
    BulkTransferUploadRecordResponse,
    BulkTransferUploadResponse,
    GetBatchIssueRedeemResponse,
    GetBatchRegisterPersonalInfoResponse,
    HolderCountResponse,
    HolderResponse,
    HoldersResponse,
    IbetStraightBondAdditionalIssue,
    IbetStraightBondBulkTransferRequest,
    IbetStraightBondCreate,
    IbetStraightBondRedeem,
    IbetStraightBondResponse,
    IbetStraightBondScheduledUpdate,
    IbetStraightBondTransfer,
    IbetStraightBondUpdate,
    IssueRedeemHistoryResponse,
    ListAdditionalIssuanceHistoryQuery,
    ListAllAdditionalIssueUploadQuery,
    ListAllHoldersQuery,
    ListAllHoldersSortItem,
    ListAllPersonalInfoBatchRegistrationUploadQuery,
    ListAllRedeemUploadQuery,
    ListAllTokenLockEventsQuery,
    ListAllTokenLockEventsResponse,
    ListAllTokenLockEventsSortItem,
    ListBatchIssueRedeemUploadResponse,
    ListBatchRegisterPersonalInfoUploadResponse,
    ListBulkTransferQuery,
    ListBulkTransferUploadQuery,
    ListRedeemHistoryQuery,
    ListSpecificTokenTransferApprovalHistoryQuery,
    ListTokenOperationLogHistoryQuery,
    ListTokenOperationLogHistoryResponse,
    ListTransferApprovalHistoryQuery,
    ListTransferHistoryQuery,
    ListTransferHistorySortItem,
    LockEventCategory,
    PersonalInfoDataSource,
    RegisterHolderExtraInfoRequest,
    RegisterPersonalInfoRequest,
    ScheduledEventIdListResponse,
    ScheduledEventIdResponse,
    ScheduledEventResponse,
    TokenAddressResponse,
    TransferApprovalHistoryResponse,
    TransferApprovalsResponse,
    TransferApprovalTokenDetailResponse,
    TransferHistoryResponse,
    UpdateTransferApprovalOperationType,
    UpdateTransferApprovalRequest,
)
from app.model.schema.base import ValueOperator
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    validate_headers,
)
from app.utils.contract_utils import AsyncContractUtils
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

router = APIRouter(
    prefix="/bond",
    tags=["bond"],
)

LOG = log.get_logger()
local_tz = pytz.timezone(config.TZ)
utc_tz = pytz.timezone("UTC")


# POST: /bond/tokens
@router.post(
    "/tokens",
    operation_id="IssueBondToken",
    response_model=TokenAddressResponse,
    responses=get_routers_responses(
        422, 401, AuthorizationError, SendTransactionError, ContractRevertError
    ),
)
async def issue_bond_token(
    db: DBAsyncSession,
    request: Request,
    token: IbetStraightBondCreate,
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Issue ibetStraightBond token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Deploy
    _symbol = token.symbol if token.symbol is not None else ""
    _redemption_date = (
        token.redemption_date if token.redemption_date is not None else ""
    )
    _redemption_value = (
        token.redemption_value if token.redemption_value is not None else 0
    )
    _redemption_value_currency = (
        token.redemption_value_currency
        if token.redemption_value_currency is not None
        else ""
    )
    _return_date = token.return_date if token.return_date is not None else ""
    _return_amount = token.return_amount if token.return_amount is not None else ""
    arguments = [
        token.name,
        _symbol,
        token.total_supply,
        token.face_value,
        token.face_value_currency,
        _redemption_date,
        _redemption_value,
        _redemption_value_currency,
        _return_date,
        _return_amount,
        token.purpose,
    ]
    try:
        contract_address, abi, tx_hash = await IbetStraightBondContract().create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Check need update
    update_items = [
        "interest_rate",
        "interest_payment_date",
        "interest_payment_currency",
        "base_fx_rate",
        "transferable",
        "status",
        "is_offering",
        "is_redeemed",
        "tradable_exchange_contract_address",
        "personal_info_contract_address",
        "require_personal_info_registered",
        "contact_information",
        "privacy_policy",
        "transfer_approval_required",
    ]
    token_dict = token.__dict__
    is_update = False
    for key in update_items:
        item = token_dict.get(key)
        if item is not None:
            is_update = True
            break

    if is_update:
        # Register token for the update batch
        _update_token = UpdateToken()
        _update_token.token_address = contract_address
        _update_token.issuer_address = issuer_address
        _update_token.type = TokenType.IBET_STRAIGHT_BOND.value
        _update_token.arguments = token_dict
        _update_token.status = 0  # pending
        _update_token.trigger = "Issue"
        db.add(_update_token)

        token_status = 0  # processing
    else:
        # Register token_address token list
        try:
            await TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address=contract_address,
                token_template=TokenType.IBET_STRAIGHT_BOND,
                tx_from=issuer_address,
                private_key=private_key,
            )
        except SendTransactionError:
            raise SendTransactionError("failed to register token address token list")

        # Insert initial position data
        _position = IDXPosition()
        _position.token_address = contract_address
        _position.account_address = issuer_address
        _position.balance = token.total_supply
        _position.exchange_balance = 0
        _position.exchange_commitment = 0
        _position.pending_transfer = 0
        db.add(_position)

        # Insert issuer's UTXO data
        block = await AsyncContractUtils.get_block_by_transaction_hash(tx_hash)
        _utxo = UTXO()
        _utxo.transaction_hash = tx_hash
        _utxo.account_address = issuer_address
        _utxo.token_address = contract_address
        _utxo.amount = token.total_supply
        _utxo.block_number = block["number"]
        _utxo.block_timestamp = datetime.fromtimestamp(block["timestamp"], UTC).replace(
            tzinfo=None
        )
        db.add(_utxo)

        token_status = 1  # succeeded

    # Register token data
    _token = Token()
    _token.type = TokenType.IBET_STRAIGHT_BOND.value
    _token.tx_hash = tx_hash
    _token.issuer_address = issuer_address
    _token.token_address = contract_address
    _token.abi = abi
    _token.token_status = token_status
    _token.version = TokenVersion.V_24_09
    db.add(_token)

    # Register operation log
    operation_log = TokenUpdateOperationLog()
    operation_log.token_address = contract_address
    operation_log.issuer_address = issuer_address
    operation_log.type = TokenType.IBET_STRAIGHT_BOND.value
    operation_log.arguments = token.model_dump()
    operation_log.original_contents = None
    operation_log.operation_category = TokenUpdateOperationCategory.ISSUE.value
    db.add(operation_log)

    await db.commit()

    return json_response(
        {"token_address": _token.token_address, "token_status": token_status}
    )


# GET: /bond/tokens
@router.get(
    "/tokens",
    operation_id="ListAllBondTokens",
    response_model=List[IbetStraightBondResponse],
    responses=get_routers_responses(422),
)
async def list_all_bond_tokens(
    db: DBAsyncSession,
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all issued bond tokens"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get issued token list
    if issuer_address is None:
        tokens: Sequence[Token] = (
            await db.scalars(
                select(Token)
                .where(Token.type == TokenType.IBET_STRAIGHT_BOND)
                .order_by(Token.id)
            )
        ).all()
    else:
        tokens: Sequence[Token] = (
            await db.scalars(
                select(Token)
                .where(
                    and_(
                        Token.type == TokenType.IBET_STRAIGHT_BOND,
                        Token.issuer_address == issuer_address,
                    )
                )
                .order_by(Token.id)
            )
        ).all()

    bond_tokens = []
    for token in tokens:
        # Get contract data
        bond_token = (
            await IbetStraightBondContract(token.token_address).get()
        ).__dict__
        issue_datetime_utc = pytz.timezone("UTC").localize(token.created)
        bond_token["issue_datetime"] = issue_datetime_utc.astimezone(
            local_tz
        ).isoformat()
        bond_token["token_status"] = token.token_status
        bond_token["contract_version"] = token.version
        bond_token.pop("contract_name")
        bond_tokens.append(bond_token)

    return json_response(bond_tokens)


# GET: /bond/tokens/{token_address}
@router.get(
    "/tokens/{token_address}",
    operation_id="RetrieveBondToken",
    response_model=IbetStraightBondResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
async def retrieve_bond_token(
    db: DBAsyncSession, token_address: Annotated[str, Path()]
):
    """Retrieve the bond token"""
    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get contract data
    bond_token = (await IbetStraightBondContract(token_address).get()).__dict__
    issue_datetime_utc = pytz.timezone("UTC").localize(_token.created)
    bond_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
    bond_token["token_status"] = _token.token_status
    bond_token["contract_version"] = _token.version
    bond_token.pop("contract_name")

    return json_response(bond_token)


# POST: /bond/tokens/{token_address}
@router.post(
    "/tokens/{token_address}",
    operation_id="UpdateBondToken",
    response_model=None,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
        OperationNotSupportedVersionError,
    ),
)
async def update_bond_token(
    db: DBAsyncSession,
    request: Request,
    update_data: IbetStraightBondUpdate,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Update the bond token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Verify that the token version supports the operation
    if _token.version < TokenVersion.V_23_12:
        if (
            update_data.face_value_currency is not None
            or update_data.interest_payment_currency is not None
            or update_data.redemption_value_currency is not None
            or update_data.base_fx_rate is not None
        ):
            raise OperationNotSupportedVersionError(
                f"the operation is not supported in {_token.version}"
            )

    if _token.version < TokenVersion.V_24_06:
        if update_data.require_personal_info_registered is not None:
            raise OperationNotSupportedVersionError(
                f"the operation is not supported in {_token.version}"
            )

    if _token.version < TokenVersion.V_24_09:
        if update_data.redemption_date is not None or update_data.purpose is not None:
            raise OperationNotSupportedVersionError(
                f"the operation is not supported in {_token.version}"
            )

    # Send transaction
    try:
        token_contract = IbetStraightBondContract(token_address)
        original_contents = (await token_contract.get()).__dict__
        await token_contract.update(
            data=UpdateParams(**update_data.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Register operation log
    operation_log = TokenUpdateOperationLog()
    operation_log.token_address = token_address
    operation_log.issuer_address = issuer_address
    operation_log.type = TokenType.IBET_STRAIGHT_BOND.value
    operation_log.arguments = update_data.model_dump(exclude_none=True)
    operation_log.original_contents = original_contents
    operation_log.operation_category = TokenUpdateOperationCategory.UPDATE.value
    db.add(operation_log)

    await db.commit()
    return


# GET: /bond/tokens/{token_address}/history
@router.get(
    "/tokens/{token_address}/history",
    operation_id="ListBondOperationLogHistory",
    response_model=ListTokenOperationLogHistoryResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
async def list_bond_operation_log_history(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    request_query: Annotated[ListTokenOperationLogHistoryQuery, Query()],
):
    """List all bond token operation log history"""
    stmt = select(TokenUpdateOperationLog).where(
        and_(
            TokenUpdateOperationLog.type == TokenType.IBET_STRAIGHT_BOND,
            TokenUpdateOperationLog.token_address == token_address,
        )
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.operation_category:
        stmt = stmt.where(
            TokenUpdateOperationLog.operation_category
            == request_query.operation_category
        )
    if request_query.modified_contents:
        stmt = stmt.where(
            cast(TokenUpdateOperationLog.arguments, String).like(
                "%" + request_query.modified_contents + "%"
            )
        )
    if request_query.created_from:
        _created_from = datetime.strptime(
            request_query.created_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            TokenUpdateOperationLog.created
            >= local_tz.localize(_created_from).astimezone(utc_tz)
        )
    if request_query.created_to:
        _created_to = datetime.strptime(
            request_query.created_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            TokenUpdateOperationLog.created
            <= local_tz.localize(_created_to).astimezone(utc_tz)
        )

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    sort_attr = getattr(TokenUpdateOperationLog, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if request_query.sort_item != TokenUpdateOperationLog.created:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(TokenUpdateOperationLog.created))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    history: Sequence[TokenUpdateOperationLog] = (await db.scalars(stmt)).all()

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total,
            },
            "history": [
                {
                    "original_contents": h.original_contents,
                    "modified_contents": h.arguments,
                    "operation_category": h.operation_category,
                    "created": utc_tz.localize(h.created).astimezone(local_tz),
                }
                for h in history
            ],
        }
    )


# GET: /bond/tokens/{token_address}/additional_issue
@router.get(
    "/tokens/{token_address}/additional_issue",
    operation_id="ListBondAdditionalIssuanceHistory",
    response_model=IssueRedeemHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_bond_additional_issuance_history(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    request_query: Annotated[ListAdditionalIssuanceHistoryQuery, Query()],
):
    """List bond additional issuance history"""
    # Get token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get history record
    stmt = select(IDXIssueRedeem).where(
        and_(
            IDXIssueRedeem.event_type == IDXIssueRedeemEventType.ISSUE,
            IDXIssueRedeem.token_address == token_address,
        )
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    # Sort
    sort_attr = getattr(IDXIssueRedeem, request_query.sort_item, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if request_query.sort_item != IDXIssueRedeemSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(IDXIssueRedeem.block_timestamp))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _events: Sequence[IDXIssueRedeem] = (await db.scalars(stmt)).all()

    history = []
    for _event in _events:
        block_timestamp_utc = pytz.timezone("UTC").localize(_event.block_timestamp)
        history.append(
            {
                "transaction_hash": _event.transaction_hash,
                "token_address": token_address,
                "locked_address": _event.locked_address,
                "target_address": _event.target_address,
                "amount": _event.amount,
                "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat(),
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total,
            },
            "history": history,
        }
    )


# POST: /bond/tokens/{token_address}/additional_issue
@router.post(
    "/tokens/{token_address}/additional_issue",
    operation_id="IssueAdditionalBond",
    response_model=None,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
    ),
)
async def issue_additional_bond(
    db: DBAsyncSession,
    request: Request,
    data: IbetStraightBondAdditionalIssue,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Issue additional bonds"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        await IbetStraightBondContract(token_address).additional_issue(
            data=AdditionalIssueParams(**data.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /bond/tokens/{token_address}/additional_issue/batch
@router.get(
    "/tokens/{token_address}/additional_issue/batch",
    operation_id="ListAllBatchAdditionalBondIssue",
    response_model=ListBatchIssueRedeemUploadResponse,
    responses=get_routers_responses(422),
)
async def list_all_batch_additional_bond_issue(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    get_query: Annotated[ListAllAdditionalIssueUploadQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all bond batch additional issues"""
    # Get a list of uploads
    stmt = select(BatchIssueRedeemUpload).where(
        and_(
            BatchIssueRedeemUpload.token_address == token_address,
            BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND,
            BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.ISSUE,
        )
    )

    if issuer_address is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.issuer_address == issuer_address)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if get_query.processed is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.processed == get_query.processed)

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(BatchIssueRedeemUpload.created)
    else:  # DESC
        stmt = stmt.order_by(desc(BatchIssueRedeemUpload.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _upload_list: Sequence[BatchIssueRedeemUpload] = (await db.scalars(stmt)).all()

    uploads = []
    for _upload in _upload_list:
        created_utc = pytz.timezone("UTC").localize(_upload.created)
        uploads.append(
            {
                "batch_id": _upload.upload_id,
                "issuer_address": _upload.issuer_address,
                "token_type": _upload.token_type,
                "token_address": _upload.token_address,
                "processed": _upload.processed,
                "created": created_utc.astimezone(local_tz).isoformat(),
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": get_query.offset,
            "limit": get_query.limit,
            "total": total,
        },
        "uploads": uploads,
    }
    return json_response(resp)


# POST: /bond/tokens/{token_address}/additional_issue/batch
@router.post(
    "/tokens/{token_address}/additional_issue/batch",
    operation_id="IssueAdditionalBondsInBatch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(
        422, 401, 404, AuthorizationError, InvalidParameterError
    ),
)
async def issue_additional_bonds_in_batch(
    db: DBAsyncSession,
    request: Request,
    data: List[IbetStraightBondAdditionalIssue],
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Issue additional bonds in batch"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Validate params
    if len(data) < 1:
        raise InvalidParameterError("list length must be at least one")

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Check token status
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Generate upload_id
    upload_id = uuid.uuid4()

    # Add batch data
    _batch_upload = BatchIssueRedeemUpload()
    _batch_upload.upload_id = upload_id
    _batch_upload.issuer_address = issuer_address
    _batch_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
    _batch_upload.token_address = token_address
    _batch_upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
    _batch_upload.processed = False
    db.add(_batch_upload)

    for _item in data:
        _batch_issue = BatchIssueRedeem()
        _batch_issue.upload_id = upload_id
        _batch_issue.account_address = _item.account_address
        _batch_issue.amount = _item.amount
        _batch_issue.status = 0
        db.add(_batch_issue)

    await db.commit()

    return json_response({"batch_id": str(upload_id)})


# GET: /bond/tokens/{token_address}/additional_issue/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/additional_issue/batch/{batch_id}",
    operation_id="RetrieveBatchAdditionalBondIssueStatus",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404),
)
async def retrieve_batch_additional_bond_issue_status(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    batch_id: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
):
    """Retrieve detailed status of additional bond batch issuance"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Upload Existence Check
    batch: Optional[BatchIssueRedeemUpload] = (
        await db.scalars(
            select(BatchIssueRedeemUpload)
            .where(
                and_(
                    BatchIssueRedeemUpload.upload_id == batch_id,
                    BatchIssueRedeemUpload.issuer_address == issuer_address,
                    BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND,
                    BatchIssueRedeemUpload.token_address == token_address,
                    BatchIssueRedeemUpload.category
                    == BatchIssueRedeemProcessingCategory.ISSUE,
                )
            )
            .limit(1)
        )
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: Sequence[tuple[BatchIssueRedeem, IDXPersonalInfo | None]] = (
        (
            await db.execute(
                select(BatchIssueRedeem, IDXPersonalInfo)
                .outerjoin(
                    IDXPersonalInfo,
                    and_(
                        BatchIssueRedeem.account_address
                        == IDXPersonalInfo.account_address,
                        IDXPersonalInfo.issuer_address == issuer_address,
                    ),
                )
                .where(BatchIssueRedeem.upload_id == batch_id)
            )
        )
        .tuples()
        .all()
    )

    personal_info_default = {
        "key_manager": None,
        "name": None,
        "postal_code": None,
        "address": None,
        "email": None,
        "birth": None,
        "is_corporate": None,
        "tax_category": None,
    }

    return json_response(
        {
            "processed": batch.processed,
            "results": [
                {
                    "account_address": record[0].account_address,
                    "amount": record[0].amount,
                    "status": record[0].status,
                    "personal_information": (
                        record[1].personal_info if record[1] else personal_info_default
                    ),
                }
                for record in record_list
            ],
        }
    )


# GET: /bond/tokens/{token_address}/redeem
@router.get(
    "/tokens/{token_address}/redeem",
    operation_id="ListBondRedemptionHistory",
    response_model=IssueRedeemHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_bond_redemption_history(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    get_query: Annotated[ListRedeemHistoryQuery, Query()],
):
    """List the history of bond redemptions"""
    # Get token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get history record
    stmt = select(IDXIssueRedeem).where(
        and_(
            IDXIssueRedeem.event_type == IDXIssueRedeemEventType.REDEEM,
            IDXIssueRedeem.token_address == token_address,
        )
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    # Sort
    sort_attr = getattr(IDXIssueRedeem, get_query.sort_item, None)
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if get_query.sort_item != IDXIssueRedeemSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(IDXIssueRedeem.block_timestamp))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _events: Sequence[IDXIssueRedeem] = (await db.scalars(stmt)).all()

    history = []
    for _event in _events:
        block_timestamp_utc = pytz.timezone("UTC").localize(_event.block_timestamp)
        history.append(
            {
                "transaction_hash": _event.transaction_hash,
                "token_address": token_address,
                "locked_address": _event.locked_address,
                "target_address": _event.target_address,
                "amount": _event.amount,
                "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat(),
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "history": history,
        }
    )


# POST: /bond/tokens/{token_address}/redeem
@router.post(
    "/tokens/{token_address}/redeem",
    operation_id="RedeemBond",
    response_model=None,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
    ),
)
async def redeem_bond(
    db: DBAsyncSession,
    request: Request,
    data: IbetStraightBondRedeem,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Redeem bond token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        await IbetStraightBondContract(token_address).redeem(
            data=RedeemParams(**data.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /bond/tokens/{token_address}/redeem/batch
@router.get(
    "/tokens/{token_address}/redeem/batch",
    operation_id="ListAllBatchBondRedemption",
    response_model=ListBatchIssueRedeemUploadResponse,
    responses=get_routers_responses(422),
)
async def list_all_batch_bond_redemption(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    get_query: Annotated[ListAllRedeemUploadQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all batch bond redemptions"""
    # Get a list of uploads
    stmt = select(BatchIssueRedeemUpload).where(
        and_(
            BatchIssueRedeemUpload.token_address == token_address,
            BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND,
            BatchIssueRedeemUpload.category
            == BatchIssueRedeemProcessingCategory.REDEEM,
        )
    )

    if issuer_address is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.issuer_address == issuer_address)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if get_query.processed is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.processed == get_query.processed)

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(BatchIssueRedeemUpload.created)
    else:  # DESC
        stmt = stmt.order_by(desc(BatchIssueRedeemUpload.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _upload_list: Sequence[BatchIssueRedeemUpload] = (await db.scalars(stmt)).all()

    uploads = []
    for _upload in _upload_list:
        created_utc = pytz.timezone("UTC").localize(_upload.created)
        uploads.append(
            {
                "batch_id": _upload.upload_id,
                "issuer_address": _upload.issuer_address,
                "token_type": _upload.token_type,
                "token_address": _upload.token_address,
                "processed": _upload.processed,
                "created": created_utc.astimezone(local_tz).isoformat(),
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": get_query.offset,
            "limit": get_query.limit,
            "total": total,
        },
        "uploads": uploads,
    }
    return json_response(resp)


# POST: /bond/tokens/{token_address}/redeem/batch
@router.post(
    "/tokens/{token_address}/redeem/batch",
    operation_id="RedeemBondsInBatch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(
        422, 401, 404, AuthorizationError, InvalidParameterError
    ),
)
async def redeem_bonds_in_batch(
    db: DBAsyncSession,
    request: Request,
    data: List[IbetStraightBondRedeem],
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Redeem bonds in batch"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Validate params
    if len(data) < 1:
        raise InvalidParameterError("list length must be at least one")

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Check token status
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Generate upload_id
    upload_id = uuid.uuid4()

    # Add batch data
    _batch_upload = BatchIssueRedeemUpload()
    _batch_upload.upload_id = upload_id
    _batch_upload.issuer_address = issuer_address
    _batch_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
    _batch_upload.token_address = token_address
    _batch_upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
    _batch_upload.processed = False
    db.add(_batch_upload)

    for _item in data:
        _batch_issue = BatchIssueRedeem()
        _batch_issue.upload_id = upload_id
        _batch_issue.account_address = _item.account_address
        _batch_issue.amount = _item.amount
        _batch_issue.status = 0
        db.add(_batch_issue)

    await db.commit()

    return json_response({"batch_id": str(upload_id)})


# GET: /bond/tokens/{token_address}/redeem/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/redeem/batch/{batch_id}",
    operation_id="RetrieveBatchBondRedemptionStatus",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404),
)
async def retrieve_batch_bond_redemption_status(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    batch_id: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
):
    """Retrieve detailed status of batch bond redemption"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Upload Existence Check
    batch: Optional[BatchIssueRedeemUpload] = (
        await db.scalars(
            select(BatchIssueRedeemUpload)
            .where(
                and_(
                    BatchIssueRedeemUpload.upload_id == batch_id,
                    BatchIssueRedeemUpload.issuer_address == issuer_address,
                    BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND,
                    BatchIssueRedeemUpload.token_address == token_address,
                    BatchIssueRedeemUpload.category
                    == BatchIssueRedeemProcessingCategory.REDEEM,
                )
            )
            .limit(1)
        )
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: Sequence[tuple[BatchIssueRedeem, IDXPersonalInfo | None]] = (
        (
            await db.execute(
                select(BatchIssueRedeem, IDXPersonalInfo)
                .outerjoin(
                    IDXPersonalInfo,
                    and_(
                        BatchIssueRedeem.account_address
                        == IDXPersonalInfo.account_address,
                        IDXPersonalInfo.issuer_address == issuer_address,
                    ),
                )
                .where(BatchIssueRedeem.upload_id == batch_id)
            )
        )
        .tuples()
        .all()
    )

    personal_info_default = {
        "key_manager": None,
        "name": None,
        "postal_code": None,
        "address": None,
        "email": None,
        "birth": None,
        "is_corporate": None,
        "tax_category": None,
    }

    return json_response(
        {
            "processed": batch.processed,
            "results": [
                {
                    "account_address": record[0].account_address,
                    "amount": record[0].amount,
                    "status": record[0].status,
                    "personal_information": (
                        record[1].personal_info if record[1] else personal_info_default
                    ),
                }
                for record in record_list
            ],
        }
    )


# GET: /bond/tokens/{token_address}/scheduled_events
@router.get(
    "/tokens/{token_address}/scheduled_events",
    operation_id="ListAllScheduledBondTokenUpdateEvents",
    response_model=List[ScheduledEventResponse],
)
async def list_all_scheduled_bond_token_update_events(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all scheduled bond token update events"""

    if issuer_address is None:
        _token_events: Sequence[ScheduledEvents] = (
            await db.scalars(
                select(ScheduledEvents)
                .where(
                    and_(
                        ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND,
                        ScheduledEvents.token_address == token_address,
                    )
                )
                .order_by(ScheduledEvents.id)
            )
        ).all()
    else:
        _token_events: Sequence[ScheduledEvents] = (
            await db.scalars(
                select(ScheduledEvents)
                .where(
                    and_(
                        ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND,
                        ScheduledEvents.issuer_address == issuer_address,
                        ScheduledEvents.token_address == token_address,
                    )
                )
                .order_by(ScheduledEvents.id)
            )
        ).all()

    token_events = []
    for _token_event in _token_events:
        scheduled_datetime_utc = pytz.timezone("UTC").localize(
            _token_event.scheduled_datetime
        )
        created_utc = pytz.timezone("UTC").localize(_token_event.created)
        token_events.append(
            {
                "scheduled_event_id": _token_event.event_id,
                "token_address": token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "scheduled_datetime": scheduled_datetime_utc.astimezone(
                    local_tz
                ).isoformat(),
                "event_type": _token_event.event_type,
                "status": _token_event.status,
                "data": _token_event.data,
                "created": created_utc.astimezone(local_tz).isoformat(),
            }
        )
    return json_response(token_events)


# POST: /bond/tokens/{token_address}/scheduled_events
@router.post(
    "/tokens/{token_address}/scheduled_events",
    operation_id="ScheduleBondTokenUpdateEvent",
    response_model=ScheduledEventIdResponse,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        OperationNotSupportedVersionError,
    ),
)
async def schedule_bond_token_update_event(
    db: DBAsyncSession,
    request: Request,
    event_data: IbetStraightBondScheduledUpdate,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Schedule a new bond token update event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Verify that the token version supports the operation
    if _token.version < TokenVersion.V_23_12:
        if (
            event_data.data.face_value_currency is not None
            or event_data.data.interest_payment_currency is not None
            or event_data.data.redemption_value_currency is not None
            or event_data.data.base_fx_rate is not None
        ):
            raise OperationNotSupportedVersionError(
                f"the operation is not supported in {_token.version}"
            )

    if _token.version < TokenVersion.V_24_06:
        if event_data.data.require_personal_info_registered is not None:
            raise OperationNotSupportedVersionError(
                f"the operation is not supported in {_token.version}"
            )

    if _token.version < TokenVersion.V_24_09:
        if (
            event_data.data.redemption_date is not None
            or event_data.data.purpose is not None
        ):
            raise OperationNotSupportedVersionError(
                f"the operation is not supported in {_token.version}"
            )

    # Register an event
    _scheduled_event = ScheduledEvents()
    _scheduled_event.event_id = str(uuid.uuid4())
    _scheduled_event.issuer_address = issuer_address
    _scheduled_event.token_address = token_address
    _scheduled_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
    _scheduled_event.scheduled_datetime = event_data.scheduled_datetime
    _scheduled_event.event_type = event_data.event_type
    _scheduled_event.data = event_data.data.model_dump()
    _scheduled_event.status = 0
    db.add(_scheduled_event)
    await db.commit()

    return json_response({"scheduled_event_id": _scheduled_event.event_id})


# POST: /bond/tokens/{token_address}/scheduled_events/batch
@router.post(
    "/tokens/{token_address}/scheduled_events/batch",
    operation_id="ScheduleBondTokenUpdateEventsInBatch",
    response_model=ScheduledEventIdListResponse,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        OperationNotSupportedVersionError,
    ),
)
async def schedule_bond_token_update_events_in_batch(
    db: DBAsyncSession,
    request: Request,
    event_data_list: list[IbetStraightBondScheduledUpdate],
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Schedule bond token update events in batch"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    _event_id_list = []
    for event_data in event_data_list:
        # Verify that the token version supports the operation
        if _token.version < TokenVersion.V_23_12:
            if (
                event_data.data.face_value_currency is not None
                or event_data.data.interest_payment_currency is not None
                or event_data.data.redemption_value_currency is not None
                or event_data.data.base_fx_rate is not None
            ):
                raise OperationNotSupportedVersionError(
                    f"the operation is not supported in {_token.version}"
                )

        if _token.version < TokenVersion.V_24_06:
            if event_data.data.require_personal_info_registered is not None:
                raise OperationNotSupportedVersionError(
                    f"the operation is not supported in {_token.version}"
                )

        if _token.version < TokenVersion.V_24_09:
            if (
                event_data.data.redemption_date is not None
                or event_data.data.purpose is not None
            ):
                raise OperationNotSupportedVersionError(
                    f"the operation is not supported in {_token.version}"
                )

        # Register an event
        _scheduled_event = ScheduledEvents()
        _scheduled_event.event_id = str(uuid.uuid4())
        _scheduled_event.issuer_address = issuer_address
        _scheduled_event.token_address = token_address
        _scheduled_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _scheduled_event.scheduled_datetime = event_data.scheduled_datetime
        _scheduled_event.event_type = event_data.event_type
        _scheduled_event.data = event_data.data.model_dump()
        _scheduled_event.status = 0
        db.add(_scheduled_event)

        _event_id_list.append(_scheduled_event.event_id)

    await db.commit()

    return json_response({"scheduled_event_id_list": _event_id_list})


# GET: /bond/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.get(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    operation_id="RetrieveScheduledBondTokenUpdateEvent",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(404),
)
async def retrieve_scheduled_bond_token_update_event(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    scheduled_event_id: Annotated[str, Path()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """Retrieve a scheduled bond token update event"""

    if issuer_address is None:
        _token_event: ScheduledEvents | None = (
            await db.scalars(
                select(ScheduledEvents)
                .where(
                    and_(
                        ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND,
                        ScheduledEvents.event_id == scheduled_event_id,
                        ScheduledEvents.token_address == token_address,
                    )
                )
                .limit(1)
            )
        ).first()
    else:
        _token_event: ScheduledEvents | None = (
            await db.scalars(
                select(ScheduledEvents)
                .where(
                    and_(
                        ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND,
                        ScheduledEvents.event_id == scheduled_event_id,
                        ScheduledEvents.issuer_address == issuer_address,
                        ScheduledEvents.token_address == token_address,
                    )
                )
                .limit(1)
            )
        ).first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="event not found")

    scheduled_datetime_utc = pytz.timezone("UTC").localize(
        _token_event.scheduled_datetime
    )
    created_utc = pytz.timezone("UTC").localize(_token_event.created)
    return json_response(
        {
            "scheduled_event_id": _token_event.event_id,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "scheduled_datetime": scheduled_datetime_utc.astimezone(
                local_tz
            ).isoformat(),
            "event_type": _token_event.event_type,
            "status": _token_event.status,
            "data": _token_event.data,
            "created": created_utc.astimezone(local_tz).isoformat(),
        }
    )


# DELETE: /bond/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.delete(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    operation_id="DeleteScheduledBondTokenUpdateEvent",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError),
)
async def delete_scheduled_bond_token_update_event(
    db: DBAsyncSession,
    request: Request,
    token_address: Annotated[str, Path()],
    scheduled_event_id: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Delete a scheduled bond token update event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authorization
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Delete an event
    _token_event: ScheduledEvents | None = (
        await db.scalars(
            select(ScheduledEvents)
            .where(
                and_(
                    ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND,
                    ScheduledEvents.event_id == scheduled_event_id,
                    ScheduledEvents.issuer_address == issuer_address,
                    ScheduledEvents.token_address == token_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="event not found")

    scheduled_datetime_utc = pytz.timezone("UTC").localize(
        _token_event.scheduled_datetime
    )
    created_utc = pytz.timezone("UTC").localize(_token_event.created)
    rtn = {
        "scheduled_event_id": _token_event.event_id,
        "token_address": token_address,
        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data,
        "created": created_utc.astimezone(local_tz).isoformat(),
    }

    await db.delete(_token_event)
    await db.commit()

    return json_response(rtn)


# GET: /bond/tokens/{token_address}/holders
@router.get(
    "/tokens/{token_address}/holders",
    operation_id="ListAllBondTokenHolders",
    response_model=HoldersResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
async def list_all_bond_token_holders(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    get_query: Annotated[ListAllHoldersQuery, Query()],
    issuer_address: Annotated[str, Header()],
):
    """List all bond token holders"""
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Account
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    locked_value = func.sum(IDXLockedPosition.value)
    stmt = (
        select(
            IDXPosition,
            locked_value,
            IDXPersonalInfo,
            TokenHolderExtraInfo,
            func.max(IDXLockedPosition.modified),
        )
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == IDXPosition.token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .outerjoin(
            IDXPersonalInfo,
            and_(
                IDXPersonalInfo.issuer_address == issuer_address,
                IDXPersonalInfo.account_address == IDXPosition.account_address,
            ),
        )
        .outerjoin(
            TokenHolderExtraInfo,
            and_(
                TokenHolderExtraInfo.token_address == IDXPosition.token_address,
                TokenHolderExtraInfo.account_address == IDXPosition.account_address,
            ),
        )
        .where(IDXPosition.token_address == token_address)
        .group_by(
            IDXPosition.id,
            IDXPersonalInfo.id,
            TokenHolderExtraInfo.token_address,
            TokenHolderExtraInfo.account_address,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
    )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if not get_query.include_former_holder:
        stmt = stmt.where(
            or_(
                IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0,
            )
        )

    if get_query.balance is not None and get_query.balance_operator is not None:
        match get_query.balance_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(IDXPosition.balance == get_query.balance)
            case ValueOperator.GTE:
                stmt = stmt.where(IDXPosition.balance >= get_query.balance)
            case ValueOperator.LTE:
                stmt = stmt.where(IDXPosition.balance <= get_query.balance)

    if (
        get_query.pending_transfer is not None
        and get_query.pending_transfer_operator is not None
    ):
        match get_query.pending_transfer_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(
                    IDXPosition.pending_transfer == get_query.pending_transfer
                )
            case ValueOperator.GTE:
                stmt = stmt.where(
                    IDXPosition.pending_transfer >= get_query.pending_transfer
                )
            case ValueOperator.LTE:
                stmt = stmt.where(
                    IDXPosition.pending_transfer <= get_query.pending_transfer
                )

    if get_query.locked is not None and get_query.locked_operator is not None:
        match get_query.locked_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.having(coalesce(locked_value, 0) == get_query.locked)
            case ValueOperator.GTE:
                stmt = stmt.having(coalesce(locked_value, 0) >= get_query.locked)
            case ValueOperator.LTE:
                stmt = stmt.having(coalesce(locked_value, 0) <= get_query.locked)

    if (
        get_query.balance_and_pending_transfer is not None
        and get_query.balance_and_pending_transfer_operator is not None
    ):
        match get_query.balance_and_pending_transfer_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(
                    IDXPosition.balance + IDXPosition.pending_transfer
                    == get_query.balance_and_pending_transfer
                )
            case ValueOperator.GTE:
                stmt = stmt.where(
                    IDXPosition.balance + IDXPosition.pending_transfer
                    >= get_query.balance_and_pending_transfer
                )
            case ValueOperator.LTE:
                stmt = stmt.where(
                    IDXPosition.balance + IDXPosition.pending_transfer
                    <= get_query.balance_and_pending_transfer
                )

    if get_query.account_address is not None:
        stmt = stmt.where(
            IDXPosition.account_address.like("%" + get_query.account_address + "%")
        )

    if get_query.holder_name is not None:
        stmt = stmt.where(
            IDXPersonalInfo._personal_info["name"]
            .as_string()
            .like("%" + get_query.holder_name + "%")
        )

    if get_query.key_manager is not None:
        stmt = stmt.where(
            IDXPersonalInfo._personal_info["key_manager"]
            .as_string()
            .like("%" + get_query.key_manager + "%")
        )

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if get_query.sort_item == ListAllHoldersSortItem.holder_name:
        sort_attr = IDXPersonalInfo._personal_info["name"].as_string()
    elif get_query.sort_item == ListAllHoldersSortItem.key_manager:
        sort_attr = IDXPersonalInfo._personal_info["key_manager"].as_string()
    elif get_query.sort_item == ListAllHoldersSortItem.locked:
        sort_attr = locked_value
    elif get_query.sort_item == ListAllHoldersSortItem.balance_and_pending_transfer:
        sort_attr = IDXPosition.balance + IDXPosition.pending_transfer
    else:
        sort_attr = getattr(IDXPosition, get_query.sort_item)

    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(asc(sort_attr))
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if get_query.sort_item != ListAllHoldersSortItem.created:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(asc(IDXPosition.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _holders: Sequence[
        tuple[
            IDXPosition,
            int,
            IDXPersonalInfo | None,
            TokenHolderExtraInfo | None,
            datetime | None,
        ]
    ] = (await db.execute(stmt)).tuples().all()

    personal_info_default = {
        "key_manager": None,
        "name": None,
        "postal_code": None,
        "address": None,
        "email": None,
        "birth": None,
        "is_corporate": None,
        "tax_category": None,
    }

    holders = []
    for (
        _position,
        _locked,
        _personal_info,
        _holder_extra_info,
        _lock_event_latest_created,
    ) in _holders:
        personal_info = (
            _personal_info.personal_info
            if _personal_info is not None
            else personal_info_default
        )
        if _position is None and _lock_event_latest_created is not None:
            modified: datetime = _lock_event_latest_created
        elif _position is not None and _lock_event_latest_created is None:
            modified: datetime = _position.modified
        else:
            modified: datetime = (
                _position.modified
                if (_position.modified > _lock_event_latest_created)
                else _lock_event_latest_created
            )

        holders.append(
            {
                "account_address": _position.account_address,
                "personal_information": personal_info,
                "holder_extra_info": _holder_extra_info.extra_info()
                if _holder_extra_info is not None
                else TokenHolderExtraInfo.default_extra_info,
                "balance": _position.balance,
                "exchange_balance": _position.exchange_balance,
                "exchange_commitment": _position.exchange_commitment,
                "pending_transfer": _position.pending_transfer,
                "locked": _locked if _locked is not None else 0,
                "modified": modified,
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "total": total,
                "limit": get_query.limit,
                "offset": get_query.offset,
            },
            "holders": holders,
        }
    )


# GET: /bond/tokens/{token_address}/holders/count
@router.get(
    "/tokens/{token_address}/holders/count",
    operation_id="CountBondTokenHolders",
    response_model=HolderCountResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
async def count_bond_token_holders(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
):
    """Count the number of bond token holders"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Account
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    stmt = (
        select(IDXPosition, func.sum(IDXLockedPosition.value))
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == IDXPosition.token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .where(
            and_(
                IDXPosition.token_address == token_address,
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.pending_transfer != 0,
                    IDXPosition.exchange_commitment != 0,
                    IDXLockedPosition.value != 0,
                ),
            )
        )
        .group_by(
            IDXPosition.id,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
    )
    _count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    return json_response({"count": _count})


# GET: /bond/tokens/{token_address}/holders/{account_address}
@router.get(
    "/tokens/{token_address}/holders/{account_address}",
    operation_id="RetrieveBondTokenHolder",
    response_model=HolderResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
async def retrieve_bond_token_holder(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    account_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
):
    """Retrieve bond token holder"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Issuer
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    _holder: tuple[IDXPosition, int, datetime | None] = (
        (
            await db.execute(
                select(
                    IDXPosition,
                    func.sum(IDXLockedPosition.value),
                    func.max(IDXLockedPosition.modified),
                )
                .outerjoin(
                    IDXLockedPosition,
                    and_(
                        IDXLockedPosition.token_address == IDXPosition.token_address,
                        IDXLockedPosition.account_address
                        == IDXPosition.account_address,
                    ),
                )
                .where(
                    and_(
                        IDXPosition.token_address == token_address,
                        IDXPosition.account_address == account_address,
                    )
                )
                .group_by(
                    IDXPosition.id,
                    IDXLockedPosition.token_address,
                    IDXLockedPosition.account_address,
                )
                .limit(1)
            )
        )
        .tuples()
        .first()
    )

    if _holder is None:
        balance = 0
        exchange_balance = 0
        exchange_commitment = 0
        pending_transfer = 0
        locked = 0
        modified = None
    else:
        balance = _holder[0].balance
        exchange_balance = _holder[0].exchange_balance
        exchange_commitment = _holder[0].exchange_commitment
        pending_transfer = _holder[0].pending_transfer
        locked = _holder[1]

        if _holder[0] is None and _holder[2] is not None:
            modified = _holder[2]
        elif _holder[0] is not None and _holder[2] is None:
            modified = _holder[0].modified
        else:
            modified = (
                _holder[0].modified
                if (_holder[0].modified > _holder[2])
                else _holder[2]
            )

    # Get personal information
    personal_info_default = {
        "key_manager": None,
        "name": None,
        "postal_code": None,
        "address": None,
        "email": None,
        "birth": None,
        "is_corporate": None,
        "tax_category": None,
    }
    _personal_info_record: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == account_address,
                    IDXPersonalInfo.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _personal_info_record is None:
        _personal_info = personal_info_default
    else:
        _personal_info = _personal_info_record.personal_info

    # Get holder's extra information
    _holder_extra_info: TokenHolderExtraInfo | None = (
        await db.scalars(
            select(TokenHolderExtraInfo)
            .where(
                and_(
                    TokenHolderExtraInfo.token_address == token_address,
                    TokenHolderExtraInfo.account_address == account_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _holder_extra_info is None:
        holder_extra_info = TokenHolderExtraInfo.default_extra_info
    else:
        holder_extra_info = _holder_extra_info.extra_info()

    holder = {
        "account_address": account_address,
        "personal_information": _personal_info,
        "holder_extra_info": holder_extra_info,
        "balance": balance,
        "exchange_balance": exchange_balance,
        "exchange_commitment": exchange_commitment,
        "pending_transfer": pending_transfer,
        "locked": locked if locked is not None else 0,
        "modified": modified,
    }

    return json_response(holder)


# POST: /bond/tokens/{token_address}/holders/{account_address}/holder_extra_info
@router.post(
    "/tokens/{token_address}/holders/{account_address}/holder_extra_info",
    operation_id="RegisterBondTokenHolderExtraInfo",
    response_model=None,
    responses=get_routers_responses(
        422,
        404,
        AuthorizationError,
        InvalidParameterError,
    ),
)
async def register_bond_token_holder_extra_info(
    db: DBAsyncSession,
    request: Request,
    extra_info: RegisterHolderExtraInfoRequest,
    token_address: Annotated[str, Path()],
    account_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer_address
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Insert/Update token holder's extra information
    # NOTE: Overwrite if a same record already exists.
    _holder_extra_info = TokenHolderExtraInfo()
    _holder_extra_info.token_address = token_address
    _holder_extra_info.account_address = account_address
    _holder_extra_info.external_id_1_type = extra_info.external_id_1_type
    _holder_extra_info.external_id_1 = extra_info.external_id_1
    _holder_extra_info.external_id_2_type = extra_info.external_id_2_type
    _holder_extra_info.external_id_2 = extra_info.external_id_2
    _holder_extra_info.external_id_3_type = extra_info.external_id_3_type
    _holder_extra_info.external_id_3 = extra_info.external_id_3
    await db.merge(_holder_extra_info)
    await db.commit()

    return


# POST: /bond/tokens/{token_address}/personal_info
@router.post(
    "/tokens/{token_address}/personal_info",
    operation_id="RegisterBondTokenHolderPersonalInfo",
    response_model=None,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
        PersonalInfoExceedsSizeLimit,
    ),
)
async def register_bond_token_holder_personal_info(
    db: DBAsyncSession,
    request: Request,
    personal_info: RegisterPersonalInfoRequest,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Register personal information of bond token holders"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    issuer_account, _ = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer_address
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Register Personal Info
    input_personal_info = personal_info.model_dump(
        include={
            "key_manager",
            "name",
            "postal_code",
            "address",
            "email",
            "birth",
            "is_corporate",
            "tax_category",
        }
    )
    if personal_info.data_source == PersonalInfoDataSource.OFF_CHAIN:
        _off_personal_info = IDXPersonalInfo()
        _off_personal_info.issuer_address = issuer_address
        _off_personal_info.account_address = personal_info.account_address
        _off_personal_info.personal_info = input_personal_info
        _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
        await db.merge(_off_personal_info)
        await db.commit()
    else:
        # Check the length of personal info content
        if (
            len(json.dumps(input_personal_info).encode("utf-8"))
            > config.PERSONAL_INFO_MESSAGE_SIZE_LIMIT
        ):
            raise PersonalInfoExceedsSizeLimit

        token_contract = await IbetStraightBondContract(token_address).get()
        try:
            personal_info_contract = PersonalInfoContract(
                logger=LOG,
                issuer=issuer_account,
                contract_address=token_contract.personal_info_contract_address,
            )
            await personal_info_contract.register_info(
                account_address=personal_info.account_address,
                data=input_personal_info,
                default_value=None,
            )
        except SendTransactionError:
            raise SendTransactionError("failed to register personal information")

    return


# GET: /bond/tokens/{token_address}/personal_info/batch
@router.get(
    "/tokens/{token_address}/personal_info/batch",
    operation_id="ListAllBondTokenBatchPersonalInfoRegistration",
    response_model=ListBatchRegisterPersonalInfoUploadResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_all_bond_token_batch_personal_info_registration(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    get_query: Annotated[ListAllPersonalInfoBatchRegistrationUploadQuery, Query()],
):
    """List all personal information batch registration"""
    # Verify that the token is issued by the issuer_address
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get a list of uploads
    stmt = select(BatchRegisterPersonalInfoUpload).where(
        BatchRegisterPersonalInfoUpload.issuer_address == issuer_address
    )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if get_query.status is not None:
        stmt = stmt.where(BatchRegisterPersonalInfoUpload.status == get_query.status)

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(BatchRegisterPersonalInfoUpload.created)
    else:  # DESC
        stmt = stmt.order_by(desc(BatchRegisterPersonalInfoUpload.created))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _upload_list: Sequence[BatchRegisterPersonalInfoUpload] = (
        await db.scalars(stmt)
    ).all()

    uploads = []
    for _upload in _upload_list:
        created_utc = pytz.timezone("UTC").localize(_upload.created)
        uploads.append(
            {
                "batch_id": _upload.upload_id,
                "status": _upload.status,
                "created": created_utc.astimezone(local_tz).isoformat(),
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "uploads": uploads,
        }
    )


# POST: /bond/tokens/{token_address}/personal_info/batch
@router.post(
    "/tokens/{token_address}/personal_info/batch",
    operation_id="InitiateBondTokenBatchPersonalInfoRegistration",
    response_model=BatchRegisterPersonalInfoUploadResponse,
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        BatchPersonalInfoRegistrationValidationError,
    ),
)
async def initiate_bond_token_batch_personal_info_registration(
    db: DBAsyncSession,
    request: Request,
    personal_info_list: List[RegisterPersonalInfoRequest],
    token_address: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Initiate bond token batch personal information registration"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer_address
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")
    if len(personal_info_list) == 0:
        raise InvalidParameterError("personal information list must not be empty")

    batch_id = str(uuid.uuid4())
    batch = BatchRegisterPersonalInfoUpload()
    batch.upload_id = batch_id
    batch.issuer_address = issuer_address
    batch.status = BatchRegisterPersonalInfoUploadStatus.PENDING.value
    db.add(batch)

    errs = []
    bulk_register_record_list = []

    for i, personal_info in enumerate(personal_info_list):
        bulk_register_record = BatchRegisterPersonalInfo()
        bulk_register_record.upload_id = batch_id
        bulk_register_record.token_address = token_address
        bulk_register_record.account_address = personal_info.account_address
        bulk_register_record.status = 0
        bulk_register_record.personal_info = personal_info.model_dump()

        # Check the length of personal info content
        if (
            personal_info.data_source == PersonalInfoDataSource.ON_CHAIN
            and len(json.dumps(bulk_register_record.personal_info).encode("utf-8"))
            > config.PERSONAL_INFO_MESSAGE_SIZE_LIMIT
        ):
            errs.append(
                RecordErrorDetail(
                    row_num=i,
                    error_reason="PersonalInfoExceedsSizeLimit",
                )
            )

        if not errs:
            bulk_register_record_list.append(bulk_register_record)

    if len(errs) > 0:
        raise BatchPersonalInfoRegistrationValidationError(
            detail=InvalidUploadErrorDetail(record_error_details=errs)
        )

    db.add_all(bulk_register_record_list)

    await db.commit()

    return json_response(
        {
            "batch_id": batch_id,
            "status": batch.status,
            "created": pytz.timezone("UTC")
            .localize(batch.created)
            .astimezone(local_tz)
            .isoformat(),
        }
    )


# GET: /bond/tokens/{token_address}/personal_info/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/personal_info/batch/{batch_id}",
    operation_id="RetrieveBondTokenPersonalInfoBatchRegistrationStatus",
    response_model=GetBatchRegisterPersonalInfoResponse,
    responses=get_routers_responses(422, 401, 404),
)
async def retrieve_bond_token_personal_info_batch_registration_status(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    batch_id: Annotated[str, Path()],
    issuer_address: Annotated[str, Header()],
):
    """Retrieve the status of bond token personal information batch registration"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Upload Existence Check
    batch: Optional[BatchRegisterPersonalInfoUpload] = (
        await db.scalars(
            select(BatchRegisterPersonalInfoUpload)
            .where(
                and_(
                    BatchRegisterPersonalInfoUpload.upload_id == batch_id,
                    BatchRegisterPersonalInfoUpload.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: Sequence[BatchRegisterPersonalInfo] = (
        await db.scalars(
            select(BatchRegisterPersonalInfo).where(
                and_(
                    BatchRegisterPersonalInfo.upload_id == batch_id,
                    BatchRegisterPersonalInfo.token_address == token_address,
                )
            )
        )
    ).all()

    return json_response(
        {
            "status": batch.status,
            "results": [
                {
                    "status": record.status,
                    "account_address": record.account_address,
                    "key_manager": record.personal_info.get("key_manager"),
                    "name": record.personal_info.get("name"),
                    "postal_code": record.personal_info.get("postal_code"),
                    "address": record.personal_info.get("address"),
                    "email": record.personal_info.get("email"),
                    "birth": record.personal_info.get("birth"),
                    "is_corporate": record.personal_info.get("is_corporate"),
                    "tax_category": record.personal_info.get("tax_category"),
                }
                for record in record_list
            ],
        }
    )


# GET: /bond/tokens/{token_address}/lock_events
@router.get(
    "/tokens/{token_address}/lock_events",
    operation_id="ListBondTokenLockUnlockEvents",
    response_model=ListAllTokenLockEventsResponse,
    responses=get_routers_responses(422),
)
async def list_bond_token_lock_unlock_events(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    request_query: Annotated[ListAllTokenLockEventsQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all lock/unlock bond token events"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Base query
    stmt_lock = (
        select(
            literal(value=LockEventCategory.Lock.value, type_=String).label("category"),
            IDXLock.transaction_hash.label("transaction_hash"),
            IDXLock.msg_sender.label("msg_sender"),
            IDXLock.token_address.label("token_address"),
            IDXLock.lock_address.label("lock_address"),
            IDXLock.account_address.label("account_address"),
            null().label("recipient_address"),
            IDXLock.value.label("value"),
            IDXLock.data.label("data"),
            IDXLock.block_timestamp.label("block_timestamp"),
            Token,
        )
        .join(Token, IDXLock.token_address == Token.token_address)
        .where(
            and_(
                Token.type == TokenType.IBET_STRAIGHT_BOND,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
    )
    if issuer_address is not None:
        stmt_lock = stmt_lock.where(Token.issuer_address == issuer_address)

    stmt_unlock = (
        select(
            literal(value=LockEventCategory.Unlock.value, type_=String).label(
                "category"
            ),
            IDXUnlock.transaction_hash.label("transaction_hash"),
            IDXUnlock.msg_sender.label("msg_sender"),
            IDXUnlock.token_address.label("token_address"),
            IDXUnlock.lock_address.label("lock_address"),
            IDXUnlock.account_address.label("account_address"),
            IDXUnlock.recipient_address.label("recipient_address"),
            IDXUnlock.value.label("value"),
            IDXUnlock.data.label("data"),
            IDXUnlock.block_timestamp.label("block_timestamp"),
            Token,
        )
        .join(Token, IDXUnlock.token_address == Token.token_address)
        .where(
            and_(
                Token.type == TokenType.IBET_STRAIGHT_BOND,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
    )
    if issuer_address is not None:
        stmt_unlock = stmt_unlock.where(Token.issuer_address == issuer_address)

    total = (
        await db.scalar(select(func.count()).select_from(stmt_lock.subquery()))
    ) + (await db.scalar(select(func.count()).select_from(stmt_unlock.subquery())))

    # Filter
    match request_query.category:
        case LockEventCategory.Lock.value:
            all_lock_event_alias = aliased(stmt_lock.subquery("all_lock_event"))
        case LockEventCategory.Unlock.value:
            all_lock_event_alias = aliased(stmt_unlock.subquery("all_lock_event"))
        case _:
            all_lock_event_alias = aliased(
                stmt_lock.union_all(stmt_unlock).subquery("all_lock_event")
            )
    stmt = select(all_lock_event_alias)

    if request_query.msg_sender is not None:
        stmt = stmt.where(all_lock_event_alias.c.msg_sender == request_query.msg_sender)
    if request_query.account_address is not None:
        stmt = stmt.where(
            all_lock_event_alias.c.account_address == request_query.account_address
        )
    if request_query.lock_address is not None:
        stmt = stmt.where(
            all_lock_event_alias.c.lock_address == request_query.lock_address
        )
    if request_query.recipient_address is not None:
        stmt = stmt.where(
            all_lock_event_alias.c.recipient_address == request_query.recipient_address
        )

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    sort_attr = column(request_query.sort_item)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if request_query.sort_item != ListAllTokenLockEventsSortItem.block_timestamp.value:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(
            desc(column(ListAllTokenLockEventsSortItem.block_timestamp.value))
        )

    # Pagination
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)

    entries = [
        all_lock_event_alias.c.category,
        all_lock_event_alias.c.transaction_hash,
        all_lock_event_alias.c.msg_sender,
        all_lock_event_alias.c.token_address,
        all_lock_event_alias.c.lock_address,
        all_lock_event_alias.c.account_address,
        all_lock_event_alias.c.recipient_address,
        all_lock_event_alias.c.value,
        all_lock_event_alias.c.data,
        all_lock_event_alias.c.block_timestamp,
        Token,
    ]
    lock_events = (
        (await db.execute(select(*entries).from_statement(stmt))).tuples().all()
    )

    resp_data = []
    for lock_event in lock_events:
        token: Token = lock_event.Token
        bond_contract = await IbetStraightBondContract(token.token_address).get()
        block_timestamp_utc = pytz.timezone("UTC").localize(lock_event.block_timestamp)
        resp_data.append(
            {
                "category": lock_event.category,
                "transaction_hash": lock_event.transaction_hash,
                "msg_sender": lock_event.msg_sender,
                "issuer_address": token.issuer_address,
                "token_address": token.token_address,
                "token_type": token.type,
                "token_name": bond_contract.name,
                "lock_address": lock_event.lock_address,
                "account_address": lock_event.account_address,
                "recipient_address": lock_event.recipient_address,
                "value": lock_event.value,
                "data": lock_event.data,
                "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat(),
            }
        )

    data = {
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total,
        },
        "events": resp_data,
    }
    return json_response(data)


# POST: /bond/transfers
@router.post(
    "/transfers",
    operation_id="TransferBondTokenOwnership",
    response_model=None,
    responses=get_routers_responses(
        422,
        401,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
    ),
)
async def transfer_bond_token_ownership(
    db: DBAsyncSession,
    request: Request,
    token: IbetStraightBondTransfer,
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Transfer bond token ownership"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Verify that the token is issued by the issuer_address
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token.token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise InvalidParameterError("token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    try:
        await IbetStraightBondContract(token.token_address).forced_transfer(
            data=ForcedTransferParams(**token.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /bond/transfers/{token_address}
@router.get(
    "/transfers/{token_address}",
    operation_id="ListBondTokenTransferHistory",
    response_model=TransferHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_bond_token_transfer_history(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    query: Annotated[ListTransferHistoryQuery, Query()],
):
    """List bond token transfer history"""
    # Check if the token has been issued
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer history
    from_address_personal_info = aliased(IDXPersonalInfo)
    to_address_personal_info = aliased(IDXPersonalInfo)
    stmt = (
        select(IDXTransfer, from_address_personal_info, to_address_personal_info)
        .join(Token, IDXTransfer.token_address == Token.token_address)
        .outerjoin(
            from_address_personal_info,
            and_(
                Token.issuer_address == from_address_personal_info.issuer_address,
                IDXTransfer.from_address == from_address_personal_info.account_address,
            ),
        )
        .outerjoin(
            to_address_personal_info,
            and_(
                Token.issuer_address == to_address_personal_info.issuer_address,
                IDXTransfer.to_address == to_address_personal_info.account_address,
            ),
        )
        .where(IDXTransfer.token_address == token_address)
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Filter
    if query.block_timestamp_from is not None:
        stmt = stmt.where(
            IDXTransfer.block_timestamp
            >= local_tz.localize(query.block_timestamp_from).astimezone(UTC)
        )
    if query.block_timestamp_to is not None:
        stmt = stmt.where(
            IDXTransfer.block_timestamp
            <= local_tz.localize(query.block_timestamp_to).astimezone(UTC)
        )
    if query.from_address is not None:
        stmt = stmt.where(IDXTransfer.from_address == query.from_address)
    if query.to_address is not None:
        stmt = stmt.where(IDXTransfer.to_address == query.to_address)
    if query.from_address_name:
        stmt = stmt.where(
            from_address_personal_info._personal_info["name"]
            .as_string()
            .like("%" + query.from_address_name + "%")
        )
    if query.to_address_name:
        stmt = stmt.where(
            to_address_personal_info._personal_info["name"]
            .as_string()
            .like("%" + query.to_address_name + "%")
        )
    if query.amount is not None and query.amount_operator is not None:
        match query.amount_operator:
            case ValueOperator.EQUAL:
                stmt = stmt.where(IDXTransfer.amount == query.amount)
            case ValueOperator.GTE:
                stmt = stmt.where(IDXTransfer.amount >= query.amount)
            case ValueOperator.LTE:
                stmt = stmt.where(IDXTransfer.amount <= query.amount)
    if query.source_event is not None:
        stmt = stmt.where(IDXTransfer.source_event == query.source_event)
    if query.data is not None:
        stmt = stmt.where(cast(IDXTransfer.data, String).like("%" + query.data + "%"))
    if query.message is not None:
        stmt = stmt.where(IDXTransfer.message == query.message)
    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    match query.sort_item:
        case ListTransferHistorySortItem.FROM_ADDRESS_NAME:
            sort_attr = from_address_personal_info._personal_info["name"].as_string()
        case ListTransferHistorySortItem.TO_ADDRESS_NAME:
            sort_attr = to_address_personal_info._personal_info["name"].as_string()
        case _:
            sort_attr = getattr(IDXTransfer, query.sort_item.value, None)

    if query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if query.sort_item != ListTransferHistorySortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(IDXTransfer.block_timestamp))

    # Pagination
    if query.limit is not None:
        stmt = stmt.limit(query.limit)
    if query.offset is not None:
        stmt = stmt.offset(query.offset)

    _transfers: Sequence[
        tuple[IDXTransfer, IDXPersonalInfo | None, IDXPersonalInfo | None]
    ] = (await db.execute(stmt)).all()

    transfer_history = []
    for _transfer, _from_address_personal_info, _to_address_personal_info in _transfers:
        block_timestamp_utc = pytz.timezone("UTC").localize(_transfer.block_timestamp)
        transfer_history.append(
            {
                "transaction_hash": _transfer.transaction_hash,
                "token_address": token_address,
                "from_address": _transfer.from_address,
                "from_address_personal_information": (
                    _from_address_personal_info.personal_info
                    if _from_address_personal_info is not None
                    else None
                ),
                "to_address": _transfer.to_address,
                "to_address_personal_information": (
                    _to_address_personal_info.personal_info
                    if _to_address_personal_info is not None
                    else None
                ),
                "amount": _transfer.amount,
                "source_event": _transfer.source_event,
                "data": _transfer.data,
                "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat(),
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": query.offset,
                "limit": query.limit,
                "total": total,
            },
            "transfer_history": transfer_history,
        }
    )


# GET: /bond/transfer_approvals
@router.get(
    "/transfer_approvals",
    operation_id="ListAllBondTokenTransferApprovalHistory",
    response_model=TransferApprovalsResponse,
    responses=get_routers_responses(422),
)
async def list_all_bond_token_transfer_approval_history(
    db: DBAsyncSession,
    get_query: Annotated[ListTransferApprovalHistoryQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List all bond token transfer approval history"""
    # Create a subquery for 'status' added IDXTransferApproval
    subquery = aliased(
        IDXTransferApproval,
        select(
            IDXTransferApproval,
            TransferApprovalHistory,
            case(
                (
                    and_(
                        IDXTransferApproval.escrow_finished == True,
                        IDXTransferApproval.transfer_approved == None,
                        TransferApprovalHistory.operation_type == None,
                    ),
                    1,
                ),  # EscrowFinish(escrow_finished)
                (
                    and_(
                        IDXTransferApproval.transfer_approved == None,
                        TransferApprovalHistory.operation_type
                        == TransferApprovalOperationType.APPROVE.value,
                    ),
                    2,
                ),  # Approve(operation completed, event synchronizing)
                (
                    IDXTransferApproval.transfer_approved == True,
                    2,
                ),  # Approve(transferred)
                (
                    and_(
                        IDXTransferApproval.cancelled == None,
                        TransferApprovalHistory.operation_type
                        == TransferApprovalOperationType.CANCEL.value,
                    ),
                    3,
                ),  # Cancel(operation completed, event synchronizing)
                (IDXTransferApproval.cancelled == True, 3),  # Cancel(canceled)
                else_=0,  # ApplyFor(unapproved)
            ).label("status"),
        )
        .outerjoin(
            TransferApprovalHistory,
            and_(
                IDXTransferApproval.token_address
                == TransferApprovalHistory.token_address,
                IDXTransferApproval.exchange_address
                == TransferApprovalHistory.exchange_address,
                IDXTransferApproval.application_id
                == TransferApprovalHistory.application_id,
            ),
        )
        .subquery(),
    )

    # Get transfer approval history
    stmt = (
        select(
            Token.issuer_address,
            subquery.token_address,
            func.count(subquery.id),
            func.count(or_(literal_column("status") == 0, None)),
            func.count(or_(literal_column("status") == 1, None)),
            func.count(or_(literal_column("status") == 2, None)),
            func.count(or_(literal_column("status") == 3, None)),
        )
        .join(Token, subquery.token_address == Token.token_address)
        .where(
            and_(Token.type == TokenType.IBET_STRAIGHT_BOND, Token.token_status != 2)
        )
    )
    if issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == issuer_address)

    stmt = stmt.group_by(Token.issuer_address, subquery.token_address).order_by(
        Token.issuer_address, subquery.token_address
    )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # NOTE: Because no filtering is performed, `total` and `count` have the same value.
    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _transfer_approvals = (await db.execute(stmt)).tuples().all()

    transfer_approvals = []
    for (
        issuer_address,
        token_address,
        application_count,
        unapproved_count,
        escrow_finished_count,
        transferred_count,
        canceled_count,
    ) in _transfer_approvals:
        transfer_approvals.append(
            {
                "issuer_address": issuer_address,
                "token_address": token_address,
                "application_count": application_count,
                "unapproved_count": unapproved_count,
                "escrow_finished_count": escrow_finished_count,
                "transferred_count": transferred_count,
                "canceled_count": canceled_count,
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "transfer_approvals": transfer_approvals,
        }
    )


# GET: /bond/transfer_approvals/{token_address}
@router.get(
    "/transfer_approvals/{token_address}",
    operation_id="ListSpecificBondTokenTransferApprovalHistory",
    response_model=TransferApprovalHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def list_specific_bond_token_transfer_approval_history(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    get_query: Annotated[ListSpecificTokenTransferApprovalHistoryQuery, Query()],
):
    """List specific bond token transfer approval history"""
    # Get token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Create a subquery for 'status' added IDXTransferApproval
    subquery = aliased(
        IDXTransferApproval,
        select(
            IDXTransferApproval,
            TransferApprovalHistory,
            case(
                (
                    and_(
                        IDXTransferApproval.escrow_finished == True,
                        IDXTransferApproval.transfer_approved == None,
                        TransferApprovalHistory.operation_type == None,
                    ),
                    1,
                ),  # EscrowFinish(escrow_finished)
                (
                    and_(
                        IDXTransferApproval.transfer_approved == None,
                        TransferApprovalHistory.operation_type
                        == TransferApprovalOperationType.APPROVE.value,
                    ),
                    2,
                ),  # Approve(operation completed, event synchronizing)
                (
                    IDXTransferApproval.transfer_approved == True,
                    2,
                ),  # Approve(transferred)
                (
                    and_(
                        IDXTransferApproval.cancelled == None,
                        TransferApprovalHistory.operation_type
                        == TransferApprovalOperationType.CANCEL.value,
                    ),
                    3,
                ),  # Cancel(operation completed, event synchronizing)
                (IDXTransferApproval.cancelled == True, 3),  # Cancel(canceled)
                else_=0,  # ApplyFor(unapproved)
            ).label("status"),
        )
        .outerjoin(
            TransferApprovalHistory,
            and_(
                IDXTransferApproval.token_address
                == TransferApprovalHistory.token_address,
                IDXTransferApproval.exchange_address
                == TransferApprovalHistory.exchange_address,
                IDXTransferApproval.application_id
                == TransferApprovalHistory.application_id,
            ),
        )
        .subquery(),
    )

    # Get transfer approval history
    from_address_personal_info = aliased(IDXPersonalInfo)
    to_address_personal_info = aliased(IDXPersonalInfo)
    stmt = (
        select(
            subquery,
            literal_column("status"),
            # Snapshot Personal Information
            TransferApprovalHistory.from_address_personal_info,
            TransferApprovalHistory.to_address_personal_info,
            # Latest Personal Information
            from_address_personal_info,
            to_address_personal_info,
        )
        .join(Token, subquery.token_address == Token.token_address)
        .outerjoin(
            TransferApprovalHistory,
            and_(
                TransferApprovalHistory.token_address == token_address,
                subquery.token_address == TransferApprovalHistory.token_address,
                subquery.exchange_address == TransferApprovalHistory.exchange_address,
                subquery.application_id == TransferApprovalHistory.application_id,
            ),
        )
        .outerjoin(
            from_address_personal_info,
            and_(
                Token.issuer_address == from_address_personal_info.issuer_address,
                subquery.from_address == from_address_personal_info.account_address,
            ),
        )
        .outerjoin(
            to_address_personal_info,
            and_(
                Token.issuer_address == to_address_personal_info.issuer_address,
                subquery.to_address == to_address_personal_info.account_address,
            ),
        )
        .where(subquery.token_address == token_address)
    )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if get_query.from_address is not None:
        stmt = stmt.where(subquery.from_address == get_query.from_address)
    if get_query.to_address is not None:
        stmt = stmt.where(subquery.to_address == get_query.to_address)
    if get_query.status is not None:
        stmt = stmt.where(literal_column("status").in_(get_query.status))

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if get_query.sort_item != IDXTransferApprovalsSortItem.STATUS:
        sort_attr = getattr(subquery, get_query.sort_item, None)
    else:
        sort_attr = literal_column("status")
    if get_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if get_query.sort_item != IDXTransferApprovalsSortItem.ID:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(subquery.id))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _transfer_approvals: Sequence[
        tuple[
            IDXTransferApproval,
            int,
            dict | None,
            dict | None,
            IDXPersonalInfo | None,
            IDXPersonalInfo | None,
        ]
    ] = (await db.execute(stmt)).all()

    transfer_approval_history = []
    for (
        _transfer_approval,
        status,
        _from_address_snapshot_personal_info,
        _to_address_snapshot_personal_info,
        _from_address_latest_personal_info,
        _to_address_latest_personal_info,
    ) in _transfer_approvals:
        if status == 2:
            transfer_approved = True
            cancelled = False
        elif status == 3:
            transfer_approved = False
            cancelled = True
        else:
            transfer_approved = False
            cancelled = False

        escrow_finished = False
        if _transfer_approval.exchange_address != config.ZERO_ADDRESS:
            if _transfer_approval.escrow_finished is True:
                escrow_finished = True

        if _transfer_approval.exchange_address != config.ZERO_ADDRESS:
            issuer_cancelable = False
        else:
            issuer_cancelable = True

        application_datetime_utc = pytz.timezone("UTC").localize(
            _transfer_approval.application_datetime
        )
        application_datetime = application_datetime_utc.astimezone(local_tz).isoformat()

        application_blocktimestamp_utc = pytz.timezone("UTC").localize(
            _transfer_approval.application_blocktimestamp
        )
        application_blocktimestamp = application_blocktimestamp_utc.astimezone(
            local_tz
        ).isoformat()

        if _transfer_approval.approval_datetime is not None:
            approval_datetime_utc = pytz.timezone("UTC").localize(
                _transfer_approval.approval_datetime
            )
            approval_datetime = approval_datetime_utc.astimezone(local_tz).isoformat()
        else:
            approval_datetime = None

        if _transfer_approval.approval_blocktimestamp is not None:
            approval_blocktimestamp_utc = pytz.timezone("UTC").localize(
                _transfer_approval.approval_blocktimestamp
            )
            approval_blocktimestamp = approval_blocktimestamp_utc.astimezone(
                local_tz
            ).isoformat()
        else:
            approval_blocktimestamp = None

        if _transfer_approval.cancellation_blocktimestamp is not None:
            cancellation_blocktimestamp_utc = pytz.timezone("UTC").localize(
                _transfer_approval.cancellation_blocktimestamp
            )
            cancellation_blocktimestamp = cancellation_blocktimestamp_utc.astimezone(
                local_tz
            ).isoformat()
        else:
            cancellation_blocktimestamp = None

        from_address_personal_info = (
            _from_address_snapshot_personal_info
            if _from_address_snapshot_personal_info is not None
            else (
                _from_address_latest_personal_info.personal_info
                if _from_address_latest_personal_info is not None
                else None
            )
        )
        to_address_personal_info = (
            _to_address_snapshot_personal_info
            if _to_address_snapshot_personal_info is not None
            else (
                _to_address_latest_personal_info.personal_info
                if _to_address_latest_personal_info is not None
                else None
            )
        )
        transfer_approval_history.append(
            {
                "id": _transfer_approval.id,
                "token_address": token_address,
                "exchange_address": _transfer_approval.exchange_address,
                "application_id": _transfer_approval.application_id,
                "from_address": _transfer_approval.from_address,
                "to_address": _transfer_approval.to_address,
                "amount": _transfer_approval.amount,
                "application_datetime": application_datetime,
                "application_blocktimestamp": application_blocktimestamp,
                "approval_datetime": approval_datetime,
                "approval_blocktimestamp": approval_blocktimestamp,
                "cancellation_blocktimestamp": cancellation_blocktimestamp,
                "cancelled": cancelled,
                "escrow_finished": escrow_finished,
                "transfer_approved": transfer_approved,
                "status": status,
                "issuer_cancelable": issuer_cancelable,
                "from_address_personal_information": from_address_personal_info,
                "to_address_personal_information": to_address_personal_info,
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "transfer_approval_history": transfer_approval_history,
        }
    )


# POST: /bond/transfer_approvals/{token_address}/{id}
@router.post(
    "/transfer_approvals/{token_address}/{id}",
    operation_id="UpdateBondTokenTransferApprovalStatus",
    responses=get_routers_responses(
        422,
        401,
        404,
        AuthorizationError,
        InvalidParameterError,
        SendTransactionError,
        ContractRevertError,
        OperationNotAllowedStateError,
    ),
)
async def update_bond_token_transfer_approval_status(
    db: DBAsyncSession,
    request: Request,
    data: UpdateTransferApprovalRequest,
    token_address: Annotated[str, Path()],
    id: Annotated[int, Path()],
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Update bond token transfer approval status"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json, password=decrypt_password.encode("utf-8")
    )

    # Get token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer approval history
    _transfer_approval: IDXTransferApproval | None = (
        await db.scalars(
            select(IDXTransferApproval)
            .where(
                and_(
                    IDXTransferApproval.id == id,
                    IDXTransferApproval.token_address == token_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")

    if _transfer_approval.transfer_approved is True:
        raise InvalidParameterError("already approved")
    if _transfer_approval.cancelled is True:
        raise InvalidParameterError("canceled application")
    if (
        _transfer_approval.exchange_address != config.ZERO_ADDRESS
        and _transfer_approval.escrow_finished is not True
    ):
        raise InvalidParameterError("escrow has not been finished yet")
    if (
        data.operation_type == UpdateTransferApprovalOperationType.CANCEL
        and _transfer_approval.exchange_address != config.ZERO_ADDRESS
    ):
        # Cancellation is possible only against approval of the transfer of a token contract.
        raise InvalidParameterError("application that cannot be canceled")

    transfer_approval_op: TransferApprovalHistory | None = (
        await db.scalars(
            select(TransferApprovalHistory)
            .where(
                and_(
                    TransferApprovalHistory.token_address
                    == _transfer_approval.token_address,
                    TransferApprovalHistory.exchange_address
                    == _transfer_approval.exchange_address,
                    TransferApprovalHistory.application_id
                    == _transfer_approval.application_id,
                    TransferApprovalHistory.operation_type == data.operation_type,
                )
            )
            .limit(1)
        )
    ).first()
    if transfer_approval_op is not None:
        raise InvalidParameterError("duplicate operation")

    # Check the existence of personal information data for from_address and to_address
    _from_address_personal_info: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == _transfer_approval.from_address,
                    IDXPersonalInfo.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _from_address_personal_info is None:
        raise OperationNotAllowedStateError(
            101, "personal information for from_address is not registered"
        )

    _to_address_personal_info: IDXPersonalInfo | None = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == _transfer_approval.to_address,
                    IDXPersonalInfo.issuer_address == issuer_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _to_address_personal_info is None:
        raise OperationNotAllowedStateError(
            101, "personal information for to_address is not registered"
        )

    # Send transaction
    #  - APPROVE -> approveTransfer
    #    In the case of a transfer approval for a token, if the transaction is reverted,
    #    a cancelTransfer is performed immediately.
    #  - CANCEL -> cancelTransfer
    try:
        now = str(datetime.now(UTC).replace(tzinfo=None).timestamp())
        if data.operation_type == UpdateTransferApprovalOperationType.APPROVE:
            if _transfer_approval.exchange_address == config.ZERO_ADDRESS:
                _data = {
                    "application_id": _transfer_approval.application_id,
                    "data": now,
                }
                try:
                    await IbetStraightBondContract(token_address).approve_transfer(
                        data=ApproveTransferParams(**_data),
                        tx_from=issuer_address,
                        private_key=private_key,
                    )
                except ContractRevertError:
                    # If approveTransfer end with revert,
                    # cancelTransfer should be performed immediately.
                    # After cancelTransfer, ContractRevertError is returned.
                    try:
                        await IbetStraightBondContract(token_address).cancel_transfer(
                            data=CancelTransferParams(**_data),
                            tx_from=issuer_address,
                            private_key=private_key,
                        )
                    except ContractRevertError:
                        raise
                    except Exception:
                        raise SendTransactionError
                    # If cancel transfer is successful, approve_transfer error is raised.
                    raise
            else:
                _data = {"escrow_id": _transfer_approval.application_id, "data": now}
                escrow = IbetSecurityTokenEscrow(_transfer_approval.exchange_address)
                try:
                    await escrow.approve_transfer(
                        data=EscrowApproveTransferParams(**_data),
                        tx_from=issuer_address,
                        private_key=private_key,
                    )
                except ContractRevertError:
                    # If approveTransfer end with revert, error should be thrown immediately.
                    raise
                except Exception:
                    raise SendTransactionError
        else:  # CANCEL
            _data = {"application_id": _transfer_approval.application_id, "data": now}
            try:
                await IbetStraightBondContract(token_address).cancel_transfer(
                    data=CancelTransferParams(**_data),
                    tx_from=issuer_address,
                    private_key=private_key,
                )
            except ContractRevertError:
                # If approveTransfer end with revert, error should be thrown immediately.
                raise
            except Exception:
                raise SendTransactionError
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Record operation history
    transfer_approval_op = TransferApprovalHistory()
    transfer_approval_op.token_address = _transfer_approval.token_address
    transfer_approval_op.exchange_address = _transfer_approval.exchange_address
    transfer_approval_op.application_id = _transfer_approval.application_id
    transfer_approval_op.operation_type = data.operation_type
    transfer_approval_op.from_address_personal_info = (
        _from_address_personal_info.personal_info
    )
    transfer_approval_op.to_address_personal_info = (
        _to_address_personal_info.personal_info
    )
    db.add(transfer_approval_op)
    await db.commit()


# GET: /bond/transfer_approvals/{token_address}/{id}
@router.get(
    "/transfer_approvals/{token_address}/{id}",
    operation_id="RetrieveBondTokenTransferApprovalStatus",
    response_model=TransferApprovalTokenDetailResponse,
    responses=get_routers_responses(
        422,
        404,
        InvalidParameterError,
    ),
)
async def retrieve_bond_token_transfer_approval_status(
    db: DBAsyncSession,
    token_address: Annotated[str, Path()],
    id: Annotated[int, Path()],
):
    """Retrieve bond token transfer approval status"""
    # Get token
    _token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer approval history
    _transfer_approval: IDXTransferApproval | None = (
        await db.scalars(
            select(IDXTransferApproval)
            .where(
                and_(
                    IDXTransferApproval.id == id,
                    IDXTransferApproval.token_address == token_address,
                )
            )
            .limit(1)
        )
    ).first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")

    _transfer_approval_op: TransferApprovalHistory | None = (
        await db.scalars(
            select(TransferApprovalHistory)
            .where(
                and_(
                    TransferApprovalHistory.token_address
                    == _transfer_approval.token_address,
                    TransferApprovalHistory.exchange_address
                    == _transfer_approval.exchange_address,
                    TransferApprovalHistory.application_id
                    == _transfer_approval.application_id,
                )
            )
            .limit(1)
        )
    ).first()

    status = 0
    if (
        _transfer_approval.escrow_finished is True
        and _transfer_approval.transfer_approved is not True
        and _transfer_approval_op is None
    ):
        status = 1  # EscrowFinish(escrow_finished)
    elif (
        _transfer_approval.transfer_approved is not True
        and _transfer_approval_op is not None
        and _transfer_approval_op.operation_type
        == TransferApprovalOperationType.APPROVE.value
    ):
        status = 2  # Approve(operation completed, event synchronizing)
    elif _transfer_approval.transfer_approved is True:
        status = 2  # Approve(transferred)
    elif (
        _transfer_approval.cancelled is not True
        and _transfer_approval_op is not None
        and _transfer_approval_op.operation_type
        == TransferApprovalOperationType.CANCEL.value
    ):
        status = 3  # Cancel(operation completed, event synchronizing)
    elif _transfer_approval.cancelled is True:
        status = 3  # Cancel(canceled)

    if status == 2:
        transfer_approved = True
        cancelled = False
    elif status == 3:
        transfer_approved = False
        cancelled = True
    else:
        transfer_approved = False
        cancelled = False

    escrow_finished = False
    if _transfer_approval.exchange_address != config.ZERO_ADDRESS:
        if _transfer_approval.escrow_finished is True:
            escrow_finished = True

    if _transfer_approval.exchange_address != config.ZERO_ADDRESS:
        issuer_cancelable = False
    else:
        issuer_cancelable = True

    application_datetime_utc = pytz.timezone("UTC").localize(
        _transfer_approval.application_datetime
    )
    application_datetime = application_datetime_utc.astimezone(local_tz).isoformat()

    application_blocktimestamp_utc = pytz.timezone("UTC").localize(
        _transfer_approval.application_blocktimestamp
    )
    application_blocktimestamp = application_blocktimestamp_utc.astimezone(
        local_tz
    ).isoformat()

    if _transfer_approval.approval_datetime is not None:
        approval_datetime_utc = pytz.timezone("UTC").localize(
            _transfer_approval.approval_datetime
        )
        approval_datetime = approval_datetime_utc.astimezone(local_tz).isoformat()
    else:
        approval_datetime = None

    if _transfer_approval.approval_blocktimestamp is not None:
        approval_blocktimestamp_utc = pytz.timezone("UTC").localize(
            _transfer_approval.approval_blocktimestamp
        )
        approval_blocktimestamp = approval_blocktimestamp_utc.astimezone(
            local_tz
        ).isoformat()
    else:
        approval_blocktimestamp = None

    if _transfer_approval.cancellation_blocktimestamp is not None:
        cancellation_blocktimestamp_utc = pytz.timezone("UTC").localize(
            _transfer_approval.cancellation_blocktimestamp
        )
        cancellation_blocktimestamp = cancellation_blocktimestamp_utc.astimezone(
            local_tz
        ).isoformat()
    else:
        cancellation_blocktimestamp = None

    # Get personal information of account address
    # NOTE:
    #   If the transfer approval operation has already been performed, get the data at that time.
    #   Otherwise, get the latest data.
    if (
        _transfer_approval_op is not None
        and _transfer_approval_op.from_address_personal_info is not None
        and _transfer_approval_op.to_address_personal_info is not None
    ):
        _from_address_personal_info = _transfer_approval_op.from_address_personal_info
        _to_address_personal_info = _transfer_approval_op.to_address_personal_info
    else:
        _from_account: IDXPersonalInfo | None = (
            await db.scalars(
                select(IDXPersonalInfo)
                .where(
                    and_(
                        IDXPersonalInfo.account_address
                        == _transfer_approval.from_address,
                        IDXPersonalInfo.issuer_address == _token.issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        _from_address_personal_info = (
            _from_account.personal_info if _from_account is not None else None
        )

        _to_account: IDXPersonalInfo | None = (
            await db.scalars(
                select(IDXPersonalInfo)
                .where(
                    and_(
                        IDXPersonalInfo.account_address
                        == _transfer_approval.to_address,
                        IDXPersonalInfo.issuer_address == _token.issuer_address,
                    )
                )
                .limit(1)
            )
        ).first()
        _to_address_personal_info = (
            _to_account.personal_info if _to_account is not None else None
        )

    history = {
        "id": _transfer_approval.id,
        "token_address": token_address,
        "exchange_address": _transfer_approval.exchange_address,
        "application_id": _transfer_approval.application_id,
        "from_address": _transfer_approval.from_address,
        "from_address_personal_information": _from_address_personal_info,
        "to_address": _transfer_approval.to_address,
        "to_address_personal_information": _to_address_personal_info,
        "amount": _transfer_approval.amount,
        "application_datetime": application_datetime,
        "application_blocktimestamp": application_blocktimestamp,
        "approval_datetime": approval_datetime,
        "approval_blocktimestamp": approval_blocktimestamp,
        "cancellation_blocktimestamp": cancellation_blocktimestamp,
        "cancelled": cancelled,
        "escrow_finished": escrow_finished,
        "transfer_approved": transfer_approved,
        "status": status,
        "issuer_cancelable": issuer_cancelable,
    }
    return json_response(history)


# POST: /bond/bulk_transfer
@router.post(
    "/bulk_transfer",
    operation_id="BulkTransferBondTokenOwnership",
    response_model=BulkTransferUploadIdResponse,
    responses=get_routers_responses(
        401,
        422,
        AuthorizationError,
        InvalidParameterError,
        MultipleTokenTransferNotAllowedError,
        TokenNotExistError,
        NonTransferableTokenError,
    ),
)
async def bulk_transfer_bond_token_ownership(
    db: DBAsyncSession,
    request: Request,
    transfer_req: IbetStraightBondBulkTransferRequest,
    issuer_address: Annotated[str, Header()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Bulk transfer bond token ownership

    - All `token_address` must be the same.
    """
    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the same token address is set.
    token_addr_set = set()
    for _transfer in transfer_req.transfer_list:
        token_addr_set.add(_transfer.token_address)

    if len(token_addr_set) > 1:
        raise MultipleTokenTransferNotAllowedError(
            "All token_address must be the same."
        )
    token_address = token_addr_set.pop()

    # Verify that the tokens are issued by the issuer_address
    _issued_token: Token | None = (
        await db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_STRAIGHT_BOND,
                    Token.issuer_address == issuer_address,
                    Token.token_address == token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        )
    ).first()
    if _issued_token is None:
        raise TokenNotExistError(f"token not found: {token_address}")
    if _issued_token.token_status == 0:
        raise NonTransferableTokenError(
            f"this token is temporarily unavailable: {token_address}"
        )

    # Generate upload_id
    upload_id = uuid.uuid4()

    # Add bulk transfer upload record
    _bulk_transfer_upload = BulkTransferUpload()
    _bulk_transfer_upload.upload_id = upload_id
    _bulk_transfer_upload.issuer_address = issuer_address
    _bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
    _bulk_transfer_upload.token_address = token_address
    _bulk_transfer_upload.status = 0
    db.add(_bulk_transfer_upload)

    # add bulk transfer records
    for _transfer in transfer_req.transfer_list:
        _bulk_transfer = BulkTransfer()
        _bulk_transfer.issuer_address = issuer_address
        _bulk_transfer.upload_id = upload_id
        _bulk_transfer.token_address = _transfer.token_address
        _bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _bulk_transfer.from_address = _transfer.from_address
        _bulk_transfer.to_address = _transfer.to_address
        _bulk_transfer.amount = _transfer.amount
        _bulk_transfer.status = 0
        db.add(_bulk_transfer)

    await db.commit()

    return json_response({"upload_id": str(upload_id)})


# GET: /bond/bulk_transfer
@router.get(
    "/bulk_transfer",
    operation_id="ListBondTokenBulkTransfers",
    response_model=BulkTransferUploadResponse,
    responses=get_routers_responses(422),
)
async def list_bond_token_bulk_transfers(
    db: DBAsyncSession,
    get_query: Annotated[ListBulkTransferUploadQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """List bond token bulk transfers"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Select statement
    if issuer_address is None:
        stmt = (
            select(BulkTransferUpload)
            .where(BulkTransferUpload.token_type == TokenType.IBET_STRAIGHT_BOND)
            .order_by(BulkTransferUpload.issuer_address)
        )
    else:
        stmt = select(BulkTransferUpload).where(
            and_(
                BulkTransferUpload.issuer_address == issuer_address,
                BulkTransferUpload.token_type == TokenType.IBET_STRAIGHT_BOND,
            )
        )

    if get_query.token_address is not None:
        upload_id_subquery = (
            select(distinct(BulkTransfer.upload_id).label("upload_id"))
            .where(BulkTransfer.token_address == get_query.token_address)
            .subquery()
        )
        stmt = stmt.join(
            upload_id_subquery,
            upload_id_subquery.c.upload_id == BulkTransferUpload.upload_id,
        )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    # Get bulk transfer upload list
    _uploads: Sequence[BulkTransferUpload] = (await db.scalars(stmt)).all()
    uploads = []
    for _upload in _uploads:
        created_utc = pytz.timezone("UTC").localize(_upload.created)
        uploads.append(
            {
                "issuer_address": _upload.issuer_address,
                "token_type": _upload.token_type,
                "token_address": _upload.token_address,
                "upload_id": _upload.upload_id,
                "status": _upload.status,
                "created": created_utc.astimezone(local_tz).isoformat(),
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "bulk_transfer_uploads": uploads,
        }
    )


# GET: /bond/bulk_transfer/{upload_id}
@router.get(
    "/bulk_transfer/{upload_id}",
    operation_id="RetrieveBondTokenBulkTransfer",
    response_model=BulkTransferUploadRecordResponse,
    responses=get_routers_responses(422, 404),
)
async def retrieve_bond_token_bulk_transfer(
    db: DBAsyncSession,
    upload_id: Annotated[str, Path()],
    get_query: Annotated[ListBulkTransferQuery, Query()],
    issuer_address: Annotated[Optional[str], Header()] = None,
):
    """Retrieve bond token bulk transfer upload records"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Select statement
    from_address_personal_info = aliased(IDXPersonalInfo)
    to_address_personal_info = aliased(IDXPersonalInfo)
    if issuer_address is None:
        stmt = (
            select(BulkTransfer, from_address_personal_info, to_address_personal_info)
            .where(
                and_(
                    BulkTransfer.upload_id == upload_id,
                    BulkTransfer.token_type == TokenType.IBET_STRAIGHT_BOND,
                )
            )
            .outerjoin(
                from_address_personal_info,
                and_(
                    BulkTransfer.issuer_address
                    == from_address_personal_info.issuer_address,
                    BulkTransfer.from_address
                    == from_address_personal_info.account_address,
                ),
            )
            .outerjoin(
                to_address_personal_info,
                and_(
                    BulkTransfer.issuer_address
                    == to_address_personal_info.issuer_address,
                    BulkTransfer.to_address == to_address_personal_info.account_address,
                ),
            )
            .order_by(BulkTransfer.issuer_address)
        )
    else:
        stmt = (
            select(BulkTransfer, from_address_personal_info, to_address_personal_info)
            .where(
                and_(
                    BulkTransfer.issuer_address == issuer_address,
                    BulkTransfer.upload_id == upload_id,
                    BulkTransfer.token_type == TokenType.IBET_STRAIGHT_BOND,
                )
            )
            .outerjoin(
                from_address_personal_info,
                and_(
                    BulkTransfer.issuer_address
                    == from_address_personal_info.issuer_address,
                    BulkTransfer.from_address
                    == from_address_personal_info.account_address,
                ),
            )
            .outerjoin(
                to_address_personal_info,
                and_(
                    BulkTransfer.issuer_address
                    == to_address_personal_info.issuer_address,
                    BulkTransfer.to_address == to_address_personal_info.account_address,
                ),
            )
        )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    # Get bulk transfer upload list
    _bulk_transfers: Sequence[
        tuple[BulkTransfer, IDXPersonalInfo | None, IDXPersonalInfo | None]
    ] = (await db.execute(stmt)).all()
    bulk_transfers = []
    for (
        _bulk_transfer,
        _from_address_personal_info,
        _to_address_personal_info,
    ) in _bulk_transfers:
        bulk_transfers.append(
            {
                "issuer_address": _bulk_transfer.issuer_address,
                "token_type": _bulk_transfer.token_type,
                "upload_id": _bulk_transfer.upload_id,
                "token_address": _bulk_transfer.token_address,
                "from_address": _bulk_transfer.from_address,
                "from_address_personal_information": (
                    _from_address_personal_info.personal_info
                    if _from_address_personal_info is not None
                    else None
                ),
                "to_address": _bulk_transfer.to_address,
                "to_address_personal_information": (
                    _to_address_personal_info.personal_info
                    if _to_address_personal_info is not None
                    else None
                ),
                "amount": _bulk_transfer.amount,
                "status": _bulk_transfer.status,
                "transaction_error_code": _bulk_transfer.transaction_error_code,
                "transaction_error_message": _bulk_transfer.transaction_error_message,
            }
        )

    if len(bulk_transfers) < 1:
        raise HTTPException(status_code=404, detail="bulk transfer not found")

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": get_query.offset,
                "limit": get_query.limit,
                "total": total,
            },
            "bulk_transfer_upload_records": bulk_transfers,
        }
    )
