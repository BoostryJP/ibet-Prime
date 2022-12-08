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
from app.utils.contract_error_code import error_code_msg


class InvalidParameterError(Exception):
    pass


class SendTransactionError(Exception):
    pass


class ContractRevertError(Exception):

    def __init__(self, code_msg: str):
        code, message = error_code_msg(code_msg)
        self.code = code
        self.message = message
        super().__init__(message)

    def __repr__(self):
        return f"<ContractRevertError(code={self.code}, message={self.message})>"


class AuthorizationError(Exception):
    pass


class ServiceUnavailableError(Exception):
    pass


class AuthTokenAlreadyExistsError(Exception):
    pass

class ResponseLimitExceededError(Exception):
    pass
