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
    literal_column
)
from sqlalchemy.orm import (
    Session,
    aliased
)
from eth_keyfile import decode_keyfile_json
from pytz import timezone

import config
from app.database import db_session
from app.model.schema import (
    IbetShareCreate,
    IbetShareUpdate,
    IbetShareTransfer,
    IbetShareAdd,
    IbetShareResponse,
    TokenAddressResponse,
    HolderResponse,
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
    IbetSecurityTokenApproveTransfer,
    IbetSecurityTokenCancelTransfer,
    IbetSecurityTokenEscrowApproveTransfer
)
from app.model.schema.types import (
    TransfersSortItem,
    TransferApprovalsSortItem
)
from app.utils.check_utils import (
    validate_headers,
    address_is_valid_address,
    eoa_password_is_required,
    eoa_password_is_encrypted_value,
    check_auth
)
from app.utils.docs_utils import get_routers_responses
from app.model.db import (
    Account,
    Token,
    TokenType,
    AdditionalTokenInfo,
    UpdateToken,
    IDXPosition,
    IDXPersonalInfo,
    BulkTransfer,
    BulkTransferUpload,
    IDXTransfer,
    IDXTransferApproval,
    ScheduledEvents
)
from app.model.blockchain import (
    IbetShareContract,
    TokenListContract,
    PersonalInfoContract,
    IbetSecurityTokenEscrow
)
from app.exceptions import (
    InvalidParameterError,
    SendTransactionError
)

router = APIRouter(
    prefix="/share",
    tags=["share"],
)

local_tz = timezone(config.TZ)


# POST: /share/tokens
@router.post(
    "/tokens",
    response_model=TokenAddressResponse,
    responses=get_routers_responses(422, 401, SendTransactionError)
)
def issue_token(
        request: Request,
        token: IbetShareCreate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Issue ibetShare token"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Authentication
    _account, decrypt_password = check_auth(issuer_address, eoa_password, db, request)

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
        int(_dividends * 100),
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
    except SendTransactionError:
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
        _update_token.type = TokenType.IBET_SHARE
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
                token_template=TokenType.IBET_SHARE,
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

        token_status = 1  # succeeded

    # Register token data
    _token = Token()
    _token.type = TokenType.IBET_SHARE
    _token.tx_hash = tx_hash
    _token.issuer_address = issuer_address
    _token.token_address = contract_address
    _token.abi = abi
    _token.token_status = token_status
    db.add(_token)

    # Register additional token info data
    if token.is_manual_transfer_approval is not None:
        _additional_info = AdditionalTokenInfo()
        _additional_info.token_address = contract_address
        _additional_info.is_manual_transfer_approval = token.is_manual_transfer_approval
        db.add(_additional_info)

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
            filter(Token.type == TokenType.IBET_SHARE). \
            all()
    else:
        tokens = db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE). \
            filter(Token.issuer_address == issuer_address). \
            all()

    share_tokens = []
    for token in tokens:
        # Get contract data
        share_token = IbetShareContract.get(contract_address=token.token_address).__dict__
        issue_datetime_utc = timezone("UTC").localize(token.created)
        share_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
        share_token["token_status"] = token.token_status

        # Set additional info
        _additional_info = db.query(AdditionalTokenInfo). \
            filter(AdditionalTokenInfo.token_address == token.token_address). \
            first()
        is_manual_transfer_approval = False
        if _additional_info is not None and _additional_info.is_manual_transfer_approval is not None:
            is_manual_transfer_approval = _additional_info.is_manual_transfer_approval
        share_token["is_manual_transfer_approval"] = is_manual_transfer_approval

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
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Get contract data
    share_token = IbetShareContract.get(contract_address=token_address).__dict__
    issue_datetime_utc = timezone("UTC").localize(_token.created)
    share_token["issue_datetime"] = issue_datetime_utc.astimezone(local_tz).isoformat()
    share_token["token_status"] = _token.token_status

    # Set additional info
    _additional_info = db.query(AdditionalTokenInfo). \
        filter(AdditionalTokenInfo.token_address == token_address). \
        first()
    is_manual_transfer_approval = False
    if _additional_info is not None and _additional_info.is_manual_transfer_approval is not None:
        is_manual_transfer_approval = _additional_info.is_manual_transfer_approval
    share_token["is_manual_transfer_approval"] = is_manual_transfer_approval

    return share_token


