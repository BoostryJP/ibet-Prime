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
from typing import List, Optional

from fastapi import APIRouter, Depends, Header
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from eth_keyfile import decode_keyfile_json

from app.database import db_session
from app.model.schema import IbetShareCreate, IbetShareUpdate, \
    IbetShareTransfer, IbetShareAdd, \
    IbetShareResponse, HolderResponse
from app.model.utils import SecureValueUtils, headers_validate, address_is_valid_address
from app.model.db import Account, Token, TokenType, IDXPosition, IDXPersonalInfo
from app.model.blockchain import IbetShareContract
from app.exceptions import InvalidParameterError, SendTransactionError

router = APIRouter(
    prefix="/share",
    tags=["share"],
    responses={404: {"description": "Not found"}},
)


# POST: /share/tokens
@router.post("/tokens")
async def issue_token(
        token: IbetShareCreate,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Issue ibetShare token"""

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get private key
    keyfile_json = _account.keyfile
    decrypt_password = SecureValueUtils.decrypt(_account.eoa_password)
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Deploy Arguments
    arguments = [
        token.name,
        token.symbol,
        token.issue_price,
        token.total_supply,
        int(token.dividends * 100),
        token.dividend_record_date,
        token.dividend_payment_date,
        token.cancellation_date
    ]

    # Deploy
    try:
        contract_address, abi, tx_hash = IbetShareContract.create(
            args=arguments,
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
    db.commit()

    return {"token_address": _token.token_address}


# GET: /share/tokens
@router.get("/tokens", response_model=List[IbetShareResponse])
async def list_all_tokens(
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

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
        share_tokens.append(
            IbetShareContract.get(contract_address=token.token_address).__dict__
        )

    return share_tokens


# GET: /share/tokens/{token_address}
@router.get("/tokens/{token_address}", response_model=IbetShareResponse)
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

    return share_token


# POST: /share/tokens/{token_address}
@router.post("/tokens/{token_address}")
async def update_token(
        token_address: str,
        token: IbetShareUpdate,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Update a token"""

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get private key
    keyfile_json = _account.keyfile
    decrypt_password = SecureValueUtils.decrypt(_account.eoa_password)
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


# POST: /bond/tokens/{token_address}/add
@router.post("/tokens/{token_address}/add")
async def additional_issue(
        token_address: str,
        token: IbetShareAdd,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Add token"""

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get private key
    keyfile_json = _account.keyfile
    decrypt_password = SecureValueUtils.decrypt(_account.eoa_password)
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


# GET: /share/tokens/{token_address}/holders
@router.get("/tokens/{token_address}/holders", response_model=List[HolderResponse])
async def list_all_holders(
        token_address: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """List all share token holders"""

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

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
            "balance": _holder.balance
        })

    return holders


# GET: /share/tokens/{token_address}/holders/{account_address}
@router.get("/share/tokens/{token_address}/holders/{account_address}", response_model=HolderResponse)
async def retrieve_holder(
        token_address: str,
        account_address: str,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Retrieve share token holder"""

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

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
        "balance": _holder.balance
    }

    return holder


# POST: /share/transfer
@router.post("/transfer")
async def transfer_ownership(
        token: IbetShareTransfer,
        issuer_address: str = Header(...),
        db: Session = Depends(db_session)):
    """Transfer token ownership"""

    # Headers Validate
    headers_validate([{
        "name": "issuer-address",
        "value": issuer_address,
        "validator": address_is_valid_address
    }])

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get private key
    keyfile_json = _account.keyfile
    decrypt_password = SecureValueUtils.decrypt(_account.eoa_password)
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
            contract_address=token.token_address,
            data=token,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


