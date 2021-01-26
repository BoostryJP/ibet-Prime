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

from app.database import db_session
from app.model.schema import IbetStraightBond
from app.model.db import Token, TokenType

router = APIRouter(
    prefix="/bond",
    tags=["bond"],
    responses={404: {"description": "Not found"}},
)


@router.get("/tokens", response_model=List[IbetStraightBond])
async def get_tokens(db: Session = Depends(db_session)):
    """Get issued tokens"""
    tokens = db.query(Token).all()
    return tokens


@router.post("/tokens")
async def issue_token(token: IbetStraightBond, db: Session = Depends(db_session)):
    """Issue ibet Straight Bond"""
    _token = Token()
    _token.type = TokenType.IBET_STRAIGHT_BOND
    _token.tx_hash = "aaaa"
    _token.issuer_address = token.issuer_address
    _token.token_address = "0xaaaaa"
    _token.abi = {}
    db.add(_token)
    db.commit()

    return {"token_address": _token.token_address}
