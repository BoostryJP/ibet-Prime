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

PROC_LIST="${PROC_LIST} batch/processor_generate_rsa_key.py"
PROC_LIST="${PROC_LIST} batch/processor_modify_personal_info.py"
PROC_LIST="${PROC_LIST} batch/processor_bulk_transfer.py"
PROC_LIST="${PROC_LIST} batch/processor_create_utxo.py"
PROC_LIST="${PROC_LIST} batch/processor_scheduled_events.py"
PROC_LIST="${PROC_LIST} batch/processor_monitor_block_sync.py"
PROC_LIST="${PROC_LIST} batch/processor_update_token.py"

if [ -n "${E2E_MESSAGING_CONTRACT_ADDRESS}" ]; then
  PROC_LIST="${PROC_LIST} batch/processor_rotate_e2e_messaging_rsa_key.py"
fi

for i in ${PROC_LIST}; do
  # shellcheck disable=SC2009
  ps -ef | grep -v grep | grep "$i"
  if [ $? -ne 0 ]; then
    exit 1
  fi
done