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
  ./bin/run_server.sh start &
elif [ "${RUN_MODE}" == "batch" ]; then
  ./bin/run_indexer.sh &
  ./bin/run_processor.sh &
elif [ "${RUN_MODE}" == "batch_indexer" ]; then
  ./bin/run_indexer.sh &
elif [ "${RUN_MODE}" == "batch_processor" ]; then
  ./bin/run_processor.sh &
elif [ "${RUN_MODE}" == "all" ]; then
  ./bin/run_server.sh start &
  ./bin/run_indexer.sh &
  ./bin/run_processor.sh &
else
  echo "RUN_MODE is invalid value." >&2
  exit 1
fi

function trap_sigterm() {
  echo "$0: Shutdown."
  if [ "${RUN_MODE}" == "server" ]; then
    PIDS=$(ps -ef | grep "[p]ython run.py" | awk '{print $2}')
  else
    PIDS=$(ps -ef | grep "[p]ython batch" | awk '{print $2}')
  fi

  for PID in $PIDS; do
    echo "Sending SIGTERM to PID $PID"
    kill -15 $PID
  done
  for PID in $PIDS; do
    tail --pid=$PID -f /dev/null
    echo "$PID is shutdown"
  done
  exit 0
}
trap trap_sigterm INT TERM

while :; do
  sleep 5
done
