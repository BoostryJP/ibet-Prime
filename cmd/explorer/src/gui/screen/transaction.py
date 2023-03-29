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
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from rich.text import Text
from src import connector
from src.gui.consts import ID
from src.gui.screen.base import TuiScreen
from src.gui.widget.block_list_table import BlockListTable
from src.gui.widget.tx_detail_view import TxDetailView
from src.gui.widget.tx_list_table import TxListTable
from src.gui.widget.tx_list_view import TxListView
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Label

from app.model.schema.bc_explorer import TxDataDetail


class TransactionScreen(TuiScreen):
    BINDINGS = [Binding("q", "quit", "Close", priority=True)]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Horizontal(
                    Label(Text.from_markup(" [bold]ibet-Prime BC Explorer[/bold]")),
                    Label(" | "),
                    Label(f"Selected block: -", id=ID.TX_SELECTED_BLOCK_NUMBER),
                    id="tx_list_header",
                ),
                Horizontal(
                    TxListView(classes="column"), TxDetailView(classes="column")
                ),
                classes="column",
            )
        )
        yield Footer()

    ##################################################
    # Event
    ##################################################

    async def on_mount(self) -> None:
        """
        Occurs when Self is mounted
        """
        self.query(TxListTable)[0].focus()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Occurs when DataTable row is selected
        """
        event.stop()
        event.prevent_default()
        selected_row = self.query_one(TxListTable).data.get(event.cursor_row)
        if selected_row is None:
            return

        tx_hash = selected_row[0]
        async with TCPConnector(limit=1, keepalive_timeout=0) as tcp_connector:
            async with ClientSession(
                connector=tcp_connector, timeout=ClientTimeout(30)
            ) as session:
                tx_detail: TxDataDetail = await connector.get_tx_data(
                    session,
                    self.tui.url,
                    tx_hash,
                )
                self.query_one(TxDetailView).tx_detail = tx_detail

    async def on_screen_suspend(self):
        """
        Occurs when Self is suspended
        """
        self.query_one(TxListTable).update_rows([])

    async def on_screen_resume(self):
        """
        Occurs when Self is resumed
        """
        if self.tui.state.tx_list_query is not None:
            async with TCPConnector(limit=1, keepalive_timeout=0) as tcp_connector:
                async with ClientSession(
                    connector=tcp_connector, timeout=ClientTimeout(30)
                ) as session:
                    tx_list = await connector.list_tx_data(
                        session=session,
                        url=self.tui.url,
                        query=self.tui.state.tx_list_query,
                    )
                    self.query_one(TxListTable).update_rows(tx_list.tx_data)
                    self.query_one(f"#{ID.TX_SELECTED_BLOCK_NUMBER}", Label).update(
                        f"Selected block: {self.tui.state.tx_list_query.block_number}"
                    )

    ##################################################
    # Key binding
    ##################################################

    def action_quit(self):
        """
        Occurs when keybind related to `quit` is called.
        """
        self.tui.pop_screen()
        self.tui.query(BlockListTable)[0].can_focus = True
        self.tui.query(BlockListTable)[0].focus()
