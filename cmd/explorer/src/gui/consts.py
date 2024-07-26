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

from enum import StrEnum

UP = "\u2191"
DOWN = "\u2193"
LEFT = "\u2190"
RIGHT = "\u2192"
RIGHT_TRIANGLE = "\u25b6"
BIG_RIGHT_TRIANGLE = "\ue0b0"
DOWN_TRIANGLE = "\u25bc"

THINKING_FACE = ":thinking_face:"
FIRE = ":fire:"
INFO = "[blue]:information:[/]"


class ID(StrEnum):
    BLOCK_CONNECTED = "block_connected"
    BLOCK_CURRENT_BLOCK_NUMBER = "block_current_block_number"
    BLOCK_IS_SYNCED = "block_is_synced"
    BLOCK_NOTION = "block_notion"
    BLOCK_SCREEN_HEADER = "block_screen_header"

    BLOCK_LIST_FILTER = "block_list_filter"
    BLOCK_LIST_LOADED_TIME = "block_list_loaded_time"
    BLOCK_LIST_LOADING = "block_list_loading"
    BLOCK_LIST_DESCRIPTION = "block_list_description"
    BLOCK_LIST_TABLE = "block_list_table"

    TX_SELECTED_BLOCK_NUMBER = "tx_selected_block_number"

    MENU = "menu"
    MENU_CANCEL = "menu_cancel"
    MENU_SHOW_TX = "menu_show_tx"

    QUERY_PANEL = "query_panel"
    QUERY_PANEL_FROM_BLOCK_INPUT = "query_panel_from_block_input"
    QUERY_PANEL_TO_BLOCK_INPUT = "query_panel_to_block_input"
    QUERY_PANEL_SORT_ORDER_CHOICE = "query_panel_sort_order_choice"
    QUERY_PANEL_ENTER = "query_panel_enter"
