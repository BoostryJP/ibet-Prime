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
from sqlalchemy import Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UploadFile(Base):
    """Upload File"""

    __tablename__ = "upload_file"

    # file id (UUID)
    file_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # issuer address
    issuer_address: Mapped[str] = mapped_column(String(42), nullable=False)
    # item related with this file
    relation: Mapped[str | None] = mapped_column(String(50))
    # file_name
    file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    # content
    content: Mapped[str] = mapped_column(LargeBinary, nullable=False)
    # content size
    content_size: Mapped[int | None] = mapped_column(Integer)
    # description
    description: Mapped[str | None] = mapped_column(String(1000))
    # label
    label: Mapped[str] = mapped_column(String(200), default="", nullable=False)
