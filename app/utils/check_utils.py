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
from fastapi.exceptions import RequestValidationError
from pydantic import MissingError
from pydantic.error_wrappers import ErrorWrapper
from web3 import Web3

from config import (
    EOA_PASSWORD_CHECK_ENABLED,
    E2EE_REQUEST_ENABLED
)
from app.exceptions import AuthorizationError
from app.log import (
    auth_info,
    auth_error
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.db import Account


def validate_headers(**kwargs):
    """Header-Parameters Validation Function

    :param kwargs: keyword is header name(Replace hyphens with underscores).
                   value is tuple({header-param}, {valid-func}),
                   {valid-func} can be specified even in list.
    :raises Exception: wrong call
    :raises RequestValidationError: detected validation error

    Call examples

    e.g.) headers_validate(issuer_address=(issuer_address, address_is_valid_address))

    e.g.) headers_validate(eoa_password=(pwd_encrypt_str, [eoa_password_is_required, eoa_password_is_encrypted_value]))
    """

    errors = []
    for name, v in kwargs.items():
        if not isinstance(v, tuple) or len(v) != 2:
            raise Exception
        name = name.replace("_", "-")
        value, validators = v
        if not isinstance(validators, list):
            validators = [validators]
        for valid_func in validators:
            if not callable(valid_func):
                raise Exception
            try:
                valid_func(name, value)
            except Exception as err:
                errors.append(ErrorWrapper(exc=err, loc=("header", name)))

    if len(errors) > 0:
        raise RequestValidationError(errors)


def address_is_valid_address(name, value):
    if value:
        if not Web3.isAddress(value):
            raise ValueError(f"{name} is not a valid address")


def eoa_password_is_required(_, value):
    if EOA_PASSWORD_CHECK_ENABLED:
        if not value:
            raise MissingError


def eoa_password_is_encrypted_value(name, value):
    if E2EE_REQUEST_ENABLED:
        check_value_is_encrypted(name, value)


def check_value_is_encrypted(name, value):
    if value:
        try:
            E2EEUtils.decrypt(value)
        except ValueError:
            raise ValueError(f"{name} is not a Base64-encoded encrypted data")


def check_password_for_auth(checked_pwd, correct_pwd, issuer_address, request):
    if EOA_PASSWORD_CHECK_ENABLED:
        if E2EE_REQUEST_ENABLED:
            decrypt_pwd = E2EEUtils.decrypt(checked_pwd)
            result = decrypt_pwd == correct_pwd
        else:
            result = checked_pwd == correct_pwd
        if not result:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError("issuer does not exist, or password mismatch")
        auth_info(request, issuer_address, "authentication succeed")


def check_auth(eoa_password, issuer_address, db, request):
    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError("issuer does not exist, or password mismatch")
    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
    check_password_for_auth(eoa_password, decrypt_password, issuer_address, request)
