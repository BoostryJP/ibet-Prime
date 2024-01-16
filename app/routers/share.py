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
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Sequence

from eth_keyfile import decode_keyfile_json
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.exceptions import HTTPException
from pytz import timezone
from sqlalchemy import (
    String,
    and_,
    case,
    cast,
    column,
    desc,
    func,
    literal,
    literal_column,
    null,
    or_,
    select,
)
from sqlalchemy.orm import aliased

import config
from app import log
from app.database import DBSession
from app.exceptions import (
    AuthorizationError,
    ContractRevertError,
    InvalidParameterError,
    OperationNotAllowedStateError,
    SendTransactionError,
)
from app.model.blockchain import (
    IbetSecurityTokenEscrow,
    IbetShareContract,
    PersonalInfoContract,
    TokenListContract,
)
from app.model.blockchain.tx_params.ibet_security_token_escrow import (
    ApproveTransferParams as EscrowApproveTransferParams,
)
from app.model.blockchain.tx_params.ibet_share import (
    AdditionalIssueParams,
    ApproveTransferParams,
    CancelTransferParams,
    RedeemParams,
    TransferParams,
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
    BulkTransferResponse,
    BulkTransferUploadIdResponse,
    BulkTransferUploadResponse,
    GetBatchIssueRedeemResponse,
    GetBatchRegisterPersonalInfoResponse,
    HolderCountResponse,
    HolderResponse,
    HoldersResponse,
    IbetShareAdditionalIssue,
    IbetShareBulkTransferRequest,
    IbetShareCreate,
    IbetShareRedeem,
    IbetShareResponse,
    IbetShareScheduledUpdate,
    IbetShareTransfer,
    IbetShareUpdate,
    IssueRedeemHistoryResponse,
    ListAdditionalIssuanceHistoryQuery,
    ListAllAdditionalIssueUploadQuery,
    ListAllHoldersQuery,
    ListAllPersonalInfoBatchRegistrationUploadQuery,
    ListAllRedeemUploadQuery,
    ListAllTokenLockEventsQuery,
    ListAllTokenLockEventsResponse,
    ListAllTokenLockEventsSortItem,
    ListBatchIssueRedeemUploadResponse,
    ListBatchRegisterPersonalInfoUploadResponse,
    ListRedeemHistoryQuery,
    ListTokenOperationLogHistoryQuery,
    ListTokenOperationLogHistoryResponse,
    ListTransferApprovalHistoryQuery,
    ListTransferHistoryQuery,
    ListTransferHistorySortItem,
    LockEventCategory,
    RegisterPersonalInfoRequest,
    ScheduledEventIdResponse,
    ScheduledEventResponse,
    TokenAddressResponse,
    TokenUpdateOperationCategory,
    TransferApprovalHistoryResponse,
    TransferApprovalsResponse,
    TransferApprovalTokenDetailResponse,
    TransferHistoryResponse,
    UpdateTransferApprovalOperationType,
    UpdateTransferApprovalRequest,
)
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    validate_headers,
)
from app.utils.contract_utils import ContractUtils
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

router = APIRouter(
    prefix="/share",
    tags=["share"],
)

LOG = log.get_logger()
local_tz = timezone(config.TZ)
utc_tz = timezone("UTC")


