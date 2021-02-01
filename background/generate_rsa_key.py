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
import time
from Crypto.PublicKey import RSA
from Crypto import Random

from sqlalchemy.orm import Session

from app.config import KEY_FILE_PASSWORD
from app.model.db import Account
from app import log
LOG = log.get_logger()


def process(db: Session, issuer_address: str):
    """Generate RSA key"""
    time.sleep(1)
    LOG.info(f"RSA key generation started: {issuer_address}")

    _account = db.query(Account). \
        filter(Account.issuer_address == issuer_address). \
        first()
    if _account is None:
        LOG.error(f"RSA key generation failed: {issuer_address}")
        return

    random_func = Random.new().read
    rsa = RSA.generate(10240, random_func)
    rsa_private_pem = rsa.exportKey(format="PEM", passphrase=KEY_FILE_PASSWORD).decode()
    rsa_public_pem = rsa.publickey().exportKey().decode()

    # Register key data to the DB
    _account.rsa_private_key = rsa_private_pem
    _account.rsa_public_key = rsa_public_pem
    db.merge(_account)
    db.commit()

    LOG.info(f"RSA key generation succeeded: {issuer_address}")
    return
