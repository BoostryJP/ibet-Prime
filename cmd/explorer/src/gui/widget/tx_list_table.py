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
from typing import Iterable

from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import DataTable

from app.model.schema.bc_explorer import TxData


class TxListTable(DataTable):
    BINDINGS = [
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
    ]
    only_include_tx = reactive(False)
    raw_data: Iterable[TxData] = []

    def __init__(self, name: str, complete_refresh: bool):
        super().__init__()
        self.table_name = name
        self.column_labels = ["Txn Hash", "Block"]
        self.cursor_type = "row"
        self.complete_refresh = complete_refresh

    def on_mount(self) -> None:
        """
        Occurs when Self is mounted
        """
        self.add_columns(*self.column_labels)

    def update_rows(self, data: Iterable[TxData]):
        if self.complete_refresh:
            self.clear()
        rows = [[d.hash, str(d.block_number)] for d in data]
        self.add_rows(rows)
        self.refresh()

    def action_select_cursor(self) -> None:
        """
        Occurs when keybind related to `select_cursor` is called.
        """
        self._set_hover_cursor(False)
        if self.show_cursor and self.cursor_type != "none" and self.has_focus:
            self._emit_selected_message()
