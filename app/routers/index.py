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

from app.model.utils import E2EEUtils
from app.model.schema import E2EEResponse

router = APIRouter(tags=["index"])


# GET: /e2ee
@router.get("/e2ee", response_model=E2EEResponse)
def get_e2ee():
    """Get E2EE info"""

    _, public_key = E2EEUtils.get_key()
    
    return {
        "public_key": public_key
    }
