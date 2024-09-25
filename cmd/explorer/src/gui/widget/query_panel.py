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

from typing import TYPE_CHECKING, cast

from rich.markdown import Markdown
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Button, Input, Label

from app.model.schema import ListBlockDataQuery
from app.model.schema.base import SortOrder
from src.gui.consts import ID
from src.gui.widget.base import TuiWidget
from src.gui.widget.block_list_table import BlockListTable
from src.gui.widget.block_list_view import BlockListQueryPanel
from src.gui.widget.choice import Choices

if TYPE_CHECKING:
    from src.gui.explorer import ExplorerApp


class ToBlockInput(Input):
    @property
    def tui(self) -> "ExplorerApp":
        return cast("ExplorerApp", self.app)

    def increment_value(self, increment: int) -> None:
        """
        Increments the value by the increment
        """
        if self.value is None:
            self.value = str(0)

        if (
            self.tui.state.current_block_number is not None
            and int(self.value) + increment > self.tui.state.current_block_number
        ):
            self.value = f"{self.tui.state.current_block_number}"
        elif int(self.value) + increment < 0:
            self.value = str(0)
        else:
            self.value = str(int(self.value) + increment)

    def insert_text_at_cursor(self, text: str) -> None:
        """
        Insert new text at the cursor, move the cursor to the end of the new text.
        """
        if self.value == "0":
            if text == "0":
                return
            self.value = str(int(self.value) + int(text))
            self.cursor_position = 1
            return

        if self.cursor_position > len(self.value):
            if (
                self.tui.state.current_block_number is not None
                and int(self.value + text) > self.tui.state.current_block_number
            ):
                self.value = f"{self.tui.state.current_block_number}"
            else:
                self.value += text
                self.cursor_position = len(self.value)
        else:
            value = self.value
            before = value[: self.cursor_position]
            after = value[self.cursor_position :]
            if (
                self.tui.state.current_block_number is not None
                and int(before + text + after) > self.tui.state.current_block_number
            ):
                self.value = f"{self.tui.state.current_block_number}"
            else:
                self.value = f"{before}{text}{after}"
                self.cursor_position += len(text)

    async def on_key(self, event: events.Key) -> None:
        """
        Occurs when `Key` is emitted.
        """
        self._cursor_visible = True
        if self.cursor_blink:
            self._blink_timer.reset()

        event.prevent_default()
        event.stop()
        if await self.handle_key(event):
            return

        if event.character is not None and event.character.isdigit():
            if event.character == "0" and self.cursor_position == 0:
                self.cursor_position += 1
                return
            self.insert_text_at_cursor(event.character)
        elif event.key in ["left", "ctrl+b"]:
            if self.cursor_position != 0:
                self.cursor_position -= 1
        elif event.key in ["right", "ctrl+f"]:
            if self.cursor_position != len(self.value):
                self.cursor_position += 1
        elif event.key in ["up", "ctrl+p"]:
            self.increment_value(10)
            self.cursor_position = len(self.value)
        elif event.key in ["down", "ctrl+n"]:
            self.increment_value(-10)
            self.cursor_position = len(self.value)
        elif event.key in ["home", "ctrl+a"]:
            self.cursor_position = 0
        elif event.key in ["end", "ctrl+e"]:
            self.cursor_position = len(self.value)
        elif event.key == "backspace":
            if self.cursor_position == 0:
                return
            elif len(self.value) == 1:
                self.value = str(0)
                self.cursor_position = 0
            elif len(self.value) == 2:
                if self.cursor_position == 1:
                    self.value = self.value[1]
                    self.cursor_position = 0
                else:
                    self.value = self.value[0]
                    self.cursor_position = 1
            else:
                if self.cursor_position == 1:
                    self.value = self.value[1:]
                    self.cursor_position = 0
                elif self.cursor_position == len(self.value):
                    self.value = self.value[:-1]
                    self.cursor_position -= 1
                else:
                    new_value = (
                        self.value[: self.cursor_position - 1]
                        + self.value[self.cursor_position :]
                    )
                    if new_value != "":
                        self.value = new_value
                        self.cursor_position -= 1


