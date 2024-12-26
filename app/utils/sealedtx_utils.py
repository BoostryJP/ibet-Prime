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
from typing import Annotated

from eth_account.messages import encode_defunct
from fastapi import Depends, Header, Request
from web3.auto import w3

from app import log
from app.exceptions import InvalidParameterError

LOG = log.get_logger()


async def get_body(req: Request):
    return await req.body()


RawRequestBody = Annotated[bytes, Depends(get_body)]

SealedTxSignatureHeader = Annotated[str, Header(alias="X-SealedTx-Signature")]


def VerifySealedTxSignature(req: Request, body: dict | None, signature: str):
    """
    Verify X-SealedTx-Signature
    - https://github.com/BoostryJP/ibet-Prime/issues/689
    """

    if signature == "":
        raise InvalidParameterError("Signature is empty")
    LOG.debug("X-SealedTx-Signature: " + signature)

    # Calculating the hash value of the request body
    if body:
        request_body = json.dumps(body, separators=(",", ":"))
    else:
        request_body = json.dumps({})
    LOG.debug("request_body: " + request_body)
    request_body_hash = w3.keccak(text=request_body).hex()

    # Normalize the query parameters
    kvs = []
    for k, v in sorted(req.query_params.items()):
        if type(v) == int:
            v = str(v)
        kvs.append(k + "=" + v)

    if len(kvs) == 0:
        query_params = ""
    else:
        query_params = "?" + "&".join(kvs)

    # Generate a CanonicalRequest
    canonical_request = (
        req.method
        + "\n"
        + req.url.path
        + "\n"
        + query_params
        + "\n"
        + request_body_hash
    )
    LOG.debug("Canonical Request: " + canonical_request)

    # Verify the signature
    try:
        recovered_address = w3.eth.account.recover_message(
            encode_defunct(text=canonical_request),
            signature=signature,
        )
        LOG.debug("Recovered EOA: " + recovered_address)
    except Exception:
        raise InvalidParameterError("failed to recover hash")

    return recovered_address
