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

from typing import Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from eth_utils.address import to_checksum_address
from eth_utils.crypto import keccak

_SECP256K1 = ec.SECP256K1()
_FIELD_PRIME = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


def private_key_to_public_key(private_key: bytes, *, compressed: bool = True) -> bytes:
    """Derive the public key from a private key."""
    private_key_int = int.from_bytes(private_key, "big")
    public_key = ec.derive_private_key(private_key_int, _SECP256K1).public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=(
            serialization.PublicFormat.CompressedPoint
            if compressed
            else serialization.PublicFormat.UncompressedPoint
        ),
    )


def public_key_to_address(public_key: bytes) -> str:
    """Derive the Ethereum address from a public key."""
    uncompressed_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        _SECP256K1, public_key
    ).public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return to_checksum_address(keccak(uncompressed_public_key[1:])[-20:])


def combine_public_keys(
    public_keys: Sequence[bytes], *, compressed: bool = True
) -> bytes:
    """Combine multiple public keys into a single public key by adding their points together."""
    if not public_keys:
        raise ValueError("public_keys must not be empty")

    combined_point = _decode_public_key(public_keys[0])
    for public_key in public_keys[1:]:
        combined_point = _add_points(combined_point, _decode_public_key(public_key))

    public_numbers = ec.EllipticCurvePublicNumbers(
        combined_point[0], combined_point[1], _SECP256K1
    )
    public_key = public_numbers.public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=(
            serialization.PublicFormat.CompressedPoint
            if compressed
            else serialization.PublicFormat.UncompressedPoint
        ),
    )


def _decode_public_key(public_key: bytes) -> tuple[int, int]:
    """Decode a public key into its (x, y) coordinates."""
    public_numbers = ec.EllipticCurvePublicKey.from_encoded_point(
        _SECP256K1, public_key
    ).public_numbers()
    return public_numbers.x, public_numbers.y


def _add_points(point_1: tuple[int, int], point_2: tuple[int, int]) -> tuple[int, int]:
    """Add two points on the elliptic curve."""
    x1, y1 = point_1
    x2, y2 = point_2

    if x1 == x2:
        if (y1 + y2) % _FIELD_PRIME == 0:
            raise ValueError("point addition produced the point at infinity")
        slope = (3 * x1 * x1) * pow(2 * y1, -1, _FIELD_PRIME)
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, _FIELD_PRIME)

    slope %= _FIELD_PRIME
    x3 = (slope * slope - x1 - x2) % _FIELD_PRIME
    y3 = (slope * (x1 - x3) - y1) % _FIELD_PRIME
    return x3, y3
