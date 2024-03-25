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

from pydantic import BaseModel
from rich.text import Text
from src.gui.consts import ID
from src.gui.widget.base import TuiWidget
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button


class MenuInstruction(BaseModel):
    block_number: int
    block_hash: str
    selected_row: int


class Menu(TuiWidget):
    BINDINGS = [
        Binding("tab,down,ctrl+n", "focus_next", "Focus Next", show=False),
        Binding("shift+tab,up,ctrl+p", "focus_previous", "Focus Previous", show=False),
        Binding("ctrl+r", "", "", show=False),
        Binding("t", "click('menu_show_tx')", "Show Transactions"),
        Binding("c,q", "click('menu_cancel')", "Cancel", key_display="Q, C"),
    ]
    ix: MenuInstruction | None = None

    def compose(self) -> ComposeResult:
        yield Button(
            Text.from_markup("\[t] Show Transactions :package:", overflow="crop"),
            id=ID.MENU_SHOW_TX,
            classes="menubutton",
        )
        yield Button(r"\[c] Cancel", id=ID.MENU_CANCEL, classes="menubutton")

    def show(self, ix: MenuInstruction):
        self.ix = ix
        self.add_class("visible")
        self.query_one(f"#{ID.MENU_SHOW_TX}", Button).focus()

    def hide(self) -> MenuInstruction | None:
        self.remove_class("visible")
        return self.ix

    def action_click(self, _id: str):
        """
        Occurs when keybind related to `click` is called.
        """
        self.query_one(f"#{_id}", Button).press()
