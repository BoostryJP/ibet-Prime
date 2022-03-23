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
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends
)
from fastapi.exceptions import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import (
    Session,
    aliased
)
from sqlalchemy.sql import func
from sha3 import keccak_256
from coincurve import PublicKey
from Crypto import Random
from Crypto.PublicKey import RSA
from eth_keyfile import decode_keyfile_json
from eth_utils import to_checksum_address
import eth_keyfile
import boto3

from config import (
    EOA_PASSWORD_PATTERN,
    EOA_PASSWORD_PATTERN_MSG,
    E2E_MESSAGING_CONTRACT_ADDRESS,
    E2E_MESSAGING_RSA_PASSPHRASE_PATTERN,
    E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG,
    E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE,
    E2EE_REQUEST_ENABLED,
    AWS_REGION_NAME,
    AWS_KMS_GENERATE_RANDOM_ENABLED
)
from app.database import db_session
from app.model.schema import (
    E2EMessagingAccountCreateKeyRequest,
    E2EMessagingAccountUpdateRequest,
    E2EMessagingAccountGenerateRsaKeyRequest,
    E2EMessagingAccountChangeEOAPasswordRequest,
    E2EMessagingAccountChangeRSAPassphraseRequest,
    E2EMessagingAccountResponse
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.utils.docs_utils import get_routers_responses
from app.model.db import (
    AccountRsaStatus,
    E2EMessagingAccount,
    E2EMessagingAccountRsaKey,
    TransactionLock
)
from app.model.blockchain.e2e_messaging import E2EMessaging
from app.exceptions import (
    InvalidParameterError,
    SendTransactionError
)
from app import log

LOG = log.get_logger()

router = APIRouter(tags=["e2e_messaging_account"])


# POST: /e2e_messaging_accounts
@router.post(
    "/e2e_messaging_accounts",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(422, InvalidParameterError)
)
def create_key(
        data: E2EMessagingAccountCreateKeyRequest,
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
    _account = E2EMessagingAccount()
    _account.account_address = addr
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    _account.rsa_key_generate_interval = data.rsa_key_generate_interval
    _account.rsa_generation = data.rsa_generation
    _account.is_deleted = False
    db.add(_account)

    # Insert initial transaction execution management record
    _tm = TransactionLock()
    _tm.tx_from = addr
    db.add(_tm)

    db.commit()

    return {
        "account_address": _account.account_address,
        "rsa_key_generate_interval": _account.rsa_key_generate_interval,
        "rsa_generation": _account.rsa_generation,
        "rsa_public_key": None,
        "rsa_status": AccountRsaStatus.UNSET.value,
        "is_deleted": _account.is_deleted
    }


# GET: /e2e_messaging_accounts
@router.get(
    "/e2e_messaging_accounts",
    response_model=List[E2EMessagingAccountResponse]
)
def list_all_accounts(db: Session = Depends(db_session)):
    """List all e2e messaging accounts"""

    # Create query to get the latest RSA key
    # NOTE:
    #   SELECT * FROM e2e_messaging_account_rsa_key t1
    #   WHERE block_timestamp = (
    #     SELECT max(block_timestamp) FROM e2e_messaging_account_rsa_key t2
    #     WHERE t2.account_address = t1.account_address
    #   )
    rsa_key_aliased = aliased(E2EMessagingAccountRsaKey)
    subquery_max = db.query(func.max(rsa_key_aliased.block_timestamp)). \
        filter(rsa_key_aliased.account_address == E2EMessagingAccountRsaKey.account_address)
    subquery = db.query(E2EMessagingAccountRsaKey). \
        filter(E2EMessagingAccountRsaKey.block_timestamp == subquery_max)
    latest_rsa_key = aliased(E2EMessagingAccountRsaKey, subquery.subquery("latest_rsa_key"), adapt_on_names=True)

    # Register key data to the DB
    _accounts = db.query(E2EMessagingAccount, latest_rsa_key.rsa_public_key). \
        outerjoin(latest_rsa_key, E2EMessagingAccount.account_address == latest_rsa_key.account_address). \
        order_by(E2EMessagingAccount.account_address). \
        all()

    account_list = []
    for _account, rsa_public_key in _accounts:
        if rsa_public_key is not None:
            rsa_status = AccountRsaStatus.SET.value
        else:
            rsa_status = AccountRsaStatus.UNSET.value

        account_list.append({
            "account_address": _account.account_address,
            "rsa_key_generate_interval": _account.rsa_key_generate_interval,
            "rsa_generation": _account.rsa_generation,
            "rsa_public_key": rsa_public_key,
            "rsa_status": rsa_status,
            "is_deleted": _account.is_deleted
        })

    return account_list


# GET: /e2e_messaging_accounts/{account_address}
@router.get(
    "/e2e_messaging_accounts/{account_address}",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(404)
)
def retrieve_account(account_address: str, db: Session = Depends(db_session)):
    """Retrieve an e2e messaging account"""

    _account = db.query(E2EMessagingAccount). \
        filter(E2EMessagingAccount.account_address == account_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="e2e messaging account is not exists")

    _rsa_key = db.query(E2EMessagingAccountRsaKey). \
        filter(E2EMessagingAccountRsaKey.account_address == account_address). \
        order_by(desc(E2EMessagingAccountRsaKey.block_timestamp)). \
        first()
    if _rsa_key is not None:
        rsa_public_key = _rsa_key.rsa_public_key
        rsa_status = AccountRsaStatus.SET.value
    else:
        rsa_public_key = None
        rsa_status = AccountRsaStatus.UNSET.value

    return {
        "account_address": _account.account_address,
        "rsa_key_generate_interval": _account.rsa_key_generate_interval,
        "rsa_generation": _account.rsa_generation,
        "rsa_public_key": rsa_public_key,
        "rsa_status": rsa_status,
        "is_deleted": _account.is_deleted
    }


# POST: /e2e_messaging_accounts/{account_address}
@router.post(
    "/e2e_messaging_accounts/{account_address}",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(422, 404)
)
def update_account(
        account_address: str,
        data: E2EMessagingAccountUpdateRequest,
        db: Session = Depends(db_session)):
    """Update an e2e messaging account"""

    _account = db.query(E2EMessagingAccount). \
        filter(E2EMessagingAccount.account_address == account_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="e2e messaging account is not exists")

    _rsa_key = db.query(E2EMessagingAccountRsaKey). \
        filter(E2EMessagingAccountRsaKey.account_address == account_address). \
        order_by(desc(E2EMessagingAccountRsaKey.block_timestamp)). \
        first()
    if _rsa_key is not None:
        rsa_public_key = _rsa_key.rsa_public_key
        rsa_status = AccountRsaStatus.SET.value
    else:
        rsa_public_key = None
        rsa_status = AccountRsaStatus.UNSET.value

    _account.rsa_key_generate_interval = data.rsa_key_generate_interval
    _account.rsa_generation = data.rsa_generation
    db.merge(_account)

    db.commit()

    return {
        "account_address": _account.account_address,
        "rsa_key_generate_interval": _account.rsa_key_generate_interval,
        "rsa_generation": _account.rsa_generation,
        "rsa_public_key": rsa_public_key,
        "rsa_status": rsa_status,
        "is_deleted": _account.is_deleted
    }


# DELETE: /e2e_messaging_accounts/{account_address}
@router.delete(
    "/e2e_messaging_accounts/{account_address}",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(404)
)
def delete_account(account_address: str, db: Session = Depends(db_session)):
    """Logically delete an e2e messaging account"""

    _account = db.query(E2EMessagingAccount). \
        filter(E2EMessagingAccount.account_address == account_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="e2e messaging account is not exists")

    _account.is_deleted = True
    db.merge(_account)

    # NOTE: RSA key is physically delete
    db.query(E2EMessagingAccountRsaKey). \
        filter(E2EMessagingAccountRsaKey.account_address == account_address). \
        delete()

    db.commit()

    return {
        "account_address": _account.account_address,
        "rsa_key_generate_interval": _account.rsa_key_generate_interval,
        "rsa_generation": _account.rsa_generation,
        "rsa_public_key": None,
        "rsa_status": AccountRsaStatus.UNSET.value,
        "is_deleted": _account.is_deleted
    }


# POST: /e2e_messaging_accounts/{account_address}/rsakey
@router.post(
    "/e2e_messaging_accounts/{account_address}/rsakey",
    response_model=E2EMessagingAccountResponse,
    responses=get_routers_responses(422, 404, InvalidParameterError, SendTransactionError)
)
def generate_rsa_key(
        account_address: str,
        data: E2EMessagingAccountGenerateRsaKeyRequest,
        db: Session = Depends(db_session)):
    """Generate RSA key"""

    # Get E2E Messaging Account
    _account = db.query(E2EMessagingAccount). \
        filter(E2EMessagingAccount.account_address == account_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="e2e messaging account is not exists")

    # Check Password Policy
    if data.rsa_passphrase:
        rsa_passphrase = E2EEUtils.decrypt(data.rsa_passphrase) if E2EE_REQUEST_ENABLED else data.rsa_passphrase
        if not re.match(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
            raise InvalidParameterError(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG)
    else:
        rsa_passphrase = E2E_MESSAGING_RSA_DEFAULT_PASSPHRASE

    # Generate RSA Key
    random_func = Random.new().read
    rsa = RSA.generate(4096, random_func)
    rsa_private_key = rsa.exportKey(format="PEM", passphrase=rsa_passphrase).decode()
    rsa_public_key = rsa.publickey().exportKey().decode()

    # Get private key
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
    keyfile_json = _account.keyfile
    private_key = decode_keyfile_json(
        raw_keyfile_json=keyfile_json,
        password=decrypt_password.encode("utf-8")
    )

    # Send transaction
    try:
        tx_hash, _ = E2EMessaging.set_public_key(
            contract_address=E2E_MESSAGING_CONTRACT_ADDRESS,
            public_key=rsa_public_key,
            key_type="RSA4096",
            tx_from=account_address,
            private_key=private_key
        )
    except SendTransactionError:
        raise SendTransactionError("failed to send transaction")

    # Register RSA key to DB
    block = ContractUtils.get_block_by_transaction_hash(tx_hash=tx_hash)
    _account_rsa_key = E2EMessagingAccountRsaKey()
    _account_rsa_key.transaction_hash = tx_hash
    _account_rsa_key.account_address = account_address
    _account_rsa_key.rsa_private_key = rsa_private_key
    _account_rsa_key.rsa_public_key = rsa_public_key
    _account_rsa_key.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    _account_rsa_key.block_timestamp = datetime.utcfromtimestamp(block["timestamp"])
    db.add(_account_rsa_key)

    return {
        "account_address": _account.account_address,
        "rsa_key_generate_interval": _account.rsa_key_generate_interval,
        "rsa_generation": _account.rsa_generation,
        "rsa_public_key": rsa_public_key,
        "rsa_status": AccountRsaStatus.SET.value,
        "is_deleted": _account.is_deleted
    }


# POST: /e2e_messaging_accounts/{account_address}/eoa_password
@router.post(
    "/e2e_messaging_accounts/{account_address}/eoa_password",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError))
def change_eoa_password(
        account_address: str,
        data: E2EMessagingAccountChangeEOAPasswordRequest,
        db: Session = Depends(db_session)):
    """Change EOA Password"""

    # Get E2E Messaging Account
    _account = db.query(E2EMessagingAccount). \
        filter(E2EMessagingAccount.account_address == account_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="e2e messaging account is not exists")

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


# POST: /e2e_messaging_accounts/{account_address}/rsa_passphrase
@router.post(
    "/e2e_messaging_accounts/{account_address}/rsa_passphrase",
    response_model=None,
    responses=get_routers_responses(422, 404, InvalidParameterError))
def change_rsa_passphrase(
        account_address: str,
        data: E2EMessagingAccountChangeRSAPassphraseRequest,
        db: Session = Depends(db_session)):
    """Change RSA Passphrase"""

    # Get E2E Messaging Account
    _account = db.query(E2EMessagingAccount). \
        filter(E2EMessagingAccount.account_address == account_address). \
        first()
    if _account is None:
        raise HTTPException(status_code=404, detail="e2e messaging account is not exists")

    # Get latest RSA key
    _rsa_key = db.query(E2EMessagingAccountRsaKey). \
        filter(E2EMessagingAccountRsaKey.account_address == account_address). \
        order_by(desc(E2EMessagingAccountRsaKey.block_timestamp)). \
        first()
    if _rsa_key is None:
        raise HTTPException(status_code=404, detail="e2e messaging rsa key is not exists")

    # Check Old Passphrase
    old_rsa_passphrase = E2EEUtils.decrypt(data.old_rsa_passphrase) if E2EE_REQUEST_ENABLED else data.old_rsa_passphrase
    correct_rsa_passphrase = E2EEUtils.decrypt(_rsa_key.rsa_passphrase)
    if old_rsa_passphrase != correct_rsa_passphrase:
        raise InvalidParameterError("old passphrase mismatch")

    # Check Password Policy
    rsa_passphrase = E2EEUtils.decrypt(data.rsa_passphrase) if E2EE_REQUEST_ENABLED else data.rsa_passphrase
    if not re.match(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN, rsa_passphrase):
        raise InvalidParameterError(E2E_MESSAGING_RSA_PASSPHRASE_PATTERN_MSG)

    # Create New RSA Private Key
    old_rsa_private_key = _rsa_key.rsa_private_key
    rsa_key = RSA.importKey(old_rsa_private_key, old_rsa_passphrase)
    rsa_private_key = rsa_key.exportKey(format="PEM", passphrase=rsa_passphrase).decode()

    # Update data to the DB
    _rsa_key.rsa_private_key = rsa_private_key
    _rsa_key.rsa_passphrase = E2EEUtils.encrypt(rsa_passphrase)
    db.merge(_rsa_key)

    db.commit()

    return
