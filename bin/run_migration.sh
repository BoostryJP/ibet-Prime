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

function usage () {
  cat << EOS 1>&2
usage:
    $0 init
        Setup Migration Environment, and Execute All Migration Script.

    $0 upgrade [\$rev] [-p]
        Upgrade Database.

        args:
            rev: Migration Revision(default: head)
            -p: Print SQL string(not reflect database)

    $0 downgrade [\$rev] [-p]
        Downgrade Database.

        args:
            rev: Migration Revision(default: base)
            -p: Print SQL string(not reflect database)

    $0 generate \$file_suffix
        Generate Migration Script.

        args:
            file_suffix: Script file suffix

    $0 reset
        Delete Version Control Table.

    $0 sync
        Sync App DB Model, but Not Manage Version Control.
EOS
}

function init() {
  alembic upgrade head
}

function upgrade() {
  REV=${1:-head}
  if [ "$2" == "-p" ]; then
    alembic upgrade "${REV}" --sql 2>&1 | grep -v "alembic.runtime.migration"
  else
    alembic upgrade "${REV}"
  fi
}

function downgrade() {
  REV=${1:-base}
  if [ "$2" == "-p" ]; then
    alembic downgrade "${REV}" --sql 2>&1 | grep -v "alembic.runtime.migration"
  else
    alembic downgrade "${REV}"
  fi
}

function generate() {
  SUF=$1
  alembic revision --autogenerate -m "${SUF}"
}

function reset() {
  python migrations/manage.py reset
}

function sync() {
  mkdir migrations/versions_tmp/
  mv migrations/versions/* migrations/versions_tmp/
  reset
  generate "dummy"
  upgrade
  reset
  rm -fr migrations/versions/*
  mv migrations/versions_tmp/* migrations/versions/
  rm -fr migrations/versions_tmp/
}

case "$1" in
  "init")
    init
    ;;
  "upgrade")
    shift 1
    upgrade "$@"
    ;;
  "downgrade")
    shift 1
    downgrade "$@"
    ;;
  "generate")
    shift 1
    generate "$@"
    ;;
  "reset")
    reset
    ;;
  "sync")
    sync
    ;;
  *)
    usage
    ;;
esac
