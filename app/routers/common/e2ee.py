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

from app import log
from app.model.schema import E2EEResponse
from app.utils.e2ee_utils import E2EEUtils
from app.utils.fastapi_utils import json_response
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper
from config import E2EE_REQUEST_ENABLED

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
