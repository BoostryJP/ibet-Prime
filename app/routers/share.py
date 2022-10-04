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
from typing import (
    List,
    Optional
)

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Request
)
from fastapi.exceptions import HTTPException
from sqlalchemy import (
    desc,
    case,
    and_,
    or_,
    func,
    literal_column
)
from sqlalchemy.orm import (
    Session,
    aliased
)
from eth_keyfile import decode_keyfile_json
from pytz import timezone

import config
from app import log
from app.database import db_session
from app.model.schema import (
    IbetShareCreate,
    IbetShareUpdate,
    IbetShareTransfer,
    IbetShareAdditionalIssue,
    IbetShareRedeem,
    IbetShareResponse,
    TokenAddressResponse,
    HolderResponse,
    HolderCountResponse,
    TransferApprovalsResponse,
    TransferHistoryResponse,
    TransferApprovalHistoryResponse,
    TransferApprovalTokenResponse,
    BulkTransferUploadIdResponse,
    BulkTransferUploadResponse,
    BulkTransferResponse,
    IbetShareScheduledUpdate,
    ScheduledEventIdResponse,
    ScheduledEventResponse,
    ModifyPersonalInfoRequest,
    RegisterPersonalInfoRequest,
    IbetSecurityTokenApproveTransfer,
    IbetSecurityTokenCancelTransfer,
    IbetSecurityTokenEscrowApproveTransfer,
    UpdateTransferApprovalRequest,
    BatchIssueRedeemUploadIdResponse,
    GetBatchIssueRedeemResponse,
    GetBatchIssueRedeemResult,
    ListBatchIssueRedeemUploadResponse,
    BatchRegisterPersonalInfoUploadResponse,
    ListBatchRegisterPersonalInfoUploadResponse,
    GetBatchRegisterPersonalInfoResponse,
    BatchRegisterPersonalInfoResult,
    UpdateTransferApprovalOperationType,
    IssueRedeemHistoryResponse
)
from app.model.db import (
    Account,
    Token,
    TokenType,
    UpdateToken,
    IDXPosition,
    IDXPersonalInfo,
    BulkTransfer,
    BulkTransferUpload,
    IDXTransfer,
    IDXTransfersSortItem,
    IDXTransferApproval,
    IDXTransferApprovalsSortItem,
    ScheduledEvents,
    UTXO,
    BatchIssueRedeemUpload,
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    BatchRegisterPersonalInfo,
    IDXIssueRedeemSortItem,
    IDXIssueRedeem,
    IDXIssueRedeemEventType,
    TransferApprovalHistory,
    TransferApprovalOperationType
)
from app.model.blockchain import (
    IbetShareContract,
    TokenListContract,
    PersonalInfoContract,
    IbetSecurityTokenEscrow
)
from app.utils.contract_utils import ContractUtils
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address,
    eoa_password_is_encrypted_value,
    check_auth
)
from app.utils.docs_utils import get_routers_responses
from app.exceptions import (
    InvalidParameterError,
    SendTransactionError,
    ContractRevertError,
    AuthorizationError
)

router = APIRouter(
    prefix="/share",
    tags=["share"],
)

LOG = log.get_logger()
local_tz = timezone(config.TZ)


