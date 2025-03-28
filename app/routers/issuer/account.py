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
import json
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, List, Optional, Sequence

import boto3
import eth_keyfile
import pytz
from coincurve import PublicKey
from Crypto.PublicKey import RSA
from eth_utils import keccak, to_checksum_address
from fastapi import APIRouter, Header, Path, Query, Request
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError as SAIntegrityError,
    OperationalError,
)

import config
from app.database import DBAsyncSession
from app.exceptions import (
    AuthorizationError,
    AuthTokenAlreadyExistsError,
    BatchPersonalInfoRegistrationValidationError,
    InvalidParameterError,
    InvalidUploadErrorDetail,
    OperationNotPermittedForOlderIssuers,
    PersonalInfoExceedsSizeLimit,
    RecordErrorDetail,
    ServiceUnavailableError,
)
from app.model.db import (
    Account,
    AccountRsaKeyTemporary,
    AccountRsaStatus,
    AuthToken,
    ChildAccount,
    ChildAccountIndex,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
    TmpChildAccountBatchCreate,
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
    BatchCreateChildAccountRequest,
    BatchCreateChildAccountResponse,
    ChildAccountResponse,
    CreateChildAccountResponse,
    CreateUpdateChildAccountRequest,
    ListAllChildAccountQuery,
    ListAllChildAccountResponse,
    ListAllChildAccountSortItem,
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

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# POST: /accounts
@router.post(
    "/accounts",
    operation_id="CreateIssuerKey",
    response_model=AccountResponse,
    responses=get_routers_responses(422, InvalidParameterError),
)
async def create_issuer_key(db: DBAsyncSession, data: AccountCreateKeyRequest):
    """Create Issuer Key"""
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
    public_key = PublicKey.from_valid_secret(private_key)
    addr = to_checksum_address(keccak(public_key.format(compressed=False)[1:])[-20:])
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
    )

    # Register key data to the DB
    _account = Account()
    _account.issuer_address = addr
    _account.issuer_public_key = public_key.format().hex()
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    _account.rsa_status = AccountRsaStatus.UNSET.value
    _account.is_deleted = False
    db.add(_account)

    # Insert an initial record for the child account index.
    _child_idx = ChildAccountIndex()
    _child_idx.issuer_address = addr
    _child_idx.next_index = 1
    db.add(_child_idx)

    # Insert an initial record for transaction execution management.
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
@router.get(
    "/accounts", operation_id="ListAllIssuers", response_model=List[AccountResponse]
)
async def list_all_issuers(db: DBAsyncSession):
    """List all issuer accounts"""

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
    operation_id="RetrieveIssuer",
    response_model=AccountResponse,
    responses=get_routers_responses(404),
)
async def retrieve_issuer(db: DBAsyncSession, issuer_address: Annotated[str, Path()]):
    """Retrieve an issuer account"""

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
    operation_id="DeleteIssuer",
    response_model=AccountResponse,
    responses=get_routers_responses(404),
)
async def delete_issuer(db: DBAsyncSession, issuer_address: Annotated[str, Path()]):
    """Logically delete an issuer account"""

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


