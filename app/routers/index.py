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
from fastapi import (
    APIRouter,
    Depends
)
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import (
    E2EE_REQUEST_ENABLED,
    WEB3_HTTP_PROVIDER
)
from app.database import db_session
from app.model.db import Node
from app.utils.e2ee_utils import E2EEUtils
from app.model.schema import E2EEResponse
from app.exceptions import ServiceUnavailableError
from app import log

LOG = log.get_logger()

router = APIRouter(tags=["index"])

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


# GET: /e2ee
@router.get(
    "/e2ee",
    response_model=E2EEResponse
)
def e2e_encryption_key():
    """Get E2EE public key"""

    if not E2EE_REQUEST_ENABLED:
        return {"public_key": None}

    _, public_key = E2EEUtils.get_key()

    return {"public_key": public_key}


# GET: /healthcheck
@router.get(
    "/healthcheck",
    response_model=None
)
def check_health(
        db: Session = Depends(db_session)
):
    errors = []

    # Check DB Connection
    try:
        db.connection()

        # Check Ethereum Connection and Block Synchronization
        __check_ethereum(errors, db)

    except Exception as err:
        LOG.exception(err)
        errors.append("Can't connect to database")

        # Check Ethereum Connection
        __check_ethereum(errors)

    # Check E2EE Setting
    try:
        E2EEUtils.get_key()
    except Exception as err:
        LOG.exception(err)
        errors.append("Setting E2EE key is invalid")

    if len(errors) > 0:
        raise ServiceUnavailableError(errors)

    return


def __check_ethereum(errors: list, db: Session = None):
    try:
        # Check Ethereum Connection
        _ = web3.eth.blockNumber

        if db is not None:
            # Check Ethereum Block Synchronization
            _node = db.query(Node).first()
            if _node is not None and not _node.is_synced:
                msg = "Ethereum node's block synchronization is down"
                LOG.error(msg)
                errors.append(msg)
    except Exception as err:
        LOG.exception(err)
        errors.append("Can't connect to ethereum node")
