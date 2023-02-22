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
    literal_column,
    cast,
    String,
    literal,
    null,
    column
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
    # Request
    IbetStraightBondCreate,
    IbetStraightBondUpdate,
    IbetStraightBondTransfer,
    IbetStraightBondAdditionalIssue,
    IbetStraightBondRedeem,
    RegisterPersonalInfoRequest,
    IbetStraightBondScheduledUpdate,
    UpdateTransferApprovalOperationType,
    UpdateTransferApprovalRequest,
    ListTransferHistorySortItem,
    ListTransferHistoryQuery,
    ListAllTokenLockEventsQuery,
    ListAllTokenLockEventsSortItem,
    LockEventCategory,
    # Response
    IbetStraightBondResponse,
    TokenAddressResponse,
    HolderResponse,
    HolderCountResponse,
    TransferHistoryResponse,
    BulkTransferUploadIdResponse,
    BulkTransferUploadResponse,
    BulkTransferResponse,
    ScheduledEventIdResponse,
    ScheduledEventResponse,
    TransferApprovalsResponse,
    TransferApprovalHistoryResponse,
    TransferApprovalTokenResponse,
    BatchIssueRedeemUploadIdResponse,
    GetBatchIssueRedeemResponse,
    ListBatchIssueRedeemUploadResponse,
    IssueRedeemHistoryResponse,
    BatchRegisterPersonalInfoUploadResponse,
    ListBatchRegisterPersonalInfoUploadResponse,
    GetBatchRegisterPersonalInfoResponse,
    ListAllTokenLockEventsResponse
)
from app.model.db import (
    Account,
    Token,
    TokenType,
    UpdateToken,
    IDXPosition,
    IDXLockedPosition,
    IDXPersonalInfo,
    BulkTransfer,
    BulkTransferUpload,
    IDXTransfer,
    IDXTransferApproval,
    IDXTransferApprovalsSortItem,
    IDXIssueRedeem,
    IDXIssueRedeemEventType,
    IDXIssueRedeemSortItem,
    ScheduledEvents,
    UTXO,
    BatchIssueRedeemUpload,
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    BatchRegisterPersonalInfo,
    TransferApprovalHistory,
    TransferApprovalOperationType,
    IDXLock,
    IDXUnlock
)
from app.model.blockchain import (
    IbetStraightBondContract,
    TokenListContract,
    PersonalInfoContract,
    IbetSecurityTokenEscrow
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    UpdateParams,
    TransferParams,
    AdditionalIssueParams,
    RedeemParams,
    ApproveTransferParams,
    CancelTransferParams
)
from app.model.blockchain.tx_params.ibet_security_token_escrow import (
    ApproveTransferParams as EscrowApproveTransferParams
)
from app.utils.fastapi import json_response
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
    prefix="/bond",
    tags=["bond"],
)

LOG = log.get_logger()
local_tz = timezone(config.TZ)


