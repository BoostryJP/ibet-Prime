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

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic_core import ErrorDetails, PydanticCustomError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from app.exceptions import AuthorizationError
from app.log import auth_error, auth_info
from app.model.db import Account, AuthToken
from app.utils.e2ee_utils import E2EEUtils
from config import E2EE_REQUEST_ENABLED, EOA_PASSWORD_CHECK_ENABLED


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
                if isinstance(err, PydanticCustomError):
                    type_str = err.type
                elif isinstance(err, ValueError):
                    type_str = "value_error"
                else:
                    type_str = "type_error"
                errors.append(
                    ErrorDetails(
                        msg=str(err), loc=("header", name), input=value, type=type_str
                    )
                )

    if len(errors) > 0:
        raise RequestValidationError(errors)


def address_is_valid_address(name, value):
    if value:
        if not Web3.is_address(value):
            raise ValueError(f"{name} is not a valid address")


def eoa_password_is_required(_, value):
    if EOA_PASSWORD_CHECK_ENABLED:
        if not value:
            raise PydanticCustomError("value_error.missing", "field required")


def eoa_password_is_encrypted_value(name, value):
    if E2EE_REQUEST_ENABLED:
        check_value_is_encrypted(name, value)


def check_value_is_encrypted(name, value):
    if value:
        try:
            E2EEUtils.decrypt(value)
        except ValueError:
            raise ValueError(f"{name} is not a Base64-encoded encrypted data")


async def check_auth(
    request: Request,
    db: AsyncSession,
    issuer_address: str,
    eoa_password: Optional[str] = None,
    auth_token: Optional[str] = None,
):
    # Check for existence of issuer account
    try:
        account, decrypted_eoa_password = await check_account_for_auth(
            db, issuer_address
        )
    except AuthorizationError:
        auth_error(request, issuer_address, "issuer does not exist")
        raise AuthorizationError(
            "issuer does not exist, or password mismatch"
        ) from None

    if EOA_PASSWORD_CHECK_ENABLED:
        if eoa_password is None and auth_token is None:
            auth_error(request, issuer_address, "password mismatch")
            raise AuthorizationError(
                "issuer does not exist, or password mismatch"
            ) from None
        elif eoa_password is not None:
            # Check EOA password
            try:
                check_eoa_password_for_auth(
                    checked_pwd=eoa_password,
                    correct_pwd=decrypted_eoa_password,
                )
            except AuthorizationError:
                auth_error(request, issuer_address, "password mismatch")
                raise AuthorizationError(
                    "issuer does not exist, or password mismatch"
                ) from None
        elif auth_token is not None:
            # Check auth token
            try:
                await check_token_for_auth(
                    db=db, issuer_address=issuer_address, auth_token=auth_token
                )
            except AuthorizationError:
                auth_error(request, issuer_address, "password mismatch")
                raise AuthorizationError(
                    "issuer does not exist, or password mismatch"
                ) from None

    auth_info(request, issuer_address, "authentication succeed")
    return account, decrypted_eoa_password


async def check_account_for_auth(db: AsyncSession, issuer_address: str):
    account = (
        await db.scalars(
            select(Account).where(Account.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if account is None:
        raise AuthorizationError
    decrypted_eoa_password = E2EEUtils.decrypt(account.eoa_password)
    return account, decrypted_eoa_password


def check_eoa_password_for_auth(checked_pwd: str, correct_pwd: str):
    if E2EE_REQUEST_ENABLED:
        decrypted_pwd = E2EEUtils.decrypt(checked_pwd)
        result = decrypted_pwd == correct_pwd
    else:
        result = checked_pwd == correct_pwd
    if not result:
        raise AuthorizationError


async def check_token_for_auth(db: AsyncSession, issuer_address: str, auth_token: str):
    issuer_token: Optional[AuthToken] = (
        await db.scalars(
            select(AuthToken).where(AuthToken.issuer_address == issuer_address).limit(1)
        )
    ).first()
    if issuer_token is None:
        raise AuthorizationError
    else:
        hashed_token = hashlib.sha256(auth_token.encode()).hexdigest()
        if issuer_token.auth_token != hashed_token:
            raise AuthorizationError
        elif issuer_token.valid_duration != 0 and issuer_token.usage_start + timedelta(
            seconds=issuer_token.valid_duration
        ) < datetime.now(UTC).replace(tzinfo=None):
            raise AuthorizationError
