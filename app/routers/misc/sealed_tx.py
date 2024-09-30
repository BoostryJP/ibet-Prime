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

from fastapi import APIRouter
from starlette.requests import Request

from app.database import DBAsyncSession
from app.exceptions import InvalidParameterError
from app.model.db import (
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
)
from app.model.schema import SealedTxRegisterPersonalInfoRequest
from app.utils.docs_utils import get_routers_responses
from app.utils.sealedtx_utils import (
    RawRequestBody,
    SealedTxSignatureHeader,
    VerifySealedTxSignature,
)

router = APIRouter(prefix="/sealed_tx", tags=["[misc] sealed_tx"])


# POST: /personal_info/register
@router.post(
    "/personal_info/register",
    operation_id="SealedTxRegisterPersonalInfo",
    response_model=None,
    responses=get_routers_responses(InvalidParameterError),
)
async def sealed_tx_register_personal_info(
    db: DBAsyncSession,
    raw_request_body: RawRequestBody,
    request: Request,
    sealed_tx_sig: SealedTxSignatureHeader,
    register_data: SealedTxRegisterPersonalInfoRequest,
):
    # Verify sealed tx signature
    account_address = VerifySealedTxSignature(
        req=request, body=json.loads(raw_request_body.decode()), signature=sealed_tx_sig
    )

    # Insert offchain personal information
    # NOTE: Overwrite if a record for the same account already exists.
    personal_info = register_data.personal_information.model_dump()
    _off_personal_info = IDXPersonalInfo()
    _off_personal_info.issuer_address = register_data.link_address
    _off_personal_info.account_address = account_address
    _off_personal_info.personal_info = personal_info
    _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
    await db.merge(_off_personal_info)

    # Insert personal information history
    _personal_info_history = IDXPersonalInfoHistory()
    _personal_info_history.issuer_address = register_data.link_address
    _personal_info_history.account_address = account_address
    _personal_info_history.event_type = PersonalInfoEventType.REGISTER
    _personal_info_history.personal_info = personal_info
    db.add(_personal_info_history)

    await db.commit()

    return
