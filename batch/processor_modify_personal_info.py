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
import os
import sys
import time
from typing import Sequence, Set

from sqlalchemy import and_, create_engine, delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import batch_log

from app.exceptions import ServiceUnavailableError
from app.model.blockchain import (
    IbetShareContract,
    IbetStraightBondContract,
    PersonalInfoContract,
)
from app.model.db import (
    Account,
    AccountRsaKeyTemporary,
    AccountRsaStatus,
    IDXPersonalInfo,
    Token,
    TokenType,
)
from app.utils.contract_utils import ContractUtils
from config import DATABASE_URL, ZERO_ADDRESS

"""
[PROCESSOR-Modify-Personal-Info]

Re-encryption of investor's personal information 
when the issuer's RSA key is updated.
"""

process_name = "PROCESSOR-Modify-Personal-Info"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            temporary_list = self.__get_temporary_list(db_session=db_session)
            for temporary in temporary_list:
                LOG.info(f"Process start: issuer={temporary.issuer_address}")

                contract_accessor_list = (
                    self.__get_personal_info_contract_accessor_list(
                        db_session=db_session, issuer_address=temporary.issuer_address
                    )
                )

                # Get target PersonalInfo account address
                idx_personal_info_list: Sequence[IDXPersonalInfo] = db_session.scalars(
                    select(IDXPersonalInfo).where(
                        IDXPersonalInfo.issuer_address == temporary.issuer_address
                    )
                ).all()

                count = len(idx_personal_info_list)
                completed_count = 0
                for idx_personal_info in idx_personal_info_list:
                    # Get target PersonalInfo contract accessor
                    for contract_accessor in contract_accessor_list:
                        is_registered = ContractUtils.call_function(
                            contract=contract_accessor.personal_info_contract,
                            function_name="isRegistered",
                            args=(
                                idx_personal_info.account_address,
                                idx_personal_info.issuer_address,
                            ),
                            default_returns=False,
                        )
                        if is_registered:
                            target_contract_accessor = contract_accessor
                            break

                    is_modify = self.__modify_personal_info(
                        temporary=temporary,
                        idx_personal_info=idx_personal_info,
                        personal_info_contract_accessor=target_contract_accessor,
                    )
                    if not is_modify:
                        # Confirm after being reflected in Contract.
                        # Confirm to that modify data is not modified in the next process.
                        completed_count += 1

                # Once all investors' personal information has been updated,
                # update the status of the issuer's RSA key.
                if count == completed_count:
                    self.__sink_on_account(
                        db_session=db_session, issuer_address=temporary.issuer_address
                    )
                    db_session.commit()

                LOG.info(f"Process end: issuer={temporary.issuer_address}")
        finally:
            db_session.close()

    def __get_temporary_list(self, db_session: Session):
        # NOTE: rsa_private_key in Account DB and AccountRsaKeyTemporary DB is the same when API is executed,
        #       Account DB is changed when RSA generate batch is completed.
        temporary_list: Sequence[AccountRsaKeyTemporary] = db_session.scalars(
            select(AccountRsaKeyTemporary)
            .join(
                Account, AccountRsaKeyTemporary.issuer_address == Account.issuer_address
            )
            .where(AccountRsaKeyTemporary.rsa_private_key != Account.rsa_private_key)
        ).all()

        return temporary_list

    def __get_personal_info_contract_accessor_list(
        self, db_session: Session, issuer_address: str
    ) -> Set[PersonalInfoContract]:
        token_list: Sequence[Token] = db_session.scalars(
            select(Token).where(
                and_(Token.issuer_address == issuer_address, Token.token_status == 1)
            )
        ).all()
        personal_info_contract_list = set()
        for token in token_list:
            if token.type == TokenType.IBET_SHARE.value:
                token_contract = IbetShareContract(token.token_address).get()
            elif token.type == TokenType.IBET_STRAIGHT_BOND.value:
                token_contract = IbetStraightBondContract(token.token_address).get()
            else:
                continue

            contract_address = token_contract.personal_info_contract_address
            if contract_address != ZERO_ADDRESS:
                personal_info_contract_list.add(
                    PersonalInfoContract(
                        db=db_session,
                        issuer_address=issuer_address,
                        contract_address=contract_address,
                    )
                )

        return personal_info_contract_list

    def __modify_personal_info(
        self,
        temporary: AccountRsaKeyTemporary,
        idx_personal_info: IDXPersonalInfo,
        personal_info_contract_accessor: PersonalInfoContract,
    ) -> bool:
        # Unset information assumes completed.
        personal_info_state = ContractUtils.call_function(
            contract=personal_info_contract_accessor.personal_info_contract,
            function_name="personal_info",
            args=(
                idx_personal_info.account_address,
                idx_personal_info.issuer_address,
            ),
            default_returns=[ZERO_ADDRESS, ZERO_ADDRESS, ""],
        )
        encrypted_info = personal_info_state[2]
        if encrypted_info == "":
            return False

        # If previous rsa key decrypted succeed, need modify.
        # Backup origin RSA
        org_rsa_private_key = personal_info_contract_accessor.issuer.rsa_private_key
        org_rsa_passphrase = personal_info_contract_accessor.issuer.rsa_passphrase
        # Replace RSA
        personal_info_contract_accessor.issuer.rsa_private_key = (
            temporary.rsa_private_key
        )
        personal_info_contract_accessor.issuer.rsa_passphrase = temporary.rsa_passphrase
        # Modify
        info = personal_info_contract_accessor.get_info(
            idx_personal_info.account_address, default_value=None
        )
        # Back RSA
        personal_info_contract_accessor.issuer.rsa_private_key = org_rsa_private_key
        personal_info_contract_accessor.issuer.rsa_passphrase = org_rsa_passphrase
        default_info = {
            "key_manager": None,
            "name": None,
            "postal_code": None,
            "address": None,
            "email": None,
            "birth": None,
            "is_corporate": None,
            "tax_category": None,
        }
        if info == default_info:
            return False

        # Modify personal information
        personal_info_contract_accessor.modify_info(
            account_address=idx_personal_info.account_address,
            data=info,
            default_value=None,
        )
        return True

    @staticmethod
    def __sink_on_account(db_session: Session, issuer_address: str):
        db_session.execute(
            update(Account)
            .where(Account.issuer_address == issuer_address)
            .values(rsa_status=AccountRsaStatus.SET.value)
        )
        db_session.execute(
            delete(AccountRsaKeyTemporary).where(
                AccountRsaKeyTemporary.issuer_address == issuer_address
            )
        )


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(10)


if __name__ == "__main__":
    main()
