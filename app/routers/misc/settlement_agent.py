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
from datetime import UTC
from typing import Sequence

import boto3
import eth_keyfile
import pytz
from coincurve import PublicKey
from eth_keyfile import decode_keyfile_json
from eth_utils import keccak, to_checksum_address
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, func, select

import config
from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError, SendTransactionError
from app.model.blockchain.exchange import IbetSecurityTokenDVP
from app.model.blockchain.tx_params.ibet_security_token_dvp import (
    AbortDeliveryParams,
    FinishDeliveryParams,
)
from app.model.db import DVPAgentAccount, IDXDelivery, TransactionLock
from app.model.schema import (
    AbortDVPDeliveryRequest,
    CreateDVPAgentAccountRequest,
    DVPAgentAccountChangeEOAPasswordRequest,
    DVPAgentAccountResponse,
    FinishDVPDeliveryRequest,
    ListAllDVPAgentAccountResponse,
    ListAllDVPAgentDeliveriesQuery,
    ListAllDVPDeliveriesResponse,
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
)

router = APIRouter(prefix="/settlement", tags=["[misc] settlement_agent"])

local_tz = pytz.timezone(config.TZ)


# POST: /settlement/dvp/agent/accounts
@router.post(
    "/dvp/agent/accounts",
    operation_id="CreateDVPAgentAccount",
    response_model=DVPAgentAccountResponse,
    responses=get_routers_responses(422, InvalidParameterError),
)
async def create_account(
    db: DBAsyncSession,
    create_req: CreateDVPAgentAccountRequest,
):
    """Create DVP-Payment Agent Account"""

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
    public_key = PublicKey.from_valid_secret(private_key).format(compressed=False)[1:]
    addr = to_checksum_address(keccak(public_key)[-20:])
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
    )

    # Register account data to the DB
    _account = DVPAgentAccount()
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


# GET: /settlement/dvp/agent/accounts
@router.get(
    "/dvp/agent/accounts",
    operation_id="ListAllDVPAgentAccount",
    response_model=ListAllDVPAgentAccountResponse,
)
async def list_all_accounts(db: DBAsyncSession):
    """List all DVP-Payment Agent accounts"""

    _accounts: Sequence[DVPAgentAccount] = (
        await db.scalars(select(DVPAgentAccount))
    ).all()

    account_list = [
        {
            "account_address": _account.account_address,
            "is_deleted": _account.is_deleted,
        }
        for _account in _accounts
    ]
    return json_response(account_list)


