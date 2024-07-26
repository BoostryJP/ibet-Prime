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

from typing import Literal

from rich.align import Align
from rich.panel import Panel
from rich.style import Style
from rich.traceback import Traceback

from src.gui import styles
from src.gui.widget.base import TuiWidget


class TracebackWidget(TuiWidget):
    def render(self) -> Panel:
        style: Style | Literal["none"] = Style()
        if self.tui.state.error is not None:
            trace_back = Traceback.from_exception(
                exc_type=type(self.tui.state.error),
                exc_value=self.tui.state.error,
                traceback=self.tui.state.error.__traceback__,
            )
            content: Align = Align.center(trace_back, vertical="middle")
        else:
            content = Align.center("", vertical="middle")

        panel = Panel(
            content,
            title="[bold]Exception[/]",
            style=style,
            border_style=styles.BORDER,
            box=styles.BOX,
            title_align="left",
            padding=0,
            highlight=True,
        )

        return panel
