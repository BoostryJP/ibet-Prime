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

from gui.screen.base import TuiScreen
from gui.widget.block_list_table import BlockListTable
from gui.widget.traceback import TracebackWidget
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer


class TracebackScreen(TuiScreen):
    BINDINGS = [Binding("q,enter,space", "quit", "Close", priority=True)]

    def compose(self) -> ComposeResult:
        yield TracebackWidget()
        yield Footer()

    ##################################################
    # Event
    ##################################################

    async def on_mount(self) -> None:
        """
        Occurs when Self is mounted
        """
        self.query(TracebackWidget)[0].focus()

    ##################################################
    # Key binding
    ##################################################

    def action_quit(self):
        """
        Occurs when keybind related to `quit` is called.
        """
        self.tui.pop_screen()
        self.tui.query_one(BlockListTable).focus()