# POST: /accounts/{issuer_address}/eoa_password
@router.post(
    "/accounts/{issuer_address}/eoa_password",
    operation_id="ChangeIssuerEOAPassword",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def change_issuer_eoa_password(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    data: AccountChangeEOAPasswordRequest,
):
    """Change Issuer's EOA-Password"""

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


# POST: /accounts/{issuer_address}/rsakey
@router.post(
    "/accounts/{issuer_address}/rsakey",
    operation_id="CreateIssuerRSAKey",
    response_model=AccountResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def create_issuer_rsa_key(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    data: AccountGenerateRsaKeyRequest,
):
    """Create issuer's RSA key"""

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


# POST: /accounts/{issuer_address}/rsa_passphrase
@router.post(
    "/accounts/{issuer_address}/rsa_passphrase",
    operation_id="ChangeIssuerRSAPassphrase",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
async def change_issuer_rsa_passphrase(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    data: AccountChangeRSAPassphraseRequest,
):
    """Change issuer's RSA-Passphrase"""

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
    operation_id="GenerateIssuerAuthToken",
    response_model=AccountAuthTokenResponse,
    responses=get_routers_responses(
        422, 404, InvalidParameterError, AuthTokenAlreadyExistsError
    ),
)
async def generate_issuer_auth_token(
    db: DBAsyncSession,
    request: Request,
    data: AccountAuthTokenRequest,
    issuer_address: Annotated[str, Path()],
    eoa_password: Annotated[Optional[str], Header()] = None,
):
    """Generate issuer's auth token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(
            eoa_password,
            [eoa_password_is_required, eoa_password_is_encrypted_value],
        ),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
    )

    # Generate new auth token
    new_token = secrets.token_hex()
    hashed_token = hashlib.sha256(new_token.encode()).hexdigest()

    # Get current datetime
    current_datetime_utc = pytz.timezone("UTC").localize(
        datetime.now(UTC).replace(tzinfo=None)
    )
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
            if datetime.now(UTC).replace(tzinfo=None) <= expiration_datetime:
                raise AuthTokenAlreadyExistsError()
        # Update auth token
        auth_token.auth_token = hashed_token
        auth_token.usage_start = current_datetime_utc.replace(tzinfo=None)
        auth_token.valid_duration = data.valid_duration
        await db.merge(auth_token)
        await db.commit()
    else:
        try:
            auth_token = AuthToken()
            auth_token.issuer_address = issuer_address
            auth_token.auth_token = hashed_token
            auth_token.usage_start = current_datetime_utc.replace(tzinfo=None)
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
    operation_id="DeleteIssuerAuthToken",
    response_model=None,
    responses=get_routers_responses(422, 404, AuthorizationError),
)
async def delete_issuer_auth_token(
    db: DBAsyncSession,
    request: Request,
    issuer_address: Annotated[str, Path()],
    eoa_password: Annotated[Optional[str], Header()] = None,
    auth_token: Annotated[Optional[str], Header()] = None,
):
    """Delete issuer's auth token"""

    # Validate Headers
    validate_headers(
        issuer_address=(issuer_address, address_is_valid_address),
        eoa_password=(eoa_password, eoa_password_is_encrypted_value),
    )

    # Authentication
    await check_auth(
        request=request,
        db=db,
        issuer_address=issuer_address,
        eoa_password=eoa_password,
        auth_token=auth_token,
    )

    # Delete auth token
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


# POST: /accounts/{issuer_address}/child_accounts
@router.post(
    "/accounts/{issuer_address}/child_accounts",
    operation_id="CreateChildAccount",
    response_model=CreateChildAccountResponse,
    responses=get_routers_responses(
        404,
        OperationNotPermittedForOlderIssuers,
        ServiceUnavailableError,
        PersonalInfoExceedsSizeLimit,
    ),
)
async def create_child_account(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    account_req: CreateUpdateChildAccountRequest,
):
    """Create the child account"""

    # Check if the issuer exists.
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check if the issuer was created in version 24.12 or later.
    if _account.issuer_public_key is None:
        raise OperationNotPermittedForOlderIssuers

    issuer_pk = PublicKey(data=bytes.fromhex(_account.issuer_public_key))

    # Lock child account index table
    try:
        _child_index = (
            await db.scalars(
                select(ChildAccountIndex)
                .where(ChildAccountIndex.issuer_address == issuer_address)
                .limit(1)
                .with_for_update(nowait=True)
            )
        ).first()
    except (OperationalError, DBAPIError):
        await db.rollback()
        await db.close()
        raise ServiceUnavailableError(
            "Creation of child accounts for this issuer is temporarily unavailable"
        )

    index = _child_index.next_index
    index_sk = int(index).to_bytes(32)
    index_pk = PublicKey.from_valid_secret(index_sk)

    # Derive the child address
    child_pk = PublicKey.combine_keys([issuer_pk, index_pk])
    child_addr = to_checksum_address(
        keccak(child_pk.format(compressed=False)[1:])[-20:]
    )

    # Insert child account record and update index
    _child_account = ChildAccount()
    _child_account.issuer_address = _account.issuer_address
    _child_account.child_account_index = index
    _child_account.child_account_address = child_addr
    db.add(_child_account)

    _child_index.next_index = index + 1
    await db.merge(_child_index)

    # Insert offchain personal information
    personal_info = account_req.personal_information.model_dump()
    personal_info["key_manager"] = "SELF"

    if (
        len(json.dumps(personal_info).encode("utf-8"))
        > config.PERSONAL_INFO_MESSAGE_SIZE_LIMIT
    ):
        raise PersonalInfoExceedsSizeLimit

    _off_personal_info = IDXPersonalInfo()
    _off_personal_info.issuer_address = _account.issuer_address
    _off_personal_info.account_address = child_addr
    _off_personal_info.personal_info = personal_info
    _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
    db.add(_off_personal_info)

    # Insert personal information history
    _personal_info_history = IDXPersonalInfoHistory()
    _personal_info_history.issuer_address = issuer_address
    _personal_info_history.account_address = child_addr
    _personal_info_history.event_type = PersonalInfoEventType.REGISTER
    _personal_info_history.personal_info = personal_info
    db.add(_personal_info_history)

    await db.commit()

    return json_response({"child_account_index": index})


# POST: /accounts/{issuer_address}/child_accounts/batch
@router.post(
    "/accounts/{issuer_address}/child_accounts/batch",
    operation_id="CreateChildAccountInBatch",
    response_model=BatchCreateChildAccountResponse,
    responses=get_routers_responses(
        404,
        OperationNotPermittedForOlderIssuers,
        ServiceUnavailableError,
        BatchPersonalInfoRegistrationValidationError,
    ),
)
async def create_child_account_in_batch(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    account_list_req: BatchCreateChildAccountRequest,
):
    # Check if the issuer exists.
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check if the issuer was created in version 24.12 or later.
    if _account.issuer_public_key is None:
        raise OperationNotPermittedForOlderIssuers

    # Lock child account index table
    try:
        _child_index = (
            await db.scalars(
                select(ChildAccountIndex)
                .where(ChildAccountIndex.issuer_address == issuer_address)
                .limit(1)
                .with_for_update(nowait=True)
            )
        ).first()
    except (OperationalError, DBAPIError):
        await db.rollback()
        await db.close()
        raise ServiceUnavailableError(
            "Creation of child accounts for this issuer is temporarily unavailable"
        )

    # Insert temporary table
    _next_index = _child_index.next_index
    _index_list = []
    errs = []
    for i, _personal_info in enumerate(account_list_req.personal_information_list):
        personal_info = _personal_info.model_dump()
        personal_info["key_manager"] = "SELF"

        # Check the length of personal info content
        if (
            len(json.dumps(personal_info).encode("utf-8"))
            > config.PERSONAL_INFO_MESSAGE_SIZE_LIMIT
        ):
            errs.append(
                RecordErrorDetail(
                    row_num=i,
                    error_reason="PersonalInfoExceedsSizeLimit",
                )
            )

        _batch_create = TmpChildAccountBatchCreate()
        _batch_create.issuer_address = _account.issuer_address
        _batch_create.child_account_index = _next_index
        _batch_create.personal_info = personal_info
        db.add(_batch_create)

        _index_list.append(_next_index)
        _next_index += 1

    if len(errs) > 0:
        raise BatchPersonalInfoRegistrationValidationError(
            detail=InvalidUploadErrorDetail(record_error_details=errs)
        )

    _child_index.next_index = _next_index
    await db.merge(_child_index)

    await db.commit()

    return json_response({"child_account_index_list": _index_list})


# GET: /accounts/{issuer_address}/child_accounts
@router.get(
    "/accounts/{issuer_address}/child_accounts",
    operation_id="ListAllChildAccount",
    response_model=ListAllChildAccountResponse,
    responses=get_routers_responses(404),
)
async def list_all_child_account(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    get_query: Annotated[ListAllChildAccountQuery, Query()],
):
    """List all child accounts"""

    # Check if the issuer exists.
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Search child accounts
    stmt = (
        select(ChildAccount, IDXPersonalInfo)
        .where(ChildAccount.issuer_address == issuer_address)
        .outerjoin(
            IDXPersonalInfo,
            and_(
                ChildAccount.issuer_address == IDXPersonalInfo.issuer_address,
                ChildAccount.child_account_address == IDXPersonalInfo.account_address,
                IDXPersonalInfo.data_source == PersonalInfoDataSource.OFF_CHAIN,
            ),
        )
    )
    total = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(ChildAccount).order_by(None)
    )

    if get_query.child_account_address is not None:
        stmt = stmt.where(
            ChildAccount.child_account_address.like(
                "%" + get_query.child_account_address + "%"
            )
        )
    if get_query.name is not None:
        stmt = stmt.where(
            IDXPersonalInfo._personal_info["name"]
            .as_string()
            .like("%" + get_query.name + "%")
        )
    if get_query.created_from:
        _created_from = datetime.strptime(
            get_query.created_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.created
            >= local_tz.localize(_created_from).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.created_to:
        _created_to = datetime.strptime(
            get_query.created_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.created
            <= local_tz.localize(_created_to).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.modified_from:
        _modified_from = datetime.strptime(
            get_query.modified_from + ".000000", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.modified
            >= local_tz.localize(_modified_from).astimezone(utc_tz).replace(tzinfo=None)
        )
    if get_query.modified_to:
        _modified_to = datetime.strptime(
            get_query.modified_to + ".999999", "%Y-%m-%d %H:%M:%S.%f"
        )
        stmt = stmt.where(
            IDXPersonalInfo.modified
            <= local_tz.localize(_modified_to).astimezone(utc_tz).replace(tzinfo=None)
        )

    count = await db.scalar(
        stmt.with_only_columns(func.count()).select_from(ChildAccount).order_by(None)
    )

    # Sort
    def _order(_order):
        if _order == 0:
            return asc
        else:
            return desc

    _sort_order = get_query.sort_order
    match get_query.sort_item:
        case ListAllChildAccountSortItem.child_account_index:
            stmt = stmt.order_by(_order(_sort_order)(ChildAccount.child_account_index))
        case ListAllChildAccountSortItem.child_account_address:
            stmt = stmt.order_by(
                _order(_sort_order)(ChildAccount.child_account_address)
            )
        case ListAllChildAccountSortItem.name:
            stmt = stmt.order_by(
                _order(_sort_order)(IDXPersonalInfo._personal_info["name"].as_string())
            )
        case ListAllChildAccountSortItem.created:
            stmt = stmt.order_by(_order(_sort_order)(IDXPersonalInfo.created))
        case ListAllChildAccountSortItem.modified:
            stmt = stmt.order_by(_order(_sort_order)(IDXPersonalInfo.modified))

    # Pagination
    if get_query.limit is not None:
        stmt = stmt.limit(get_query.limit)
    if get_query.offset is not None:
        stmt = stmt.offset(get_query.offset)

    _tmp_child_accounts: Sequence[tuple[ChildAccount, IDXPersonalInfo | None]] = (
        (await db.execute(stmt)).tuples().all()
    )

    child_accounts = []
    for _tmp_child_account in _tmp_child_accounts:
        if _tmp_child_account[1] is not None:
            _personal_info = _tmp_child_account[1].json()
            _child_account = {
                "issuer_address": _tmp_child_account[0].issuer_address,
                "child_account_index": _tmp_child_account[0].child_account_index,
                "child_account_address": _tmp_child_account[0].child_account_address,
                "personal_information": _personal_info["personal_info"],
                "created": _personal_info["created"],
                "modified": _personal_info["modified"],
            }
        else:
            _child_account = {
                "issuer_address": _tmp_child_account[0].issuer_address,
                "child_account_index": _tmp_child_account[0].child_account_index,
                "child_account_address": _tmp_child_account[0].child_account_address,
                "personal_information": None,
                "created": None,
                "modified": None,
            }
        child_accounts.append(_child_account)

    return json_response(
        {
            "result_set": {
                "count": count,
                "total": total,
                "limit": get_query.limit,
                "offset": get_query.offset,
            },
            "child_accounts": child_accounts,
        }
    )


# GET: /accounts/{issuer_address}/child_accounts/{child_account_index}
@router.get(
    "/accounts/{issuer_address}/child_accounts/{child_account_index}",
    operation_id="RetrieveChildAccount",
    response_model=ChildAccountResponse,
    responses=get_routers_responses(404),
)
async def retrieve_child_account(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    child_account_index: Annotated[int, Path()],
):
    """Retrieve the child account"""

    # Check if the issuer exists.
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Search child accounts
    _child_account = (
        (
            await db.execute(
                select(ChildAccount, IDXPersonalInfo)
                .where(
                    and_(
                        ChildAccount.issuer_address == issuer_address,
                        ChildAccount.child_account_index == child_account_index,
                    )
                )
                .outerjoin(
                    IDXPersonalInfo,
                    and_(
                        ChildAccount.issuer_address == IDXPersonalInfo.issuer_address,
                        ChildAccount.child_account_address
                        == IDXPersonalInfo.account_address,
                        IDXPersonalInfo.data_source == PersonalInfoDataSource.OFF_CHAIN,
                    ),
                )
                .limit(1)
            )
        )
        .tuples()
        .first()
    )
    if _child_account is None:
        raise HTTPException(status_code=404, detail="child account does not exist")

    if _child_account[1] is not None:
        _personal_info = _child_account[1].json()
        _resp_account = {
            "issuer_address": _child_account[0].issuer_address,
            "child_account_index": _child_account[0].child_account_index,
            "child_account_address": _child_account[0].child_account_address,
            "personal_information": _personal_info["personal_info"],
            "created": _personal_info["created"],
            "modified": _personal_info["modified"],
        }
    else:
        _resp_account = {
            "issuer_address": _child_account[0].issuer_address,
            "child_account_index": _child_account[0].child_account_index,
            "child_account_address": _child_account[0].child_account_address,
            "personal_information": None,
            "created": None,
            "modified": None,
        }

    return json_response(_resp_account)


# POST: /accounts/{issuer_address}/child_accounts/{child_account_index}
@router.post(
    "/accounts/{issuer_address}/child_accounts/{child_account_index}",
    operation_id="UpdateChildAccount",
    response_model=None,
    responses=get_routers_responses(404, PersonalInfoExceedsSizeLimit),
)
async def update_child_account(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    child_account_index: Annotated[int, Path()],
    account_req: CreateUpdateChildAccountRequest,
):
    """Update the personal information of the child account"""

    # Check if the issuer exists.
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check if the child account exists.
    _child_account = (
        await db.scalars(
            select(ChildAccount)
            .where(
                and_(
                    ChildAccount.issuer_address == issuer_address,
                    ChildAccount.child_account_index == child_account_index,
                )
            )
            .limit(1)
        )
    ).first()
    if _child_account is None:
        raise HTTPException(status_code=404, detail="child account does not exist")

    # Update offchain personal information
    _offchain_personal_info = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.issuer_address == issuer_address,
                    IDXPersonalInfo.account_address
                    == _child_account.child_account_address,
                    IDXPersonalInfo.data_source == PersonalInfoDataSource.OFF_CHAIN,
                )
            )
            .limit(1)
        )
    ).first()
    if _offchain_personal_info is not None:
        personal_info = account_req.personal_information.model_dump()
        personal_info["key_manager"] = "SELF"

        if (
            len(json.dumps(personal_info).encode("utf-8"))
            > config.PERSONAL_INFO_MESSAGE_SIZE_LIMIT
        ):
            raise PersonalInfoExceedsSizeLimit

        _offchain_personal_info.personal_info = personal_info
        await db.merge(_offchain_personal_info)

        # Insert personal information history
        _personal_info_history = IDXPersonalInfoHistory()
        _personal_info_history.issuer_address = issuer_address
        _personal_info_history.account_address = _child_account.child_account_address
        _personal_info_history.event_type = PersonalInfoEventType.MODIFY
        _personal_info_history.personal_info = personal_info
        db.add(_personal_info_history)

    await db.commit()

    return


