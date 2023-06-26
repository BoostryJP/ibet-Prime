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
from fastapi import status

from app.utils.contract_error_code import REVERT_CODE_MAP, error_code_msg


class AppError(Exception):
    status_code: int
    code: int | None = None
    code_list: list[int] | None = None


class InvalidParameterError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = 1


class SendTransactionError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = 2


class ContractRevertError(AppError):
    """
    * Error code is defined here
      * https://github.com/BoostryJP/ibet-SmartContract/blob/dev-23.3/docs/Errors.md
    * If contract doesn't throw error code, 0 is returned.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    code_list = [0] + list(REVERT_CODE_MAP.keys())

    def __init__(self, code_msg: str):
        code, message = error_code_msg(code_msg)
        self.code = code
        self.message = message
        super().__init__(message)

    def __repr__(self):
        return f"<ContractRevertError(code={self.code}, message={self.message})>"


class AuthorizationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = 1


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = 1


class AuthTokenAlreadyExistsError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = 3


class ResponseLimitExceededError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = 4


class Integer64bitLimitExceededError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = 5
