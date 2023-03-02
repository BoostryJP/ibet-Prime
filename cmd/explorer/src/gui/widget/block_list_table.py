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
from typing import Iterable

from rich.progress_bar import ProgressBar
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.widgets import DataTable

from utils.time import human_time

path = os.path.join(os.path.dirname(__file__), "../../../../../")
sys.path.append(path)

from app.model.schema.bc_explorer import BlockData


class BlockListTable(DataTable):
    BINDINGS = [
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
    ]
    only_include_tx = reactive(False)
    raw_data: Iterable[BlockData] = []

    def __init__(self, name: str, complete_refresh: bool, id: str):
        super().__init__(name=name, id=id)
        self.table_name = name
        self.cursor_type = "row"
        self.complete_refresh = complete_refresh

    def on_mount(self) -> None:
        """
        Occurs when Self is mounted
        """
        self.add_column("Block", width=10)
        self.add_column("Age", width=24)
        self.add_column("Txn", width=4)
        self.add_column("Hash", width=70)
        self.add_column("Gas Used")

    def toggle_filter(self) -> bool:
        self.only_include_tx = not self.only_include_tx
        self.update_rows(self.raw_data)
        return self.only_include_tx

    def update_rows(self, data: Iterable[BlockData]):
        self.raw_data = data
        selected_row = self.cursor_row
        if len(self.data) > 0:
            selected_block_number = self.data[selected_row][0]
        else:
            selected_block_number = None

        if self.complete_refresh:
            self.clear()

        current = int(round(time.time()))
        rows = [
            [
                str(d.number),
                human_time(current - d.timestamp) + " ago",
                str(len(d.transactions)),
                d.hash,
                ProgressBar(completed=(d.gas_used / d.gas_limit) * 100, width=10),
            ]
            for d in data
        ]
        if self.only_include_tx:
            rows = list(filter(lambda r: r[2] != "0", rows))
        self.add_rows(rows)

        # Keep current selected position
        if selected_block_number is not None:
            row_to_be_selected = next(
                (i for i, row in enumerate(rows) if row[0] == selected_block_number),
                len(rows) - 1 if len(rows) > 0 else 0,
            )
            self.cursor_cell = Coordinate(row_to_be_selected, 0)
            self.hover_cell = Coordinate(row_to_be_selected, 0)
        else:
            self.cursor_cell = Coordinate(0, 0)
            self.hover_cell = Coordinate(0, 0)

        self._scroll_cursor_into_view(animate=False)
        self.refresh()

    def action_select_cursor(self) -> None:
        """
        Occurs when keybind related to `select_cursor` is called.
        """
        self._set_hover_cursor(False)
        if self.show_cursor and self.cursor_type != "none" and self.has_focus:
            self._emit_selected_message()