# POST: /share/tokens
@router.post(
    "/tokens",
    response_model=TokenAddressResponse,
    responses=get_routers_responses(422, 401, AuthorizationError, SendTransactionError, ContractRevertError)
)
def issue_token(
        request: Request,
        token: IbetShareCreate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Issue ibetShare token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Deploy
    _symbol = token.symbol if token.symbol is not None else ""
    _dividends = token.dividends if token.dividends is not None else 0
    _dividend_record_date = token.dividend_record_date if token.dividend_record_date is not None else ""
    _dividend_payment_date = token.dividend_payment_date if token.dividend_payment_date is not None else ""
    _cancellation_date = token.cancellation_date if token.cancellation_date is not None else ""
    arguments = [
        token.name,
        _symbol,
        token.issue_price,
        token.total_supply,
        int(Decimal(str(_dividends)) * Decimal("10000000000000")),
        _dividend_record_date,
        _dividend_payment_date,
        _cancellation_date,
        token.principal_value
    ]
    try:
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError as e:
        raise SendTransactionError("failed to send transaction")

    # Check need update
    update_items = ["tradable_exchange_contract_address", "personal_info_contract_address", "transferable",
                    "status", "is_offering", "contact_information", "privacy_policy", "transfer_approval_required",
                    "is_canceled"]
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
            TokenListContract.register(
                token_list_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
                token_address=contract_address,
                token_template=TokenType.IBET_SHARE.value,
                account_address=issuer_address,
                private_key=private_key
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
    db.add(_token)

    db.commit()

    return {
        "token_address": _token.token_address,
        "token_status": token_status
    }


# GET: /share/tokens
@router.get(
    "/tokens",
    response_model=List[IbetShareResponse],
    responses=get_routers_responses(422)
)
def list_all_tokens(
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    """List all issued tokens"""
    # Get issued token list
    if issuer_address is None:
        tokens = db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE.value). \
            all()
    else:
        tokens = db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE.value). \
            filter(Token.issuer_address == issuer_address). \
            all()

    share_tokens = []
    for token in tokens:
        # Get contract data
        share_token = IbetShareContract.get(contract_address=token.token_address).__dict__
        issue_datetime_utc = timezone("UTC").localize(token.created)
        share_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
        share_token["token_status"] = token.token_status
        share_tokens.append(share_token)

    return share_tokens


# GET: /share/tokens/{token_address}
@router.get(
    "/tokens/{token_address}",
    response_model=IbetShareResponse,
    responses=get_routers_responses(404, InvalidParameterError)
)
def retrieve_token(
        token_address: str,
        db: Session = Depends(db_session)):
    """Retrieve token"""
    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get contract data
    share_token = IbetShareContract.get(contract_address=token_address).__dict__
    issue_datetime_utc = timezone("UTC").localize(_token.created)
    share_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
    share_token["token_status"] = _token.token_status

    return share_token


# POST: /share/tokens/{token_address}
@router.post(
    "/tokens/{token_address}",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def update_token(
        request: Request,
        token_address: str,
        token: IbetShareUpdate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Update a token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        IbetShareContract.update(
            contract_address=token_address,
            data=token,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    db.commit()

    return


# GET: /share/tokens/{token_address}/additional_issue
@router.get(
    "/tokens/{token_address}/additional_issue",
    response_model=IssueRedeemHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_additional_issuance_history(
        token_address: str,
        sort_item: IDXIssueRedeemSortItem = Query(IDXIssueRedeemSortItem.BLOCK_TIMESTAMP),
        sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)):
    """List additional issuance history"""

    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get history record
    query = db.query(IDXIssueRedeem). \
        filter(IDXIssueRedeem.event_type == IDXIssueRedeemEventType.ISSUE). \
        filter(IDXIssueRedeem.token_address == token_address)
    total = query.count()
    count = total

    # Sort
    sort_attr = getattr(IDXIssueRedeem, sort_item.value, None)
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != IDXIssueRedeemSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(IDXIssueRedeem.block_timestamp))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _events: List[IDXIssueRedeem] = query.all()

    history = []
    for _event in _events:
        block_timestamp_utc = timezone("UTC").localize(_event.block_timestamp)
        history.append({
            "transaction_hash": _event.transaction_hash,
            "token_address": token_address,
            "locked_address": _event.locked_address,
            "target_address": _event.target_address,
            "amount": _event.amount,
            "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat()
        })

    return IssueRedeemHistoryResponse(
        result_set={
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        history=history
    )


# POST: /share/tokens/{token_address}/additional_issue
@router.post(
    "/tokens/{token_address}/additional_issue",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def additional_issue(
        request: Request,
        token_address: str,
        data: IbetShareAdditionalIssue,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Additional issue"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        IbetShareContract.additional_issue(
            contract_address=token_address,
            data=data,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/tokens/{token_address}/additional_issue/batch
@router.get(
    "/tokens/{token_address}/additional_issue/batch",
    response_model=ListBatchIssueRedeemUploadResponse,
    responses=get_routers_responses(422)
)
def list_all_additional_issue_upload(
    token_address: str,
    processed: Optional[bool] = Query(None),
    sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc (created)"),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    issuer_address: Optional[str] = Header(None),
    db: Session = Depends(db_session)
):
    # Get a list of uploads
    query = db.query(BatchIssueRedeemUpload). \
        filter(BatchIssueRedeemUpload.token_address == token_address). \
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE.value). \
        filter(BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.ISSUE.value)

    if issuer_address is not None:
        query = query.filter(BatchIssueRedeemUpload.issuer_address == issuer_address)

    total = query.count()

    if processed is not None:
        query = query.filter(BatchIssueRedeemUpload.processed == processed)

    count = query.count()

    # Sort
    if sort_order == 0:  # ASC
        query = query.order_by(BatchIssueRedeemUpload.created)
    else:  # DESC
        query = query.order_by(desc(BatchIssueRedeemUpload.created))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _upload_list: list[BatchIssueRedeemUpload] = query.all()

    uploads = []
    for _upload in _upload_list:
        created_utc = timezone("UTC").localize(_upload.created)
        uploads.append({
            "batch_id": _upload.upload_id,
            "issuer_address": _upload.issuer_address,
            "token_type": _upload.token_type,
            "token_address": _upload.token_address,
            "processed": _upload.processed,
            "created": created_utc.astimezone(local_tz).isoformat()
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "uploads": uploads
    }
    return resp


# POST: /share/tokens/{token_address}/additional_issue/batch
@router.post(
    "/tokens/{token_address}/additional_issue/batch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def additional_issue_in_batch(
        request: Request,
        token_address: str,
        data: List[IbetShareAdditionalIssue],
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Additional issue (Batch)"""

    # Validate headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
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
        auth_token=auth_token
    )

    # Check token status
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
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

    return BatchIssueRedeemUploadIdResponse(batch_id=str(upload_id))


# GET: /share/tokens/{token_address}/additional_issue/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/additional_issue/batch/{batch_id}",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404)
)
def retrieve_batch_additional_issue(
        token_address: str,
        batch_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Get Batch status for additional issue"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address)
    )

    # Upload Existence Check
    batch: Optional[BatchIssueRedeemUpload] = db.query(BatchIssueRedeemUpload). \
        filter(BatchIssueRedeemUpload.upload_id == batch_id). \
        filter(BatchIssueRedeemUpload.issuer_address == issuer_address). \
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE.value). \
        filter(BatchIssueRedeemUpload.token_address == token_address). \
        filter(BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.ISSUE.value). \
        first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
        filter(BatchIssueRedeem.upload_id == batch_id). \
        all()

    return GetBatchIssueRedeemResponse(
        processed=batch.processed,
        results=[
            GetBatchIssueRedeemResult(
                account_address=record.account_address,
                amount=record.amount,
                status=record.status
            ) for record in record_list
        ]
    )


# GET: /share/tokens/{token_address}/redeem
@router.get(
    "/tokens/{token_address}/redeem",
    response_model=IssueRedeemHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_redeem_history(
        token_address: str,
        sort_item: IDXIssueRedeemSortItem = Query(IDXIssueRedeemSortItem.BLOCK_TIMESTAMP),
        sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)):
    """List redemption history"""

    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get history record
    query = db.query(IDXIssueRedeem). \
        filter(IDXIssueRedeem.event_type == IDXIssueRedeemEventType.REDEEM). \
        filter(IDXIssueRedeem.token_address == token_address)
    total = query.count()
    count = total

    # Sort
    sort_attr = getattr(IDXIssueRedeem, sort_item.value, None)
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != IDXIssueRedeemSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(IDXIssueRedeem.block_timestamp))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _events: List[IDXIssueRedeem] = query.all()

    history = []
    for _event in _events:
        block_timestamp_utc = timezone("UTC").localize(_event.block_timestamp)
        history.append({
            "transaction_hash": _event.transaction_hash,
            "token_address": token_address,
            "locked_address": _event.locked_address,
            "target_address": _event.target_address,
            "amount": _event.amount,
            "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat()
        })

    return IssueRedeemHistoryResponse(
        result_set={
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        history=history
    )


# POST: /share/tokens/{token_address}/redeem
@router.post(
    "/tokens/{token_address}/redeem",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def redeem_token(
        request: Request,
        token_address: str,
        data: IbetShareRedeem,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Redeem a token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Send transaction
    try:
        IbetShareContract.redeem(
            contract_address=token_address,
            data=data,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/tokens/{token_address}/redeem/batch
@router.get(
    "/tokens/{token_address}/redeem/batch",
    response_model=ListBatchIssueRedeemUploadResponse,
    responses=get_routers_responses(422)
)
def list_all_redeem_upload(
    token_address: str,
    processed: Optional[bool] = Query(None),
    sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc (created)"),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    issuer_address: Optional[str] = Header(None),
    db: Session = Depends(db_session)
):
    # Get a list of uploads
    query = db.query(BatchIssueRedeemUpload). \
        filter(BatchIssueRedeemUpload.token_address == token_address). \
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE.value). \
        filter(BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.REDEEM.value)

    if issuer_address is not None:
        query = query.filter(BatchIssueRedeemUpload.issuer_address == issuer_address)

    total = query.count()

    if processed is not None:
        query = query.filter(BatchIssueRedeemUpload.processed == processed)

    count = query.count()

    # Sort
    if sort_order == 0:  # ASC
        query = query.order_by(BatchIssueRedeemUpload.created)
    else:  # DESC
        query = query.order_by(desc(BatchIssueRedeemUpload.created))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _upload_list: list[BatchIssueRedeemUpload] = query.all()

    uploads = []
    for _upload in _upload_list:
        created_utc = timezone("UTC").localize(_upload.created)
        uploads.append({
            "batch_id": _upload.upload_id,
            "issuer_address": _upload.issuer_address,
            "token_type": _upload.token_type,
            "token_address": _upload.token_address,
            "processed": _upload.processed,
            "created": created_utc.astimezone(local_tz).isoformat()
        })

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "uploads": uploads
    }
    return resp


# POST: /share/tokens/{token_address}/redeem/batch
@router.post(
    "/tokens/{token_address}/redeem/batch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def redeem_token_in_batch(
        request: Request,
        token_address: str,
        data: List[IbetShareRedeem],
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Redeem a token (Batch)"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
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
        auth_token=auth_token
    )

    # Check token status
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
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

    return BatchIssueRedeemUploadIdResponse(batch_id=str(upload_id))


# GET: /share/tokens/{token_address}/redeem/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/redeem/batch/{batch_id}",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404)
)
def retrieve_batch_additional_issue(
        token_address: str,
        batch_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Get Batch status for additional issue"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address)
    )

    # Upload Existence Check
    batch: Optional[BatchIssueRedeemUpload] = db.query(BatchIssueRedeemUpload). \
        filter(BatchIssueRedeemUpload.upload_id == batch_id). \
        filter(BatchIssueRedeemUpload.issuer_address == issuer_address). \
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_SHARE.value). \
        filter(BatchIssueRedeemUpload.token_address == token_address). \
        filter(BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.REDEEM.value). \
        first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
        filter(BatchIssueRedeem.upload_id == batch_id). \
        all()

    return GetBatchIssueRedeemResponse(
        processed=batch.processed,
        results=[
            GetBatchIssueRedeemResult(
                account_address=record.account_address,
                amount=record.amount,
                status=record.status
            ) for record in record_list
        ]
    )


# GET: /share/tokens/{token_address}/scheduled_events
@router.get(
    "/tokens/{token_address}/scheduled_events",
    response_model=List[ScheduledEventResponse]
)
def list_all_scheduled_events(
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """List all scheduled update events"""

    if issuer_address is None:
        _token_events = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE.value). \
            filter(ScheduledEvents.token_address == token_address). \
            order_by(ScheduledEvents.id). \
            all()
    else:
        _token_events = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE.value). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            filter(ScheduledEvents.token_address == token_address). \
            order_by(ScheduledEvents.id). \
            all()

    token_events = []
    for _token_event in _token_events:
        scheduled_datetime_utc = timezone("UTC").localize(_token_event.scheduled_datetime)
        created_utc = timezone("UTC").localize(_token_event.created)
        token_events.append(
            {
                "scheduled_event_id": _token_event.event_id,
                "token_address": token_address,
                "token_type": TokenType.IBET_SHARE.value,
                "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
                "event_type": _token_event.event_type,
                "status": _token_event.status,
                "data": _token_event.data,
                "created": created_utc.astimezone(local_tz).isoformat()
            }
        )
    return token_events


# POST: /share/tokens/{token_address}/scheduled_events
@router.post(
    "/tokens/{token_address}/scheduled_events",
    response_model=ScheduledEventIdResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def schedule_new_update_event(
        request: Request,
        token_address: str,
        event_data: IbetShareScheduledUpdate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Register a new update event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Verify that the token is issued by the issuer
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
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
    _scheduled_event.data = event_data.data.dict()
    _scheduled_event.status = 0
    db.add(_scheduled_event)
    db.commit()

    return {"scheduled_event_id": _scheduled_event.event_id}


# GET: /share/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.get(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(404)
)
def retrieve_token_event(
        token_address: str,
        scheduled_event_id: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve a scheduled token event"""

    if issuer_address is None:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE.value). \
            filter(ScheduledEvents.event_id == scheduled_event_id). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    else:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE.value). \
            filter(ScheduledEvents.event_id == scheduled_event_id). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="event not found")

    scheduled_datetime_utc = timezone("UTC").localize(_token_event.scheduled_datetime)
    created_utc = timezone("UTC").localize(_token_event.created)
    return {
        "scheduled_event_id": _token_event.event_id,
        "token_address": token_address,
        "token_type": TokenType.IBET_SHARE.value,
        "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data,
        "created": created_utc.astimezone(local_tz).isoformat()
    }


# DELETE: /share/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.delete(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError)
)
def delete_scheduled_event(
        request: Request,
        token_address: str,
        scheduled_event_id: str,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Delete a scheduled event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Delete an event
    _token_event = db.query(ScheduledEvents). \
        filter(ScheduledEvents.token_type == TokenType.IBET_SHARE.value). \
        filter(ScheduledEvents.event_id == scheduled_event_id). \
        filter(ScheduledEvents.issuer_address == issuer_address). \
        filter(ScheduledEvents.token_address == token_address). \
        first()
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
        "created": created_utc.astimezone(local_tz).isoformat()
    }

    db.delete(_token_event)
    db.commit()

    return rtn


# GET: /share/tokens/{token_address}/holders
@router.get(
    "/tokens/{token_address}/holders",
    response_model=List[HolderResponse],
    responses=get_routers_responses(422, InvalidParameterError, 404)
)
def list_all_holders(
        token_address: str,
        include_former_holder: bool = False,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """List all share token holders"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    query = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address)
    if not include_former_holder:
        # Get Holders
        query = query.filter(or_(
            IDXPosition.balance != 0,
            IDXPosition.exchange_balance != 0,
            IDXPosition.pending_transfer != 0,
            IDXPosition.exchange_commitment != 0
        ))
    _holders = query.order_by(IDXPosition.id).all()

    # Get personal information
    _personal_info_list = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        all()
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
        "tax_category": None
    }

    holders = []
    for _holder in _holders:
        _personal_info = _personal_info_dict.get(
            _holder.account_address,
            personal_info_default
        )
        holders.append({
            "account_address": _holder.account_address,
            "personal_information": _personal_info,
            "balance": _holder.balance,
            "exchange_balance": _holder.exchange_balance,
            "exchange_commitment": _holder.exchange_commitment,
            "pending_transfer": _holder.pending_transfer
        })

    return holders


# GET: /share/tokens/{token_address}/holders/count
@router.get(
    "/tokens/{token_address}/holders/count",
    response_model=HolderCountResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404)
)
def count_number_of_holders(
        token_address: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Count the number of holders"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    _count: int = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address). \
        filter(
            or_(IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_commitment != 0)
        ). \
        count()

    return HolderCountResponse(count=_count)


# GET: /share/tokens/{token_address}/holders/{account_address}
@router.get(
    "/tokens/{token_address}/holders/{account_address}",
    response_model=HolderResponse,
    responses=get_routers_responses(422, InvalidParameterError, 404)
)
def retrieve_holder(
        token_address: str,
        account_address: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Retrieve share token holder"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get Issuer
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    _holder = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address). \
        filter(IDXPosition.account_address == account_address). \
        first()
    if _holder is None:
        balance = 0
        exchange_balance = 0
        exchange_commitment = 0
        pending_transfer = 0
    else:
        balance = _holder.balance
        exchange_balance = _holder.exchange_balance
        exchange_commitment = _holder.exchange_commitment
        pending_transfer = _holder.pending_transfer

    # Get personal information
    personal_info_default = {
        "key_manager": None,
        "name": None,
        "postal_code": None,
        "address": None,
        "email": None,
        "birth": None,
        "is_corporate": None,
        "tax_category": None
    }
    _personal_info_record = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.account_address == account_address). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        first()
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
        "pending_transfer": pending_transfer
    }

    return holder


# POST: /share/tokens/{token_address}/holders/{account_address}/personal_info
@router.post(
    "/tokens/{token_address}/holders/{account_address}/personal_info",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError),
    deprecated=True
)
def modify_holder_personal_info(
        request: Request,
        token_address: str,
        account_address: str,
        personal_info: ModifyPersonalInfoRequest,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Modify the holder's personal information"""
    LOG.warning(DeprecationWarning("Deprecated API: /share/tokens/{token_address}/holders/{account_address}/personal_info"))

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Verify that the token is issued by the issuer_address
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Modify Personal Info
    token_contract = IbetShareContract.get(token_address)
    try:
        personal_info_contract = PersonalInfoContract(
            db=db,
            issuer_address=issuer_address,
            contract_address=token_contract.personal_info_contract_address
        )
        personal_info_contract.modify_info(
            account_address=account_address,
            data=personal_info.dict(),
            default_value=None
        )
    except SendTransactionError:
        raise SendTransactionError("failed to modify personal information")

    return


# GET: /share/tokens/{token_address}/personal_info/batch
@router.get(
    "/tokens/{token_address}/personal_info/batch",
    response_model=ListBatchRegisterPersonalInfoUploadResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_all_personal_info_batch_registration_uploads(
        token_address: str,
        issuer_address: str = Header(...),
        status: Optional[str] = Query(None),
        sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc (created)"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)):
    """List all personal information batch registration uploads"""

    # Verify that the token is issued by the issuer_address
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get a list of uploads
    query = db.query(BatchRegisterPersonalInfoUpload). \
        filter(BatchRegisterPersonalInfoUpload.issuer_address == issuer_address)

    total = query.count()

    if status is not None:
        query = query.filter(BatchRegisterPersonalInfoUpload.status == status)

    count = query.count()

    # Sort
    if sort_order == 0:  # ASC
        query = query.order_by(BatchRegisterPersonalInfoUpload.created)
    else:  # DESC
        query = query.order_by(desc(BatchRegisterPersonalInfoUpload.created))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    _upload_list: list[BatchRegisterPersonalInfoUpload] = query.all()

    uploads = []
    for _upload in _upload_list:
        created_utc = timezone("UTC").localize(_upload.created)
        uploads.append({
            "batch_id": _upload.upload_id,
            "issuer_address": _upload.issuer_address,
            "status": _upload.status,
            "created": created_utc.astimezone(local_tz).isoformat()
        })

    return ListBatchRegisterPersonalInfoUploadResponse(
        result_set={
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        uploads=uploads
    )


# POST: /share/tokens/{token_address}/personal_info
@router.post(
    "/tokens/{token_address}/personal_info",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def register_holder_personal_info(
        request: Request,
        token_address: str,
        personal_info: RegisterPersonalInfoRequest,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Register the holder's personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Verify that the token is issued by the issuer_address
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Register Personal Info
    token_contract = IbetShareContract.get(token_address)
    try:
        personal_info_contract = PersonalInfoContract(
            db=db,
            issuer_address=issuer_address,
            contract_address=token_contract.personal_info_contract_address
        )
        personal_info_contract.register_info(
            account_address=personal_info.account_address,
            data=personal_info.dict(),
            default_value=None
        )
    except SendTransactionError:
        raise SendTransactionError("failed to register personal information")

    return


# POST: /share/tokens/{token_address}/personal_info/batch
@router.post(
    "/tokens/{token_address}/personal_info/batch",
    response_model=BatchRegisterPersonalInfoUploadResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def batch_register_personal_info(
        request: Request,
        token_address: str,
        personal_info_list: List[RegisterPersonalInfoRequest],
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Create Batch for register personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Verify that the token is issued by the issuer_address
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
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
        bulk_register_record.personal_info = personal_info.dict()
        bulk_register_record.status = 0
        db.add(bulk_register_record)

    db.commit()

    return {
        "batch_id": batch_id,
        "status": batch.status,
        "created": timezone("UTC").localize(batch.created).astimezone(local_tz).isoformat()
    }


# GET: /share/tokens/{token_address}/personal_info/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/personal_info/batch/{batch_id}",
    response_model=GetBatchRegisterPersonalInfoResponse,
    responses=get_routers_responses(422, 404)
)
def retrieve_batch_register_personal_info(
        token_address: str,
        batch_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Get Batch status for register personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
    )

    # Upload Existence Check
    batch: Optional[BatchRegisterPersonalInfoUpload] = db.query(BatchRegisterPersonalInfoUpload). \
        filter(BatchRegisterPersonalInfoUpload.upload_id == batch_id). \
        filter(BatchRegisterPersonalInfoUpload.issuer_address == issuer_address). \
        first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list = db.query(BatchRegisterPersonalInfo). \
        filter(BatchRegisterPersonalInfo.upload_id == batch_id). \
        filter(BatchRegisterPersonalInfo.token_address == token_address). \
        all()

    return GetBatchRegisterPersonalInfoResponse(
        status=batch.status,
        results=[
            BatchRegisterPersonalInfoResult(
                status=record.status,
                account_address=record.account_address,
                key_manager=record.personal_info.get("key_manager"),
                name=record.personal_info.get("name"),
                postal_code=record.personal_info.get("postal_code"),
                address=record.personal_info.get("address"),
                email=record.personal_info.get("email"),
                birth=record.personal_info.get("birth"),
                is_corporate=record.personal_info.get("is_corporate"),
                tax_category=record.personal_info.get("tax_category")
            ) for record in record_list
        ]
    )


# POST: /share/transfers
@router.post(
    "/transfers",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def transfer_ownership(
        request: Request,
        token: IbetShareTransfer,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Transfer token ownership"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Check that it is a token that has been issued.
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token.token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    try:
        IbetShareContract.transfer(
            data=token,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/transfers/{token_address}
@router.get(
    "/transfers/{token_address}",
    response_model=TransferHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_transfer_history(
        token_address: str,
        sort_item: IDXTransfersSortItem = Query(IDXTransfersSortItem.BLOCK_TIMESTAMP),
        sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)
):
    """List token transfer history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer history
    query = db.query(IDXTransfer). \
        filter(IDXTransfer.token_address == token_address)
    total = query.count()

    # NOTE: Because it don`t filter, `total` and `count` will be the same.
    count = query.count()

    # Sort
    sort_attr = getattr(IDXTransfer, sort_item.value, None)
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != IDXTransfersSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(IDXTransfer.block_timestamp))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfers = query.all()

    transfer_history = []
    for _transfer in _transfers:
        block_timestamp_utc = timezone("UTC").localize(_transfer.block_timestamp)
        transfer_history.append({
            "transaction_hash": _transfer.transaction_hash,
            "token_address": token_address,
            "from_address": _transfer.from_address,
            "to_address": _transfer.to_address,
            "amount": _transfer.amount,
            "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat()
        })

    return {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "transfer_history": transfer_history
    }


# GET: /share/transfer_approvals
@router.get(
    "/transfer_approvals",
    response_model=TransferApprovalsResponse,
    responses=get_routers_responses(422)
)
def list_transfer_approval_history(
        issuer_address: Optional[str] = Header(None),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)
):
    """List transfer approval history"""
    # Create a subquery for 'status' added IDXTransferApproval
    subquery = aliased(
        IDXTransferApproval,
        db.query(
            IDXTransferApproval,
            TransferApprovalHistory,
            case(
                [
                    (
                        and_(IDXTransferApproval.escrow_finished == True,
                             IDXTransferApproval.transfer_approved == None,
                             TransferApprovalHistory.operation_type == None),
                        1
                    ),  # EscrowFinish(escrow_finished)
                    (
                        and_(IDXTransferApproval.transfer_approved == None,
                             TransferApprovalHistory.operation_type == TransferApprovalOperationType.APPROVE.value),
                        2
                    ),  # Approve(operation completed, event synchronizing)
                    (
                        IDXTransferApproval.transfer_approved == True,
                        2
                    ),  # Approve(transferred)
                    (
                        and_(IDXTransferApproval.cancelled == None,
                             TransferApprovalHistory.operation_type == TransferApprovalOperationType.CANCEL.value),
                        3
                    ),  # Cancel(operation completed, event synchronizing)
                    (
                        IDXTransferApproval.cancelled == True,
                        3
                    ),  # Cancel(canceled)
                ],
                else_=0  # ApplyFor(unapproved)
            ).label("status")
        ).outerjoin(
            TransferApprovalHistory,
            and_(IDXTransferApproval.token_address == TransferApprovalHistory.token_address,
                 IDXTransferApproval.exchange_address == TransferApprovalHistory.exchange_address,
                 IDXTransferApproval.application_id == TransferApprovalHistory.application_id)
        ).subquery()
    )

    # Get transfer approval history
    query = db.query(Token.issuer_address,
                     subquery.token_address,
                     func.count(subquery.id),
                     func.count(or_(literal_column("status") == 0, None)),
                     func.count(or_(literal_column("status") == 1, None)),
                     func.count(or_(literal_column("status") == 2, None)),
                     func.count(or_(literal_column("status") == 3, None))). \
        join(Token, subquery.token_address == Token.token_address). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.token_status != 2)
    if issuer_address is not None:
        query = query.filter(Token.issuer_address == issuer_address)
    query = query.group_by(Token.issuer_address, subquery.token_address). \
        order_by(Token.issuer_address, subquery.token_address)
    total = query.count()

    # NOTE: Because no filtering is performed, `total` and `count` have the same value.
    count = query.count()

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfer_approvals = query.all()

    transfer_approvals = []
    for issuer_address, token_address, application_count, \
        unapproved_count, escrow_finished_count, transferred_count, canceled_count \
            in _transfer_approvals:
        transfer_approvals.append({
            "issuer_address": issuer_address,
            "token_address": token_address,
            "application_count": application_count,
            "unapproved_count": unapproved_count,
            "escrow_finished_count": escrow_finished_count,
            "transferred_count": transferred_count,
            "canceled_count": canceled_count,
        })

    return {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "transfer_approvals": transfer_approvals
    }


# GET: /share/transfer_approvals/{token_address}
@router.get(
    "/transfer_approvals/{token_address}",
    response_model=TransferApprovalHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_token_transfer_approval_history(
        token_address: str,
        from_address: Optional[str] = Query(None),
        to_address: Optional[str] = Query(None),
        status: Optional[List[int]] = Query(
            None,
            ge=0,
            le=3,
            description="0:unapproved, 1:escrow_finished, 2:transferred, 3:canceled"
        ),
        sort_item: Optional[IDXTransferApprovalsSortItem] = Query(IDXTransferApprovalsSortItem.ID),
        sort_order: Optional[int] = Query(1, ge=0, le=1, description="0:asc, 1:desc"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)
):
    """List token transfer approval history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Create a subquery for 'status' added IDXTransferApproval
    subquery = aliased(
        IDXTransferApproval,
        db.query(
            IDXTransferApproval,
            TransferApprovalHistory,
            case(
                [
                    (
                        and_(IDXTransferApproval.escrow_finished == True,
                             IDXTransferApproval.transfer_approved == None,
                             TransferApprovalHistory.operation_type == None),
                        1
                    ),  # EscrowFinish(escrow_finished)
                    (
                        and_(IDXTransferApproval.transfer_approved == None,
                             TransferApprovalHistory.operation_type == TransferApprovalOperationType.APPROVE.value),
                        2
                    ),  # Approve(operation completed, event synchronizing)
                    (
                        IDXTransferApproval.transfer_approved == True,
                        2
                    ),  # Approve(transferred)
                    (
                        and_(IDXTransferApproval.cancelled == None,
                             TransferApprovalHistory.operation_type == TransferApprovalOperationType.CANCEL.value),
                        3
                    ),  # Cancel(operation completed, event synchronizing)
                    (
                        IDXTransferApproval.cancelled == True,
                        3
                    ),  # Cancel(canceled)
                ],
                else_=0  # ApplyFor(unapproved)
            ).label("status")
        ).outerjoin(
            TransferApprovalHistory,
            and_(IDXTransferApproval.token_address == TransferApprovalHistory.token_address,
                 IDXTransferApproval.exchange_address == TransferApprovalHistory.exchange_address,
                 IDXTransferApproval.application_id == TransferApprovalHistory.application_id)
        ).subquery()
    )

    # Get transfer approval history
    query = db.query(subquery, literal_column("status")). \
        filter(subquery.token_address == token_address)
    total = query.count()

    # Search Filter
    if from_address is not None:
        query = query.filter(subquery.from_address == from_address)
    if to_address is not None:
        query = query.filter(subquery.to_address == to_address)
    if status is not None:
        query = query.filter(literal_column("status").in_(status))
    count = query.count()

    # Sort
    if sort_item != IDXTransferApprovalsSortItem.STATUS:
        sort_attr = getattr(subquery, sort_item, None)
    else:
        sort_attr = literal_column("status")
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != IDXTransferApprovalsSortItem.ID:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(subquery.id))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfer_approvals = query.all()

    transfer_approval_history = []
    for _transfer_approval, status in _transfer_approvals:
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

        application_datetime_utc = timezone("UTC").localize(_transfer_approval.application_datetime)
        application_datetime = application_datetime_utc.astimezone(local_tz).isoformat()

        application_blocktimestamp_utc = timezone("UTC").localize(_transfer_approval.application_blocktimestamp)
        application_blocktimestamp = application_blocktimestamp_utc.astimezone(local_tz).isoformat()

        if _transfer_approval.approval_datetime is not None:
            approval_datetime_utc = timezone("UTC").localize(_transfer_approval.approval_datetime)
            approval_datetime = approval_datetime_utc.astimezone(local_tz).isoformat()
        else:
            approval_datetime = None

        if _transfer_approval.approval_blocktimestamp is not None:
            approval_blocktimestamp_utc = timezone("UTC").localize(_transfer_approval.approval_blocktimestamp)
            approval_blocktimestamp = approval_blocktimestamp_utc.astimezone(local_tz).isoformat()
        else:
            approval_blocktimestamp = None

        transfer_approval_history.append({
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
            "cancelled": cancelled,
            "escrow_finished": escrow_finished,
            "transfer_approved": transfer_approved,
            "status": status,
            "issuer_cancelable": issuer_cancelable
        })

    return {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "transfer_approval_history": transfer_approval_history
    }


# POST: /share/transfer_approvals/{token_address}/{id}
@router.post(
    "/transfer_approvals/{token_address}/{id}",
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def update_transfer_approval(
        request: Request,
        token_address: str,
        id: int,
        data: UpdateTransferApprovalRequest,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)
):
    """Update on the status of a share transfer approval"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    # Authentication
    _account, decrypt_password = check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer approval history
    _transfer_approval: IDXTransferApproval | None = db.query(IDXTransferApproval). \
        filter(IDXTransferApproval.id == id). \
        filter(IDXTransferApproval.token_address == token_address). \
        first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")

    if _transfer_approval.transfer_approved is True:
        raise InvalidParameterError("already approved")
    if _transfer_approval.cancelled is True:
        raise InvalidParameterError("canceled application")
    if _transfer_approval.exchange_address != config.ZERO_ADDRESS and \
            _transfer_approval.escrow_finished is not True:
        raise InvalidParameterError("escrow has not been finished yet")
    if data.operation_type == UpdateTransferApprovalOperationType.CANCEL and \
            _transfer_approval.exchange_address != config.ZERO_ADDRESS:
        # Cancellation is possible only against approval of the transfer of a token contract.
        raise InvalidParameterError("application that cannot be canceled")

    transfer_approval_op: TransferApprovalHistory | None = db.query(TransferApprovalHistory). \
        filter(TransferApprovalHistory.token_address == _transfer_approval.token_address). \
        filter(TransferApprovalHistory.exchange_address == _transfer_approval.exchange_address). \
        filter(TransferApprovalHistory.application_id == _transfer_approval.application_id). \
        filter(TransferApprovalHistory.operation_type == data.operation_type). \
        first()
    if transfer_approval_op is not None:
        raise InvalidParameterError("duplicate operation")

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
                    "data": now
                }
                try:
                    _, tx_receipt = IbetShareContract.approve_transfer(
                        contract_address=token_address,
                        data=IbetSecurityTokenApproveTransfer(**_data),
                        tx_from=issuer_address,
                        private_key=private_key,
                    )
                except ContractRevertError as approve_transfer_err:
                    # If approveTransfer end with revert,
                    # cancelTransfer should be performed immediately.
                    # After cancelTransfer, ContractRevertError is returned.
                    try:
                        IbetShareContract.cancel_transfer(
                            contract_address=token_address,
                            data=IbetSecurityTokenCancelTransfer(**_data),
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
                _data = {
                    "escrow_id": _transfer_approval.application_id,
                    "data": now
                }
                escrow = IbetSecurityTokenEscrow(_transfer_approval.exchange_address)
                try:
                    _, tx_receipt = escrow.approve_transfer(
                        data=IbetSecurityTokenEscrowApproveTransfer(**_data),
                        tx_from=issuer_address,
                        private_key=private_key,
                    )
                except ContractRevertError:
                    # If approveTransfer end with revert, error should be thrown immediately.
                    raise
                except Exception:
                    raise SendTransactionError
        else:  # CANCEL
            _data = {
                "application_id": _transfer_approval.application_id,
                "data": now
            }
            try:
                _, tx_receipt = IbetShareContract.cancel_transfer(
                    contract_address=token_address,
                    data=IbetSecurityTokenCancelTransfer(**_data),
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
    db.add(transfer_approval_op)
    db.commit()


# GET: /share/transfer_approvals/{token_address}/{id}
@router.get(
    "/transfer_approvals/{token_address}/{id}",
    response_model=TransferApprovalTokenResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def retrieve_transfer_approval_history(
        token_address: str,
        id: int,
        db: Session = Depends(db_session)
):
    """Retrieve share token transfer approval history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE.value). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get transfer approval history
    _transfer_approval: IDXTransferApproval | None = db.query(IDXTransferApproval). \
        filter(IDXTransferApproval.id == id). \
        filter(IDXTransferApproval.token_address == token_address). \
        first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")

    _transfer_approval_op: TransferApprovalHistory | None = db.query(TransferApprovalHistory). \
        filter(TransferApprovalHistory.token_address == _transfer_approval.token_address). \
        filter(TransferApprovalHistory.exchange_address == _transfer_approval.exchange_address). \
        filter(TransferApprovalHistory.application_id == _transfer_approval.application_id). \
        first()

    status = 0
    if _transfer_approval.escrow_finished is True and \
            _transfer_approval.transfer_approved is not True and \
            _transfer_approval_op is None:
        status = 1  # EscrowFinish(escrow_finished)
    elif _transfer_approval.transfer_approved is not True and \
            _transfer_approval_op is not None and \
            _transfer_approval_op.operation_type == TransferApprovalOperationType.APPROVE.value:
        status = 2  # Approve(operation completed, event synchronizing)
    elif _transfer_approval.transfer_approved is True:
        status = 2  # Approve(transferred)
    elif _transfer_approval.cancelled is not True and \
            _transfer_approval_op is not None and \
            _transfer_approval_op.operation_type == TransferApprovalOperationType.CANCEL.value:
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

    application_datetime_utc = timezone("UTC").localize(_transfer_approval.application_datetime)
    application_datetime = application_datetime_utc.astimezone(local_tz).isoformat()

    application_blocktimestamp_utc = timezone("UTC").localize(_transfer_approval.application_blocktimestamp)
    application_blocktimestamp = application_blocktimestamp_utc.astimezone(local_tz).isoformat()

    if _transfer_approval.approval_datetime is not None:
        approval_datetime_utc = timezone("UTC").localize(_transfer_approval.approval_datetime)
        approval_datetime = approval_datetime_utc.astimezone(local_tz).isoformat()
    else:
        approval_datetime = None

    if _transfer_approval.approval_blocktimestamp is not None:
        approval_blocktimestamp_utc = timezone("UTC").localize(_transfer_approval.approval_blocktimestamp)
        approval_blocktimestamp = approval_blocktimestamp_utc.astimezone(local_tz).isoformat()
    else:
        approval_blocktimestamp = None

    history = {
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
        "cancelled": cancelled,
        "escrow_finished": escrow_finished,
        "transfer_approved": transfer_approved,
        "status": status,
        "issuer_cancelable": issuer_cancelable
    }

    return history


# POST: /share/bulk_transfer
@router.post(
    "/bulk_transfer",
    response_model=BulkTransferUploadIdResponse,
    responses=get_routers_responses(422, AuthorizationError, InvalidParameterError, 401)
)
def bulk_transfer_ownership(
        request: Request,
        tokens: List[IbetShareTransfer],
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Bulk transfer token ownership"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value)
    )

    if len(tokens) < 1:
        raise InvalidParameterError("list length must be at least one")

    # Authentication
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Verify that the tokens are issued by the issuer_address
    for _token in tokens:
        _issued_token = db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE.value). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_address == _token.token_address). \
            filter(Token.token_status != 2). \
            first()
        if _issued_token is None:
            raise InvalidParameterError(f"token not found: {_token.token_address}")
        if _issued_token.token_status == 0:
            raise InvalidParameterError(f"this token is temporarily unavailable: {_token.token_address}")

    # generate upload_id
    upload_id = uuid.uuid4()

    # add bulk transfer upload record
    _bulk_transfer_upload = BulkTransferUpload()
    _bulk_transfer_upload.upload_id = upload_id
    _bulk_transfer_upload.issuer_address = issuer_address
    _bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
    _bulk_transfer_upload.status = 0
    db.add(_bulk_transfer_upload)

    # add bulk transfer records
    for _token in tokens:
        _bulk_transfer = BulkTransfer()
        _bulk_transfer.issuer_address = issuer_address
        _bulk_transfer.upload_id = upload_id
        _bulk_transfer.token_address = _token.token_address
        _bulk_transfer.token_type = TokenType.IBET_SHARE.value
        _bulk_transfer.from_address = _token.from_address
        _bulk_transfer.to_address = _token.to_address
        _bulk_transfer.amount = _token.amount
        _bulk_transfer.status = 0
        db.add(_bulk_transfer)

    db.commit()

    return {"upload_id": str(upload_id)}


# GET: /share/bulk_transfer
@router.get(
    "/bulk_transfer",
    response_model=List[BulkTransferUploadResponse],
    responses=get_routers_responses(422)
)
def list_bulk_transfer_upload(
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """List bulk transfer uploads"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get bulk transfer upload list
    if issuer_address is None:
        _uploads = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.token_type == TokenType.IBET_SHARE.value). \
            order_by(BulkTransferUpload.issuer_address). \
            all()
    else:
        _uploads = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.issuer_address == issuer_address). \
            filter(BulkTransferUpload.token_type == TokenType.IBET_SHARE.value). \
            all()

    uploads = []
    for _upload in _uploads:
        created_utc = timezone("UTC").localize(_upload.created)
        uploads.append({
            "issuer_address": _upload.issuer_address,
            "token_type": _upload.token_type,
            "upload_id": _upload.upload_id,
            "status": _upload.status,
            "created": created_utc.astimezone(local_tz).isoformat()
        })

    return uploads


# GET: /share/bulk_transfer/{upload_id}
@router.get(
    "/bulk_transfer/{upload_id}",
    response_model=List[BulkTransferResponse],
    responses=get_routers_responses(422, 404)
)
def retrieve_bulk_transfer(
        upload_id: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve a bulk transfer upload"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get bulk transfer upload list
    if issuer_address is None:
        _bulk_transfers = db.query(BulkTransfer). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.token_type == TokenType.IBET_SHARE.value). \
            order_by(BulkTransfer.issuer_address). \
            all()
    else:
        _bulk_transfers = db.query(BulkTransfer). \
            filter(BulkTransfer.issuer_address == issuer_address). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.token_type == TokenType.IBET_SHARE.value). \
            all()

    bulk_transfers = []
    for _bulk_transfer in _bulk_transfers:
        bulk_transfers.append({
            "issuer_address": _bulk_transfer.issuer_address,
            "token_type": _bulk_transfer.token_type,
            "upload_id": _bulk_transfer.upload_id,
            "token_address": _bulk_transfer.token_address,
            "from_address": _bulk_transfer.from_address,
            "to_address": _bulk_transfer.to_address,
            "amount": _bulk_transfer.amount,
            "status": _bulk_transfer.status
        })

    if len(bulk_transfers) < 1:
        raise HTTPException(status_code=404, detail="bulk transfer not found")

    return bulk_transfers
