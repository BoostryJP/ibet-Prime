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
from rich.console import Group
from rich.panel import Panel
from rich.table import Table

from app.model.schema import TxDataDetail


class TxDetailInfo:
    def __init__(self, tx_detail: TxDataDetail) -> None:
        self.tx_detail = tx_detail

    def __str__(self) -> str:
        return str(self.tx_detail)

    def __rich__(self) -> Group:
        common_table = Table(box=None, expand=False, show_header=False, show_edge=False)
        common_table.add_column(style="deep_pink2 bold")
        common_table.add_column()

        common_table.add_row("Transaction Hash:", self.tx_detail.hash)
        common_table.add_row("Block:", str(self.tx_detail.block_number))
        common_table.add_row("From:", self.tx_detail.from_address)
        common_table.add_row("Nonce:", str(self.tx_detail.nonce))
        common_table.add_row("To:", self.tx_detail.to_address)

        common_table.add_row("Value:", str(self.tx_detail.value))
        common_table.add_row("Gas Price:", str(self.tx_detail.gas_price))
        common_table.add_row("Gas:", str(self.tx_detail.gas))

        contract_table = Table(
            box=None, expand=False, show_header=False, show_edge=False
        )
        contract_table.add_column(style="deep_pink2 bold")
        contract_table.add_row("Contract Name:", self.tx_detail.contract_name)
        contract_table.add_row("Contract Function:", self.tx_detail.contract_function)
        if self.tx_detail.contract_parameters is not None:
            function_arguments_table = Table(
                box=None, expand=False, show_header=False, show_edge=False
            )
            for k, v in self.tx_detail.contract_parameters.items():
                function_arguments_table.add_row(f"{k}: ", str(v))
            contract_table.add_row(
                "Contract Function Arguments:", Panel(function_arguments_table)
            )

        return Group(
            Panel(common_table, expand=True, title="Common", title_align="left"),
            Panel(contract_table, expand=True, title="Contract", title_align="left"),
        )