# POST: /share/tokens/{token_address}
@router.post(
    "/tokens/{token_address}",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, InvalidParameterError, SendTransactionError)
)
def update_token(
        request: Request,
        token_address: str,
        token: IbetShareUpdate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Update a token"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Authentication
    _account, decrypt_password = check_auth(issuer_address, eoa_password, db, request)

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

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

    # Update or Register additional token info data
    if token.is_manual_transfer_approval is not None:
        _additional_info = db.query(AdditionalTokenInfo). \
            filter(AdditionalTokenInfo.token_address == token_address). \
            first()
        if _additional_info is None:
            _additional_info = AdditionalTokenInfo()
            _additional_info.token_address = token_address
        _additional_info.is_manual_transfer_approval = token.is_manual_transfer_approval
        db.merge(_additional_info)

    db.commit()
    return


# POST: /share/tokens/{token_address}/add
@router.post(
    "/tokens/{token_address}/add",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, InvalidParameterError, SendTransactionError)
)
def additional_issue(
        request: Request,
        token_address: str,
        token: IbetShareAdd,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Add token"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Authentication
    _account, decrypt_password = check_auth(issuer_address, eoa_password, db, request)

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Send transaction
    try:
        IbetShareContract.add_supply(
            contract_address=token_address,
            data=token,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


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
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
            filter(ScheduledEvents.token_address == token_address). \
            order_by(ScheduledEvents.id). \
            all()
    else:
        _token_events = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
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
                "token_type": TokenType.IBET_SHARE,
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
    responses=get_routers_responses(422, 401, 404, InvalidParameterError)
)
def schedule_new_update_event(
        request: Request,
        token_address: str,
        event_data: IbetShareScheduledUpdate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Register a new update event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value])
    )

    # Authentication
    check_auth(issuer_address, eoa_password, db, request)

    # Verify that the token is issued by the issuer
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Register an event
    _scheduled_event = ScheduledEvents()
    _scheduled_event.event_id = str(uuid.uuid4())
    _scheduled_event.issuer_address = issuer_address
    _scheduled_event.token_address = token_address
    _scheduled_event.token_type = TokenType.IBET_SHARE
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
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
            filter(ScheduledEvents.event_id == scheduled_event_id). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    else:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
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
        "token_type": TokenType.IBET_SHARE,
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
    responses=get_routers_responses(422, 401, 404)
)
def delete_scheduled_event(
        request: Request,
        token_address: str,
        scheduled_event_id: str,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Delete a scheduled event"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value])
    )

    # Authentication
    check_auth(issuer_address, eoa_password, db, request)

    # Delete an event
    _token_event = db.query(ScheduledEvents). \
        filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
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
        "token_type": TokenType.IBET_SHARE,
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
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Get Holders
    _holders = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address). \
        order_by(IDXPosition.id). \
        all()

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
        "birth": None
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
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

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
        "birth": None
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
    responses=get_routers_responses(422, 401, 404, InvalidParameterError, SendTransactionError)
)
def modify_holder_personal_info(
        request: Request,
        token_address: str,
        account_address: str,
        personal_info: ModifyPersonalInfoRequest,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Modify the holder's personal information"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value])
    )

    # Authentication
    check_auth(issuer_address, eoa_password, db, request)

    # Verify that the token is issued by the issuer_address
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

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
            data=personal_info.dict()
        )
    except SendTransactionError:
        raise SendTransactionError("failed to modify personal information")

    return


