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

import hashlib
import re
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Sequence

import boto3
import eth_keyfile
from coincurve import PublicKey
from Crypto.PublicKey import RSA
from eth_utils import keccak, to_checksum_address
from fastapi import APIRouter, Header, Request
from fastapi.exceptions import HTTPException
from pytz import timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError as SAIntegrityError

from app.database import DBAsyncSession
from app.exceptions import (
    AuthorizationError,
    AuthTokenAlreadyExistsError,
    InvalidParameterError,
)
from app.model.db import (
    Account,
    AccountRsaKeyTemporary,
    AccountRsaStatus,
    AuthToken,
    TransactionLock,
)
from app.model.schema import (
    AccountAuthTokenRequest,
    AccountAuthTokenResponse,
    AccountChangeEOAPasswordRequest,
    AccountChangeRSAPassphraseRequest,
    AccountCreateKeyRequest,
    AccountGenerateRsaKeyRequest,
    AccountResponse,
)
from app.utils.check_utils import (
    address_is_valid_address,
    check_auth,
    eoa_password_is_encrypted_value,
    eoa_password_is_required,
    validate_headers,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.e2ee_utils import E2EEUtils
from app.utils.fastapi_utils import json_response
from config import (
    AWS_KMS_GENERATE_RANDOM_ENABLED,
    AWS_REGION_NAME,
    E2EE_REQUEST_ENABLED,
    EOA_PASSWORD_PATTERN,
    EOA_PASSWORD_PATTERN_MSG,
    PERSONAL_INFO_RSA_DEFAULT_PASSPHRASE,
    PERSONAL_INFO_RSA_PASSPHRASE_PATTERN,
    PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG,
    TZ,
)

router = APIRouter(tags=["account"])

local_tz = timezone(TZ)


# POST: /accounts
@router.post(
    "/accounts",
    response_model=AccountResponse,
    responses=get_routers_responses(422, InvalidParameterError),
)
async def create_key(db: DBAsyncSession, data: AccountCreateKeyRequest):
    """Create Keys"""
    # Check Password Policy
    eoa_password = (
        E2EEUtils.decrypt(data.eoa_password)
        if E2EE_REQUEST_ENABLED
        else data.eoa_password
    )
    if not re.match(EOA_PASSWORD_PATTERN, eoa_password):
        raise InvalidParameterError(EOA_PASSWORD_PATTERN_MSG)

    # Generate Ethereum Key
    if AWS_KMS_GENERATE_RANDOM_ENABLED:
        kms = boto3.client(service_name="kms", region_name=AWS_REGION_NAME)
        result = kms.generate_random(NumberOfBytes=32)
        private_key = keccak(result.get("Plaintext"))
    else:
        private_key = keccak(secrets.token_bytes(32))
    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
    addr = to_checksum_address(keccak(public_key)[-20:])
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
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

    await db.commit()

    return json_response(
        {
            "issuer_address": _account.issuer_address,
            "rsa_public_key": "",
            "rsa_status": _account.rsa_status,
            "is_deleted": _account.is_deleted,
        }
    )


# GET: /accounts
@router.get("/accounts", response_model=List[AccountResponse])
async def list_all_accounts(db: DBAsyncSession):
    """List all accounts"""

    # Register key data to the DB
    _accounts: Sequence[Account] = (
        await db.scalars(select(Account).order_by(Account.issuer_address))
    ).all()

    account_list = []
    for _account in _accounts:
        account_list.append(
            {
                "issuer_address": _account.issuer_address,
                "rsa_public_key": _account.rsa_public_key,
                "rsa_status": _account.rsa_status,
                "is_deleted": _account.is_deleted,
            }
        )

    return json_response(account_list)


# GET: /accounts/{issuer_address}
@router.get(
    "/accounts/{issuer_address}",
    response_model=AccountResponse,
    responses=get_routers_responses(404),
)
async def retrieve_account(db: DBAsyncSession, issuer_address: str):
    """Retrieve an account"""

    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    return json_response(
        {
            "issuer_address": _account.issuer_address,
            "rsa_public_key": _account.rsa_public_key,
            "rsa_status": _account.rsa_status,
            "is_deleted": _account.is_deleted,
        }
    )


# DELETE: /accounts/{issuer_address}
@router.delete(
    "/accounts/{issuer_address}",
    response_model=AccountResponse,
    responses=get_routers_responses(404),
)
async def delete_account(db: DBAsyncSession, issuer_address: str):
    """Logically delete an account"""

    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    _account.is_deleted = True
    await db.merge(_account)
    await db.commit()

    return json_response(
        {
            "issuer_address": _account.issuer_address,
            "rsa_public_key": _account.rsa_public_key,
            "rsa_status": _account.rsa_status,
            "is_deleted": _account.is_deleted,
        }
    )


# POST: /accounts/{issuer_address}/rsakey
@router.post(
    "/accounts/{issuer_address}/rsakey",
    response_model=AccountResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def generate_rsa_key(
    db: DBAsyncSession,
    issuer_address: str,
    data: AccountGenerateRsaKeyRequest,
):
    """Generate RSA key"""

    # Get Account
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check now Generating RSA
    if (
        _account.rsa_status == AccountRsaStatus.CREATING.value
        or _account.rsa_status == AccountRsaStatus.CHANGING.value
    ):
        raise InvalidParameterError("RSA key is now generating")

    # Check Password Policy
    if data.rsa_passphrase:
        rsa_passphrase = (
            E2EEUtils.decrypt(data.rsa_passphrase)
            if E2EE_REQUEST_ENABLED
            else data.rsa_passphrase
        )
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
    await db.merge(_account)

    await db.commit()

    return json_response(
        {
            "issuer_address": issuer_address,
            "rsa_public_key": _account.rsa_public_key,
            "rsa_status": rsa_status,
            "is_deleted": _account.is_deleted,
        }
    )


# POST: /accounts/{issuer_address}/eoa_password
@router.post(
    "/accounts/{issuer_address}/eoa_password",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def change_eoa_password(
    db: DBAsyncSession,
    issuer_address: str,
    data: AccountChangeEOAPasswordRequest,
):
    """Change EOA Password"""

    # Get Account
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check Password Policy
    eoa_password = (
        E2EEUtils.decrypt(data.eoa_password)
        if E2EE_REQUEST_ENABLED
        else data.eoa_password
    )
    if not re.match(EOA_PASSWORD_PATTERN, eoa_password):
        raise InvalidParameterError(EOA_PASSWORD_PATTERN_MSG)

    # Check Old Password
    old_eoa_password = (
        E2EEUtils.decrypt(data.old_eoa_password)
        if E2EE_REQUEST_ENABLED
        else data.old_eoa_password
    )
    correct_eoa_password = E2EEUtils.decrypt(_account.eoa_password)
    if old_eoa_password != correct_eoa_password:
        raise InvalidParameterError("old password mismatch")

    # Get Ethereum Key
    old_keyfile_json = _account.keyfile
    private_key = eth_keyfile.decode_keyfile_json(
        raw_keyfile_json=old_keyfile_json, password=old_eoa_password.encode("utf-8")
    )

    # Create New Ethereum Key File
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
    )

    # Update data to the DB
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    await db.merge(_account)

    await db.commit()

    return


# POST: /accounts/{issuer_address}/rsa_passphrase
@router.post(
    "/accounts/{issuer_address}/rsa_passphrase",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def change_rsa_passphrase(
    db: DBAsyncSession,
    issuer_address: str,
    data: AccountChangeRSAPassphraseRequest,
):
    """Change RSA Passphrase"""

    # Get Account
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check Old Passphrase
    old_rsa_passphrase = (
        E2EEUtils.decrypt(data.old_rsa_passphrase)
        if E2EE_REQUEST_ENABLED
        else data.old_rsa_passphrase
    )
    correct_rsa_passphrase = E2EEUtils.decrypt(_account.rsa_passphrase)
    if old_rsa_passphrase != correct_rsa_passphrase:
        raise InvalidParameterError("old passphrase mismatch")

    # Check Password Policy
    rsa_passphrase = (
        E2EEUtils.decrypt(data.rsa_passphrase)
        if E2EE_REQUEST_ENABLED
        else data.rsa_passphrase
    )
    if not re.match(PERSONAL_INFO_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
        raise InvalidParameterError(PERSONAL_INFO_RSA_PASSPHRASE_PATTERN_MSG)

    # Create New RSA Private Key
    old_rsa_private_key = _account.rsa_private_key
    rsa_key = RSA.importKey(old_rsa_private_key, old_rsa_passphrase)
    rsa_private_key = rsa_key.exportKey(
        format="PEM", passphrase=rsa_passphrase
    ).decode()

    # Update data to the DB
    _account.rsa_private_key = rsa_private_key
    _account.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    await db.merge(_account)

    await db.commit()

    return


# POST: /accounts/{issuer_address}/auth_token
@router.post(
    "/accounts/{issuer_address}/auth_token",
    response_model=AccountAuthTokenResponse,
    responses=get_routers_responses(
        422, 404, InvalidParameterError, AuthTokenAlreadyExistsError
    ),
)
async def create_auth_token(
    db: DBAsyncSession,
    request: Request,
    data: AccountAuthTokenRequest,
    issuer_address: str,
    eoa_password: Optional[str] = Header(None),
):
    """Create Auth Token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(
            eoa_password,
            [eoa_password_is_required, eoa_password_is_encrypted_value],
        ),
    )

    # Authentication
    issuer_account, _ = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
    )

    # Generate new auth token
    new_token = secrets.token_hex()
    hashed_token = hashlib.sha256(new_token.encode()).hexdigest()

    # Get current datetime
    current_datetime_utc = timezone("UTC").localize(datetime.utcnow())
    current_datetime_local = current_datetime_utc.astimezone(local_tz).isoformat()

    # Register auth token
    auth_token: Optional[AuthToken] = (
        await db.scalars(
            select(AuthToken).where(AuthToken.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if auth_token is not None:
        # If a valid auth token already exists, return an error.
        if auth_token.valid_duration == 0:
            raise AuthTokenAlreadyExistsError()
        else:
            expiration_datetime = auth_token.usage_start + timedelta(
                seconds=auth_token.valid_duration
            )
            if datetime.utcnow() <= expiration_datetime:
                raise AuthTokenAlreadyExistsError()
        # Update auth token
        auth_token.auth_token = hashed_token
        auth_token.usage_start = current_datetime_utc
        auth_token.valid_duration = data.valid_duration
        await db.merge(auth_token)
        await db.commit()
    else:
        try:
            auth_token = AuthToken()
            auth_token.issuer_address = issuer_address
            auth_token.auth_token = hashed_token
            auth_token.usage_start = current_datetime_utc
            auth_token.valid_duration = data.valid_duration
            db.add(auth_token)
            await db.commit()
        except SAIntegrityError:
            # NOTE: Registration can be conflicting.
            raise AuthTokenAlreadyExistsError()

    return json_response(
        {
            "auth_token": new_token,
            "usage_start": current_datetime_local,
            "valid_duration": data.valid_duration,
        }
    )


# DELETE: /accounts/{issuer_address}/auth_token
@router.delete(
    "/accounts/{issuer_address}/auth_token",
    response_model=None,
    responses=get_routers_responses(422, 404, AuthorizationError),
)
async def delete_auth_token(
    db: DBAsyncSession,
    request: Request,
    issuer_address: str,
    eoa_password: Optional[str] = Header(None),
    auth_token: Optional[str] = Header(None),
):
    """Delete auth token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    issuer_account, _ = await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Delete auto token
    _auth_token: Optional[AuthToken] = (
        await db.scalars(
            select(AuthToken).where(AuthToken.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _auth_token is None:
        raise HTTPException(status_code=404, detail="auth token does not exist")

    await db.delete(_auth_token)
    await db.commit()
    return