# POST: /bond/tokens
@router.post(
    "/tokens",
    response_model=TokenAddressResponse,
    responses=get_routers_responses(422, 401, AuthorizationError, SendTransactionError, ContractRevertError)
)
def issue_token(
        request: Request,
        token: IbetStraightBondCreate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        auth_token: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Issue ibetStraightBond token"""

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
    _redemption_date = token.redemption_date if token.redemption_date is not None else ""
    _redemption_value = token.redemption_value if token.redemption_value is not None else 0
    _return_date = token.return_date if token.return_date is not None else ""
    _return_amount = token.return_amount if token.return_amount is not None else ""
    arguments = [
        token.name,
        _symbol,
        token.total_supply,
        token.face_value,
        _redemption_date,
        _redemption_value,
        _return_date,
        _return_amount,
        token.purpose
    ]
    try:
        contract_address, abi, tx_hash = IbetStraightBondContract().create(
            args=arguments,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Check need update
    update_items = [
        "interest_rate",
        "interest_payment_date",
        "transferable",
        "status",
        "is_offering",
        "is_redeemed",
        "tradable_exchange_contract_address",
        "personal_info_contract_address",
        "contact_information",
        "privacy_policy",
        "transfer_approval_required"
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
            TokenListContract(config.TOKEN_LIST_CONTRACT_ADDRESS).register(
                token_address=contract_address,
                token_template=TokenType.IBET_STRAIGHT_BOND.value,
                tx_from=issuer_address,
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
    _token.type = TokenType.IBET_STRAIGHT_BOND.value
    _token.tx_hash = tx_hash
    _token.issuer_address = issuer_address
    _token.token_address = contract_address
    _token.abi = abi
    _token.token_status = token_status
    db.add(_token)

    db.commit()

    return json_response({
        "token_address": _token.token_address,
        "token_status": token_status
    })


# GET: /bond/tokens
@router.get(
    "/tokens",
    response_model=List[IbetStraightBondResponse],
    responses=get_routers_responses(422)
)
def list_all_tokens(
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """List all issued tokens"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get issued token list
    if issuer_address is None:
        tokens = db.query(Token). \
            filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
            order_by(Token.id). \
            all()
    else:
        tokens = db.query(Token). \
            filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
            filter(Token.issuer_address == issuer_address). \
            order_by(Token.id). \
            all()

    bond_tokens = []
    for token in tokens:
        # Get contract data
        bond_token = IbetStraightBondContract(token.token_address).get().__dict__
        issue_datetime_utc = timezone("UTC").localize(token.created)
        bond_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
        bond_token["token_status"] = token.token_status
        bond_token.pop("contract_name")
        bond_tokens.append(bond_token)

    return json_response(bond_tokens)


# GET: /bond/tokens/{token_address}
@router.get(
    "/tokens/{token_address}",
    response_model=IbetStraightBondResponse,
    responses=get_routers_responses(404, InvalidParameterError)
)
def retrieve_token(
        token_address: str,
        db: Session = Depends(db_session)):
    """Retrieve token"""
    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get contract data
    bond_token = IbetStraightBondContract(token_address).get().__dict__
    issue_datetime_utc = timezone("UTC").localize(_token.created)
    bond_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
    bond_token["token_status"] = _token.token_status
    bond_token.pop("contract_name")

    return json_response(bond_token)


# POST: /bond/tokens/{token_address}
@router.post(
    "/tokens/{token_address}",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def update_token(
        request: Request,
        token_address: str,
        token: IbetStraightBondUpdate,
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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
        IbetStraightBondContract(token_address).update(
            data=UpdateParams(**token.dict()),
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    db.commit()
    return


# GET: /bond/tokens/{token_address}/additional_issue
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
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

    return json_response({
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "history": history
    })


# POST: /bond/tokens/{token_address}/additional_issue
@router.post(
    "/tokens/{token_address}/additional_issue",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def additional_issue(
        request: Request,
        token_address: str,
        data: IbetStraightBondAdditionalIssue,
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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
        IbetStraightBondContract(token_address).additional_issue(
            data=AdditionalIssueParams(**data.dict()),
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /bond/tokens/{token_address}/additional_issue/batch
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
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
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
    return json_response(resp)


# POST: /bond/tokens/{token_address}/additional_issue/batch
@router.post(
    "/tokens/{token_address}/additional_issue/batch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def additional_issue_in_batch(
        request: Request,
        token_address: str,
        data: List[IbetStraightBondAdditionalIssue],
        issuer_address: str = Header(...),
        auth_token: Optional[str] = Header(None),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Additional issue (Batch)"""

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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    db.commit()

    return json_response({
        "batch_id": str(upload_id)
    })


# GET: /bond/tokens/{token_address}/additional_issue/batch/{batch_id}
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
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(BatchIssueRedeemUpload.token_address == token_address). \
        filter(BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.ISSUE.value). \
        first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
        filter(BatchIssueRedeem.upload_id == batch_id). \
        all()

    return json_response({
        "processed": batch.processed,
        "results": [
            {
                "account_address": record.account_address,
                "amount": record.amount,
                "status": record.status
            } for record in record_list
        ]
    })


# GET: /bond/tokens/{token_address}/redeem
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
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

    return json_response({
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "history": history
    })


# POST: /bond/tokens/{token_address}/redeem
@router.post(
    "/tokens/{token_address}/redeem",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def redeem_token(
        request: Request,
        token_address: str,
        data: IbetStraightBondRedeem,
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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
        IbetStraightBondContract(token_address).redeem(
            data=RedeemParams(**data.dict()),
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /bond/tokens/{token_address}/redeem/batch
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
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
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
    return json_response(resp)


# POST: /bond/tokens/{token_address}/redeem/batch
@router.post(
    "/tokens/{token_address}/redeem/batch",
    response_model=BatchIssueRedeemUploadIdResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def redeem_token_in_batch(
        request: Request,
        token_address: str,
        data: List[IbetStraightBondRedeem],
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    db.commit()

    return json_response({
        "batch_id": str(upload_id)
    })


# GET: /bond/tokens/{token_address}/redeem/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/redeem/batch/{batch_id}",
    response_model=GetBatchIssueRedeemResponse,
    responses=get_routers_responses(422, 404)
)
def retrieve_batch_redeem(
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
        filter(BatchIssueRedeemUpload.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(BatchIssueRedeemUpload.token_address == token_address). \
        filter(BatchIssueRedeemUpload.category == BatchIssueRedeemProcessingCategory.REDEEM.value). \
        first()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    # Get Batch Records
    record_list: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
        filter(BatchIssueRedeem.upload_id == batch_id). \
        all()

    return json_response({
        "processed": batch.processed,
        "results": [
            {
                "account_address": record.account_address,
                "amount": record.amount,
                "status": record.status
            } for record in record_list
        ]
    })


# GET: /bond/tokens/{token_address}/scheduled_events
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
            filter(ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
            filter(ScheduledEvents.token_address == token_address). \
            order_by(ScheduledEvents.id). \
            all()
    else:
        _token_events = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
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
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
                "event_type": _token_event.event_type,
                "status": _token_event.status,
                "data": _token_event.data,
                "created": created_utc.astimezone(local_tz).isoformat()
            }
        )
    return json_response(token_events)


# POST: /bond/tokens/{token_address}/scheduled_events
@router.post(
    "/tokens/{token_address}/scheduled_events",
    response_model=ScheduledEventIdResponse,
    responses=get_routers_responses(422, 401, 404, AuthorizationError, InvalidParameterError)
)
def schedule_new_update_event(
        request: Request,
        token_address: str,
        event_data: IbetStraightBondScheduledUpdate,
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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
    _scheduled_event.token_type = TokenType.IBET_STRAIGHT_BOND.value
    _scheduled_event.scheduled_datetime = event_data.scheduled_datetime
    _scheduled_event.event_type = event_data.event_type
    _scheduled_event.data = event_data.data.dict()
    _scheduled_event.status = 0
    db.add(_scheduled_event)
    db.commit()

    return json_response({
        "scheduled_event_id": _scheduled_event.event_id
    })


# GET: /bond/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.get(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse,
    responses=get_routers_responses(404)
)
def retrieve_token_event(
        scheduled_event_id: str,
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve a scheduled token event"""

    if issuer_address is None:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
            filter(ScheduledEvents.event_id == scheduled_event_id). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    else:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
            filter(ScheduledEvents.event_id == scheduled_event_id). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="event not found")

    scheduled_datetime_utc = timezone("UTC").localize(_token_event.scheduled_datetime)
    created_utc = timezone("UTC").localize(_token_event.created)
    return json_response({
        "scheduled_event_id": _token_event.event_id,
        "token_address": token_address,
        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data,
        "created": created_utc.astimezone(local_tz).isoformat()
    })


# DELETE: /bond/tokens/{token_address}/scheduled_events/{scheduled_event_id}
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

    # Authorization
    check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token
    )

    # Delete an event
    _token_event = db.query(ScheduledEvents). \
        filter(ScheduledEvents.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
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
        "token_type": TokenType.IBET_STRAIGHT_BOND.value,
        "scheduled_datetime": scheduled_datetime_utc.astimezone(local_tz).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data,
        "created": created_utc.astimezone(local_tz).isoformat()
    }

    db.delete(_token_event)
    db.commit()
    return json_response(rtn)


# GET: /bond/tokens/{token_address}/holders
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
    """List all bond token holders"""

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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    query = db.query(IDXPosition, func.sum(IDXLockedPosition.value)). \
        outerjoin(
            IDXLockedPosition,
            and_(IDXLockedPosition.token_address == IDXPosition.token_address,
                 IDXLockedPosition.account_address == IDXPosition.account_address)
        ). \
        filter(IDXPosition.token_address == token_address).\
        group_by(IDXPosition.id, IDXLockedPosition.token_address, IDXLockedPosition.account_address)

    if not include_former_holder:
        query = query.filter(or_(
            IDXPosition.balance != 0,
            IDXPosition.exchange_balance != 0,
            IDXPosition.pending_transfer != 0,
            IDXPosition.exchange_commitment != 0,
            IDXLockedPosition.value != 0
        ))

    _holders = query.order_by(IDXPosition.id).all()

    # Get personal information
    _personal_info_list = db.query(IDXPersonalInfo). \
        filter(IDXPersonalInfo.issuer_address == issuer_address). \
        order_by(IDXPersonalInfo.id). \
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
    for _position, _locked in _holders:
        _personal_info = _personal_info_dict.get(
            _position.account_address,
            personal_info_default
        )
        holders.append({
            "account_address": _position.account_address,
            "personal_information": _personal_info,
            "balance": _position.balance,
            "exchange_balance": _position.exchange_balance,
            "exchange_commitment": _position.exchange_commitment,
            "pending_transfer": _position.pending_transfer,
            "locked": _locked if _locked is not None else 0
        })

    return json_response(holders)


# GET: /bond/tokens/{token_address}/holders/count
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    _count: int = db.query(IDXPosition, func.sum(IDXLockedPosition.value)). \
        outerjoin(
            IDXLockedPosition,
            and_(IDXLockedPosition.token_address == IDXPosition.token_address,
                 IDXLockedPosition.account_address == IDXPosition.account_address)
        ). \
        filter(IDXPosition.token_address == token_address). \
        filter(
            or_(IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0)
        ). \
        group_by(IDXPosition.id, IDXLockedPosition.token_address, IDXLockedPosition.account_address). \
        count()

    return json_response({
        "count": _count
    })


# GET: /bond/tokens/{token_address}/holders/{account_address}
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
    """Retrieve bond token holder"""

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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Get Holders
    _holder = db.query(IDXPosition, func.sum(IDXLockedPosition.value)). \
        outerjoin(
            IDXLockedPosition,
            and_(IDXLockedPosition.token_address == IDXPosition.token_address,
                 IDXLockedPosition.account_address == IDXPosition.account_address)
        ). \
        filter(IDXPosition.token_address == token_address). \
        filter(IDXPosition.account_address == account_address). \
        group_by(IDXPosition.id, IDXLockedPosition.token_address, IDXLockedPosition.account_address). \
        first()

    if _holder is None:
        balance = 0
        exchange_balance = 0
        exchange_commitment = 0
        pending_transfer = 0
        locked = 0
    else:
        balance = _holder[0].balance
        exchange_balance = _holder[0].exchange_balance
        exchange_commitment = _holder[0].exchange_commitment
        pending_transfer = _holder[0].pending_transfer
        locked = _holder[1]

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
        "pending_transfer": pending_transfer,
        "locked": locked if locked is not None else 0
    }

    return json_response(holder)


# POST: /bond/tokens/{token_address}/personal_info
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    # Register Personal Info
    token_contract = IbetStraightBondContract(token_address).get()
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


# GET: /bond/tokens/{token_address}/personal_info/batch
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response({
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "uploads": uploads
    })


# POST: /bond/tokens/{token_address}/personal_info/batch
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response({
        "batch_id": batch_id,
        "status": batch.status,
        "created": timezone("UTC").localize(batch.created).astimezone(local_tz).isoformat()
    })


# GET: /bond/tokens/{token_address}/personal_info/batch/{batch_id}
@router.get(
    "/tokens/{token_address}/personal_info/batch/{batch_id}",
    response_model=GetBatchRegisterPersonalInfoResponse,
    responses=get_routers_responses(422, 401, 404)
)
def retrieve_batch_register_personal_info(
        token_address: str,
        batch_id: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Get Batch status for register personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address)
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

    return json_response({
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
                "tax_category": record.personal_info.get("tax_category")
            } for record in record_list
        ]
    })


# POST: /bond/transfers
@router.post(
    "/transfers",
    response_model=None,
    responses=get_routers_responses(422, 401, AuthorizationError, InvalidParameterError, SendTransactionError, ContractRevertError)
)
def transfer_ownership(
        request: Request,
        token: IbetStraightBondTransfer,
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

    # Verify that the token is issued by the issuer_address
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token.token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise InvalidParameterError("token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("this token is temporarily unavailable")

    try:
        IbetStraightBondContract(token.token_address).transfer(
            data=TransferParams(**token.dict()),
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /bond/transfers/{token_address}
@router.get(
    "/transfers/{token_address}",
    response_model=TransferHistoryResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def list_transfer_history(
    token_address: str,
    request_query: ListTransferHistoryQuery = Depends(),
    db: Session = Depends(db_session)
):
    """List token transfer history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    if request_query.source_event is not None:
        query = query.filter(IDXTransfer.source_event == request_query.source_event.value)
    if request_query.data is not None:
        query = query.filter(cast(IDXTransfer.data, String).like("%" + request_query.data + "%"))
    count = query.count()

    # Sort
    sort_attr = getattr(IDXTransfer, request_query.sort_item.value, None)
    if request_query.sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if request_query.sort_item != ListTransferHistorySortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(IDXTransfer.block_timestamp))

    # Pagination
    if request_query.limit is not None:
        query = query.limit(request_query.limit)
    if request_query.offset is not None:
        query = query.offset(request_query.offset)
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
            "source_event": _transfer.source_event,
            "data": _transfer.data,
            "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat()
        })

    return json_response({
        "result_set": {
            "count": count,
            "offset": request_query.offset,
            "limit": request_query.limit,
            "total": total
        },
        "transfer_history": transfer_history
    })


# GET: /bond/transfer_approvals
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response({
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "transfer_approvals": transfer_approvals
    })


# GET: /bond/transfer_approvals/{token_address}
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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response({
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "transfer_approval_history": transfer_approval_history
    })


# POST: /bond/transfer_approvals/{token_address}/{id}
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
    """Update on the status of a bond transfer approval"""

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
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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
                    _, tx_receipt = IbetStraightBondContract(token_address).approve_transfer(
                        data=ApproveTransferParams(**_data),
                        tx_from=issuer_address,
                        private_key=private_key,
                    )
                except ContractRevertError as approve_transfer_err:
                    # If approveTransfer end with revert,
                    # cancelTransfer should be performed immediately.
                    # After cancelTransfer, ContractRevertError is returned.
                    try:
                        IbetStraightBondContract(token_address).cancel_transfer(
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
                _data = {
                    "escrow_id": _transfer_approval.application_id,
                    "data": now
                }
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
            _data = {
                "application_id": _transfer_approval.application_id,
                "data": now
            }
            try:
                _, tx_receipt = IbetStraightBondContract(token_address).cancel_transfer(
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
    db.add(transfer_approval_op)
    db.commit()


# GET: /bond/transfer_approvals/{token_address}/{id}
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
    """Retrieve bond token transfer approval history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response(history)


# POST: /bond/bulk_transfer
@router.post(
    "/bulk_transfer",
    response_model=BulkTransferUploadIdResponse,
    responses=get_routers_responses(422, AuthorizationError, InvalidParameterError, 401)
)
def bulk_transfer_ownership(
        request: Request,
        tokens: List[IbetStraightBondTransfer],
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
            filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value). \
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
    _bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
    _bulk_transfer_upload.status = 0
    db.add(_bulk_transfer_upload)

    # add bulk transfer records
    for _token in tokens:
        _bulk_transfer = BulkTransfer()
        _bulk_transfer.issuer_address = issuer_address
        _bulk_transfer.upload_id = upload_id
        _bulk_transfer.token_address = _token.token_address
        _bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _bulk_transfer.from_address = _token.from_address
        _bulk_transfer.to_address = _token.to_address
        _bulk_transfer.amount = _token.amount
        _bulk_transfer.status = 0
        db.add(_bulk_transfer)

    db.commit()

    return json_response({
        "upload_id": str(upload_id)
    })


# GET: /bond/bulk_transfer
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
            filter(BulkTransferUpload.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
            order_by(BulkTransferUpload.issuer_address). \
            all()
    else:
        _uploads = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.issuer_address == issuer_address). \
            filter(BulkTransferUpload.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response(uploads)


# GET: /bond/bulk_transfer/{upload_id}
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
            filter(BulkTransfer.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
            order_by(BulkTransfer.issuer_address). \
            all()
    else:
        _bulk_transfers = db.query(BulkTransfer). \
            filter(BulkTransfer.issuer_address == issuer_address). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.token_type == TokenType.IBET_STRAIGHT_BOND.value). \
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

    return json_response(bulk_transfers)


# GET: /bond/tokens/{token_address}/lock_events
@router.get(
    "/tokens/{token_address}/lock_events",
    summary="List all lock/unlock events related to given bond token",
    response_model=ListAllTokenLockEventsResponse,
    responses=get_routers_responses(422)
)
def list_all_lock_events_by_bond(
    token_address: str,
    issuer_address: Optional[str] = Header(None),
    request_query: ListAllTokenLockEventsQuery = Depends(),
    db: Session = Depends(db_session)
):
    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Request parameters
    offset = request_query.offset
    limit = request_query.limit
    sort_item = request_query.sort_item
    sort_order = request_query.sort_order

    # Base query
    query_lock = (
        db.query(
            literal(value=LockEventCategory.Lock.value, type_=String).label("category"),
            IDXLock.transaction_hash.label("transaction_hash"),
            IDXLock.token_address.label("token_address"),
            IDXLock.lock_address.label("lock_address"),
            IDXLock.account_address.label("account_address"),
            null().label("recipient_address"),
            IDXLock.value.label("value"),
            IDXLock.data.label("data"),
            IDXLock.block_timestamp.label("block_timestamp"),
            Token
        ).
        join(Token, IDXLock.token_address == Token.token_address).
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value).
        filter(Token.token_address == token_address).
        filter(Token.token_status != 2)
    )
    if issuer_address is not None:
        query_lock = query_lock.filter(Token.issuer_address == issuer_address)

    query_unlock = (
        db.query(
            literal(value=LockEventCategory.Unlock.value, type_=String).label("category"),
            IDXUnlock.transaction_hash.label("transaction_hash"),
            IDXUnlock.token_address.label("token_address"),
            IDXUnlock.lock_address.label("lock_address"),
            IDXUnlock.account_address.label("account_address"),
            IDXUnlock.recipient_address.label("recipient_address"),
            IDXUnlock.value.label("value"),
            IDXUnlock.data.label("data"),
            IDXUnlock.block_timestamp.label("block_timestamp"),
            Token
        ).
        join(Token, IDXUnlock.token_address == Token.token_address).
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND.value).
        filter(Token.token_address == token_address).
        filter(Token.token_status != 2)
    )
    if issuer_address is not None:
        query_unlock = query_unlock.filter(Token.issuer_address == issuer_address)

    total = query_lock.count() + query_unlock.count()

    # Filter
    match request_query.category:
        case LockEventCategory.Lock.value:
            query = query_lock
        case LockEventCategory.Unlock.value:
            query = query_unlock
        case _:
            query = query_lock.union_all(query_unlock)

    if request_query.account_address is not None:
        query = query.filter(column("account_address") == request_query.account_address)
    if request_query.lock_address is not None:
        query = query.filter(column("lock_address") == request_query.lock_address)
    if request_query.recipient_address is not None:
        query = query.filter(column("recipient_address") == request_query.recipient_address)

    count = query.count()

    # Sort
    sort_attr = column(sort_item)
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))

    if sort_item != ListAllTokenLockEventsSortItem.block_timestamp.value:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(column(ListAllTokenLockEventsSortItem.block_timestamp.value)))

    # Pagination
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    lock_events = query.all()

    resp_data = []
    for lock_event in lock_events:
        _token = lock_event[9]
        _bond = IbetStraightBondContract(_token.token_address).get()
        token_name = _bond.name

        block_timestamp_utc = timezone("UTC").localize(lock_event[8])
        resp_data.append({
            "category": lock_event[0],
            "transaction_hash": lock_event[1],
            "issuer_address": _token.issuer_address,
            "token_address": lock_event[2],
            "token_type": _token.type,
            "token_name": token_name,
            "lock_address": lock_event[3],
            "account_address": lock_event[4],
            "recipient_address": lock_event[5],
            "value": lock_event[6],
            "data": lock_event[7],
            "block_timestamp": block_timestamp_utc.astimezone(local_tz).isoformat()
        })

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total
        },
        "events": resp_data
    }
    return json_response(data)
