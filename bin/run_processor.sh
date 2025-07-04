#!/bin/bash

# Copyright BOOSTRY Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# shellcheck disable=SC1090
source ~/.bash_profile
cd /app/ibet-Prime

python batch/processor_generate_rsa_key.py &
python batch/processor_modify_personal_info.py &
python batch/processor_bulk_transfer.py &
python batch/processor_create_utxo.py &
python batch/processor_create_ledger.py &
python batch/processor_scheduled_events.py &
python batch/processor_monitor_block_sync.py &
python batch/processor_update_token.py &
python batch/processor_batch_issue_redeem.py &
python batch/processor_batch_register_personal_info.py &
python batch/processor_dvp_async_tx.py &
python batch/processor_batch_create_child_account.py &

if [ -n "${E2E_MESSAGING_CONTRACT_ADDRESS}" ]; then
  python batch/processor_rotate_e2e_messaging_rsa_key.py &
fi

if [[ $IBET_WST_FEATURE_ENABLED = 1 ]]; then
  python batch/processor_eth_wst_bridge_to_ibet.py &
  python batch/processor_eth_wst_monitor_bridge_events.py &
  python batch/processor_eth_wst_monitor_txreceipt.py &
  python batch/processor_eth_wst_send_tx.py &
fi

tail -f /dev/null
