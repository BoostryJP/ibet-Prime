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

from gui import styles
from gui.rendarable.block_detail_info import BlockDetailInfo
from gui.widget.base import TuiWidget
from rich.align import Align
from rich.panel import Panel
from rich.style import Style
from textual.reactive import Reactive, reactive

from app.model.schema import BlockDataDetail


class BlockDetailView(TuiWidget):
    block_detail: Reactive[BlockDataDetail | None] = reactive(None)

    def watch_block_detail(self, old: BlockDetailInfo, new: BlockDetailInfo):
        """
        Occurs when `block_detail` is changed
        """
        self.render()

    def render(self) -> Panel:
        block_detail: Union[Align, BlockDetailInfo] = Align.center(
            "Press [E] to set query", vertical="middle"
        )
        style: Style | Literal["none"] = Style(bgcolor="#004578")

        if self.block_detail is not None:
            block_detail = BlockDetailInfo(self.block_detail)
            style = "none"

        panel = Panel(
            block_detail,
            title="[bold]Block[/]",
            title_align="left",
            style=style,
            border_style=styles.BORDER,
            box=styles.BOX,
        )

        return panel
