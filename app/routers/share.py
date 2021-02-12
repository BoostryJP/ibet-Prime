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
from sqlalchemy.orm import Session
from eth_keyfile import decode_keyfile_json

from config import KEY_FILE_PASSWORD
from app.database import db_session
from app.model.schema import IbetShareCreate, IbetShareUpdate, IbetShareTransfer, \
    IbetShareResponse, HolderResponse
from app.model.db import Account, Token, TokenType, IDXPosition, IDXPersonalInfo
from app.model.blockchain import IbetShareContract
from app.exceptions import InvalidParameterError, SendTransactionError

router = APIRouter(
    prefix="/share",
    tags=["share"],
    responses={404: {"description": "Not found"}},
)


# PUT: /share/token
@router.put("/token")
async def issue_token(
        token: IbetShareCreate,
        issuer_address: str = Header(None),
        db: Session = Depends(db_session)):
    """Issue ibet Straight Share"""

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()

    # If account does not exist, return 400 error
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=KEY_FILE_PASSWORD.encode("utf-8")
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
async def get_tokens(
        issuer_address: Optional[str] = Header(None),
        db: Session = Depends(db_session)):
    """Get issued tokens"""
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
async def get_token(token_address: str):
    """Get issued token"""
    # Get contract data
    share_token = IbetShareContract.get(contract_address=token_address).__dict__

    return share_token


# POST: /share/tokens/{token_address}
@router.post("/tokens/{token_address}")
async def update_token(
        token_address: str,
        token: IbetShareUpdate,
        issuer_address: str = Header(None),
        db: Session = Depends(db_session)):
    """Update token"""

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
        raise InvalidParameterError("token not found")

    # Get private key
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=KEY_FILE_PASSWORD.encode("utf-8")
    )

    # Send transaction
    try:
        IbetShareContract.update(
            contract_address=token_address,
            update_data=token,
            tx_from=issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    return


# GET: /share/tokens/{token_address}/holders
@router.get("/tokens/{token_address}/holders", response_model=List[HolderResponse])
async def get_holders(
        token_address: str,
        issuer_address: str = Header(None),
        db: Session = Depends(db_session)):
    """Get share token holders"""

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
        raise InvalidParameterError("token not found")

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
@router.get("/share/tokens/{token_address}/holder/{account_address}", response_model=HolderResponse)
async def get_holder(
        token_address: str,
        account_address: str,
        issuer_address: str = Header(None),
        db: Session = Depends(db_session)):
    """Get share token holder"""

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
        raise InvalidParameterError("token not found")

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
async def transfer(
        token: IbetShareTransfer,
        issuer_address: str = Header(None),
        db: Session = Depends(db_session)):
    """Transfer token"""

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()

    # If account does not exist, return 400 error
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=KEY_FILE_PASSWORD.encode("utf-8")
    )

    IbetShareContract.transfer(
        contract_address=token.token_address,
        transfer_data=token,
        tx_from=issuer_address,
        private_key=private_key
    )

    return