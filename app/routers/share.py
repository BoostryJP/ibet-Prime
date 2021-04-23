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
from sqlalchemy import desc
from sqlalchemy.orm import Session
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
    TransferHistoryResponse,
    BulkTransferUploadIdResponse,
    BulkTransferUploadResponse,
    BulkTransferResponse,
    IbetShareScheduledUpdate,
    ScheduledEventIdResponse,
    ScheduledEventResponse
)
from app.model.utils import (
    E2EEUtils,
    validate_headers,
    address_is_valid_address,
    eoa_password_is_required,
    eoa_password_is_encrypted_value,
    check_password
)
from app.model.db import (
    Account,
    Token,
    TokenType,
    IDXPosition,
    IDXPersonalInfo,
    BulkTransfer,
    BulkTransferUpload,
    IDXTransfer,
    ScheduledEvents
)
from app.model.blockchain import (
    IbetShareContract,
    TokenListContract
)
from app.exceptions import (
    InvalidParameterError,
    SendTransactionError,
    AuthorizationError
)
from app.log import (
    auth_info,
    auth_error
)
from config import EOA_PASSWORD_CHECK_ENABLED

router = APIRouter(
    prefix="/share",
    tags=["share"],
    responses={404: {"description": "Not found"}},
)

local_tz = timezone(config.TZ)


