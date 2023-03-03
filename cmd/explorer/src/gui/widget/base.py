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

from textual.widget import Widget
from textual.widgets import Static

if TYPE_CHECKING:
    from src.gui.explorer import ExplorerApp


class TuiWidget(Widget):
    @property
    def tui(self) -> "ExplorerApp":
        return cast("ExplorerApp", self.app)


class TuiStatic(Static):
    @property
    def tui(self) -> "ExplorerApp":
        return cast("ExplorerApp", self.app)
