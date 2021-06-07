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
import re

from fastapi import (
    APIRouter,
    Depends
)
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from sha3 import keccak_256
from coincurve import PublicKey
from Crypto.PublicKey import RSA
from eth_utils import to_checksum_address
import eth_keyfile
import boto3

from config import (
    PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE,
    EOA_PASSWORD_PATTERN,
    EOA_PASSWORD_PATTERN_MSG,
    PERSONAL_INFO_RSA_PASSPHRASE_PATTERN,
    PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG,
    E2EE_REQUEST_ENABLED,
    AWS_REGION_NAME,
    AWS_KMS_GENERATE_RANDOM_ENABLED
)
from app.database import db_session
from app.model.schema import (
    AccountCreateKeyRequest,
    AccountResponse,
    AccountGenerateRsaKeyRequest,
    AccountChangeEOAPasswordRequest,
    AccountChangeRSAPassphraseRequest
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.docs_utils import get_routers_responses
from app.model.db import (
    Account,
    AccountRsaKeyTemporary,
    AccountRsaStatus,
    TransactionLock
)
from app.exceptions import InvalidParameterError
from app import log

LOG = log.get_logger()

router = APIRouter(tags=["account"])


# POST: /accounts
@router.post(
    "/accounts",
    response_model=AccountResponse,
    responses=get_routers_responses(422, InvalidParameterError)
)
def create_key(
        data: AccountCreateKeyRequest,
        db: Session = Depends(db_session)):
    """Create Keys"""
    # Check Password Policy
    eoa_password = E2EEUtils.decrypt(data.eoa_password) if E2EE_REQUEST_ENABLED else data.eoa_password
    if not re.match(EOA_PASSWORD_PATTERN, eoa_password):
        raise InvalidParameterError(EOA_PASSWORD_PATTERN_MSG)

    # Generate Ethereum Key
    if AWS_KMS_GENERATE_RANDOM_ENABLED:
        kms = boto3.client(service_name="kms", region_name=AWS_REGION_NAME)
        result = kms.generate_random(NumberOfBytes=32)
        private_key = keccak_256(result.get("Plaintext")).digest()
    else:
        private_key = keccak_256(secrets.token_bytes(32)).digest()
    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
    addr = to_checksum_address(keccak_256(public_key).digest()[-20:])
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key,
        password=eoa_password.encode("utf-8"),
        kdf="pbkdf2"
    )

    # Register key data to the DB
    _account = Account()
    _account.issuer_address = addr
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    _account.rsa_status = AccountRsaStatus.UNSET.value
    _account.is_deleted = False
    db.add(_account)

    # Insert initial transaction execution management record
    _tm = TransactionLock()
    _tm.tx_from = addr
    db.add(_tm)

    db.commit()

    return {
        "issuer_address": _account.issuer_address,
        "rsa_public_key": "",
        "rsa_status": _account.rsa_status,
        "is_deleted": _account.is_deleted
    }


# GET: /accounts
@router.get(
    "/accounts",
    response_model=List[AccountResponse]
)
def list_all_accounts(db: Session = Depends(db_session)):
    """List all accounts"""

    # Register key data to the DB
    _accounts = db.query(Account).all()

    account_list = []
    for _account in _accounts:
        account_list.append({
            "issuer_address": _account.issuer_address,
            "rsa_public_key": _account.rsa_public_key,
            "rsa_status": _account.rsa_status,
            "is_deleted": _account.is_deleted
        })

    return account_list


# GET: /accounts/{issuer_address}
@router.get(
    "/accounts/{issuer_address}",
    response_model=AccountResponse,
    responses=get_routers_responses(404)
)
def retrieve_account(issuer_address: str, db: Session = Depends(db_session)):
    """Retrieve an account"""

    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer is not exists")

    return {
        "issuer_address": _account.issuer_address,
        "rsa_public_key": _account.rsa_public_key,
        "rsa_status": _account.rsa_status,
        "is_deleted": _account.is_deleted
    }


# DELETE: /accounts/{issuer_address}
@router.delete(
    "/accounts/{issuer_address}",
    response_model=AccountResponse,
    responses=get_routers_responses(404)
)
def delete_account(issuer_address: str, db: Session = Depends(db_session)):
    """Logically delete an account"""

    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer is not exists")

    _account.is_deleted = True
    db.merge(_account)
    db.commit()

    return {
        "issuer_address": _account.issuer_address,
        "rsa_public_key": _account.rsa_public_key,
        "rsa_status": _account.rsa_status,
        "is_deleted": _account.is_deleted
    }


