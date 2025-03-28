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
    TokenHolderExtraInfo,
)
from app.model.schema import (
    SealedTxRegisterHolderExtraInfoRequest,
    SealedTxRegisterPersonalInfoRequest,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.sealedtx_utils import (
    RawRequestBody,
    SealedTxSignatureHeader,
    VerifySealedTxSignature,
)

router = APIRouter(prefix="/sealed_tx", tags=["[misc] sealed_tx"])


# POST: /personal_info
@router.post(
    "/personal_info",
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

    # Insert/Update offchain personal information
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


# POST: /holder_extra_info
@router.post(
    "/holder_extra_info",
    operation_id="SealedTxRegisterHolderExtraInfo",
    response_model=None,
    responses=get_routers_responses(InvalidParameterError),
)
async def sealed_tx_register_holder_extra_info(
    db: DBAsyncSession,
    raw_request_body: RawRequestBody,
    request: Request,
    sealed_tx_sig: SealedTxSignatureHeader,
    extra_info: SealedTxRegisterHolderExtraInfoRequest,
):
    # Verify sealed tx signature
    account_address = VerifySealedTxSignature(
        req=request, body=json.loads(raw_request_body.decode()), signature=sealed_tx_sig
    )

    # Insert/Update token holder's extra information
    # NOTE: Overwrite if a same record already exists.
    _holder_extra_info = TokenHolderExtraInfo()
    _holder_extra_info.token_address = extra_info.token_address
    _holder_extra_info.account_address = account_address
    _holder_extra_info.external_id1_type = extra_info.external_id1_type
    _holder_extra_info.external_id1 = extra_info.external_id1
    _holder_extra_info.external_id2_type = extra_info.external_id2_type
    _holder_extra_info.external_id2 = extra_info.external_id2
    _holder_extra_info.external_id3_type = extra_info.external_id3_type
    _holder_extra_info.external_id3 = extra_info.external_id3
    await db.merge(_holder_extra_info)
    await db.commit()

    return
