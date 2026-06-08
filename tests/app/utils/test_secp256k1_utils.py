"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from app.utils.secp256k1_utils import (
    combine_public_keys,
    private_key_to_public_key,
    public_key_to_address,
)


def test_private_key_to_public_key_vector() -> None:
    private_key = (1).to_bytes(32)

    assert (
        private_key_to_public_key(private_key).hex()
        == "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    )
    assert (
        private_key_to_public_key(private_key, compressed=False).hex()
        == "0479be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8"
    )


def test_combine_public_keys_vector() -> None:
    public_key = private_key_to_public_key((1).to_bytes(32))

    assert (
        combine_public_keys([public_key, public_key]).hex()
        == "02c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5"
    )
    assert (
        combine_public_keys([public_key, public_key], compressed=False).hex()
        == "04c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee51ae168fea63dc339a3c58419466ceaeef7f632653266d0e1236431a950cfe52a"
    )


def test_public_key_to_address_vector() -> None:
    public_key = private_key_to_public_key((1).to_bytes(32))

    assert (
        public_key_to_address(public_key)
        == "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"
    )


def test_combined_public_key_to_address_vector() -> None:
    public_key = private_key_to_public_key((1).to_bytes(32))

    assert (
        public_key_to_address(combine_public_keys([public_key, public_key]))
        == "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"
    )
