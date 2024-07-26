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

from rich.console import Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from app.model.schema import BlockDataDetail
from src.utils.time import human_time, unix_to_iso


class BlockDetailInfo:
    def __init__(self, block_detail: BlockDataDetail) -> None:
        self.block_detail = block_detail

    def __rich__(self) -> Group:
        current = int(round(time.time()))

        basic_table = Table(box=None, expand=False, show_header=False, show_edge=False)
        basic_table.add_column(style="deep_pink2 bold")
        basic_table.add_column()

        basic_table.add_row(
            Text.from_markup("Block Height:"), str(self.block_detail.number)
        )
        basic_table.add_row(
            Text.from_markup("Timestamp:"),
            f"{human_time(current - self.block_detail.timestamp)} ({unix_to_iso(self.block_detail.timestamp)})",
        )
        basic_table.add_row(
            Text.from_markup("Transactions:"),
            f"{len(self.block_detail.transactions)} transactions in this block",
        )

        content_table = Table(
            box=None, expand=False, show_header=False, show_edge=False
        )
        content_table.add_column(style="deep_pink2 bold")
        content_table.add_column()
        content_table.add_column()
        content_table.add_row(
            Text.from_markup("Total Difficulty:"), str(self.block_detail.difficulty), ""
        )
        content_table.add_row(
            Text.from_markup("Gas Used:"),
            f"{self.block_detail.gas_used} ({(self.block_detail.gas_used/self.block_detail.gas_limit)*100:.4f} %)",
            ProgressBar(
                completed=(self.block_detail.gas_used / self.block_detail.gas_limit)
                * 100,
                width=10,
            ),
        )
        content_table.add_row(
            Text.from_markup("Gas Limit:"), f"{self.block_detail.gas_limit}" ""
        )
        content_table.add_row(
            Text.from_markup("Size:"), f"{self.block_detail.size} Bytes" ""
        )

        hash_table = Table(box=None, expand=False, show_header=False, show_edge=False)
        hash_table.add_column(style="deep_pink2 bold")
        hash_table.add_column()
        hash_table.add_row(Text.from_markup("Hash:"), self.block_detail.hash)
        hash_table.add_row(
            Text.from_markup("Parent Hash:"), self.block_detail.parent_hash
        )
        hash_table.add_row("StateRoot: ", self.block_detail.state_root)
        hash_table.add_row("Nonce: ", self.block_detail.nonce)

        return Group(
            Panel(basic_table, expand=True, title="Common", title_align="left"),
            Panel(content_table, expand=True, title="Content", title_align="left"),
            Panel(hash_table, expand=True, title="Hash", title_align="left"),
        )
