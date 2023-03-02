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

from pydantic import ValidationError
from textual.app import App, ReturnType
from textual.binding import Binding

from connector import ApiNotEnabledException
from gui.screen.block import BlockScreen
from gui.screen.traceback import TracebackScreen
from gui.screen.transaction import TransactionScreen

from .error import Error

path = os.path.join(os.path.dirname(__file__), "../../../../")
sys.path.append(path)

from app.model.schema import ListBlockDataQuery, ListTxDataQuery


class AppState:
    tx_list_query: ListTxDataQuery | None = None
    block_list_query: ListBlockDataQuery | None = None
    current_block_number: int | None = None
    error: Exception | None = None


class ExplorerApp(App):
    """A Textual app to explorer ibet-Network."""

    # Base App Setting
    BINDINGS = [Binding("ctrl+c", "quit", "Quit")]
    CSS_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/explorer.css"
    SCREENS = {"transaction_screen": TransactionScreen, "traceback_screen": TracebackScreen}

    # Injectable App Setting
    url: str
    lot_size: int

    # App State
    state: AppState = AppState()

    async def run_async(
        self,
        *,
        url: str = "http://localhost:5000",
        lot_size: int = 30,
        headless: bool = False,
        size: tuple[int, int] | None = None,
        auto_pilot: None = None,
    ) -> ReturnType | None:
        self.url = url
        self.lot_size = lot_size
        return await super().run_async(headless=headless, size=size, auto_pilot=auto_pilot)

    def on_mount(self):
        """
        Occurs when Self is mounted
        """
        self.push_screen(BlockScreen(name="block_screen"))

    async def action_quit(self) -> None:
        """
        Occurs when keybind related to `quit` is called.
        """
        self.exit()

    def on_error(self, event: Error) -> None:
        if isinstance(event.error, ApiNotEnabledException):
            raise event.error from None
        if isinstance(event.error, ValidationError):
            raise ValueError(event.error.json()) from None
        self.state.error = event.error
        self.push_screen("traceback_screen")