class QuerySetting(TuiWidget):
    BINDINGS = [
        Binding("c,q,escape", "cancel()", "Cancel", key_display="Q, C", priority=True),
        Binding("tab", "focus_next", "Focus Next", show=True, priority=True),
        Binding(
            "shift+tab", "focus_previous", "Focus Previous", show=True, priority=True
        ),
        Binding("enter", "enter()", "Enter", priority=True),
        Binding("e", "", "", show=False),
        Binding("ctrl+c", "", "", show=False),
        Binding("ctrl+r", "", "", show=False),
        Binding("ctrl+n", "cursor_down", "Down", show=False),
        Binding("ctrl+p", "cursor_up", "Up", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Label(Markdown("# Query Setting"))
        yield Label(Markdown("#### To Block"))
        yield ToBlockInput(
            placeholder="100", name="to_block", id=ID.QUERY_PANEL_TO_BLOCK_INPUT
        )
        yield Label(Markdown("#### From Block(Auto set)"))
        yield Input(
            placeholder="0", name="from_block", id=ID.QUERY_PANEL_FROM_BLOCK_INPUT
        )
        yield Label(Markdown("#### Sort Order"))
        yield Choices(["DESC", "ASC"], id=ID.QUERY_PANEL_SORT_ORDER_CHOICE)
        yield Button("Enter", id=ID.QUERY_PANEL_ENTER)

    def show(self):
        self.add_class("visible")
        self.query_one(f"#{ID.QUERY_PANEL_TO_BLOCK_INPUT}", Input).focus()
        self.query_one(f"#{ID.QUERY_PANEL_FROM_BLOCK_INPUT}", Input).can_focus = False

        if self.tui.state.block_list_query is not None:
            query = self.tui.state.block_list_query
            self.query_one(f"#{ID.QUERY_PANEL_FROM_BLOCK_INPUT}", Input).value = str(
                query.from_block_number
            )
            self.query_one(f"#{ID.QUERY_PANEL_TO_BLOCK_INPUT}", Input).value = str(
                query.to_block_number
            )

            item = "ASC" if query.sort_order.value == 0 else "DESC"
            self.query_one(
                f"#{ID.QUERY_PANEL_SORT_ORDER_CHOICE}", Choices
            ).index = self.query_one(
                f"#{ID.QUERY_PANEL_SORT_ORDER_CHOICE}", Choices
            ).choices.index(item)

    def hide(self) -> None:
        self.remove_class("visible")
        self.tui.query(BlockListTable)[0].can_focus = True
        self.tui.query(BlockListTable)[0].focus()

    def on_key(self, event: events.Key):
        """
        Occurs when `Key` is emitted.
        """
        if event.key == "Enter":
            self.action_enter()
            from_block = self.query_one(
                f"#{ID.QUERY_PANEL_FROM_BLOCK_INPUT}", Input
            ).value
            to_block = self.query_one(f"#{ID.QUERY_PANEL_TO_BLOCK_INPUT}", Input).value
            sort_order = self.query_one(
                f"#{ID.QUERY_PANEL_SORT_ORDER_CHOICE}", Choices
            ).current_value()

            query = ListBlockDataQuery(
                from_block_number=int(from_block),
                to_block_number=int(to_block),
                sort_order=SortOrder.DESC if sort_order == "DESC" else SortOrder.ASC,
            )
            self.tui.state.block_list_query = query
            self.tui.query_one(BlockListQueryPanel).block_list_query = query

            self.hide()
        else:
            event.stop()
            event.prevent_default()

    async def on_input_changed(self, event: ToBlockInput.Changed):
        """
        Occurs when `Input.Changed` is emitted.
        """
        event.prevent_default()
        event.stop()
        if event.input.id == ID.QUERY_PANEL_TO_BLOCK_INPUT:
            self.query_one(f"#{ID.QUERY_PANEL_FROM_BLOCK_INPUT}", Input).value = str(
                max(int(event.input.value) - self.tui.lot_size - 1, 0)
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Occurs when `Button.Pressed` is emitted.
        """
        if event.button.id == ID.QUERY_PANEL_ENTER:
            self.action_enter()
        else:
            event.stop()
            event.prevent_default()

    class Enter(Message):
        pass

    def action_enter(self):
        """
        Occurs when keybind related to `enter` is called.
        """
        from_block = self.query_one(f"#{ID.QUERY_PANEL_FROM_BLOCK_INPUT}", Input).value
        to_block = self.query_one(f"#{ID.QUERY_PANEL_TO_BLOCK_INPUT}", Input).value
        sort_order = self.query_one(
            f"#{ID.QUERY_PANEL_SORT_ORDER_CHOICE}", Choices
        ).current_value()

        query = ListBlockDataQuery(
            from_block_number=int(from_block),
            to_block_number=int(to_block),
            sort_order=SortOrder.DESC if sort_order == "DESC" else SortOrder.ASC,
        )
        self.tui.state.block_list_query = query
        self.tui.query_one(BlockListQueryPanel).block_list_query = query

        self.post_message(self.Enter())
        self.hide()

    def action_cancel(self):
        """
        Occurs when keybind related to `cancel` is called.
        """
        self.hide()
