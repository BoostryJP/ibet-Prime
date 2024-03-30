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

from datetime import datetime

from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from src.gui import styles
from src.gui.consts import ID
from src.gui.widget.base import TuiStatic, TuiWidget
from src.gui.widget.block_list_table import BlockListTable
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import Reactive, reactive
from textual.timer import Timer

from app.model.schema import ListBlockDataQuery


class BlockListQueryPanel(TuiStatic):
    block_list_query: Reactive[ListBlockDataQuery | None] = reactive(None)

    def watch_block_list_query(self, old: ListBlockDataQuery, new: ListBlockDataQuery):
        """
        Occurs when `block_list_query` is changed
        """
        self.render()

    def render(self) -> Panel:
        content = Table(
            show_header=True, header_style="bold", show_edge=False, show_lines=False
        )
        content.add_column("From", justify="center", width=10)
        content.add_column("To", justify="center", width=10)
        content.add_column("Sort", justify="center", width=7)

        if self.block_list_query is not None:
            content.add_row(
                *[
                    str(self.block_list_query.from_block_number),
                    str(self.block_list_query.to_block_number),
                    "Asc" if self.block_list_query.sort_order == 0 else "Desc",
                ]
            )
        else:
            content.add_row(*["", "", ""])

        style = "none"
        panel = Panel(
            content,
            title="[bold]Query[/]",
            title_align="left",
            style=style,
            border_style=styles.BORDER,
            box=styles.BOX,
        )

        return panel


class BlockListSummaryPanel(TuiStatic):
    loading: reactive[bool | None] = reactive(False)
    loaded_time: reactive[datetime | None] = reactive(None)
    only_block_filter: reactive[bool | None] = reactive(False)

    update_render: Timer | None = None

    def __init__(self, classes: str | None = None):
        super().__init__(classes=classes)
        self._spinner = Spinner("dots")

    def watch_loading(self, new: bool):
        """
        Occurs when `loading` is changed
        """
        if new:
            if self.update_render is None:
                self.update_render = self.set_interval(1 / 60, self.update_spinner)
            else:
                self.update_render.resume()
        else:
            if self.update_render is not None:
                self.update_render.pause()

    def watch_loaded_time(self, new: datetime):
        """
        Occurs when `loaded_time` is changed
        """
        self.render()

    def watch_only_block_filter(self, new: bool):
        """
        Occurs when `only_block_filter` is changed
        """
        self.render()

    def update_spinner(self) -> None:
        self.render()
        self.refresh()

    def render(self) -> Panel:
        content = Table(
            show_header=True, header_style="bold", show_edge=False, show_lines=False
        )
        content.add_column("Loading", justify="center")
        content.add_column("Only Blocks Including Tx", style="dim", justify="center")
        content.add_column("Loaded Time", style="dim", justify="center")

        content.add_row(
            self._spinner if self.loading else "",
            f"{self.only_block_filter}",
            (
                f"{self.loaded_time.strftime('%Y/%m/%d %H:%M:%S')}"
                if self.loaded_time is not None
                else ""
            ),
        )

        style = "none"
        panel = Panel(
            content,
            title="[bold]Result[/]",
            title_align="left",
            style=style,
            border_style=styles.BORDER,
            box=styles.BOX,
        )

        return panel


class BlockListView(TuiWidget):
    BINDINGS = [
        Binding("t", "filter", "Toggle Only Blocks Including Tx"),
    ]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            BlockListQueryPanel(classes="column_auto"),
            BlockListSummaryPanel(classes="column"),
            id=ID.BLOCK_LIST_DESCRIPTION,
        )
        yield BlockListTable(
            name="blocks", complete_refresh=True, id=ID.BLOCK_LIST_TABLE
        )

    def action_filter(self):
        """
        Occurs when keybind related to `filter` is called.
        """
        if self.query_one(BlockListTable).can_focus:
            toggle = self.query_one(BlockListTable).toggle_filter()
            self.query_one(BlockListSummaryPanel).only_block_filter = toggle
