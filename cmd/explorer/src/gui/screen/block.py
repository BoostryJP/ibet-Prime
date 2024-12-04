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

import asyncio
from asyncio import Event, Lock
from datetime import datetime
from typing import Optional

import connector
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from gui.consts import ID
from gui.error import Error
from gui.screen.base import TuiScreen
from gui.widget.block_detail_view import BlockDetailView
from gui.widget.block_list_table import BlockListTable
from gui.widget.block_list_view import (
    BlockListQueryPanel,
    BlockListSummaryPanel,
    BlockListView,
)
from gui.widget.menu import Menu, MenuInstruction
from gui.widget.query_panel import QuerySetting
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import Reactive
from textual.widgets import Button, DataTable, Footer, Label, Static

from app.model.schema import (
    BlockDataDetail,
    BlockDataListResponse,
    BlockNumberResponse,
    ListBlockDataQuery,
    ListTxDataQuery,
)
from app.model.schema.base import SortOrder


class BlockScreen(TuiScreen):
    BINDINGS = [
        Binding("e", "edit_query", "Edit list block data query"),
    ]
    dark = Reactive(True)
    mutex_reload_block = Reactive(Lock())
    background_lock: Optional[Event] = None

    def __init__(
        self, name: str | None = None, id: str | None = None, classes: str | None = None
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.base_url = self.tui.url
        self.refresh_rate = 5.0
        self.block_detail_header_widget = BlockDetailView(classes="column")

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Horizontal(
                    Label(Text.from_markup(" [bold]ibet-Prime BC Explorer[/bold]")),
                    Label(" | "),
                    Label(
                        "Fetching current block...", id=ID.BLOCK_CURRENT_BLOCK_NUMBER
                    ),
                    Label(" | "),
                    Label("Fetching current status...", id=ID.BLOCK_IS_SYNCED),
                    Label(" | "),
                    Label("Loading...", id=ID.BLOCK_NOTION),
                    id=ID.BLOCK_SCREEN_HEADER,
                ),
                Horizontal(
                    BlockListView(classes="column"), self.block_detail_header_widget
                ),
                classes="column",
            )
        )
        yield Footer()
        yield Menu(id=ID.MENU)
        yield QuerySetting(id=ID.QUERY_PANEL)

    ##################################################
    # Event
    ##################################################

    async def on_mount(self) -> None:
        """
        Occurs when Self is mounted
        """
        self.query_one(Menu).hide()
        self.remove_class("menu")
        self.query_one(QuerySetting).hide()
        self.query(BlockListTable)[0].focus()
        self.set_interval(self.refresh_rate, self.fetch_sync_status)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Occurs when Button is pressed
        """
        event.stop()
        event.prevent_default()
        match event.button.id:
            case ID.MENU_CANCEL:
                self.query_one(Menu).hide()
                self.remove_class("menu")
                self.query(BlockListTable)[0].can_focus = True
                self.query_one(BlockListTable).focus()
            case ID.MENU_SHOW_TX:
                ix = self.query_one(Menu).hide()
                self.remove_class("menu")
                get_query = ListTxDataQuery()
                get_query.block_number = ix.block_number
                self.tui.state.tx_list_query = get_query
                await self.app.push_screen("transaction_screen")
            case ID.QUERY_PANEL_ENTER:
                self.reload_block()

    async def on_query_setting_enter(self, event: QuerySetting.Enter):
        """
        Occurs when QuerySetting.Enter is emitted
        """
        event.stop()
        event.prevent_default()
        self.reload_block()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        Occurs when DataTable row is selected
        """
        event.stop()
        event.prevent_default()
        selected_row = self.query_one(BlockListTable)._data.get(event.row_key)
        if selected_row is None:
            return
        block_number = selected_row.get(list(selected_row.keys())[0])
        block_hash = selected_row.get(list(selected_row.keys())[3])
        await self.fetch_block_detail(int(block_number))

        if int(selected_row.get(list(selected_row.keys())[2], 0)) == 0:
            # If the number of transaction is 0, menu is not pop up.
            return

        self.query_one(Menu).show(
            MenuInstruction(
                block_number=block_number,
                block_hash=block_hash,
                selected_row=event.cursor_row,
            )
        )
        self.add_class("menu")
        self.query(BlockListTable)[0].can_focus = False

    def reload_block(self) -> None:
        if (
            self.tui.state.current_block_number is None
            or self.tui.state.block_list_query is None
        ):
            return

        self.query_one(
            BlockListQueryPanel
        ).block_list_query = self.tui.state.block_list_query
        asyncio.create_task(self.fetch_block_list())

    ##################################################
    # Key binding
    ##################################################

    def action_edit_query(self) -> None:
        """
        Occurs when keybind related to `edit_query` is called.
        """
        if (
            self.tui.state.current_block_number is None
            or self.tui.state.block_list_query is None
        ):
            return

        self.query_one(QuerySetting).show()
        self.query(BlockListTable)[0].can_focus = False

    ##################################################
    # Fetch data
    ##################################################

    async def fetch_sync_status(self):
        async with TCPConnector(limit=2, keepalive_timeout=0) as tcp_connector:
            async with ClientSession(
                connector=tcp_connector, timeout=ClientTimeout(30)
            ) as session:
                try:
                    block_number_response: BlockNumberResponse = (
                        await connector.get_block_number(session, self.base_url)
                    )
                    block_number = block_number_response.block_number
                except Exception as e:
                    if hasattr(self, "emit_no_wait"):
                        self.emit_no_wait(Error(e, self))
                    return
                self.update_current_block(block_number)
                self.update_is_synced(True)
                if (
                    self.tui.state.current_block_number is None
                    and self.tui.state.block_list_query is None
                ):
                    # initialize block list query
                    query = ListBlockDataQuery()
                    query.to_block_number = block_number
                    query.from_block_number = max(
                        block_number - self.tui.lot_size - 1, 0
                    )
                    query.sort_order = SortOrder.DESC
                    self.tui.state.block_list_query = query
                    self.query_one(BlockListQueryPanel).block_list_query = query

                self.tui.state.current_block_number = block_number

    async def fetch_block_list(self) -> None:
        if self.tui.state.current_block_number == 0:
            return
        try:
            self.query_one(BlockListSummaryPanel).loading = True
            await asyncio.sleep(5)
            async with TCPConnector(limit=1, keepalive_timeout=0) as tcp_connector:
                async with ClientSession(
                    connector=tcp_connector, timeout=ClientTimeout(30)
                ) as session:
                    try:
                        block_data_list: BlockDataListResponse = (
                            await connector.list_block_data(
                                session, self.base_url, self.tui.state.block_list_query
                            )
                        )
                    except Exception as e:
                        if hasattr(self, "emit_no_wait"):
                            self.emit_no_wait(Error(e, self))
                        return
                    self.query_one(BlockListTable).update_rows(
                        block_data_list.block_data
                    )
                    self.query_one(BlockListSummaryPanel).loaded_time = datetime.now()

        finally:
            self.query_one(BlockListSummaryPanel).loading = False

    async def fetch_block_detail(self, block_number: int):
        async with TCPConnector(limit=1, keepalive_timeout=0) as tcp_connector:
            async with ClientSession(
                connector=tcp_connector, timeout=ClientTimeout(30)
            ) as session:
                try:
                    block_detail: BlockDataDetail = await connector.get_block_data(
                        session,
                        self.base_url,
                        block_number,
                    )
                except Exception as e:
                    if hasattr(self, "emit_no_wait"):
                        self.emit_no_wait(Error(e, self))
                    return
                self.query_one(BlockDetailView).block_detail = block_detail

    def update_current_block(self, latest_block_number: int):
        self.query_one(f"#{ID.BLOCK_CURRENT_BLOCK_NUMBER}", Static).update(
            f"Current Block: {latest_block_number}"
        )

    def update_is_synced(self, is_synced: bool):
        self.query_one(f"#{ID.BLOCK_IS_SYNCED}", Static).update(
            f"Is Synced: {is_synced}"
        )
        self.query_one(f"#{ID.BLOCK_NOTION}", Static).update(
            "Press [E] To Load Block List"
        )
