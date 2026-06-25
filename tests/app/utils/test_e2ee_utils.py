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

import base64
import importlib
import sys
from datetime import datetime
from unittest import mock

import pytest

from app.utils.e2ee_utils import E2EEUtils


class TestE2EEUtils:
    @mock.patch(
        "app.utils.e2ee_utils.E2EEUtils.cache",
        {
            "private_key": None,
            "public_key": None,
            "encrypted_length": None,
            "expiration_datetime": datetime.min,
        },
    )
    def test_error_when_rsa_resource_is_not_configured(self):
        with (
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_RESOURCE_MODE", 0),
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_RESOURCE", None),
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_PASSPHRASE", "password"),
        ):
            with pytest.raises(ValueError, match="E2EE_RSA_RESOURCE is not configured"):
                E2EEUtils.get_key()

    @mock.patch(
        "app.utils.e2ee_utils.E2EEUtils.cache",
        {
            "private_key": None,
            "public_key": None,
            "encrypted_length": None,
            "expiration_datetime": datetime.min,
        },
    )
    def test_error_when_rsa_resource_mode_is_not_configured(self):
        with (
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_RESOURCE_MODE", None),
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_RESOURCE", "dummy.pem"),
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_PASSPHRASE", "password"),
        ):
            with pytest.raises(
                ValueError, match="E2EE_RSA_RESOURCE_MODE is not configured"
            ):
                E2EEUtils.get_key()

    @mock.patch(
        "app.utils.e2ee_utils.E2EEUtils.cache",
        {
            "private_key": "cached-private-key",
            "public_key": "cached-public-key",
            "encrypted_length": 256,
            "expiration_datetime": datetime.max,
        },
    )
    def test_error_when_rsa_passphrase_is_not_configured_even_if_cache_is_warm(self):
        with (
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_RESOURCE_MODE", 0),
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_RESOURCE", "dummy.pem"),
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_PASSPHRASE", None),
        ):
            with pytest.raises(
                ValueError, match="E2EE_RSA_PASSPHRASE is not configured"
            ):
                E2EEUtils.get_key()

    def test_decrypt_uses_validated_rsa_passphrase(self):
        crypto_data = {"private_key": "dummy-private-key", "encrypted_length": None}
        cipher = mock.MagicMock()
        cipher.decrypt.return_value = b"decrypted"
        validated_rsa_settings = (0, "dummy.pem", "validated-passphrase")
        base64_encrypt_data = base64.b64encode(b"encrypted").decode()

        with (
            mock.patch("app.utils.e2ee_utils.E2EE_RSA_PASSPHRASE", None),
            mock.patch(
                "app.utils.e2ee_utils.E2EEUtils._E2EEUtils__get_rsa_settings",
                return_value=validated_rsa_settings,
            ),
            mock.patch(
                "app.utils.e2ee_utils.E2EEUtils._E2EEUtils__get_crypto_data",
                return_value=crypto_data,
            ) as mock_get_crypto_data,
            mock.patch("app.utils.e2ee_utils.RSA.importKey") as mock_import_key,
            mock.patch("app.utils.e2ee_utils.PKCS1_OAEP.new", return_value=cipher),
        ):
            assert E2EEUtils.decrypt(base64_encrypt_data) == "decrypted"

        mock_get_crypto_data.assert_called_once_with()
        mock_import_key.assert_called_once_with(
            "dummy-private-key", passphrase="validated-passphrase"
        )
        cipher.decrypt.assert_called_once_with(b"encrypted")


def test_config_import_does_not_require_e2ee_env(monkeypatch: pytest.MonkeyPatch):
    with monkeypatch.context() as context:
        context.setenv("APP_ENV", "dev")
        context.delenv("E2EE_RSA_RESOURCE_MODE", raising=False)
        context.delenv("E2EE_RSA_RESOURCE", raising=False)
        context.delenv("E2EE_RSA_PASSPHRASE", raising=False)

        # Simulate a normal application import path where config is reloaded
        # without test or migration tooling already imported. This ensures the
        # test validates that E2EE env vars are not required merely because
        # pytest/alembic-specific import-time detection is unavailable.
        context.delitem(sys.modules, "pytest", raising=False)
        context.delitem(sys.modules, "alembic", raising=False)
        context.delitem(sys.modules, "config", raising=False)

        reloaded_config = importlib.import_module("config")

        assert reloaded_config is not None
        assert reloaded_config is sys.modules["config"]
        assert reloaded_config.__name__ == "config"
        assert reloaded_config.E2EE_RSA_RESOURCE_MODE is None
        assert reloaded_config.E2EE_RSA_RESOURCE is None
        assert reloaded_config.E2EE_RSA_PASSPHRASE is None
