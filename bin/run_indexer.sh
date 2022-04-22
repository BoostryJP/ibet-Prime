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

python batch/indexer_personal_info.py &
python batch/indexer_position_bond.py &
python batch/indexer_position_share.py &
python batch/indexer_token_holders.py &
python batch/indexer_transfer.py &
python batch/indexer_transfer_approval.py &

if [ -n "${E2E_MESSAGING_CONTRACT_ADDRESS}" ]; then
  python batch/indexer_e2e_messaging.py &
fi

tail -f /dev/null
