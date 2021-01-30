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
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sha3 import keccak_256
from coincurve import PublicKey
from eth_utils import to_checksum_address
import eth_keyfile

from app.config import KEY_FILE_PASSWORD
from app.database import db_session
from app.model.schema import AccountResponse
from app.model.db import Account

router = APIRouter(tags=["account"])


@router.put("/account", response_model=AccountResponse)
async def create_key(db: Session = Depends(db_session)):
    """Create Key"""
    private_key = keccak_256(secrets.token_bytes(32)).digest()
    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
    addr = to_checksum_address(keccak_256(public_key).digest()[-20:])
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key,
        password=KEY_FILE_PASSWORD.encode("utf-8"),
        kdf="pbkdf2"
    )
    # Register keyfile to the DB
    _account = Account()
    _account.issuer_address = addr
    _account.keyfile = keyfile_json
    db.add(_account)
    db.commit()

    return {"issuer_address": _account.issuer_address}
