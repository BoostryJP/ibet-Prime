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
import secrets
import time
from Crypto.PublicKey import RSA
from Crypto import Random

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from sha3 import keccak_256
from coincurve import PublicKey
from eth_utils import to_checksum_address
import eth_keyfile

from config import KEY_FILE_PASSWORD
from app.database import db_session
from app.model.schema import AccountResponse
from app.model.db import Account
from app import log
LOG = log.get_logger()

router = APIRouter(tags=["account"])


def generate_rsa_key(db: Session, issuer_address: str):
    """Generate RSA key"""
    time.sleep(1)
    LOG.info(f"RSA key generation started: {issuer_address}")

    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        LOG.error(f"RSA key generation failed: {issuer_address}")
        return

    random_func = Random.new().read
    rsa = RSA.generate(10240, random_func)
    rsa_private_pem = rsa.exportKey(format="PEM", passphrase=KEY_FILE_PASSWORD).decode()
    rsa_public_pem = rsa.publickey().exportKey().decode()

    # Register key data to the DB
    _account.rsa_private_key = rsa_private_pem
    _account.rsa_public_key = rsa_public_pem
    db.merge(_account)
    db.commit()

    LOG.info(f"RSA key generation succeeded: {issuer_address}")
    return


# POST: /accounts
@router.post("/accounts", response_model=AccountResponse)
async def create_key(
        background_tasks: BackgroundTasks,
        db: Session = Depends(db_session)):
    """Create Keys"""

    # Generate Ethereum Key
    private_key = keccak_256(secrets.token_bytes(32)).digest()
    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
    addr = to_checksum_address(keccak_256(public_key).digest()[-20:])
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key,
        password=KEY_FILE_PASSWORD.encode("utf-8"),
        kdf="pbkdf2"
    )

    # Register key data to the DB
    _account = Account()
    _account.issuer_address = addr
    _account.keyfile = keyfile_json
    db.add(_account)
    db.commit()

    # Generate RSA key (background)
    background_tasks.add_task(generate_rsa_key, db, addr)

    return {
        "issuer_address": _account.issuer_address,
        "rsa_public_key": ""
    }


# GET: /accounts
@router.get("/accounts", response_model=List[AccountResponse])
async def list_all_accounts(db: Session = Depends(db_session)):
    """List all accounts"""

    # Register key data to the DB
    _accounts = db.query(Account).all()

    account_list = []
    for _account in _accounts:
        account_list.append({
            "issuer_address": _account.issuer_address,
            "rsa_public_key": _account.rsa_public_key
        })

    return account_list


# GET: /accounts/{issuer_address}
@router.get("/accounts/{issuer_address}", response_model=AccountResponse)
async def retrieve_account(issuer_address: str, db: Session = Depends(db_session)):
    """Retrieve an account"""

    # Register key data to the DB
    _account = db.query(Account).\
        filter(Account.issuer_address == issuer_address).\
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer is not exists")

    return {
        "issuer_address": _account.issuer_address,
        "rsa_public_key": _account.rsa_public_key
    }