# POST: /accounts/{issuer_address}/rsakey
@router.post(
    "/accounts/{issuer_address}/rsakey",
    response_model=AccountResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError)
)
def generate_rsa_key(
        issuer_address: str,
        data: AccountGenerateRsaKeyRequest,
        db: Session = Depends(db_session)):
    """Generate RSA key"""

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer is not exists")

    # Check now Generating RSA
    if _account.rsa_status == AccountRsaStatus.CREATING.value or \
            _account.rsa_status == AccountRsaStatus.CHANGING.value:
        raise InvalidParameterError("RSA key is now generating")

    # Check Password Policy
    if data.rsa_passphrase:
        rsa_passphrase = E2EEUtils.decrypt(data.rsa_passphrase) if E2EE_REQUEST_ENABLED else data.rsa_passphrase
        if not re.match(PERSONAL_INFO_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
            raise InvalidParameterError(PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG)
    else:
        rsa_passphrase = PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE

    # NOTE: rsa_status is updated to AccountRsaStatus.SET on the batch.
    rsa_status = AccountRsaStatus.CREATING.value
    if _account.rsa_status == AccountRsaStatus.SET.value:
        # Create data to the temporary DB
        # NOTE: This data is deleted in the Batch when PersonalInfo modify is completed.
        temporary = AccountRsaKeyTemporary()
        temporary.issuer_address = _account.issuer_address
        temporary.rsa_private_key = _account.rsa_private_key
        temporary.rsa_public_key = _account.rsa_public_key
        rsa_passphrase_org = _account.rsa_passphrase
        temporary.rsa_passphrase = rsa_passphrase_org
        db.add(temporary)

        rsa_status = AccountRsaStatus.CHANGING.value

    # Update data to the DB
    _account.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    _account.rsa_status = rsa_status
    db.merge(_account)

    db.commit()

    return {
        "issuer_address": issuer_address,
        "rsa_public_key": _account.rsa_public_key,
        "rsa_status": rsa_status,
        "is_deleted": _account.is_deleted
    }


# POST: /accounts/{issuer_address}/eoa_password
@router.post(
    "/accounts/{issuer_address}/eoa_password",
    responses=get_routers_responses(422, 404, InvalidParameterError))
def change_eoa_password(
        issuer_address: str,
        data: AccountChangeEOAPasswordRequest,
        db: Session = Depends(db_session)):
    """Change EOA Password"""

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer is not exists")

    # Check Password Policy
    eoa_password = E2EEUtils.decrypt(data.eoa_password) if E2EE_REQUEST_ENABLED else data.eoa_password
    if not re.match(EOA_PASSWORD_PATTERN, eoa_password):
        raise InvalidParameterError(EOA_PASSWORD_PATTERN_MSG)

    # Check Old Password
    old_eoa_password = E2EEUtils.decrypt(data.old_eoa_password) if E2EE_REQUEST_ENABLED else data.old_eoa_password
    correct_eoa_password = E2EEUtils.decrypt(_account.eoa_password)
    if old_eoa_password != correct_eoa_password:
        raise InvalidParameterError("old password mismatch")

    # Get Ethereum Key
    old_keyfile_json = _account.keyfile
    private_key = eth_keyfile.decode_keyfile_json(
        raw_keyfile_json=old_keyfile_json,
        password=old_eoa_password.encode("utf-8")
    )

    # Create New Ethereum Key File
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key,
        password=eoa_password.encode("utf-8"),
        kdf="pbkdf2"
    )

    # Update data to the DB
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    db.merge(_account)

    db.commit()

    return


# POST: /accounts/{issuer_address}/rsa_passphrase
@router.post(
    "/accounts/{issuer_address}/rsa_passphrase",
    responses=get_routers_responses(422, 404, InvalidParameterError))
def change_rsa_passphrase(
        issuer_address: str,
        data: AccountChangeRSAPassphraseRequest,
        db: Session = Depends(db_session)):
    """Change RSA Passphrase"""

    # Get Account
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer is not exists")

    # Check Old Passphrase
    old_rsa_passphrase = E2EEUtils.decrypt(data.old_rsa_passphrase) if E2EE_REQUEST_ENABLED else data.old_rsa_passphrase
    correct_rsa_passphrase = E2EEUtils.decrypt(_account.rsa_passphrase)
    if old_rsa_passphrase != correct_rsa_passphrase:
        raise InvalidParameterError("old passphrase mismatch")

    # Check Password Policy
    rsa_passphrase = E2EEUtils.decrypt(data.rsa_passphrase) if E2EE_REQUEST_ENABLED else data.rsa_passphrase
    if not re.match(PERSONAL_INFO_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
        raise InvalidParameterError(PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG)

    # Create New RSA Private Key
    old_rsa_private_key = _account.rsa_private_key
    rsa_key = RSA.importKey(old_rsa_private_key, old_rsa_passphrase)
    rsa_private_key = rsa_key.exportKey(format="PEM", passphrase=rsa_passphrase).decode()

    # Update data to the DB
    _account.rsa_private_key = rsa_private_key
    _account.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    db.merge(_account)

    db.commit()

    return
