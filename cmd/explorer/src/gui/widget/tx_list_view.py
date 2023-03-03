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
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static

from src.gui.widget.base import TuiWidget
from src.gui.widget.tx_list_table import TxListTable


class TxListView(TuiWidget):
    BINDINGS = []

    def __init__(self, *children: Widget, name: str | None = None, id: str | None = None, classes: str | None = None):
        super().__init__(*children, name=name, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        yield TxListTable(name="transactions", complete_refresh=True)
        yield Horizontal(
            Static("", classes="column"),
            id="tx_list_description",
        )
