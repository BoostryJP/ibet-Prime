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

import json as j

from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from web3.auto import w3


def _params_to_query_string(params):
    kvs = []
    for k, v in sorted(params.items()):
        if type(v) == int:
            v = str(v)
        kvs.append(k + "=" + v)

    if len(kvs) == 0:
        return ""
    return "&".join(kvs)


def _canonical_request(method, path, request_body, query_string):
    if request_body is None:
        request_body = "{}"

    if query_string != "":
        query_string = "?" + query_string

    request_body_hash = w3.keccak(text=request_body).hex()
    canonical_request = (
        method + "\n" + path + "\n" + query_string + "\n" + request_body_hash
    )

    return canonical_request


def _generate_signature(private_key, **kwargs):
    canonical_request = _canonical_request(**kwargs)
    signable_message = encode_defunct(text=canonical_request)
    signed_message: SignedMessage = w3.eth.account.sign_message(
        signable_message, private_key=private_key
    )
    return signed_message.signature.hex()


def generate_sealed_tx_signature(
    method: str,
    path: str,
    private_key: str,
    params: dict | None = None,
    json: dict | None = None,
):
    query_string = ""
    request_body = None
    if params is not None:
        query_string = _params_to_query_string(params)
    if json is not None:
        request_body = j.dumps(json, separators=(",", ":"))

    signature = _generate_signature(
        private_key=private_key,
        method=method,
        path=path,
        request_body=request_body,
        query_string=query_string,
    )
    return signature