# POST: /share/tokens
@router.post(
    "/tokens",
    response_model=TokenAddressResponse
)
async def issue_token(
        request: Request,
        token: IbetShareCreate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Issue ibetShare token"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Validate update items
    # Note: Items set at the time of issue do not need to be updated.
    _data = {
        "tradable_exchange_contract_address": token.tradable_exchange_contract_address,
        "personal_info_contract_address": token.personal_info_contract_address,
        "image_url": token.image_url,
        "transferable": token.transferable,
        "status": token.status,
        "offering_status": token.offering_status,
        "contact_information": token.contact_information,
        "privacy_policy": token.privacy_policy
    }
    _update_data = IbetShareUpdate(**_data)

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist, or password mismatch")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)

    # Check Password
    if EOA_PASSWORD_CHECK_ENABLED:
        result = check_password(eoa_password, decrypt_password)
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Deploy
    arguments = [
        token.name,
        token.symbol,
        token.issue_price,
        token.total_supply,
        int(token.dividends * 100),
        token.dividend_record_date,
        token.dividend_payment_date,
        token.cancellation_date,
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

    # Update
    try:
        IbetShareContract.update(
            contract_address=contract_address,
            data=_update_data,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Register token data
    _token = Token()
    _token.type = TokenType.IBET_SHARE
    _token.tx_hash = tx_hash
    _token.issuer_address = issuer_address
    _token.token_address = contract_address
    _token.abi = abi
    db.add(_token)

    # Insert initial position data
    _position = IDXPosition()
    _position.token_address = contract_address
    _position.account_address = issuer_address
    _position.balance = token.total_supply
    _position.pending_transfer = 0
    db.add(_position)

    db.commit()

    return {"token_address": _token.token_address}


# GET: /share/tokens
@router.get(
    "/tokens",
    response_model=List[IbetShareResponse]
)
async def list_all_tokens(
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

    # Get contract data
    share_tokens = []
    for token in tokens:
        share_token = IbetShareContract.get(contract_address=token.token_address).__dict__
        share_token["issue_datetime"] = local_tz.localize(token.created).isoformat()
        share_tokens.append(share_token)

    return share_tokens


# GET: /share/tokens/{token_address}
@router.get(
    "/tokens/{token_address}",
    response_model=IbetShareResponse
)
async def retrieve_token(
        token_address: str,
        db: Session = Depends(db_session)):
    """Retrieve token"""
    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

    # Get contract data
    share_token = IbetShareContract.get(contract_address=token_address).__dict__
    share_token["issue_datetime"] = local_tz.localize(_token.created).isoformat()

    return share_token


# POST: /share/tokens/{token_address}
@router.post(
    "/tokens/{token_address}",
    response_model=None
)
async def update_token(
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

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist, or password mismatch")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)

    # Check Password
    if EOA_PASSWORD_CHECK_ENABLED:
        result = check_password(eoa_password, decrypt_password)
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")

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
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

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

    return


# POST: /share/tokens/{token_address}/add
@router.post(
    "/tokens/{token_address}/add",
    response_model=None
)
async def additional_issue(
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

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist, or password mismatch")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)

    # Check Password
    if EOA_PASSWORD_CHECK_ENABLED:
        result = check_password(eoa_password, decrypt_password)
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")

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
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

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
async def list_all_token_events(
        token_address: str,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve token event"""
    # Get Token
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

    # Get contract data
    token_events = []
    for _token_event in _token_events:
        token_events.append(
            {
                "scheduled_event_id": _token_event.id,
                "token_address": token_address,
                "token_type": TokenType.IBET_SHARE,
                "scheduled_datetime": local_tz.localize(_token_event.scheduled_datetime).isoformat(),
                "event_type": _token_event.event_type,
                "status": _token_event.status,
                "data": _token_event.data
            }
        )
    return token_events


# GET: /share/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.get(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse
)
async def retrieve_token_events(
        token_address: str,
        scheduled_event_id: int,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve token event"""
    # Get Token
    if issuer_address is None:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
            filter(ScheduledEvents.id == scheduled_event_id). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    else:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
            filter(ScheduledEvents.id == scheduled_event_id). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            filter(ScheduledEvents.token_address == token_address). \
            first()

    if _token_event is None:
        raise HTTPException(status_code=404, detail="scheduled event scheduled_event_id not found")

    # Get contract data
    return {
        "scheduled_event_id": _token_event.id,
        "token_address": token_address,
        "token_type": TokenType.IBET_SHARE,
        "scheduled_datetime": local_tz.localize(_token_event.scheduled_datetime).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data
    }


# POST: /share/tokens/{token_address}/scheduled_events
@router.post(
    "/tokens/{token_address}/scheduled_events",
    response_model=ScheduledEventIdResponse
)
async def schedule_token_update_event(
        request: Request,
        token_address: str,
        event_data: IbetShareScheduledUpdate,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Update a token according to schedule"""
    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value])
    )

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)

    # Check Password
    if EOA_PASSWORD_CHECK_ENABLED:
        result = check_password(eoa_password, decrypt_password)
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")

    # Get Token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.issuer_address == issuer_address). \
        filter(Token.token_address == token_address). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

    # Register Events
    _scheduled_event = ScheduledEvents()
    _scheduled_event.issuer_address = issuer_address
    _scheduled_event.token_address = token_address
    _scheduled_event.token_type = TokenType.IBET_SHARE
    _scheduled_event.scheduled_datetime = event_data.scheduled_datetime
    _scheduled_event.event_type = event_data.event_type
    _scheduled_event.data = event_data.data.dict()
    _scheduled_event.status = 0
    db.add(_scheduled_event)
    db.commit()

    return {"scheduled_event_id": _scheduled_event.id}


# DELETE: /share/tokens/{token_address}/scheduled_events/{scheduled_event_id}
@router.delete(
    "/tokens/{token_address}/scheduled_events/{scheduled_event_id}",
    response_model=ScheduledEventResponse
)
async def delete_token_event(
        token_address: str,
        scheduled_event_id: int,
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Retrieve token event"""
    # Get Token
    if issuer_address is None:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
            filter(ScheduledEvents.id == scheduled_event_id). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    else:
        _token_event = db.query(ScheduledEvents). \
            filter(ScheduledEvents.token_type == TokenType.IBET_SHARE). \
            filter(ScheduledEvents.id == scheduled_event_id). \
            filter(ScheduledEvents.issuer_address == issuer_address). \
            filter(ScheduledEvents.token_address == token_address). \
            first()
    if _token_event is None:
        raise HTTPException(status_code=404, detail="scheduled event scheduled_event_id not found")

    # Get contract data
    rtn = {
        "scheduled_event_id": _token_event.id,
        "token_address": token_address,
        "token_type": TokenType.IBET_SHARE,
        "scheduled_datetime": local_tz.localize(_token_event.scheduled_datetime).isoformat(),
        "event_type": _token_event.event_type,
        "status": _token_event.status,
        "data": _token_event.data
    }
    db.delete(_token_event)
    db.commit()
    return rtn


# GET: /share/tokens/{token_address}/holders
@router.get(
    "/tokens/{token_address}/holders",
    response_model=List[HolderResponse]
)
async def list_all_holders(
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
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

    # Get Holders
    _holders = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address). \
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
            "pending_transfer": _holder.pending_transfer
        })

    return holders


# GET: /share/tokens/{token_address}/holders/{account_address}
@router.get(
    "/tokens/{token_address}/holders/{account_address}",
    response_model=HolderResponse
)
async def retrieve_holder(
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
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

    # Get Holders
    _holder = db.query(IDXPosition). \
        filter(IDXPosition.token_address == token_address). \
        filter(IDXPosition.account_address == account_address). \
        first()
    if _holder is None:
        raise HTTPException(status_code=404, detail="holder not found")

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
        "account_address": _holder.account_address,
        "personal_information": _personal_info,
        "balance": _holder.balance,
        "pending_transfer": _holder.pending_transfer
    }

    return holder


# POST: /share/transfers
@router.post(
    "/transfers",
    response_model=None
)
async def transfer_ownership(
        request: Request,
        token: IbetShareTransfer,
        issuer_address: str = Header(...),
        eoa_password: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Transfer token ownership"""

    # Validate Headers
    validate_headers(issuer_address=(issuer_address, address_is_valid_address),
                     eoa_password=(eoa_password, [eoa_password_is_required, eoa_password_is_encrypted_value]))

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist, or password mismatch")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)

    # Check Password
    if EOA_PASSWORD_CHECK_ENABLED:
        result = check_password(eoa_password, decrypt_password)
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")

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
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

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
    response_model=TransferHistoryResponse
)
async def list_transfer_history(
        token_address: str,
        offset: Optional[int] = Query(None),
        limit: Optional[int] = Query(None),
        db: Session = Depends(db_session)
):
    """List token transfer history"""
    # Get token
    _token = db.query(Token). \
        filter(Token.type == TokenType.IBET_SHARE). \
        filter(Token.token_address == token_address). \
        first()
    if _token is None:
        raise HTTPException(status_code=404, detail="token not found")

    # Get transfer history
    query = db.query(IDXTransfer). \
        filter(IDXTransfer.token_address == token_address). \
        order_by(desc(IDXTransfer.id))
    total = query.count()

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    _transfers = query.all()
    count = query.count()

    transfer_history = []
    for _transfer in _transfers:
        transfer_history.append({
            "transaction_hash": _transfer.transaction_hash,
            "token_address": token_address,
            "from_address": _transfer.transfer_from,
            "to_address": _transfer.transfer_to,
            "amount": _transfer.amount,
            "block_timestamp": _transfer.block_timestamp.strftime("%Y/%m/%d %H:%M:%S")
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


# POST: /share/bulk_transfer
@router.post(
    "/bulk_transfer",
    response_model=BulkTransferUploadIdResponse
)
async def bulk_transfer_ownership(
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

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist, or password mismatch")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)

    # Check Password
    if EOA_PASSWORD_CHECK_ENABLED:
        result = check_password(eoa_password, decrypt_password)
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")

    # Verify that the tokens are issued by the issuer_address
    for _token in tokens:
        _issued_token = db.query(Token). \
            filter(Token.type == TokenType.IBET_SHARE). \
            filter(Token.issuer_address == issuer_address). \
            filter(Token.token_address == _token.token_address). \
            first()
        if _issued_token is None:
            raise InvalidParameterError(f"token not found: {_token.token_address}")

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
        _bulk_transfer.from_address = _token.transfer_from
        _bulk_transfer.to_address = _token.transfer_to
        _bulk_transfer.amount = _token.amount
        _bulk_transfer.status = 0
        db.add(_bulk_transfer)

    db.commit()

    return {"upload_id": str(upload_id)}


# GET: /share/bulk_transfer
@router.get(
    "/bulk_transfer",
    response_model=List[BulkTransferUploadResponse]
)
async def list_bulk_transfer_upload(
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
        uploads.append({
            "issuer_address": _upload.issuer_address,
            "token_type": _upload.token_type,
            "upload_id": _upload.upload_id,
            "status": _upload.status
        })

    return uploads


# GET: /share/bulk_transfer/{upload_id}
@router.get(
    "/bulk_transfer/{upload_id}",
    response_model=List[BulkTransferResponse]
)
async def retrieve_bulk_transfer(
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
