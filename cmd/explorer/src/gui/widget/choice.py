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
from textual.binding import Binding
from textual.widgets import Label, ListItem, ListView


class Choices(ListView):
    BINDINGS = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False, priority=True),
        Binding("ctrl+p", "cursor_up", "Cursor Up", show=False, priority=True),
        Binding("down", "cursor_down", "Cursor Down", show=False, priority=True),
        Binding("ctrl+n", "cursor_down", "Cursor Down", show=False, priority=True),
    ]

    def __init__(self, choices: list[str], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.choices = choices

    def compose(self) -> ComposeResult:
        for choice in self.choices:
            yield ListItem(Label(choice))

    @property
    def value(self) -> ListItem | None:
        return self.highlighted_child

    @value.setter
    def value(self, v: str):
        idx = self.choices.index(v)
        if idx is None:
            return
        else:
            self.index = idx
            self.render()

    def current_value(self):
        return self.choices[self.index]