# POST: /share/transfers
@router.post(
    "/transfers",
    response_model=None,
    responses=get_routers_responses(422, 401, 404, InvalidParameterError, SendTransactionError)
)
def transfer_ownership(
        request: Request,
        token: IbetShareTransfer,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Transfer token ownership"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Authentication
    _account, decrypt_password = check_auth(issuer_address, eoa_password, db, request)

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Check that it is a token that has been issued.
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token.token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

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
        sort_item: TransfersSortItem = Query(TransfersSortItem.BLOCK_TIMESTAMP),
        sort_order: int = Query(1, ge=0, le=1, description="0:asc, 1:desc"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)
):
    """List token transfer history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Get transfer history
    query = db.query(IDXTransfer). \
        filter(IDXTransfer.token_address == token_address)
    total = query.count()

    # Sort
    sort_attr = getattr(IDXTransfer, sort_item.value, None)
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != TransfersSortItem.BLOCK_TIMESTAMP:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(IDXTransfer.block_timestamp))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfers = query.all()
    count = query.count()

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
    case_status = case(
        [(and_(IDXTransferApproval.transfer_approved == True,
               IDXTransferApproval.approval_blocktimestamp == None),
          1),  # approved
         (and_(IDXTransferApproval.transfer_approved == True,
               IDXTransferApproval.approval_blocktimestamp != None),
          2),  # transferred
         (IDXTransferApproval.cancelled == True,
          3)],  # canceled
        else_=0).label("status")  # unapproved
    subquery = aliased(IDXTransferApproval,
                       db.query(IDXTransferApproval, case_status).subquery())

    # Get transfer approval history
    query = db.query(Token.issuer_address,
                     subquery.token_address,
                     func.count(subquery.id),
                     func.count(or_(literal_column("status") == 0, None)),
                     func.count(or_(literal_column("status") == 1, None)),
                     func.count(or_(literal_column("status") == 2, None)),
                     func.count(or_(literal_column("status") == 3, None))). \
        join(Token, subquery.token_address == Token.token_address). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_status != 2)
    if issuer_address is not None:
        query = query.filter(Token.issuer_address == issuer_address)
    query = query.group_by(Token.issuer_address, subquery.token_address). \
        order_by(Token.issuer_address, subquery.token_address)
    total = query.count()

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfer_approvals = query.all()
    count = query.count()

    transfer_approvals = []
    for issuer_address, token_address, application_count, \
            unapproved_count, approved_count, transferred_count, canceled_count in _transfer_approvals:
        transfer_approvals.append({
            "issuer_address": issuer_address,
            "token_address": token_address,
            "application_count": application_count,
            "unapproved_count": unapproved_count,
            "approved_count": approved_count,
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
        status: Optional[int] = Query(None, ge=0, le=3,
                                      description="0:unapproved, 1:approved, 2:transferred, 3:canceled"),
        sort_item: Optional[TransferApprovalsSortItem] = Query(TransferApprovalsSortItem.ID),
        sort_order: Optional[int] = Query(1, ge=0, le=1, description="0:asc, 1:desc"),
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)
):
    """List token transfer approval history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Create a subquery for 'status' added IDXTransferApproval
    case_status = case(
        [(and_(IDXTransferApproval.transfer_approved == True,
               IDXTransferApproval.approval_blocktimestamp == None),
          1),  # approved
         (and_(IDXTransferApproval.transfer_approved == True,
               IDXTransferApproval.approval_blocktimestamp != None),
          2),  # transferred
         (IDXTransferApproval.cancelled == True,
          3)],  # canceled
        else_=0).label("status")  # unapproved
    subquery = aliased(IDXTransferApproval, db.query(IDXTransferApproval, case_status).subquery())

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
        query = query.filter(literal_column("status") == status)

    # Sort
    if sort_item != TransferApprovalsSortItem.STATUS:
        sort_attr = getattr(subquery, sort_item, None)
    else:
        sort_attr = literal_column("status")
    if sort_order == 0:  # ASC
        query = query.order_by(sort_attr)
    else:  # DESC
        query = query.order_by(desc(sort_attr))
    if sort_item != TransferApprovalsSortItem.ID:
        # NOTE: Set secondary sort for consistent results
        query = query.order_by(desc(subquery.id))

    # Pagination
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfer_approvals = query.all()
    count = query.count()

    transfer_approval_history = []
    for _transfer_approval, status in _transfer_approvals:
        if _transfer_approval.cancelled is None:
            cancelled = False
        else:
            cancelled = _transfer_approval.cancelled
        if _transfer_approval.transfer_approved is None:
            transfer_approved = False
        else:
            transfer_approved = _transfer_approval.transfer_approved

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
            "transfer_approved": transfer_approved,
            "status": status
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
    responses=get_routers_responses(422, 410, 404, InvalidParameterError)
)
def approve_transfer(
        request: Request,
        token_address: str,
        id: int,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)
):
    """Approve share token transfer"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Authentication
    _account, decrypt_password = check_auth(issuer_address, eoa_password, db, request)

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Get transfer approval history
    _transfer_approval = db.query(IDXTransferApproval). \
        filter(IDXTransferApproval.id == id). \
        filter(IDXTransferApproval.token_address == token_address). \
        first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")
    if _transfer_approval.approval_blocktimestamp is not None:
        raise InvalidParameterError("already approved")
    if _transfer_approval.cancelled is True:
        raise InvalidParameterError("canceled application")

    # Check manually approval
    _additional_info = db.query(AdditionalTokenInfo). \
        filter(AdditionalTokenInfo.token_address == token_address). \
        first()
    if _additional_info is None or _additional_info.is_manual_transfer_approval is not True:
        raise InvalidParameterError("token is automatic approval")

    # Send transaction
    try:
        now = str(datetime.utcnow().timestamp())
        if _transfer_approval.exchange_address is None:
            _data = {
                "application_id": _transfer_approval.application_id,
                "data": now
            }
            _, tx_receipt = IbetShareContract.approve_transfer(
                contract_address=token_address,
                data=IbetSecurityTokenApproveTransfer(**_data),
                tx_from=issuer_address,
                private_key=private_key,
            )
            if tx_receipt["status"] != 1:  # Success
                IbetShareContract.cancel_transfer(
                    contract_address=token_address,
                    data=IbetSecurityTokenCancelTransfer(**_data),
                    tx_from=issuer_address,
                    private_key=private_key,
                )
                raise SendTransactionError
        else:
            _data = {
                "escrow_id": _transfer_approval.application_id,
                "data": now
            }
            escrow = IbetSecurityTokenEscrow(_transfer_approval.exchange_address)
            _, tx_receipt = escrow.approve_transfer(
                data=IbetSecurityTokenEscrowApproveTransfer(**_data),
                tx_from=issuer_address,
                private_key=private_key,
            )
            if tx_receipt["status"] != 1:  # Success
                raise SendTransactionError
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")


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
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        filter(Token.token_status != 2). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")
    if _token.token_status == 0:
        raise InvalidParameterError("wait for a while as the token is being processed")

    # Get transfer approval history
    _transfer_approval = db.query(IDXTransferApproval). \
        filter(IDXTransferApproval.id == id). \
        filter(IDXTransferApproval.token_address == token_address). \
        first()
    if _transfer_approval is None:
        raise HTTPException(status_code=404, detail="transfer approval not found")

    if _transfer_approval.cancelled is None:
        cancelled = False
    else:
        cancelled = _transfer_approval.cancelled
    if _transfer_approval.transfer_approved is None:
        transfer_approved = False
    else:
        transfer_approved = _transfer_approval.transfer_approved

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

    status = 0
    if _transfer_approval.transfer_approved is True:
        if _transfer_approval.approval_blocktimestamp is None:
            status = 1
        else:
            status = 2
    if _transfer_approval.cancelled is True:
        status = 3

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
        "transfer_approved": transfer_approved,
        "status": status
    }

    return history


# POST: /share/bulk_transfer
@router.post(
    "/bulk_transfer",
    response_model=BulkTransferUploadIdResponse,
    responses=get_routers_responses(422, InvalidParameterError, 401)
)
def bulk_transfer_ownership(
        request: Request,
        tokens: List[IbetShareTransfer],
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Bulk transfer token ownership"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    if len(tokens) < 1:
        raise InvalidParameterError("list length is zero")

    # Authentication
    check_auth(issuer_address, eoa_password, db, request)

    # Verify that the tokens are issued by the issuer_address
    for _token in tokens:
        _issued_token = db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_address == _token.token_address). \
            filter(Token.token_status != 2). \
            first()
        if _issued_token is None:
            raise InvalidParameterError(f"token not found: {_token.token_address}")
        if _issued_token.token_status == 0:
            raise InvalidParameterError(f"wait for a while as the token is being processed: {_token.token_address}")

    # generate upload_id
    upload_id = uuid.uuid4()

    # add bulk transfer upload record
    _bulk_transfer_upload = BulkTransferUpload()
    _bulk_transfer_upload.upload_id = upload_id
    _bulk_transfer_upload.issuer_address = issuer_address
    _bulk_transfer_upload.token_type = TokenType.IBET_SHARE
    _bulk_transfer_upload.status = 0
    db.add(_bulk_transfer_upload)

    # add bulk transfer records
    for _token in tokens:
        _bulk_transfer = BulkTransfer()
        _bulk_transfer.issuer_address = issuer_address
        _bulk_transfer.upload_id = upload_id
        _bulk_transfer.token_address = _token.token_address
        _bulk_transfer.token_type = TokenType.IBET_SHARE
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
    """List bulk transfer upload"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get bulk transfer upload list
    if issuer_address is None:
        _uploads = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.token_type == TokenType.IBET_SHARE). \
            order_by(BulkTransferUpload.issuer_address). \
            all()
    else:
        _uploads = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.issuer_address == issuer_address). \
            filter(BulkTransferUpload.token_type == TokenType.IBET_SHARE). \
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
    """Retrieve bulk transfer"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address))

    # Get bulk transfer upload list
    if issuer_address is None:
        _bulk_transfers = db.query(BulkTransfer). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.token_type == TokenType.IBET_SHARE). \
            order_by(BulkTransfer.issuer_address). \
            all()
    else:
        _bulk_transfers = db.query(BulkTransfer). \
            filter(BulkTransfer.issuer_address == issuer_address). \
            filter(BulkTransfer.upload_id == upload_id). \
            filter(BulkTransfer.token_type == TokenType.IBET_SHARE). \
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
