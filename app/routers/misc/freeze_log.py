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

import re
import secrets
from typing import Annotated, Sequence

import boto3
from eth_keyfile.keyfile import create_keyfile_json, decode_keyfile_json
from eth_utils.crypto import keccak
from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy import select

from app.database import DBAsyncSession
from app.exceptions import (
    ContractRevertError,
    InvalidParameterError,
    SendTransactionError,
)
from app.model.db import FreezeLogAccount, TransactionLock
from app.model.ibet import FreezeLogContract
from app.model.schema import (
    CreateFreezeLogAccountRequest,
    FreezeLogAccountChangeEOAPasswordRequest,
    FreezeLogAccountResponse,
    ListAllFreezeLogAccountResponse,
    RecordNewFreezeLogRequest,
    RecordNewFreezeLogResponse,
    RetrieveFreezeLogQuery,
    RetrieveFreezeLogResponse,
    UpdateFreezeLogRequest,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.e2ee_utils import E2EEUtils
from app.utils.fastapi_utils import json_response
from app.utils.secp256k1_utils import (
    private_key_to_public_key,
    public_key_to_address,
)
from config import (
    AWS_KMS_GENERATE_RANDOM_ENABLED,
    AWS_REGION_NAME,
    E2EE_REQUEST_ENABLED,
    EOA_PASSWORD_PATTERN,
    EOA_PASSWORD_PATTERN_MSG,
    FREEZE_LOG_CONTRACT_ADDRESS,
)

router = APIRouter(prefix="/freeze_log", tags=["[misc] freeze_log"])


# POST: /freeze_log/accounts
@router.post(
    "/accounts",
    operation_id="CreateFreezeLogAccount",
    response_model=FreezeLogAccountResponse,
    responses=get_routers_responses(InvalidParameterError, 422),
)
async def create_account(
    db: DBAsyncSession,
    create_req: CreateFreezeLogAccountRequest,
):
    """Create an EOA account used to record freeze logs.

    Private key material is not returned.

    When `E2EE_REQUEST_ENABLED` is enabled, `eoa_password` must be encrypted with the public key returned by `/e2ee`.

    Errors:
    - 400 `InvalidParameterError` (code 1): the EOA password does not satisfy the configured policy.
    - 422: the request is invalid, or the encrypted password cannot be decoded.
    """

    # Check Password Policy(EOA password)
    eoa_password = (
        E2EEUtils.decrypt(create_req.eoa_password)
        if E2EE_REQUEST_ENABLED
        else create_req.eoa_password
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
    addr = public_key_to_address(
        private_key_to_public_key(private_key, compressed=False)
    )
    keyfile_json = create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
    )

    # Register account data to the DB
    _account = FreezeLogAccount()
    _account.account_address = addr
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    _account.is_deleted = False
    db.add(_account)

    # Insert initial transaction execution management record
    _tm = TransactionLock()
    _tm.tx_from = addr
    db.add(_tm)

    await db.commit()

    return json_response(
        {
            "account_address": _account.account_address,
            "is_deleted": _account.is_deleted,
        }
    )


# GET: /freeze_log/accounts
@router.get(
    "/accounts",
    operation_id="ListAllFreezeLogAccount",
    response_model=ListAllFreezeLogAccountResponse,
)
async def list_all_accounts(db: DBAsyncSession):
    """List all freeze-log EOA accounts.

    Logically deleted accounts are included.
    Encrypted passwords and key files are omitted.
    """

    _accounts: Sequence[FreezeLogAccount] = (
        await db.scalars(select(FreezeLogAccount))
    ).all()

    account_list = [
        {
            "account_address": _account.account_address,
            "is_deleted": _account.is_deleted,
        }
        for _account in _accounts
    ]
    return json_response(account_list)


# DELETE: /freeze_log/accounts/{account_address}
@router.delete(
    "/accounts/{account_address}",
    operation_id="DeleteFreezeLogAccount",
    response_model=FreezeLogAccountResponse,
    responses=get_routers_responses(404),
)
async def delete_account(db: DBAsyncSession, account_address: Annotated[str, Path()]):
    """Logically delete a freeze-log EOA account.

    Repeating the request succeeds for an existing account and leaves it deleted.

    Errors:
    - 404: no account exists for `account_address`.
    """

    # Search for an account
    _account: FreezeLogAccount | None = (
        await db.scalars(
            select(FreezeLogAccount)
            .where(FreezeLogAccount.account_address == account_address)
            .limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="account is not exists")

    # Update account
    _account.is_deleted = True
    await db.merge(_account)
    await db.commit()

    return json_response(
        {
            "account_address": _account.account_address,
            "is_deleted": _account.is_deleted,
        }
    )


# POST: /freeze_log/accounts/{account_address}/eoa_password
@router.post(
    "/accounts/{account_address}/eoa_password",
    operation_id="ChangeFreezeLogAccountPassword",
    response_model=None,
    responses=get_routers_responses(InvalidParameterError, 404, 422),
)
async def change_eoa_password(
    db: DBAsyncSession,
    account_address: Annotated[str, Path()],
    change_req: FreezeLogAccountChangeEOAPasswordRequest,
):
    """Change a freeze-log account's EOA password.

    The old password must match the stored password.
    The account address remains unchanged.

    When `E2EE_REQUEST_ENABLED` is enabled, both password values must be encrypted with the public key returned by `/e2ee`.

    Errors:
    - 400 `InvalidParameterError` (code 1): the old password does not match, or the new password does not satisfy the configured policy.
    - 404: no account exists for `account_address`.
    - 422: the request is invalid, or an encrypted password cannot be decoded.
    """

    # Search for an account
    _account: FreezeLogAccount | None = (
        await db.scalars(
            select(FreezeLogAccount)
            .where(FreezeLogAccount.account_address == account_address)
            .limit(1)
        )
    ).first()
    if _account is None:
        raise HTTPException(status_code=404, detail="account is not exists")

    # Check Old Password
    old_eoa_password = (
        E2EEUtils.decrypt(change_req.old_eoa_password)
        if E2EE_REQUEST_ENABLED
        else change_req.old_eoa_password
    )
    correct_eoa_password = E2EEUtils.decrypt(_account.eoa_password)
    if old_eoa_password != correct_eoa_password:
        raise InvalidParameterError("old password mismatch")

    # Check Password Policy
    eoa_password = (
        E2EEUtils.decrypt(change_req.eoa_password)
        if E2EE_REQUEST_ENABLED
        else change_req.eoa_password
    )
    if not re.match(EOA_PASSWORD_PATTERN, eoa_password):
        raise InvalidParameterError(EOA_PASSWORD_PATTERN_MSG)

    # Get Ethereum Key
    private_key = decode_keyfile_json(
        raw_keyfile_json=_account.keyfile, password=old_eoa_password.encode("utf-8")
    )

    # Create New Ethereum Key File
    keyfile_json = create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
    )

    # Update data
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    await db.merge(_account)

    await db.commit()

    return


# POST: /freeze_log/logs
@router.post(
    "/logs",
    operation_id="RecordNewFreezeLog",
    response_model=RecordNewFreezeLogResponse,
    responses=get_routers_responses(
        InvalidParameterError, 404, 422, 500, SendTransactionError
    ),
)
async def record_new_log(
    db: DBAsyncSession,
    req: RecordNewFreezeLogRequest,
):
    """Submit a new message to the configured freeze-log contract.

    The account password is checked, and the assigned log index is returned after submission succeeds.
    Log immutability begins after the requested grace-block count.

    `FREEZE_LOG_CONTRACT_ADDRESS` must be configured.
    When `E2EE_REQUEST_ENABLED` is enabled, `eoa_password` must be encrypted with the public key returned by `/e2ee`.

    Errors:
    - 400 `InvalidParameterError` (code 1): the EOA password does not match.
    - 404: no freeze-log account exists for the request address.
    - 422: the request is invalid.
    - 500: `FREEZE_LOG_CONTRACT_ADDRESS` is not configured.
    - 503 `SendTransactionError` (code 2): transaction submission fails, including a contract revert.
    """
    # Search for an account
    log_account: FreezeLogAccount | None = (
        await db.scalars(
            select(FreezeLogAccount)
            .where(FreezeLogAccount.account_address == req.account_address)
            .limit(1)
        )
    ).first()
    if log_account is None:
        raise HTTPException(status_code=404, detail="account is not exists")

    # Authentication
    eoa_password = (
        E2EEUtils.decrypt(req.eoa_password)
        if E2EE_REQUEST_ENABLED
        else req.eoa_password
    )
    correct_eoa_pass = E2EEUtils.decrypt(log_account.eoa_password)
    if eoa_password != correct_eoa_pass:
        raise InvalidParameterError("password mismatch")

    # Record new log
    if FREEZE_LOG_CONTRACT_ADDRESS is None:
        raise HTTPException(
            status_code=500, detail="FREEZE_LOG_CONTRACT_ADDRESS is not set"
        )
    log_contract = FreezeLogContract(
        log_account=log_account, contract_address=FREEZE_LOG_CONTRACT_ADDRESS
    )
    try:
        _, log_index = await log_contract.record_log(
            log_message=req.log_message,
            freezing_grace_block_count=req.freezing_grace_block_count,
        )
    except SendTransactionError, ContractRevertError:
        raise SendTransactionError("failed to record log")

    return json_response({"log_index": log_index})


# POST: /freeze_log/logs/{log_index}
@router.post(
    "/logs/{log_index}",
    operation_id="UpdateFreezeLog",
    response_model=None,
    responses=get_routers_responses(
        InvalidParameterError, 404, 422, 500, SendTransactionError
    ),
)
async def update_log(
    db: DBAsyncSession,
    req: UpdateFreezeLogRequest,
    log_index: Annotated[int, Path(description="Log index")],
):
    """Update a freeze-log message before its grace period expires.

    The account password is checked, and the update succeeds only while the log remains mutable.

    `FREEZE_LOG_CONTRACT_ADDRESS` must be configured.
    When `E2EE_REQUEST_ENABLED` is enabled, `eoa_password` must be encrypted with the public key returned by `/e2ee`.

    Errors:
    - 400 `InvalidParameterError` (code 1): the EOA password does not match.
    - 404: no freeze-log account exists for the request address.
    - 422: the request is invalid.
    - 500: `FREEZE_LOG_CONTRACT_ADDRESS` is not configured.
    - 503 `SendTransactionError` (code 2): transaction submission fails, including a contract revert or an immutable log.
    """
    # Search for an account
    log_account: FreezeLogAccount | None = (
        await db.scalars(
            select(FreezeLogAccount)
            .where(FreezeLogAccount.account_address == req.account_address)
            .limit(1)
        )
    ).first()
    if log_account is None:
        raise HTTPException(status_code=404, detail="account is not exists")

    # Authentication
    eoa_password = (
        E2EEUtils.decrypt(req.eoa_password)
        if E2EE_REQUEST_ENABLED
        else req.eoa_password
    )
    correct_eoa_pass = E2EEUtils.decrypt(log_account.eoa_password)
    if eoa_password != correct_eoa_pass:
        raise InvalidParameterError("password mismatch")

    # Update log
    if FREEZE_LOG_CONTRACT_ADDRESS is None:
        raise HTTPException(
            status_code=500, detail="FREEZE_LOG_CONTRACT_ADDRESS is not set"
        )
    log_contract = FreezeLogContract(
        log_account=log_account, contract_address=FREEZE_LOG_CONTRACT_ADDRESS
    )
    try:
        await log_contract.update_log(
            log_index=log_index,
            log_message=req.log_message,
        )
    except SendTransactionError, ContractRevertError:
        raise SendTransactionError("failed to update log")

    return


# GET: /freeze_log/logs/{log_index}
@router.get(
    "/logs/{log_index}",
    operation_id="RetrieveFreezeLog",
    response_model=RetrieveFreezeLogResponse,
    responses=get_routers_responses(404, 422, 500),
)
async def retrieve_log(
    db: DBAsyncSession,
    log_index: Annotated[int, Path(description="Log index")],
    req_query: Annotated[RetrieveFreezeLogQuery, Query()],
):
    """Retrieve a freeze-log entry from the configured contract.

    The block number, grace-block count, and message are returned.
    The query's account identifies the account used for the request, and `FREEZE_LOG_CONTRACT_ADDRESS` must be configured.

    Errors:
    - 404: no freeze-log account exists for the query address.
    - 422: the path or query is invalid.
    - 500: `FREEZE_LOG_CONTRACT_ADDRESS` is not configured.
    """
    # Search for an account
    log_account: FreezeLogAccount | None = (
        await db.scalars(
            select(FreezeLogAccount)
            .where(FreezeLogAccount.account_address == req_query.account_address)
            .limit(1)
        )
    ).first()
    if log_account is None:
        raise HTTPException(status_code=404, detail="account is not exists")

    # Get frozen log
    if FREEZE_LOG_CONTRACT_ADDRESS is None:
        raise HTTPException(
            status_code=500, detail="FREEZE_LOG_CONTRACT_ADDRESS is not set"
        )
    log_contract = FreezeLogContract(
        log_account=log_account, contract_address=FREEZE_LOG_CONTRACT_ADDRESS
    )
    block_number, freezing_grace_block_count, log_message = await log_contract.get_log(
        log_index=log_index
    )

    return json_response(
        {
            "block_number": block_number,
            "freezing_grace_block_count": freezing_grace_block_count,
            "log_message": log_message,
        }
    )
