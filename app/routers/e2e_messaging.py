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
import json
import re
import secrets
from datetime import datetime
from typing import List, Optional, Sequence

import boto3
import eth_keyfile
import pytz
from coincurve import PublicKey
from Crypto import Random
from Crypto.PublicKey import RSA
from eth_utils import keccak, to_checksum_address
from fastapi import APIRouter, Path, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import and_, asc, delete, desc, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func

from app.database import DBSession
from app.exceptions import (
    ContractRevertError,
    InvalidParameterError,
    SendTransactionError,
)
from app.model.blockchain import E2EMessaging
from app.model.db import (
    E2EMessagingAccount,
    E2EMessagingAccountRsaKey,
    IDXE2EMessaging,
    TransactionLock,
)
from app.model.schema import (
    E2EMessagingAccountChangeEOAPasswordRequest,
    E2EMessagingAccountChangeRSAPassphraseRequest,
    E2EMessagingAccountCreateRequest,
    E2EMessagingAccountResponse,
    E2EMessagingAccountUpdateRsaKeyRequest,
    E2EMessagingResponse,
    ListAllE2EMessagingResponse,
)
from app.utils.contract_utils import ContractUtils
from app.utils.docs_utils import get_routers_responses
from app.utils.e2ee_utils import E2EEUtils
from app.utils.fastapi_utils import json_response
from config import (
    AWS_KMS_GENERATE_RANDOM_ENABLED,
    AWS_REGION_NAME,
    E2E_MESSAGING_CONTRACT_ADDRESS,
    E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE,
    E2E_MESSAGING_RSA_PASSPHRASE_PATTERN,
    E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG,
    E2EE_REQUEST_ENABLED,
    EOA_PASSWORD_PATTERN,
    EOA_PASSWORD_PATTERN_MSG,
    TZ,
)

router = APIRouter(prefix="/e2e_messaging", tags=["messaging"])

local_tz = pytz.timezone(TZ)
utc_tz = pytz.timezone("UTC")


