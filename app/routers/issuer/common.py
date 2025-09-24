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

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import log
from app.database import DBAsyncSession
from app.exceptions import ServiceUnavailableError
from app.model.db import EthereumNode, Node
from app.model.schema import BlockNumberResponse, E2EEResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.e2ee_utils import E2EEUtils
from app.utils.fastapi_utils import json_response
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper
from config import E2EE_REQUEST_ENABLED, IBET_WST_FEATURE_ENABLED

web3 = AsyncWeb3Wrapper()

LOG = log.get_logger()

router = APIRouter(tags=["common"])


# GET: /e2ee
@router.get("/e2ee", operation_id="GetE2EEncryptionKey", response_model=E2EEResponse)
async def e2e_encryption_key():
    """Get E2EE public key"""

    if not E2EE_REQUEST_ENABLED:
        return json_response({"public_key": None})

    _, public_key = E2EEUtils.get_key()

    return json_response({"public_key": public_key})


# GET: /healthcheck
@router.get(
    "/healthcheck",
    operation_id="ServiceHealthCheck",
    response_model=None,
    responses=get_routers_responses(ServiceUnavailableError),
)
async def service_health_check(db: DBAsyncSession):
    """Service health check

    Check following services are available:
    - Database
    - ibet Node
    - Ethereum Node (if IbetWST feature is enabled)
    - E2EE Setting
    """
    errors = []

    try:
        # Check database is available
        await db.connection()
        # Check ibet node is synced
        await __check_ibet_node_is_synced(errors, db)

        if IBET_WST_FEATURE_ENABLED:
            # Check ethereum node is synced
            await __check_ethereum_node_is_synced(errors, db)

    except Exception as err:
        LOG.exception(err)
        errors.append("Can't connect to database")

    # Check E2EE Setting
    try:
        E2EEUtils.get_key()
    except Exception as err:
        LOG.exception(err)
        errors.append("Setting E2EE key is invalid")

    if len(errors) > 0:
        raise ServiceUnavailableError(errors)

    return


async def __check_ibet_node_is_synced(errors: list, db: AsyncSession):
    """Check if ibet node is synced"""
    _node = (
        await db.scalars(select(Node).where(Node.is_synced == True).limit(1))
    ).first()
    if _node is None:
        msg = "ibet node is down"
        LOG.error(msg)
        errors.append(msg)


async def __check_ethereum_node_is_synced(errors: list, db: AsyncSession):
    """Check if ethereum node is synced"""
    _node = (
        await db.scalars(
            select(EthereumNode).where(EthereumNode.is_synced == True).limit(1)
        )
    ).first()
    if _node is None:
        msg = "ethereum node is down"
        LOG.error(msg)
        errors.append(msg)


# GET: /block_number
@router.get(
    "/block_number",
    operation_id="GetLatestBlockNumber",
    response_model=BlockNumberResponse,
    responses=get_routers_responses(ServiceUnavailableError),
)
async def get_latest_block_number():
    """Get the latest block number"""
    block_number = await web3.eth.block_number

    return json_response({"block_number": block_number})
