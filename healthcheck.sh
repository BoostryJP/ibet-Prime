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
source ~/.bash_profile
RUN_MODE=${RUN_MODE:-server}
cd /app/ibet-Prime

if [ "${RUN_MODE}" == "server" ]; then
  ./bin/healthcheck_server.sh
elif [ "${RUN_MODE}" == "batch" ]; then
  ./bin/healthcheck_indexer.sh || exit 1
  ./bin/healthcheck_processor.sh
elif [ "${RUN_MODE}" == "batch_indexer" ]; then
  ./bin/healthcheck_indexer.sh
elif [ "${RUN_MODE}" == "batch_processor" ]; then
  ./bin/healthcheck_processor.sh
elif [ "${RUN_MODE}" == "all" ]; then
  ./bin/healthcheck_server.sh || exit 1
  ./bin/healthcheck_indexer.sh || exit 1
  ./bin/healthcheck_processor.sh
else
  echo "RUN_MODE is invalid value." >&2
  exit 1
fi


