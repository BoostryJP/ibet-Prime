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
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from eth_keyfile import decode_keyfile_json

from app.database import db_session
from app.model.schema import IbetStraightBondCreate, IbetStraightBondUpdate, IbetStraightBondResponse
from app.model.db import Account, Token, TokenType
from app.model.blockchain import IbetStraightBondContract
from app.config import KEY_FILE_PASSWORD
from app.utils import ContractUtils
from app.exceptions import InvalidParameterError, SendTransactionError

router = APIRouter(
    prefix="/bond",
    tags=["bond"],
    responses={404: {"description": "Not found"}},
)


@router.put("/token")
async def issue_token(token: IbetStraightBondCreate, db: Session = Depends(db_session)):
    """Issue ibet Straight Bond"""

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == token.issuer_address). \
        first()

    # If account does not exist, return 400 error
    if _account is None:
        raise InvalidParameterError("issuer does not exist")

    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=KEY_FILE_PASSWORD.encode("utf-8")
    )

    # Deploy Arguments
    arguments = [
        token.name,
        token.symbol,
        token.total_supply,
        token.face_value,
        token.redemption_date,
        token.redemption_value,
        token.return_date,
        token.return_amount,
        token.purpose
    ]

    # Deploy
    try:
        contract_address, abi, tx_hash = ContractUtils.deploy_contract(
            contract_name="IbetStraightBond",
            args=arguments,
            deployer=token.issuer_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Register token data
    _token = Token()
    _token.type = TokenType.IBET_STRAIGHT_BOND
    _token.tx_hash = tx_hash
    _token.issuer_address = token.issuer_address
    _token.token_address = contract_address
    _token.abi = abi
    db.add(_token)
    db.commit()

    return {"token_address": _token.token_address}


@router.get("/tokens", response_model=List[IbetStraightBondResponse])
async def get_tokens(db: Session = Depends(db_session)):
    """Get issued tokens"""
    # Get issued token list
    tokens = db.query(Token). \
        filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
        all()

    # Get contract data
    bond_tokens = []
    for token in tokens:
        bond_tokens.append(IbetStraightBondContract.get(contract_address=token.token_address).__dict__)

    return bond_tokens


@router.get("/token/{token_address}", response_model=IbetStraightBondResponse)
async def get_token(token_address: str):
    """Get issued token"""
    # Get contract data
    bond_token = IbetStraightBondContract.get(contract_address=token_address).__dict__

    return bond_token


@router.post("/token/{token_address}")
async def get_token(token_address: str, token: IbetStraightBondUpdate):
    """Update token"""
    # Get contract data
    bond_token = IbetStraightBondContract.get(contract_address=token_address).__dict__

    return bond_token

