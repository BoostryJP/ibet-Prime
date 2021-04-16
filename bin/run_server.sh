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

function start () {

  # TOKEN_LIST_CONTRACT_ADDRESS is HEX_ADDRESS
  if [[ ! ${TOKEN_LIST_CONTRACT_ADDRESS} =~ 0x[0-9a-fA-F]{40} ]]; then
    echo 'Please set the "TOKEN_LIST_CONTRACT_ADDRESS" environment variable and try again.' >&2
    exit 1
  fi

  # gunicorn parameters
  WORKER_COUNT=${WORKER_COUNT:-2}
  WORKER_TIMEOUT=${WORKER_TIMEOUT:-30}
  WORKER_MAX_REQUESTS=${WORKER_MAX_REQUESTS:-500}
  WORKER_MAX_REQUESTS_JITTER=${WORKER_MAX_REQUESTS_JITTER:-200}

  gunicorn --worker-class server.AppUvicornWorker \
           --workers ${WORKER_COUNT} \
           --bind :5000 \
           --timeout ${WORKER_TIMEOUT} \
           --max-requests ${WORKER_MAX_REQUESTS} \
           --max-requests-jitter ${WORKER_MAX_REQUESTS_JITTER} \
           app.main:app
}

function stop () {
  ps -ef | grep gunicorn | awk '{print $1}' | xargs kill -9
}

case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  *)
    echo "Usage: run_server.sh {start|stop}"
    exit 1
esac
