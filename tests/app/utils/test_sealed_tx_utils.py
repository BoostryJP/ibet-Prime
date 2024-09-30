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

from fastapi import Request
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app.main import app
from app.utils.sealedtx_utils import (
    RawRequestBody,
    SealedTxSignatureHeader,
    VerifySealedTxSignature,
)
from tests.app.utils.generate_signature import generate_sealed_tx_signature


class TestVerifySealedTxSignature:
    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    apiurl = "/test/TestVerifySignature"

    def setup_class(self):
        # Test API (POST）
        @app.post("/test/TestVerifySignature", tags=["Test"])
        def test_post(
            request: Request,
            raw_body: RawRequestBody,
            x_sealed_tx_signature: SealedTxSignatureHeader,
        ):
            recovered_address = VerifySealedTxSignature(
                req=request,
                body=json.loads(raw_body.decode()) if len(raw_body) > 0 else {},
                signature=x_sealed_tx_signature,
            )
            return PlainTextResponse(recovered_address)

        # Test API（GET）
        @app.get("/test/TestVerifySignature", tags=["Test"])
        def test_get(
            request: Request,
            x_ibet_signature: SealedTxSignatureHeader,
        ):
            recovered_address = VerifySealedTxSignature(
                req=request, body=None, signature=x_ibet_signature
            )
            return PlainTextResponse(recovered_address)

        self.cli = TestClient(app)

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # With query string and request body
    # POST
    def test_normal_1(self):
        signature = generate_sealed_tx_signature(
            "POST",
            self.apiurl,
            private_key=self.private_key,
            params={"password": "123", "name": "abcd"},
            json={"address":"Tokyo, Japan"},  # NOTE: JSON format without whitespace
        )

        resp = self.cli.post(
            self.apiurl,
            params={
                "password": 123,
                "name": "abcd",
            },
            content=json.dumps(
                {"address":"Tokyo, Japan"},  # NOTE: JSON format without whitespace
                separators=(",", ":")
            ),
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": signature,
            },
        )

        assert resp.status_code == 200
        assert resp.text == self.address

    # Normal_2_1
    # With query string and no request body
    # POST
    def test_normal_2_1(self, client):
        signature = generate_sealed_tx_signature(
            "POST",
            self.apiurl,
            private_key=self.private_key,
            params={"password": "123", "name": "abcd"},
        )

        resp = self.cli.post(
            self.apiurl,
            params={
                "password": 123,
                "name": "abcd",
            },
            headers={
                "X-SealedTx-Signature": signature,
            },
        )

        assert resp.status_code == 200
        assert resp.text == self.address

    # Normal_2_2
    # With query string and no request body
    # GET
    def test_normal_2_2(self, client):
        signature = generate_sealed_tx_signature(
            "GET",
            self.apiurl,
            private_key=self.private_key,
            params={"password": "123", "name": "abcd"},
        )

        resp = self.cli.get(
            self.apiurl,
            params={
                "password": 123,
                "name": "abcd",
            },
            headers={
                "X-SealedTx-Signature": signature,
            },
        )

        assert resp.status_code == 200
        assert resp.text == self.address

    # Normal_3_1
    # Without query string and with request body
    # Standard JSON format
    # POST
    def test_normal_3_1(self, client):
        signature = generate_sealed_tx_signature(
            "POST",
            self.apiurl,
            private_key=self.private_key,
            json={"address": "Tokyo, Japan"},
        )

        res = self.cli.post(
            self.apiurl,
            json={"address": "Tokyo, Japan"},
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": signature,
            },
        )

        assert res.status_code == 200
        assert res.text == self.address

    # Normal_3_2
    # Without query string and with request body
    # JSON format without whitespace
    # POST
    def test_normal_3_2(self, client):
        signature = generate_sealed_tx_signature(
            "POST",
            self.apiurl,
            private_key=self.private_key,
            json={"address":"Tokyo, Japan"},  # NOTE: JSON format without whitespace
        )

        res = self.cli.post(
            self.apiurl,
            content=json.dumps(
                {"address":"Tokyo, Japan"},  # NOTE: JSON format without whitespace
                separators=(",", ":")
            ),
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": signature,
            },
        )

        assert res.status_code == 200
        assert res.text == self.address

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # Invalid signature
    def test_error_1(self):
        resp = self.cli.post(
            self.apiurl,
            params={
                "password": 123,
                "name": "abcd",
            },
            json={"address": "Tokyo, Japan"},
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": "0xaf7117049ab338ea7fa432439172a0e2f5cd02cec8d673dac6b7abc10b6c969c53d3f8846c452581ccdb8712607d9fe3da9fe7b64ee778d2233d29ea102b9d0a1b",
            },
        )

        assert resp.status_code == 200
        assert resp.text != self.address

    # Error_2
    # Missing signature
    def test_error_2(self):
        resp = self.cli.post(
            self.apiurl,
            params={
                "password": 123,
                "name": "abcd",
            },
            json={"address": "Tokyo, Japan"},
            headers={
                "Content-Type": "application/json",
            },
        )

        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "RequestValidationError"
            },
            "detail": [
                {
                    "type": "missing",
                    "loc": ["header", "X-SealedTx-Signature"],
                    "msg": "Field required",
                    "input": None
                }
            ]
        }

    # Error_3
    # Signature format is invalid
    def test_error_3(self):
        resp = self.cli.post(
            self.apiurl,
            params={
                "password": 123,
                "name": "abcd",
            },
            json={"address": "Tokyo, Japan"},
            headers={
                "Content-Type": "application/json",
                "X-SealedTx-Signature": "0xaf7117049ab338ea7f",
            },
        )

        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {
                "code": 1,
                "title": "InvalidParameterError"
            },
            "detail": "failed to recover hash"
        }
