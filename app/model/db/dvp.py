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

from enum import IntEnum, StrEnum

from sqlalchemy import JSON, BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DVPAgentAccount(Base):
    """Account for DVP payment agent"""

    __tablename__ = "dvp_agent_account"

    # account address
    account_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # ethereum keyfile
    keyfile: Mapped[dict | None] = mapped_column(JSON)
    # ethereum account password(encrypted)
    eoa_password: Mapped[str | None] = mapped_column(String(2000))
    # delete flag
    is_deleted: Mapped[bool | None] = mapped_column(Boolean, default=False)
    # dedicated agent id
    dedicated_agent_id: Mapped[str | None] = mapped_column(String(100))


class DVPAsyncProcessType(StrEnum):
    """DvP async process type"""

    CREATE_DELIVERY = "CreateDelivery"
    CANCEL_DELIVERY = "CancelDelivery"
    FINISH_DELIVERY = "FinishDelivery"
    ABORT_DELIVERY = "AbortDelivery"


class DVPAsyncProcessStepTxStatus(StrEnum):
    """
    PENDING: The transaction has been successfully executed and is waiting to be received into the blockchain.
    DONE: The transaction has been successfully received on the blockchain.
    FAILED: The transaction has been reverted.
    RETRY: The transaction has been reverted and needs to be retried.
    """

    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    RETRY = "retry"


class DVPAsyncProcessRevertTxStatus(StrEnum):
    """
    PENDING: The transaction has been successfully executed and is waiting to be received into the blockchain.
    DONE: The transaction has been successfully received on the blockchain.
    FAILED: The transaction has been reverted.
    """

    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class DVPAsyncProcessStatus(IntEnum):
    """
    1:PROCESSING
    2:DONE(SUCCESS): All processes have been completed successfully.
    3:DONE(FAILED): All processes have been completed, but the transaction has been reverted.
    9:ERROR: The process failed midway due to a fatal error.
    """

    PROCESSING = 1
    DONE_SUCCESS = 2
    DONE_FAILED = 3
    ERROR = 9


class DVPAsyncProcess(Base):
    """DvP async process management"""

    __tablename__ = "dvp_async_process"

    # id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # process type
    process_type: Mapped[DVPAsyncProcessType] = mapped_column(
        String(30), nullable=False
    )
    # process status
    process_status: Mapped[DVPAsyncProcessStatus] = mapped_column(
        Integer, nullable=False, index=True
    )
    # dvp_contract_address
    dvp_contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # token address
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # seller address
    seller_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # buyer address
    buyer_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # amount
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # agent address
    agent_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # data
    data: Mapped[str | None] = mapped_column(Text)
    # delivery id
    delivery_id: Mapped[int | None] = mapped_column(BigInteger)
    # step
    # - CREATE_DELIVERY
    #     0) Deposit -> 1) [Seller] CreateDelivery
    #                               <Reverted>     -> [Seller] WithdrawPartial
    # - CANCEL_DELIVERY
    #     0) CancelDelivery -> 1) [Seller] WithdrawPartial
    # - FINISH_DELIVERY
    #     0) FinishDelivery -> 1) [Buyer] WithdrawPartial
    # - ABORT_DELIVERY
    #     0) AbortDelivery -> 1) [Seller] WithdrawPartial
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # latest step tx hash
    step_tx_hash: Mapped[str | None] = mapped_column(String(66))
    # latest step tx status
    step_tx_status: Mapped[DVPAsyncProcessStepTxStatus | None] = mapped_column(
        String(10), index=True
    )
    # revert tx hash
    revert_tx_hash: Mapped[str | None] = mapped_column(String(66))
    # latest step tx status
    revert_tx_status: Mapped[DVPAsyncProcessRevertTxStatus | None] = mapped_column(
        String(10), index=True
    )