# POST: /e2e_messaging/accounts
@router.post(
    "/accounts",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(
        422, InvalidParameterError, SendTransactionError, ContractRevertError
    ),
)
def create_account(
    db: DBSession,
    data: E2EMessagingAccountCreateRequest,
):
    """Create Account"""
    # Check Password Policy(EOA password)
    eoa_password = (
        E2EEUtils.decrypt(data.eoa_password)
        if E2EE_REQUEST_ENABLED
        else data.eoa_password
    )
    if not re.match(EOA_PASSWORD_PATTERN, eoa_password):
        raise InvalidParameterError(EOA_PASSWORD_PATTERN_MSG)

    # Check Password Policy(RSA passphrase)
    if data.rsa_passphrase:
        rsa_passphrase = (
            E2EEUtils.decrypt(data.rsa_passphrase)
            if E2EE_REQUEST_ENABLED
            else data.rsa_passphrase
        )
        if not re.match(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
            raise InvalidParameterError(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG)
    else:
        rsa_passphrase = E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE

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

    # Generate RSA Key
    random_func = Random.new().read
    rsa = RSA.generate(4096, random_func)
    rsa_private_key = rsa.exportKey(format="PEM", passphrase=rsa_passphrase).decode()
    rsa_public_key = rsa.publickey().exportKey().decode()

    # Send transaction
    try:
        tx_hash, _ = E2EMessaging(E2E_MESSAGING_CONTRACT_ADDRESS).set_public_key(
            public_key=rsa_public_key,
            key_type="RSA4096",
            tx_from=addr,
            private_key=private_key,
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Register account data to the DB
    _account = E2EMessagingAccount()
    _account.account_address = addr
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    _account.rsa_key_generate_interval = data.rsa_key_generate_interval
    _account.rsa_generation = data.rsa_generation
    _account.is_deleted = False
    db.add(_account)

    # Register RSA key data to DB
    block = ContractUtils.get_block_by_transaction_hash(tx_hash=tx_hash)
    _account_rsa_key = E2EMessagingAccountRsaKey()
    _account_rsa_key.transaction_hash = tx_hash
    _account_rsa_key.account_address = addr
    _account_rsa_key.rsa_private_key = rsa_private_key
    _account_rsa_key.rsa_public_key = rsa_public_key
    _account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    _account_rsa_key.block_timestamp = datetime.utcfromtimestamp(block["timestamp"])
    db.add(_account_rsa_key)

    # Insert initial transaction execution management record
    _tm = TransactionLock()
    _tm.tx_from = addr
    db.add(_tm)

    db.commit()

    return json_response(
        {
            "account_address": _account.account_address,
            "rsa_key_generate_interval": _account.rsa_key_generate_interval,
            "rsa_generation": _account.rsa_generation,
            "rsa_public_key": rsa_public_key,
            "is_deleted": _account.is_deleted,
        }
    )


# GET: /e2e_messaging/accounts
@router.get("/accounts", response_model=List[E2EMessagingAccountResponse])
def list_all_accounts(db: DBSession):
    """List all e2e messaging accounts"""

    # Create query to get the latest RSA key
    # NOTE:
    #   SELECT * FROM e2e_messaging_account_rsa_key t1
    #   WHERE block_timestamp = (
    #     SELECT max(block_timestamp) FROM e2e_messaging_account_rsa_key t2
    #     WHERE t2.account_address = t1.account_address
    #   )
    rsa_key_aliased = aliased(E2EMessagingAccountRsaKey)
    subquery_max = (
        select(func.max(rsa_key_aliased.block_timestamp))
        .where(
            rsa_key_aliased.account_address == E2EMessagingAccountRsaKey.account_address
        )
        .scalar_subquery()
    )

    subquery = select(E2EMessagingAccountRsaKey).where(
        E2EMessagingAccountRsaKey.block_timestamp == subquery_max
    )
    latest_rsa_key = aliased(
        E2EMessagingAccountRsaKey,
        subquery.subquery("latest_rsa_key"),
        adapt_on_names=True,
    )

    # Get E2E Messaging Accounts
    _accounts: Sequence[tuple[E2EMessagingAccount, str]] = (
        db.execute(
            select(E2EMessagingAccount, latest_rsa_key.rsa_public_key)
            .outerjoin(
                latest_rsa_key,
                E2EMessagingAccount.account_address == latest_rsa_key.account_address,
            )
            .order_by(E2EMessagingAccount.account_address)
        )
        .tuples()
        .all()
    )

    account_list = []
    for _account, rsa_public_key in _accounts:
        account_list.append(
            {
                "account_address": _account.account_address,
                "rsa_key_generate_interval": _account.rsa_key_generate_interval,
                "rsa_generation": _account.rsa_generation,
                "rsa_public_key": rsa_public_key,
                "is_deleted": _account.is_deleted,
            }
        )

    return json_response(account_list)


# GET: /e2e_messaging/accounts/{account_address}
@router.get(
    "/accounts/{account_address}",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(404),
)
def retrieve_account(db: DBSession, account_address: str):
    """Retrieve an e2e messaging account"""

    _account: E2EMessagingAccount | None = db.scalars(
        select(E2EMessagingAccount)
        .where(E2EMessagingAccount.account_address == account_address)
        .limit(1)
    ).first()
    if _account is None:
        raise HTTPException(
            status_code=404, detail="e2e messaging account is not exists"
        )

    rsa_public_key = None
    if _account.is_deleted is False:
        _rsa_key = db.scalars(
            select(E2EMessagingAccountRsaKey)
            .where(E2EMessagingAccountRsaKey.account_address == account_address)
            .order_by(desc(E2EMessagingAccountRsaKey.block_timestamp))
            .limit(1)
        ).first()
        rsa_public_key = _rsa_key.rsa_public_key

    return json_response(
        {
            "account_address": _account.account_address,
            "rsa_key_generate_interval": _account.rsa_key_generate_interval,
            "rsa_generation": _account.rsa_generation,
            "rsa_public_key": rsa_public_key,
            "is_deleted": _account.is_deleted,
        }
    )


# DELETE: /e2e_messaging/accounts/{account_address}
@router.delete(
    "/accounts/{account_address}",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(404),
)
def delete_account(db: DBSession, account_address: str):
    """Logically delete an e2e messaging account"""

    _account: E2EMessagingAccount | None = db.scalars(
        select(E2EMessagingAccount)
        .where(E2EMessagingAccount.account_address == account_address)
        .limit(1)
    ).first()
    if _account is None:
        raise HTTPException(
            status_code=404, detail="e2e messaging account is not exists"
        )

    _account.is_deleted = True
    db.merge(_account)

    # NOTE: RSA key is physically delete
    db.execute(
        delete(E2EMessagingAccountRsaKey).where(
            E2EMessagingAccountRsaKey.account_address == account_address
        )
    )
    db.commit()

    return json_response(
        {
            "account_address": _account.account_address,
            "rsa_key_generate_interval": _account.rsa_key_generate_interval,
            "rsa_generation": _account.rsa_generation,
            "rsa_public_key": None,
            "is_deleted": _account.is_deleted,
        }
    )


# POST: /e2e_messaging/accounts/{account_address}/rsa_key
@router.post(
    "/accounts/{account_address}/rsa_key",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(422, 404),
)
def update_account_rsa_key(
    db: DBSession,
    account_address: str,
    data: E2EMessagingAccountUpdateRsaKeyRequest,
):
    """Update an e2e messaging account rsa key"""

    _account = db.scalars(
        select(E2EMessagingAccount)
        .where(
            and_(
                E2EMessagingAccount.account_address == account_address,
                E2EMessagingAccount.is_deleted == False,
            )
        )
        .limit(1)
    ).first()
    if _account is None:
        raise HTTPException(
            status_code=404, detail="e2e messaging account is not exists"
        )

    _rsa_key: E2EMessagingAccountRsaKey | None = db.scalars(
        select(E2EMessagingAccountRsaKey)
        .where(E2EMessagingAccountRsaKey.account_address == account_address)
        .order_by(desc(E2EMessagingAccountRsaKey.block_timestamp))
        .limit(1)
    ).first()

    _account.rsa_key_generate_interval = data.rsa_key_generate_interval
    _account.rsa_generation = data.rsa_generation
    db.merge(_account)
    db.commit()

    return json_response(
        {
            "account_address": _account.account_address,
            "rsa_key_generate_interval": _account.rsa_key_generate_interval,
            "rsa_generation": _account.rsa_generation,
            "rsa_public_key": _rsa_key.rsa_public_key,
            "is_deleted": _account.is_deleted,
        }
    )


# POST: /e2e_messaging/accounts/{account_address}/eoa_password
@router.post(
    "/accounts/{account_address}/eoa_password",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def change_eoa_password(
    db: DBSession,
    account_address: str,
    data: E2EMessagingAccountChangeEOAPasswordRequest,
):
    """Change Account's EOA Password"""

    # Get E2E Messaging Account
    _account: E2EMessagingAccount | None = db.scalars(
        select(E2EMessagingAccount)
        .where(E2EMessagingAccount.account_address == account_address)
        .limit(1)
    ).first()
    if _account is None:
        raise HTTPException(
            status_code=404, detail="e2e messaging account is not exists"
        )

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
    db.merge(_account)

    db.commit()

    return


# POST: /e2e_messaging/accounts/{account_address}/rsa_passphrase
@router.post(
    "/accounts/{account_address}/rsa_passphrase",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError),
)
def change_rsa_passphrase(
    db: DBSession,
    account_address: str,
    data: E2EMessagingAccountChangeRSAPassphraseRequest,
):
    """Change Account's RSA Passphrase"""

    # Get E2E Messaging Account
    _account: E2EMessagingAccount | None = db.scalars(
        select(E2EMessagingAccount)
        .where(E2EMessagingAccount.account_address == account_address)
        .limit(1)
    ).first()
    if _account is None:
        raise HTTPException(
            status_code=404, detail="e2e messaging account is not exists"
        )

    # Get latest RSA key
    _rsa_key = db.scalars(
        select(E2EMessagingAccountRsaKey)
        .where(E2EMessagingAccountRsaKey.account_address == account_address)
        .order_by(desc(E2EMessagingAccountRsaKey.block_timestamp))
        .limit(1)
    ).first()
    if _rsa_key is None:
        raise HTTPException(
            status_code=404, detail="e2e messaging rsa key is not exists"
        )

    # Check Old Passphrase
    old_rsa_passphrase = (
        E2EEUtils.decrypt(data.old_rsa_passphrase)
        if E2EE_REQUEST_ENABLED
        else data.old_rsa_passphrase
    )
    correct_rsa_passphrase = E2EEUtils.decrypt(_rsa_key.rsa_passphrase)
    if old_rsa_passphrase != correct_rsa_passphrase:
        raise InvalidParameterError("old passphrase mismatch")

    # Check Password Policy
    rsa_passphrase = (
        E2EEUtils.decrypt(data.rsa_passphrase)
        if E2EE_REQUEST_ENABLED
        else data.rsa_passphrase
    )
    if not re.match(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
        raise InvalidParameterError(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG)

    # Update RSA Passphrase
    old_rsa_private_key = _rsa_key.rsa_private_key
    rsa_key = RSA.importKey(old_rsa_private_key, old_rsa_passphrase)
    rsa_private_key = rsa_key.exportKey(
        format="PEM", passphrase=rsa_passphrase
    ).decode()

    # Update data to the DB
    _rsa_key.rsa_private_key = rsa_private_key
    _rsa_key.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    db.merge(_rsa_key)

    db.commit()

    return


# GET: /e2e_messaging/messages
@router.get(
    "/messages",
    response_model=ListAllE2EMessagingResponse,
    responses=get_routers_responses(422),
)
def list_all_e2e_messages(
    db: DBSession,
    from_address: Optional[str] = Query(None),
    to_address: Optional[str] = Query(None),
    _type: Optional[str] = Query(None, alias="type"),
    message: Optional[str] = Query(None, description="partial match"),
    offset: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
):
    """List all e2e message"""

    # Get E2E Messaging
    stmt = select(IDXE2EMessaging).order_by(asc(IDXE2EMessaging.id))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Search Filter
    if from_address is not None:
        stmt = stmt.where(IDXE2EMessaging.from_address == from_address)
    if to_address is not None:
        stmt = stmt.where(IDXE2EMessaging.to_address == to_address)
    if _type is not None:
        stmt = stmt.where(IDXE2EMessaging.type == _type)
    if message is not None:
        stmt = stmt.where(IDXE2EMessaging.message.like("%" + message + "%"))

    count = db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Pagination
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _e2e_messaging_list: Sequence[IDXE2EMessaging] = db.scalars(stmt).all()

    e2e_messages = []
    for _e2e_messaging in _e2e_messaging_list:
        send_timestamp_formatted = (
            utc_tz.localize(_e2e_messaging.send_timestamp)
            .astimezone(local_tz)
            .isoformat()
        )
        try:
            # json or list string decode
            message = json.loads(_e2e_messaging.message)
        except json.decoder.JSONDecodeError:
            message = _e2e_messaging.message
        e2e_messages.append(
            {
                "id": _e2e_messaging.id,
                "from_address": _e2e_messaging.from_address,
                "to_address": _e2e_messaging.to_address,
                "type": _e2e_messaging.type,
                "message": message,
                "send_timestamp": send_timestamp_formatted,
            }
        )

    resp = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "e2e_messages": e2e_messages,
    }

    return json_response(resp)


# GET: /e2e_messaging/messages/{id}
@router.get(
    "/messages/{id}",
    response_model=E2EMessagingResponse,
    responses=get_routers_responses(422, 404),
)
def retrieve_e2e_messaging(db: DBSession, _id: int = Path(..., alias="id")):
    """Retrieve an e2e message"""

    # Get E2E Messaging
    _e2e_messaging: IDXE2EMessaging | None = db.scalars(
        select(IDXE2EMessaging).where(IDXE2EMessaging.id == _id).limit(1)
    ).first()
    if _e2e_messaging is None:
        raise HTTPException(status_code=404, detail="e2e messaging not found")

    send_timestamp_formatted = (
        utc_tz.localize(_e2e_messaging.send_timestamp).astimezone(local_tz).isoformat()
    )
    try:
        # json or list string decode
        message = json.loads(_e2e_messaging.message)
    except json.decoder.JSONDecodeError:
        message = _e2e_messaging.message

    return json_response(
        {
            "id": _e2e_messaging.id,
            "from_address": _e2e_messaging.from_address,
            "to_address": _e2e_messaging.to_address,
            "type": _e2e_messaging.type,
            "message": message,
            "send_timestamp": send_timestamp_formatted,
        }
    )
