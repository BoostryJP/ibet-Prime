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
from typing import Literal, Union

from rich.align import Align
from rich.panel import Panel
from rich.style import Style
from src.gui import styles
from src.gui.rendarable.tx_detail_info import TxDetailInfo
from src.gui.widget.base import TuiWidget
from textual.reactive import Reactive, reactive

from app.model.schema import TxDataDetail


class TxDetailView(TuiWidget):
    tx_detail: Reactive[TxDataDetail | None] = reactive(None)

    def on_mount(self) -> None:
        """
        Occurs when Self is mounted
        """
        pass

    def watch_tx_detail(self, old: TxDetailInfo, new: TxDetailInfo):
        """
        Occurs when `tx_detail` is changed
        """
        self.render()

    def render(self) -> Panel:
        tx_detail: Union[Align, TxDetailInfo] = Align.center(
            "Not selected", vertical="middle"
        )
        style: Style | Literal["none"] = Style(bgcolor="#004578")

        if self.tx_detail is not None:
            tx_detail = TxDetailInfo(self.tx_detail)
            style = "none"

        panel = Panel(
            tx_detail,
            title="[bold]Transaction[/]",
            style=style,
            border_style=styles.BORDER,
            box=styles.BOX,
            title_align="left",
            padding=0,
        )

        return panel