# DELETE: /accounts/{issuer_address}/child_accounts/{child_account_index}
@router.delete(
    "/accounts/{issuer_address}/child_accounts/{child_account_index}",
    operation_id="DeleteChildAccount",
    response_model=None,
    responses=get_routers_responses(404),
)
async def delete_child_account(
    db: DBAsyncSession,
    issuer_address: Annotated[str, Path()],
    child_account_index: Annotated[int, Path()],
):
    """Delete the child account and its off-chain personal information"""

    # Check if the issuer exists.
    _account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="issuer does not exist")

    # Check if the child account exists.
    _child_account = (
        await db.scalars(
            select(ChildAccount)
            .where(
                and_(
                    ChildAccount.issuer_address == issuer_address,
                    ChildAccount.child_account_index == child_account_index,
                )
            )
            .limit(1)
        )
    ).first()
    if _child_account is None:
        raise HTTPException(status_code=404, detail="child account does not exist")

    # Delete child account
    await db.delete(_child_account)

    # Delete offchain personal information
    _offchain_personal_info = (
        await db.scalars(
            select(IDXPersonalInfo)
            .where(
                and_(
                    IDXPersonalInfo.issuer_address == issuer_address,
                    IDXPersonalInfo.account_address
                    == _child_account.child_account_address,
                    IDXPersonalInfo.data_source == PersonalInfoDataSource.OFF_CHAIN,
                )
            )
            .limit(1)
        )
    ).first()
    if _offchain_personal_info is not None:
        await db.delete(_offchain_personal_info)

    await db.commit()

    return