# POST: /share/tokens
@router.post(
    "/tokens",
    response_model=TokenAddressResponse,
    responses=get_routers_responses(
        422, 401, AuthorizationError, SendTransactionError, ContractRevertError
    ),
)
def issue_token(
    db: DBSession,
    request: Request,
    token: IbetShareCreate,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Issue ibetShare token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
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
    _dividends = token.dividends if token.dividends is not None else 0
    _dividend_record_date = (
        token.dividend_record_date if token.dividend_record_date is not None else ""
    )
    _dividend_payment_date = (
        token.dividend_payment_date if token.dividend_payment_date is not None else ""
    )
    _cancellation_date = (
        token.cancellation_date if token.cancellation_date is not None else ""
    )
    arguments = [
        token.name,
        _symbol,
        token.issue_price,
        token.total_supply,
        int(Decimal(str(_dividends)) * Decimal("10000000000000")),
        _dividend_record_date,
        _dividend_payment_date,
        _cancellation_date,
        token.principal_value,
    ]
    try:
        contract_address, abi, tx_hash = IbetShareContract().create(
            args=arguments, tx_from=issuer_address, private_key=private_key
        )
    except SendTransactionError as e:
        raise SendTransactionError("failed to send transaction")

    # Check need update
    update_items = [
        "tradable_exchange_contract_address",
        "personal_info_contract_address",
        "transferable",
        "status",
        "is_offering",
        "contact_information",
        "privacy_policy",
        "transfer_approval_required",
        "is_canceled",
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
        _update_token.type = TokenType.IBET_SHARE.value
        _update_token.arguments = token_dict
        _update_token.status = 0  # pending
        _update_token.trigger = "Issue"
        db.add(_update_token)

        token_status = 0  # processing
    else:
        # Register token_address token list
        try:
            TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address=contract_address,
                token_template=TokenType.IBET_SHARE.value,
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
        block = ContractUtils.get_block_by_transaction_hash(tx_hash)
        _utxo = UTXO()
        _utxo.transaction_hash = tx_hash
        _utxo.account_address = issuer_address
        _utxo.token_address = contract_address
        _utxo.amount = token.total_supply
        _utxo.block_number = block["number"]
        _utxo.block_timestamp = datetime.utcfromtimestamp(block["timestamp"])
        db.add(_utxo)

        token_status = 1  # succeeded

    # Register token data
    _token = Token()
    _token.type = TokenType.IBET_SHARE.value
    _token.tx_hash = tx_hash
    _token.issuer_address = issuer_address
    _token.token_address = contract_address
    _token.abi = abi
    _token.token_status = token_status
    _token.version = TokenVersion.V_22_12
    db.add(_token)

    # Register operation log
    operation_log = TokenUpdateOperationLog()
    operation_log.token_address = contract_address
    operation_log.issuer_address = issuer_address
    operation_log.type = TokenType.IBET_SHARE.value
    operation_log.arguments = token.model_dump()
    operation_log.original_contents = None
    operation_log.operation_category = TokenUpdateOperationCategory.ISSUE.value
    db.add(operation_log)

    db.commit()

    return json_response(
        {"token_address": _token.token_address, "token_status": token_status}
    )


# GET: /share/tokens
@router.get(
    "/tokens",
    response_model=List[IbetShareResponse],
    responses=get_routers_responses(422),
)
def list_all_tokens(
    db: DBSession,
    issuer_address: Optional[str] = Header(None),
):
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    """List all issued tokens"""
    # Get issued token list
    if issuer_address is None:
        tokens: Sequence[Token] = db.scalars(
            select(Token).where(Token.type == TokenType.IBET_SHARE)
        ).all()
    else:
        tokens: Sequence[Token] = db.scalars(
            select(Token).where(
                and_(
                    Token.type == TokenType.IBET_SHARE,
                    Token.issuer_address == issuer_address,
                )
            )
        ).all()

    share_tokens = []
    for token in tokens:
        # Get contract data
        share_token = IbetShareContract(token.token_address).get().__dict__
        issue_datetime_utc = timezone("UTC").localize(token.created)
        share_token["issue_datetime"] = issue_datetime_utc.astimezone(
            local_tz
        ).isoformat()
        share_token["token_status"] = token.token_status
        share_token["contract_version"] = token.version
        share_token.pop("contract_name")
        share_tokens.append(share_token)

    return json_response(share_tokens)


# GET: /share/tokens/{token_address}
@router.get(
    "/tokens/{token_address}",
    response_model=IbetShareResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
def retrieve_token(db: DBSession, token_address: str):
    """Retrieve token"""
    # Get Token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get contract data
    share_token = IbetShareContract(token_address).get().__dict__
    issue_datetime_utc = timezone("UTC").localize(_token.created)
    share_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
    share_token["token_status"] = _token.token_status
    share_token["contract_version"] = _token.version
    share_token.pop("contract_name")

    return json_response(share_token)


# POST: /share/tokens/{token_address}
@router.post(
    "/tokens/{token_address}",
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
def update_token(
    db: DBSession,
    request: Request,
    token_address: str,
    token: IbetShareUpdate,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Update a token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
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
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        token_contract = IbetShareContract(token_address)
        original_contents = token_contract.get().__dict__
        token_contract.update(
            data=UpdateParams(**token.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Register operation log
    operation_log = TokenUpdateOperationLog()
    operation_log.token_address = token_address
    operation_log.issuer_address = issuer_address
    operation_log.type = TokenType.IBET_SHARE.value
    operation_log.arguments = token.model_dump(exclude_none=True)
    operation_log.original_contents = original_contents
    operation_log.operation_category = TokenUpdateOperationCategory.UPDATE.value
    db.add(operation_log)

    db.commit()
    return


# GET: /share/tokens/{token_address}/history
@router.get(
    "/tokens/{token_address}/history",
    response_model=ListTokenOperationLogHistoryResponse,
    responses=get_routers_responses(404, InvalidParameterError),
)
def list_share_operation_log_history(
    db: DBSession,
    token_address: str,
    request_query: ListTokenOperationLogHistoryQuery = Depends(),
):
    """List of token operation log history"""
    stmt = select(TokenUpdateOperationLog).where(
        and_(
            TokenUpdateOperationLog.type == TokenType.IBET_SHARE,
            TokenUpdateOperationLog.token_address == token_address,
        )
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

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
        stmt = stmt.where(
            TokenUpdateOperationLog.created
            >= local_tz.localize(request_query.created_from).astimezone(utc_tz)
        )
    if request_query.created_to:
        stmt = stmt.where(
            TokenUpdateOperationLog.created
            <= local_tz.localize(request_query.created_to).astimezone(utc_tz)
        )

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

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

    history: Sequence[TokenUpdateOperationLog] = db.scalars(stmt).all()

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


# GET: /share/tokens/{token_address}/additional_issue
@router.get(
    "/tokens/{token_address}/additional_issue",
    response_model=IssueRedeemHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def list_additional_issuance_history(
    db: DBSession,
    token_address: str,
    request_query: ListAdditionalIssuanceHistoryQuery = Depends(),
):
    """List additional issuance history"""
    sort_item = request_query.sort_item
    sort_order = request_query.sort_order
    offset = request_query.offset
    limit = request_query.limit

    # Get token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    # Sort
    sort_attr = getattr(IDXIssueRedeem, sort_item.value, None)
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != IDXIssueRedeemSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(IDXIssueRedeem.block_timestamp))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _events: Sequence[IDXIssueRedeem] = db.scalars(stmt).all()

    history = []
    for _event in _events:
        block_timestamp_utc = timezone("UTC").localize(_event.block_timestamp)
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
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "history": history,
        }
    )


# POST: /share/tokens/{token_address}/additional_issue
@router.post(
    "/tokens/{token_address}/additional_issue",
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
def additional_issue(
    db: DBSession,
    request: Request,
    token_address: str,
    data: IbetShareAdditionalIssue,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Additional issue"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
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
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        IbetShareContract(token_address).additional_issue(
            data=AdditionalIssueParams(**data.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/tokens/{token_address}/additional_issue/batch
@router.get(
    "/tokens/{token_address}/additional_issue/batch",
    response_model=ListBatchIssueRedeemUploadResponse,
    responses=get_routers_responses(422),
)
def list_all_additional_issue_upload(
    db: DBSession,
    token_address: str,
    get_query: ListAllAdditionalIssueUploadQuery = Depends(),
    issuer_address: Optional[str] = Header(None),
):
    processed = get_query.processed
    sort_order = get_query.sort_order
    offset = get_query.offset
    limit = get_query.limit

    # Get a list of uploads
    stmt = select(BatchIssueRedeemUpload).where(
        and_(
            BatchIssueRedeemUpload.token_address == token_address,
            BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE,
            BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.ISSUE,
        )
    )

    if issuer_address is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.issuer_address == issuer_address)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    if processed is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.processed == processed)

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(BatchIssueRedeemUpload.created)
    else:  # DESC
        stmt = stmt.order_by(desc(BatchIssueRedeemUpload.created))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _upload_list: Sequence[BatchIssueRedeemUpload] = db.scalars(stmt).all()

    uploads = []
    for _upload in _upload_list:
        created_utc = timezone("UTC").localize(_upload.created)
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
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "uploads": uploads,
    }
    return json_response(resp)


# POST: /share/tokens/{token_address}/additional_issue/batch
@router.post(
    "/tokens/{token_address}/additional_issue/batch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(
        422, 401, 404, AuthorizationError, InvalidParameterError
    ),
)
def additional_issue_in_batch(
    db: DBSession,
    request: Request,
    token_address: str,
    data: List[IbetShareAdditionalIssue],
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Additional issue (Batch)"""

    # Validate headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Validate params
    if len(data) < 1:
        raise InvalidParameterError("list length must be at least one")

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Check token status
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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
    _batch_upload.token_type = TokenType.IBET_SHARE.value
    _batch_upload.token_address = token_address
    _batch_upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
    _batch_upload.status = 0
    db.add(_batch_upload)

    for _item in data:
        _batch_issue = BatchIssueRedeem()
        _batch_issue.upload_id = upload_id
        _batch_issue.account_address = _item.account_address
        _batch_issue.amount = _item.amount
        _batch_issue.status = 0
        db.add(_batch_issue)

    db.commit()

    return json_response({"batch_id": str(upload_id)})


# GET: /share/tokens/{token_address}/additional_issue/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/additional_issue/batch/{batch_id}",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404),
)
def retrieve_batch_additional_issue(
    db: DBSession,
    token_address: str,
    batch_id: str,
    issuer_address: str = Header(...),
):
    """Get Batch status for additional issue"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Upload Existence Check
    batch: Optional[BatchIssueRedeemUpload] = db.scalars(
        select(BatchIssueRedeemUpload)
        .where(
            and_(
                BatchIssueRedeemUpload.upload_id == batch_id,
                BatchIssueRedeemUpload.issuer_address == issuer_address,
                BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE,
                BatchIssueRedeemUpload.token_address == token_address,
                BatchIssueRedeemUpload.category
                == BatchIssueRedeemProcessingCategory.ISSUE,
            )
        )
        .limit(1)
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: Sequence[tuple[BatchIssueRedeem, IDXPersonalInfo | None]] = (
        db.execute(
            select(BatchIssueRedeem, IDXPersonalInfo)
            .outerjoin(
                IDXPersonalInfo,
                and_(
                    BatchIssueRedeem.account_address == IDXPersonalInfo.account_address,
                    IDXPersonalInfo.issuer_address == issuer_address,
                ),
            )
            .where(BatchIssueRedeem.upload_id == batch_id)
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
                    "personal_information": record[1].personal_info
                    if record[1]
                    else personal_info_default,
                }
                for record in record_list
            ],
        }
    )


# GET: /share/tokens/{token_address}/redeem
@router.get(
    "/tokens/{token_address}/redeem",
    response_model=IssueRedeemHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def list_redeem_history(
    db: DBSession,
    token_address: str,
    get_query: ListRedeemHistoryQuery = Depends(),
):
    """List redemption history"""
    sort_item = get_query.sort_item
    sort_order = get_query.sort_order
    offset = get_query.offset
    limit = get_query.limit

    # Get token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    # Sort
    sort_attr = getattr(IDXIssueRedeem, sort_item.value, None)
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != IDXIssueRedeemSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(IDXIssueRedeem.block_timestamp))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _events: Sequence[IDXIssueRedeem] = db.scalars(stmt).all()

    history = []
    for _event in _events:
        block_timestamp_utc = timezone("UTC").localize(_event.block_timestamp)
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
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "history": history,
        }
    )


# POST: /share/tokens/{token_address}/redeem
@router.post(
    "/tokens/{token_address}/redeem",
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
def redeem_token(
    db: DBSession,
    request: Request,
    token_address: str,
    data: IbetShareRedeem,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Redeem a token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
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
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        IbetShareContract(token_address).redeem(
            data=RedeemParams(**data.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/tokens/{token_address}/redeem/batch
@router.get(
    "/tokens/{token_address}/redeem/batch",
    response_model=ListBatchIssueRedeemUploadResponse,
    responses=get_routers_responses(422),
)
def list_all_redeem_upload(
    db: DBSession,
    token_address: str,
    get_query: ListAllRedeemUploadQuery = Depends(),
    issuer_address: Optional[str] = Header(None),
):
    processed = get_query.processed
    sort_order = get_query.sort_order
    offset = get_query.offset
    limit = get_query.limit

    # Get a list of uploads
    stmt = select(BatchIssueRedeemUpload).where(
        and_(
            BatchIssueRedeemUpload.token_address == token_address,
            BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE,
            BatchIssueRedeemUpload.category
            == BatchIssueRedeemProcessingCategory.REDEEM,
        )
    )

    if issuer_address is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.issuer_address == issuer_address)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    if processed is not None:
        stmt = stmt.where(BatchIssueRedeemUpload.processed == processed)

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(BatchIssueRedeemUpload.created)
    else:  # DESC
        stmt = stmt.order_by(desc(BatchIssueRedeemUpload.created))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _upload_list: Sequence[BatchIssueRedeemUpload] = db.scalars(stmt).all()

    uploads = []
    for _upload in _upload_list:
        created_utc = timezone("UTC").localize(_upload.created)
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
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "uploads": uploads,
    }
    return json_response(resp)


# POST: /share/tokens/{token_address}/redeem/batch
@router.post(
    "/tokens/{token_address}/redeem/batch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(
        422, 401, 404, AuthorizationError, InvalidParameterError
    ),
)
def redeem_token_in_batch(
    db: DBSession,
    request: Request,
    token_address: str,
    data: List[IbetShareRedeem],
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Redeem a token (Batch)"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Validate params
    if len(data) < 1:
        raise InvalidParameterError("list length must be at least one")

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Check token status
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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
    _batch_upload.token_type = TokenType.IBET_SHARE.value
    _batch_upload.token_address = token_address
    _batch_upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
    _batch_upload.status = 0
    db.add(_batch_upload)

    for _item in data:
        _batch_issue = BatchIssueRedeem()
        _batch_issue.upload_id = upload_id
        _batch_issue.account_address = _item.account_address
        _batch_issue.amount = _item.amount
        _batch_issue.status = 0
        db.add(_batch_issue)

    db.commit()

    return json_response({"batch_id": str(upload_id)})


# GET: /share/tokens/{token_address}/redeem/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/redeem/batch/{batch_id}",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404),
)
def retrieve_batch_redeem(
    db: DBSession,
    token_address: str,
    batch_id: str,
    issuer_address: str = Header(...),
):
    """Get Batch status for additional issue"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Upload Existence Check
    batch: Optional[BatchIssueRedeemUpload] = db.scalars(
        select(BatchIssueRedeemUpload)
        .where(
            and_(
                BatchIssueRedeemUpload.upload_id == batch_id,
                BatchIssueRedeemUpload.issuer_address == issuer_address,
                BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE,
                BatchIssueRedeemUpload.token_address == token_address,
                BatchIssueRedeemUpload.category
                == BatchIssueRedeemProcessingCategory.REDEEM,
            )
        )
        .limit(1)
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: Sequence[tuple[BatchIssueRedeem, IDXPersonalInfo | None]] = (
        db.execute(
            select(BatchIssueRedeem, IDXPersonalInfo)
            .outerjoin(
                IDXPersonalInfo,
                and_(
                    BatchIssueRedeem.account_address == IDXPersonalInfo.account_address,
                    IDXPersonalInfo.issuer_address == issuer_address,
                ),
            )
            .where(BatchIssueRedeem.upload_id == batch_id)
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
                    "personal_information": record[1].personal_info
                    if record[1]
                    else personal_info_default,
                }
                for record in record_list
            ],
        }
    )


# GET: /share/tokens/{token_address}/scheduled_events
@router.get(
    "/tokens/{token_address}/scheduled_events",
    response_model=List[ScheduledEventResponse],
)
def list_all_scheduled_events(
    db: DBSession,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
):
    """List all scheduled update events"""

    if issuer_address is None:
        _token_events: Sequence[ScheduledEvents] = db.scalars(
            select(ScheduledEvents)
            .where(
                and_(
                    ScheduledEvents.token_type == TokenType.IBET_SHARE,
                    ScheduledEvents.token_address == token_address,
                )
            )
            .order_by(ScheduledEvents.id)
        ).all()
    else:
        _token_events: Sequence[ScheduledEvents] = db.scalars(
            select(ScheduledEvents)
            .where(
                and_(
                    ScheduledEvents.token_type == TokenType.IBET_SHARE,
                    ScheduledEvents.issuer_address == issuer_address,
                    ScheduledEvents.token_address == token_address,
                )
            )
            .order_by(ScheduledEvents.id)
        ).all()

    token_events = []
    for _token_event in _token_events:
        scheduled_datetime_utc = timezone("UTC").localize(
            _token_event.scheduled_datetime
        )
        created_utc = timezone("UTC").localize(_token_event.created)
        token_events.append(
            {
                "scheduled_event_id": _token_event.event_id,
                "token_address": token_address,
                "token_type": TokenType.IBET_SHARE.value,
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


# POST: /share/tokens/{token_address}/scheduled_events
@router.post(
    "/tokens/{token_address}/scheduled_events",
    response_model=ScheduledEventIdResponse,
    responses=get_routers_responses(
        422, 401, 404, AuthorizationError, InvalidParameterError
    ),
)
def schedule_new_update_event(
    db: DBSession,
    request: Request,
    token_address: str,
    event_data: IbetShareScheduledUpdate,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Register a new update event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Register an event
    _scheduled_event = ScheduledEvents()
    _scheduled_event.event_id = str(uuid.uuid4())
    _scheduled_event.issuer_address = issuer_address
    _scheduled_event.token_address = token_address
    _scheduled_event.token_type = TokenType.IBET_SHARE.value
    _scheduled_event.scheduled_datetime = event_data.scheduled_datetime
    _scheduled_event.event_type = event_data.event_type
    _scheduled_event.data = event_data.data.model_dump()
    _scheduled_event.status = 0
    db.add(_scheduled_event)
    db.commit()

    return json_response({"scheduled_event_id": _scheduled_event.event_id})


# GET: /share/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.get(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(404),
)
def retrieve_token_event(
    db: DBSession,
    token_address: str,
    scheduled_event_id: str,
    issuer_address: Optional[str] = Header(None),
):
    """Retrieve a scheduled token event"""

    if issuer_address is None:
        _token_event: ScheduledEvents | None = db.scalars(
            select(ScheduledEvents)
            .where(
                and_(
                    ScheduledEvents.token_type == TokenType.IBET_SHARE,
                    ScheduledEvents.event_id == scheduled_event_id,
                    ScheduledEvents.token_address == token_address,
                )
            )
            .limit(1)
        ).first()
    else:
        _token_event: ScheduledEvents | None = db.scalars(
            select(ScheduledEvents)
            .where(
                and_(
                    ScheduledEvents.token_type == TokenType.IBET_SHARE,
                    ScheduledEvents.event_id == scheduled_event_id,
                    ScheduledEvents.issuer_address == issuer_address,
                    ScheduledEvents.token_address == token_address,
                )
            )
            .limit(1)
        ).first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="event not found")

    scheduled_datetime_utc = timezone("UTC").localize(_token_event.scheduled_datetime)
    created_utc = timezone("UTC").localize(_token_event.created)
    return json_response(
        {
            "scheduled_event_id": _token_event.event_id,
            "token_address": token_address,
            "token_type": TokenType.IBET_SHARE.value,
            "scheduled_datetime": scheduled_datetime_utc.astimezone(
                local_tz
            ).isoformat(),
            "event_type": _token_event.event_type,
            "status": _token_event.status,
            "data": _token_event.data,
            "created": created_utc.astimezone(local_tz).isoformat(),
        }
    )


# DELETE: /share/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.delete(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError),
)
def delete_scheduled_event(
    db: DBSession,
    request: Request,
    token_address: str,
    scheduled_event_id: str,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Delete a scheduled event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Delete an event
    _token_event: ScheduledEvents | None = db.scalars(
        select(ScheduledEvents)
        .where(
            and_(
                ScheduledEvents.token_type == TokenType.IBET_SHARE,
                ScheduledEvents.event_id == scheduled_event_id,
                ScheduledEvents.issuer_address == issuer_address,
                ScheduledEvents.token_address == token_address,
            )
        )
        .limit(1)
    ).first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="event not found")

    scheduled_datetime_utc = timezone("UTC").localize(_token_event.scheduled_datetime)
    created_utc = timezone("UTC").localize(_token_event.created)
    rtn = {
        "scheduled_event_id": _token_event.event_id,
        "token_address": token_address,
        "token_type": TokenType.IBET_SHARE.value,
        "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data,
        "created": created_utc.astimezone(local_tz).isoformat(),
    }

    db.delete(_token_event)
    db.commit()

    return json_response(rtn)


# GET: /share/tokens/{token_address}/holders
@router.get(
    "/tokens/{token_address}/holders",
    response_model=HoldersResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
def list_all_holders(
    db: DBSession,
    token_address: str,
    get_query: ListAllHoldersQuery = Depends(),
    issuer_address: str = Header(...),
):
    """List all share token holders"""
    include_former_holder = get_query.include_former_holder
    sort_order = get_query.sort_order
    offset = get_query.offset
    limit = get_query.limit

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Account
    _account = db.scalars(
        select(Account).where(Account.issuer_address == issuer_address).limit(1)
    ).first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    stmt = (
        select(
            IDXPosition,
            func.sum(IDXLockedPosition.value),
            func.max(IDXLockedPosition.modified),
        )
        .outerjoin(
            IDXLockedPosition,
            and_(
                IDXLockedPosition.token_address == IDXPosition.token_address,
                IDXLockedPosition.account_address == IDXPosition.account_address,
            ),
        )
        .where(IDXPosition.token_address == token_address)
        .group_by(
            IDXPosition.id,
            IDXLockedPosition.token_address,
            IDXLockedPosition.account_address,
        )
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    if not include_former_holder:
        stmt = stmt.where(
            or_(
                IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0,
            )
        )

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(IDXPosition.id)
    else:  # DESC
        stmt = stmt.order_by(desc(IDXPosition.id))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _holders: Sequence[tuple[IDXPosition, int, datetime | None]] = (
        db.execute(stmt).tuples().all()
    )

    # Get personal information
    _personal_info_list: Sequence[IDXPersonalInfo] = db.scalars(
        select(IDXPersonalInfo)
        .where(IDXPersonalInfo.issuer_address == issuer_address)
        .order_by(IDXPersonalInfo.id)
    ).all()
    _personal_info_dict = {}
    for item in _personal_info_list:
        _personal_info_dict[item.account_address] = item.personal_info

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
    for _position, _locked, _lock_event_latest_created in _holders:
        _personal_info = _personal_info_dict.get(
            _position.account_address, personal_info_default
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
                "personal_information": _personal_info,
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
                "limit": limit,
                "offset": offset,
            },
            "holders": holders,
        }
    )


# GET: /share/tokens/{token_address}/holders/count
@router.get(
    "/tokens/{token_address}/holders/count",
    response_model=HolderCountResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
def count_number_of_holders(
    db: DBSession,
    token_address: str,
    issuer_address: str = Header(...),
):
    """Count the number of holders"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Account
    _account = db.scalars(
        select(Account).where(Account.issuer_address == issuer_address).limit(1)
    ).first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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
    _count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    return json_response({"count": _count})


# GET: /share/tokens/{token_address}/holders/{account_address}
@router.get(
    "/tokens/{token_address}/holders/{account_address}",
    response_model=HolderResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404),
)
def retrieve_holder(
    db: DBSession,
    token_address: str,
    account_address: str,
    issuer_address: str = Header(...),
):
    """Retrieve share token holder"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Issuer
    _account = db.scalars(
        select(Account).where(Account.issuer_address == issuer_address).limit(1)
    ).first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    _holder: tuple[IDXPosition, int, datetime | None] = (
        db.execute(
            select(
                IDXPosition,
                func.sum(IDXLockedPosition.value),
                func.max(IDXLockedPosition.modified),
            )
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
    _personal_info_record: IDXPersonalInfo | None = db.scalars(
        select(IDXPersonalInfo)
        .where(
            and_(
                IDXPersonalInfo.account_address == account_address,
                IDXPersonalInfo.issuer_address == issuer_address,
            )
        )
        .limit(1)
    ).first()
    if _personal_info_record is None:
        _personal_info = personal_info_default
    else:
        _personal_info = _personal_info_record.personal_info

    holder = {
        "account_address": account_address,
        "personal_information": _personal_info,
        "balance": balance,
        "exchange_balance": exchange_balance,
        "exchange_commitment": exchange_commitment,
        "pending_transfer": pending_transfer,
        "locked": locked if locked is not None else 0,
        "modified": modified,
    }

    return json_response(holder)


# POST: /share/tokens/{token_address}/personal_info
@router.post(
    "/tokens/{token_address}/personal_info",
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
def register_holder_personal_info(
    db: DBSession,
    request: Request,
    token_address: str,
    personal_info: RegisterPersonalInfoRequest,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Register the holder's personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer_address
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Register Personal Info
    token_contract = IbetShareContract(token_address).get()
    try:
        personal_info_contract = PersonalInfoContract(
            db=db,
            issuer_address=issuer_address,
            contract_address=token_contract.personal_info_contract_address,
        )
        personal_info_contract.register_info(
            account_address=personal_info.account_address,
            data=personal_info.model_dump(),
            default_value=None,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to register personal information")

    return


# GET: /share/tokens/{token_address}/personal_info/batch
@router.get(
    "/tokens/{token_address}/personal_info/batch",
    response_model=ListBatchRegisterPersonalInfoUploadResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def list_all_personal_info_batch_registration_uploads(
    db: DBSession,
    token_address: str,
    issuer_address: str = Header(...),
    get_query: ListAllPersonalInfoBatchRegistrationUploadQuery = Depends(),
):
    """List all personal information batch registration uploads"""
    status = get_query.status
    sort_order = get_query.sort_order
    offset = get_query.offset
    limit = get_query.limit

    # Verify that the token is issued by the issuer_address
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get a list of uploads
    stmt = select(BatchRegisterPersonalInfoUpload).where(
        BatchRegisterPersonalInfoUpload.issuer_address == issuer_address
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    if status is not None:
        stmt = stmt.where(BatchRegisterPersonalInfoUpload.status == status)

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(BatchRegisterPersonalInfoUpload.created)
    else:  # DESC
        stmt = stmt.order_by(desc(BatchRegisterPersonalInfoUpload.created))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _upload_list: Sequence[BatchRegisterPersonalInfoUpload] = db.scalars(stmt).all()

    uploads = []
    for _upload in _upload_list:
        created_utc = timezone("UTC").localize(_upload.created)
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
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "uploads": uploads,
        }
    )


# POST: /share/tokens/{token_address}/personal_info/batch
@router.post(
    "/tokens/{token_address}/personal_info/batch",
    response_model=BatchRegisterPersonalInfoUploadResponse,
    responses=get_routers_responses(
        422, 401, 404, AuthorizationError, InvalidParameterError
    ),
)
def batch_register_personal_info(
    db: DBSession,
    request: Request,
    token_address: str,
    personal_info_list: List[RegisterPersonalInfoRequest],
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Create Batch for register personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the token is issued by the issuer_address
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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

    for personal_info in personal_info_list:
        bulk_register_record = BatchRegisterPersonalInfo()
        bulk_register_record.upload_id = batch_id
        bulk_register_record.token_address = token_address
        bulk_register_record.account_address = personal_info.account_address
        bulk_register_record.personal_info = personal_info.model_dump()
        bulk_register_record.status = 0
        db.add(bulk_register_record)

    db.commit()

    return json_response(
        {
            "batch_id": batch_id,
            "status": batch.status,
            "created": timezone("UTC")
            .localize(batch.created)
            .astimezone(local_tz)
            .isoformat(),
        }
    )


# GET: /share/tokens/{token_address}/personal_info/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/personal_info/batch/{batch_id}",
    response_model=GetBatchRegisterPersonalInfoResponse,
    responses=get_routers_responses(422, 404),
)
def retrieve_batch_register_personal_info(
    db: DBSession,
    token_address: str,
    batch_id: str,
    issuer_address: str = Header(...),
):
    """Get Batch status for register personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
    )

    # Upload Existence Check
    batch: Optional[BatchRegisterPersonalInfoUpload] = db.scalars(
        select(BatchRegisterPersonalInfoUpload)
        .where(
            and_(
                BatchRegisterPersonalInfoUpload.upload_id == batch_id,
                BatchRegisterPersonalInfoUpload.issuer_address == issuer_address,
            )
        )
        .limit(1)
    ).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: Sequence[BatchRegisterPersonalInfo] = db.scalars(
        select(BatchRegisterPersonalInfo).where(
            and_(
                BatchRegisterPersonalInfo.upload_id == batch_id,
                BatchRegisterPersonalInfo.token_address == token_address,
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


# GET: /share/tokens/{token_address}/lock_events
@router.get(
    "/tokens/{token_address}/lock_events",
    summary="List all lock/unlock events related to given share token",
    response_model=ListAllTokenLockEventsResponse,
    responses=get_routers_responses(422),
)
def list_all_lock_events_by_share(
    db: DBSession,
    token_address: str,
    issuer_address: Optional[str] = Header(None),
    request_query: ListAllTokenLockEventsQuery = Depends(),
):
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Request parameters
    offset = request_query.offset
    limit = request_query.limit
    sort_item = request_query.sort_item
    sort_order = request_query.sort_order

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
                Token.type == TokenType.IBET_SHARE,
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
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
    )
    if issuer_address is not None:
        stmt_unlock = stmt_unlock.where(Token.issuer_address == issuer_address)

    total = db.scalar(
        select(func.count()).select_from(stmt_lock.subquery())
    ) + db.scalar(select(func.count()).select_from(stmt_unlock.subquery()))

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

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    sort_attr = column(sort_item)
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))

    if sort_item != ListAllTokenLockEventsSortItem.block_timestamp.value:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(
            desc(column(ListAllTokenLockEventsSortItem.block_timestamp.value))
        )

    # Pagination
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

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
    lock_events = db.execute(select(*entries).from_statement(stmt)).tuples().all()

    resp_data = []
    for lock_event in lock_events:
        token: Token = lock_event.Token
        share_contract = IbetShareContract(token.token_address).get()
        block_timestamp_utc = timezone("UTC").localize(lock_event.block_timestamp)
        resp_data.append(
            {
                "category": lock_event.category,
                "transaction_hash": lock_event.transaction_hash,
                "msg_sender": lock_event.msg_sender,
                "issuer_address": token.issuer_address,
                "token_address": token.token_address,
                "token_type": token.type,
                "token_name": share_contract.name,
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
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "events": resp_data,
    }
    return json_response(data)


# POST: /share/transfers
@router.post(
    "/transfers",
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
def transfer_ownership(
    db: DBSession,
    request: Request,
    token: IbetShareTransfer,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Transfer token ownership"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
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

    # Check that it is a token that has been issued.
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.issuer_address == issuer_address,
                Token.token_address == token.token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    try:
        IbetShareContract(token.token_address).transfer(
            data=TransferParams(**token.model_dump()),
            tx_from=issuer_address,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/transfers/{token_address}
@router.get(
    "/transfers/{token_address}",
    response_model=TransferHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def list_transfer_history(
    db: DBSession,
    token_address: str,
    request_query: ListTransferHistoryQuery = Depends(),
):
    """List token transfer history"""
    # Get token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.source_event is not None:
        stmt = stmt.where(IDXTransfer.source_event == request_query.source_event)
    if request_query.data is not None:
        stmt = stmt.where(
            cast(IDXTransfer.data, String).like("%" + request_query.data + "%")
        )

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    sort_attr = getattr(IDXTransfer, request_query.sort_item.value, None)
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if request_query.sort_item != ListTransferHistorySortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(IDXTransfer.block_timestamp))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _transfers: Sequence[
        tuple[IDXTransfer, IDXPersonalInfo | None, IDXPersonalInfo | None]
    ] = db.execute(stmt).all()

    transfer_history = []
    for _transfer, _from_address_personal_info, _to_address_personal_info in _transfers:
        block_timestamp_utc = timezone("UTC").localize(_transfer.block_timestamp)
        transfer_history.append(
            {
                "transaction_hash": _transfer.transaction_hash,
                "token_address": token_address,
                "from_address": _transfer.from_address,
                "from_address_personal_information": _from_address_personal_info.personal_info
                if _from_address_personal_info is not None
                else None,
                "to_address": _transfer.to_address,
                "to_address_personal_information": _to_address_personal_info.personal_info
                if _to_address_personal_info is not None
                else None,
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
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total,
            },
            "transfer_history": transfer_history,
        }
    )


# GET: /share/transfer_approvals
@router.get(
    "/transfer_approvals",
    response_model=TransferApprovalsResponse,
    responses=get_routers_responses(422),
)
def list_transfer_approval_history(
    db: DBSession,
    issuer_address: Optional[str] = Header(None),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
):
    """List transfer approval history"""
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
        .where(and_(Token.type == TokenType.IBET_SHARE, Token.token_status != 2))
    )
    if issuer_address is not None:
        stmt = stmt.where(Token.issuer_address == issuer_address)

    stmt = stmt.group_by(Token.issuer_address, subquery.token_address).order_by(
        Token.issuer_address, subquery.token_address
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # NOTE: Because no filtering is performed, `total` and `count` have the same value.
    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _transfer_approvals = db.execute(stmt).tuples().all()

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
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "transfer_approvals": transfer_approvals,
        }
    )


# GET: /share/transfer_approvals/{token_address}
@router.get(
    "/transfer_approvals/{token_address}",
    response_model=TransferApprovalHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def list_token_transfer_approval_history(
    db: DBSession,
    token_address: str,
    get_query: ListTransferApprovalHistoryQuery = Depends(),
):
    """List token transfer approval history"""
    from_address = get_query.from_address
    to_address = get_query.to_address
    status = get_query.status
    sort_item = get_query.sort_item
    sort_order = get_query.sort_order
    offset = get_query.offset
    limit = get_query.limit

    # Get token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
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

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if from_address is not None:
        stmt = stmt.where(subquery.from_address == from_address)
    if to_address is not None:
        stmt = stmt.where(subquery.to_address == to_address)
    if status is not None:
        stmt = stmt.where(literal_column("status").in_(status))

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if sort_item != IDXTransferApprovalsSortItem.STATUS:
        sort_attr = getattr(subquery, sort_item, None)
    else:
        sort_attr = literal_column("status")
    if sort_order == 0:  # ASC
        stmt = stmt.order_by(sort_attr)
    else:  # DESC
        stmt = stmt.order_by(desc(sort_attr))
    if sort_item != IDXTransferApprovalsSortItem.ID:
        # NOTE: Set secondary sort for consistent results
        stmt = stmt.order_by(desc(subquery.id))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _transfer_approvals: Sequence[
        tuple[
            IDXTransferApproval,
            int,
            dict | None,
            dict | None,
            IDXPersonalInfo | None,
            IDXPersonalInfo | None,
        ]
    ] = db.execute(stmt).all()

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

        application_datetime_utc = timezone("UTC").localize(
            _transfer_approval.application_datetime
        )
        application_datetime = application_datetime_utc.astimezone(local_tz).isoformat()

        application_blocktimestamp_utc = timezone("UTC").localize(
            _transfer_approval.application_blocktimestamp
        )
        application_blocktimestamp = application_blocktimestamp_utc.astimezone(
            local_tz
        ).isoformat()

        if _transfer_approval.approval_datetime is not None:
            approval_datetime_utc = timezone("UTC").localize(
                _transfer_approval.approval_datetime
            )
            approval_datetime = approval_datetime_utc.astimezone(local_tz).isoformat()
        else:
            approval_datetime = None

        if _transfer_approval.approval_blocktimestamp is not None:
            approval_blocktimestamp_utc = timezone("UTC").localize(
                _transfer_approval.approval_blocktimestamp
            )
            approval_blocktimestamp = approval_blocktimestamp_utc.astimezone(
                local_tz
            ).isoformat()
        else:
            approval_blocktimestamp = None

        if _transfer_approval.cancellation_blocktimestamp is not None:
            cancellation_blocktimestamp_utc = timezone("UTC").localize(
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
            else _from_address_latest_personal_info.personal_info
            if _from_address_latest_personal_info is not None
            else None
        )
        to_address_personal_info = (
            _to_address_snapshot_personal_info
            if _to_address_snapshot_personal_info is not None
            else _to_address_latest_personal_info.personal_info
            if _to_address_latest_personal_info is not None
            else None
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
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "transfer_approval_history": transfer_approval_history,
        }
    )


# POST: /share/transfer_approvals/{token_address}/{id}
@router.post(
    "/transfer_approvals/{token_address}/{id}",
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
def update_transfer_approval(
    db: DBSession,
    request: Request,
    token_address: str,
    id: int,
    data: UpdateTransferApprovalRequest,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Update on the status of a share transfer approval"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    _account, decrypt_password = check_auth(
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
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer approval history
    _transfer_approval: IDXTransferApproval | None = db.scalars(
        select(IDXTransferApproval)
        .where(
            and_(
                IDXTransferApproval.id == id,
                IDXTransferApproval.token_address == token_address,
            )
        )
        .limit(1)
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

    transfer_approval_op: TransferApprovalHistory | None = db.scalars(
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
    ).first()
    if transfer_approval_op is not None:
        raise InvalidParameterError("duplicate operation")

    # Check the existence of personal information data for from_address and to_address
    _from_address_personal_info: IDXPersonalInfo | None = db.scalars(
        select(IDXPersonalInfo)
        .where(
            and_(
                IDXPersonalInfo.account_address == _transfer_approval.from_address,
                IDXPersonalInfo.issuer_address == issuer_address,
            )
        )
        .limit(1)
    ).first()
    if _from_address_personal_info is None:
        raise OperationNotAllowedStateError(
            101, "personal information for from_address is not registered"
        )

    _to_address_personal_info: IDXPersonalInfo | None = db.scalars(
        select(IDXPersonalInfo)
        .where(
            and_(
                IDXPersonalInfo.account_address == _transfer_approval.to_address,
                IDXPersonalInfo.issuer_address == issuer_address,
            )
        )
        .limit(1)
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
        now = str(datetime.utcnow().timestamp())
        if data.operation_type == UpdateTransferApprovalOperationType.APPROVE:
            if _transfer_approval.exchange_address == config.ZERO_ADDRESS:
                _data = {
                    "application_id": _transfer_approval.application_id,
                    "data": now,
                }
                try:
                    _, tx_receipt = IbetShareContract(token_address).approve_transfer(
                        data=ApproveTransferParams(**_data),
                        tx_from=issuer_address,
                        private_key=private_key,
                    )
                except ContractRevertError as approve_transfer_err:
                    # If approveTransfer end with revert,
                    # cancelTransfer should be performed immediately.
                    # After cancelTransfer, ContractRevertError is returned.
                    try:
                        IbetShareContract(token_address).cancel_transfer(
                            data=CancelTransferParams(**_data),
                            tx_from=issuer_address,
                            private_key=private_key,
                        )
                    except ContractRevertError as cancel_transfer_err:
                        raise
                    except Exception:
                        raise SendTransactionError
                    # If cancel transfer is successful, approve_transfer error is raised.
                    raise
            else:
                _data = {"escrow_id": _transfer_approval.application_id, "data": now}
                escrow = IbetSecurityTokenEscrow(_transfer_approval.exchange_address)
                try:
                    _, tx_receipt = escrow.approve_transfer(
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
                _, tx_receipt = IbetShareContract(token_address).cancel_transfer(
                    data=CancelTransferParams(**_data),
                    tx_from=issuer_address,
                    private_key=private_key,
                )
            except ContractRevertError:
                # If cancelTransfer end with revert, error should be thrown immediately.
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
    db.commit()


# GET: /share/transfer_approvals/{token_address}/{id}
@router.get(
    "/transfer_approvals/{token_address}/{id}",
    response_model=TransferApprovalTokenDetailResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def retrieve_transfer_approval_history(
    db: DBSession,
    token_address: str,
    id: int,
):
    """Retrieve share token transfer approval history"""
    # Get token
    _token: Token | None = db.scalars(
        select(Token)
        .where(
            and_(
                Token.type == TokenType.IBET_SHARE,
                Token.token_address == token_address,
                Token.token_status != 2,
            )
        )
        .limit(1)
    ).first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer approval history
    _transfer_approval: IDXTransferApproval | None = db.scalars(
        select(IDXTransferApproval)
        .where(
            and_(
                IDXTransferApproval.id == id,
                IDXTransferApproval.token_address == token_address,
            )
        )
        .limit(1)
    ).first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")

    _transfer_approval_op: TransferApprovalHistory | None = db.scalars(
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

    application_datetime_utc = timezone("UTC").localize(
        _transfer_approval.application_datetime
    )
    application_datetime = application_datetime_utc.astimezone(local_tz).isoformat()

    application_blocktimestamp_utc = timezone("UTC").localize(
        _transfer_approval.application_blocktimestamp
    )
    application_blocktimestamp = application_blocktimestamp_utc.astimezone(
        local_tz
    ).isoformat()

    if _transfer_approval.approval_datetime is not None:
        approval_datetime_utc = timezone("UTC").localize(
            _transfer_approval.approval_datetime
        )
        approval_datetime = approval_datetime_utc.astimezone(local_tz).isoformat()
    else:
        approval_datetime = None

    if _transfer_approval.approval_blocktimestamp is not None:
        approval_blocktimestamp_utc = timezone("UTC").localize(
            _transfer_approval.approval_blocktimestamp
        )
        approval_blocktimestamp = approval_blocktimestamp_utc.astimezone(
            local_tz
        ).isoformat()
    else:
        approval_blocktimestamp = None

    if _transfer_approval.cancellation_blocktimestamp is not None:
        cancellation_blocktimestamp_utc = timezone("UTC").localize(
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
        _from_account: IDXPersonalInfo | None = db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == _transfer_approval.from_address,
                    IDXPersonalInfo.issuer_address == _token.issuer_address,
                )
            )
            .limit(1)
        ).first()
        _from_address_personal_info = (
            _from_account.personal_info if _from_account is not None else None
        )

        _to_account: IDXPersonalInfo | None = db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.account_address == _transfer_approval.to_address,
                    IDXPersonalInfo.issuer_address == _token.issuer_address,
                )
            )
            .limit(1)
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


# POST: /share/bulk_transfer
@router.post(
    "/bulk_transfer",
    response_model=BulkTransferUploadIdResponse,
    responses=get_routers_responses(
        422, AuthorizationError, InvalidParameterError, 401
    ),
)
def bulk_transfer_ownership(
    db: DBSession,
    request: Request,
    bulk_transfer_req: IbetShareBulkTransferRequest,
    issuer_address: str = Header(...),
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Bulk transfer token ownership

    By using "transaction compression mode", it is possible to consolidate multiple transfers into one transaction.
    This speeds up the time it takes for all transfers to be completed.
    On the other hand, when using transaction compression, the input data must meet the following conditions.
    - All `token_address` must be the same.
    - All `from_address` must be the same.
    - `from_address` and `issuer_address` must be the same.
    """
    tx_compression = bulk_transfer_req.transaction_compression
    transfer_list = bulk_transfer_req.transfer_list
    token_addr_set = set()
    from_addr_set = set()

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Verify that the tokens are issued by the issuer_address
    for _transfer in transfer_list:
        _issued_token: Token | None = db.scalars(
            select(Token)
            .where(
                and_(
                    Token.type == TokenType.IBET_SHARE,
                    Token.issuer_address == issuer_address,
                    Token.token_address == _transfer.token_address,
                    Token.token_status != 2,
                )
            )
            .limit(1)
        ).first()
        if _issued_token is None:
            raise InvalidParameterError(f"token not found: {_transfer.token_address}")
        if _issued_token.token_status == 0:
            raise InvalidParameterError(
                f"this token is temporarily unavailable: {_transfer.token_address}"
            )

        token_addr_set.add(_transfer.token_address)
        from_addr_set.add(_transfer.from_address)

    # Checks when compressing transactions
    if tx_compression:
        # All token_address must be the same
        if len(token_addr_set) > 1:
            raise InvalidParameterError(
                "When using transaction compression, all token_address must be the same."
            )
        # All from_address must be the same
        if len(from_addr_set) > 1:
            raise InvalidParameterError(
                "When using transaction compression, all from_address must be the same."
            )
        # from_address must be the same as issuer_address
        if next(iter(from_addr_set)) != issuer_address:
            raise InvalidParameterError(
                "When using transaction compression, from_address must be the same as issuer_address."
            )

    # Generate upload_id
    upload_id = uuid.uuid4()

    # add bulk transfer upload record
    _bulk_transfer_upload = BulkTransferUpload()
    _bulk_transfer_upload.upload_id = upload_id
    _bulk_transfer_upload.issuer_address = issuer_address
    _bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
    _bulk_transfer_upload.transaction_compression = tx_compression
    _bulk_transfer_upload.status = 0
    db.add(_bulk_transfer_upload)

    # Add bulk transfer records
    for _transfer in transfer_list:
        _bulk_transfer = BulkTransfer()
        _bulk_transfer.issuer_address = issuer_address
        _bulk_transfer.upload_id = upload_id
        _bulk_transfer.token_address = _transfer.token_address
        _bulk_transfer.token_type = TokenType.IBET_SHARE.value
        _bulk_transfer.from_address = _transfer.from_address
        _bulk_transfer.to_address = _transfer.to_address
        _bulk_transfer.amount = _transfer.amount
        _bulk_transfer.status = 0
        db.add(_bulk_transfer)

    db.commit()

    return json_response({"upload_id": str(upload_id)})


# GET: /share/bulk_transfer
@router.get(
    "/bulk_transfer",
    response_model=List[BulkTransferUploadResponse],
    responses=get_routers_responses(422),
)
def list_bulk_transfer_upload(
    db: DBSession, issuer_address: Optional[str] = Header(None)
):
    """List bulk transfer uploads"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get bulk transfer upload list
    if issuer_address is None:
        _uploads: Sequence[BulkTransferUpload] = db.scalars(
            select(BulkTransferUpload)
            .where(BulkTransferUpload.token_type == TokenType.IBET_SHARE)
            .order_by(BulkTransferUpload.issuer_address)
        ).all()
    else:
        _uploads: Sequence[BulkTransferUpload] = db.scalars(
            select(BulkTransferUpload).where(
                and_(
                    BulkTransferUpload.issuer_address == issuer_address,
                    BulkTransferUpload.token_type == TokenType.IBET_SHARE,
                )
            )
        ).all()

    uploads = []
    for _upload in _uploads:
        created_utc = timezone("UTC").localize(_upload.created)
        uploads.append(
            {
                "issuer_address": _upload.issuer_address,
                "token_type": _upload.token_type,
                "upload_id": _upload.upload_id,
                "transaction_compression": True
                if _upload.transaction_compression is True
                else False,
                "status": _upload.status,
                "created": created_utc.astimezone(local_tz).isoformat(),
            }
        )

    return json_response(uploads)


# GET: /share/bulk_transfer/{upload_id}
@router.get(
    "/bulk_transfer/{upload_id}",
    response_model=List[BulkTransferResponse],
    responses=get_routers_responses(422, 404),
)
def retrieve_bulk_transfer(
    db: DBSession,
    upload_id: str,
    issuer_address: Optional[str] = Header(None),
):
    """Retrieve a bulk transfer upload"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get bulk transfer upload list
    if issuer_address is None:
        _bulk_transfers: Sequence[BulkTransfer] = db.scalars(
            select(BulkTransfer)
            .where(
                and_(
                    BulkTransfer.upload_id == upload_id,
                    BulkTransfer.token_type == TokenType.IBET_SHARE,
                )
            )
            .order_by(BulkTransfer.issuer_address)
        ).all()
    else:
        _bulk_transfers: Sequence[BulkTransfer] = db.scalars(
            select(BulkTransfer).where(
                and_(
                    BulkTransfer.issuer_address == issuer_address,
                    BulkTransfer.upload_id == upload_id,
                    BulkTransfer.token_type == TokenType.IBET_SHARE,
                )
            )
        ).all()

    bulk_transfers = []
    for _bulk_transfer in _bulk_transfers:
        bulk_transfers.append(
            {
                "issuer_address": _bulk_transfer.issuer_address,
                "token_type": _bulk_transfer.token_type,
                "upload_id": _bulk_transfer.upload_id,
                "token_address": _bulk_transfer.token_address,
                "from_address": _bulk_transfer.from_address,
                "to_address": _bulk_transfer.to_address,
                "amount": _bulk_transfer.amount,
                "status": _bulk_transfer.status,
                "transaction_error_code": _bulk_transfer.transaction_error_code,
                "transaction_error_message": _bulk_transfer.transaction_error_message,
            }
        )

    if len(bulk_transfers) < 1:
        raise HTTPException(status_code=404, detail="bulk transfer not found")

    return json_response(bulk_transfers)