# DELETE: /settlement/dvp/agent/accounts/{account_address}
@router.delete(
    "/dvp/agent/account/{account_address}",
    operation_id="DeleteDVPAgentAccount",
    response_model=DVPAgentAccountResponse,
    responses=get_routers_responses(404),
)
async def delete_account(db: DBAsyncSession, account_address: str):
    """Logically delete an DVP-Payment Agent Account"""

    # Search for an account
    _account: DVPAgentAccount | None = (
        await db.scalars(
            select(DVPAgentAccount)
            .where(DVPAgentAccount.account_address == account_address)
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


# POST: /settlement/dvp/agent/accounts/{account_address}/eoa_password
@router.post(
    "/dvp/agent/account/{account_address}/eoa_password",
    operation_id="ChangeDVPAgentAccountPassword",
    response_model=None,
    responses=get_routers_responses(404, 422, InvalidParameterError),
)
async def change_eoa_password(
    db: DBAsyncSession,
    account_address: str,
    change_req: DVPAgentAccountChangeEOAPasswordRequest,
):
    """Change Agent's EOA Password"""

    # Search for an account
    _account: DVPAgentAccount | None = (
        await db.scalars(
            select(DVPAgentAccount)
            .where(DVPAgentAccount.account_address == account_address)
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
    private_key = eth_keyfile.decode_keyfile_json(
        raw_keyfile_json=_account.keyfile, password=old_eoa_password.encode("utf-8")
    )

    # Create New Ethereum Key File
    keyfile_json = eth_keyfile.create_keyfile_json(
        private_key=private_key, password=eoa_password.encode("utf-8"), kdf="pbkdf2"
    )

    # Update data
    _account.keyfile = keyfile_json
    _account.eoa_password = E2EEUtils.encrypt(eoa_password)
    await db.merge(_account)

    await db.commit()

    return


# GET: /settlement/dvp/agent/{exchange_address}/deliveries
@router.get(
    "/dvp/agent/{exchange_address}/deliveries",
    operation_id="ListAllDVPAgentDeliveries",
    response_model=ListAllDVPDeliveriesResponse,
    responses=get_routers_responses(404, 422, InvalidParameterError),
)
async def list_all_dvp_agent_deliveries(
    db: DBAsyncSession,
    exchange_address: str,
    request_query: ListAllDVPAgentDeliveriesQuery = Depends(),
):
    """List all DVP deliveries for paying agent"""
    stmt = select(IDXDelivery).where(
        and_(
            IDXDelivery.exchange_address == exchange_address,
            IDXDelivery.agent_address == request_query.agent_address,
        )
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    if request_query.token_address is not None:
        stmt = stmt.where(IDXDelivery.token_address == request_query.token_address)
    if request_query.seller_address is not None:
        stmt = stmt.where(IDXDelivery.seller_address == request_query.seller_address)
    if request_query.valid is not None:
        stmt = stmt.where(IDXDelivery.valid == request_query.valid)
    if request_query.status is not None:
        stmt = stmt.where(IDXDelivery.status == request_query.status)
    if request_query.create_blocktimestamp_from is not None:
        stmt = stmt.where(
            IDXDelivery.create_blocktimestamp
            >= local_tz.localize(request_query.create_blocktimestamp_from).astimezone(
                tz=UTC
            )
        )
    if request_query.create_blocktimestamp_to is not None:
        stmt = stmt.where(
            IDXDelivery.create_blocktimestamp
            <= local_tz.localize(request_query.create_blocktimestamp_to).astimezone(
                tz=UTC
            )
        )

    count = await db.scalar(select(func.count()).select_from(stmt.subquery()))

    # Sort
    if request_query.sort_order == 0:  # ASC
        stmt = stmt.order_by(IDXDelivery.create_blocktimestamp)
    else:  # DESC
        stmt = stmt.order_by(desc(IDXDelivery.create_blocktimestamp))

    # Pagination
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)
    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)

    _deliveries: Sequence[IDXDelivery] = (await db.scalars(stmt)).all()

    deliveries = []
    for _delivery in _deliveries:
        if _delivery.create_blocktimestamp is not None:
            create_blocktimestamp = (
                local_tz.localize(_delivery.create_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            create_blocktimestamp = None
        if _delivery.cancel_blocktimestamp is not None:
            cancel_blocktimestamp = (
                local_tz.localize(_delivery.cancel_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            cancel_blocktimestamp = None
        if _delivery.confirm_blocktimestamp is not None:
            confirm_blocktimestamp = (
                local_tz.localize(_delivery.confirm_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            confirm_blocktimestamp = None
        if _delivery.finish_blocktimestamp is not None:
            finish_blocktimestamp = (
                local_tz.localize(_delivery.finish_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            finish_blocktimestamp = None
        if _delivery.abort_blocktimestamp is not None:
            abort_blocktimestamp = (
                local_tz.localize(_delivery.abort_blocktimestamp)
                .astimezone(tz=UTC)
                .isoformat()
            )
        else:
            abort_blocktimestamp = None

        deliveries.append(
            {
                "exchange_address": _delivery.exchange_address,
                "delivery_id": _delivery.delivery_id,
                "token_address": _delivery.token_address,
                "buyer_address": _delivery.buyer_address,
                "seller_address": _delivery.seller_address,
                "amount": _delivery.amount,
                "agent_address": _delivery.agent_address,
                "data": _delivery.data,
                "create_blocktimestamp": create_blocktimestamp,
                "create_transaction_hash": _delivery.create_transaction_hash,
                "cancel_blocktimestamp": cancel_blocktimestamp,
                "cancel_transaction_hash": _delivery.cancel_transaction_hash,
                "confirm_blocktimestamp": confirm_blocktimestamp,
                "confirm_transaction_hash": _delivery.confirm_transaction_hash,
                "finish_blocktimestamp": finish_blocktimestamp,
                "finish_transaction_hash": _delivery.finish_transaction_hash,
                "abort_blocktimestamp": abort_blocktimestamp,
                "abort_transaction_hash": _delivery.abort_transaction_hash,
                "confirmed": _delivery.confirmed,
                "valid": _delivery.valid,
                "status": _delivery.status,
            }
        )

    return json_response(
        {
            "result_set": {
                "count": count,
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total,
            },
            "deliveries": deliveries,
        }
    )


# POST: /settlement/dvp/agent/{exchange_address}/delivery/{delivery_id}
@router.post(
    "/dvp/agent/{exchange_address}/delivery/{delivery_id}",
    operation_id="UpdateDVPAgentDelivery",
    response_model=None,
    responses=get_routers_responses(
        404, 422, InvalidParameterError, SendTransactionError
    ),
)
async def update_dvp_agent_delivery(
    db: DBAsyncSession,
    exchange_address: str,
    delivery_id: str,
    data: FinishDVPDeliveryRequest | AbortDVPDeliveryRequest,
):
    """Finish/Abort DVP delivery"""

    match data.operation_type:
        case "Finish":
            # Search for agent account
            agent_account: DVPAgentAccount | None = (
                await db.scalars(
                    select(DVPAgentAccount)
                    .where(DVPAgentAccount.account_address == data.account_address)
                    .limit(1)
                )
            ).first()
            if agent_account is None:
                raise HTTPException(
                    status_code=404, detail="agent account is not exists"
                )

            # Authentication
            eoa_password = (
                E2EEUtils.decrypt(data.eoa_password)
                if E2EE_REQUEST_ENABLED
                else data.eoa_password
            )
            correct_eoa_pass = E2EEUtils.decrypt(agent_account.eoa_password)
            if eoa_password != correct_eoa_pass:
                raise InvalidParameterError("password mismatch")

            # Get private key
            keyfile_json = agent_account.keyfile
            private_key = decode_keyfile_json(
                raw_keyfile_json=keyfile_json, password=correct_eoa_pass.encode("utf-8")
            )

            # Cancel delivery
            dvp_contract = IbetSecurityTokenDVP(contract_address=exchange_address)
            try:
                _data = {"delivery_id": delivery_id}
                await dvp_contract.finish_delivery(
                    data=FinishDeliveryParams(**_data),
                    tx_from=agent_account.account_address,
                    private_key=private_key,
                )
            except SendTransactionError:
                raise SendTransactionError("failed to finish delivery")
            return

        case "Abort":
            # Search for agent account
            agent_account: DVPAgentAccount | None = (
                await db.scalars(
                    select(DVPAgentAccount)
                    .where(DVPAgentAccount.account_address == data.account_address)
                    .limit(1)
                )
            ).first()
            if agent_account is None:
                raise HTTPException(
                    status_code=404, detail="agent account is not exists"
                )

            # Authentication
            eoa_password = (
                E2EEUtils.decrypt(data.eoa_password)
                if E2EE_REQUEST_ENABLED
                else data.eoa_password
            )
            correct_eoa_pass = E2EEUtils.decrypt(agent_account.eoa_password)
            if eoa_password != correct_eoa_pass:
                raise InvalidParameterError("password mismatch")

            # Get private key
            keyfile_json = agent_account.keyfile
            private_key = decode_keyfile_json(
                raw_keyfile_json=keyfile_json, password=correct_eoa_pass.encode("utf-8")
            )

            # Cancel delivery
            dvp_contract = IbetSecurityTokenDVP(contract_address=exchange_address)
            try:
                _data = {"delivery_id": delivery_id}
                await dvp_contract.abort_delivery(
                    data=AbortDeliveryParams(**_data),
                    tx_from=agent_account.account_address,
                    private_key=private_key,
                )
            except SendTransactionError:
                raise SendTransactionError("failed to abort delivery")
            return
