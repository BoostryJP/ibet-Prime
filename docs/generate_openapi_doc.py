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

import os
import sys

import typer
from ruamel.yaml import YAML

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.main import app


def str_represent(dumper, data):
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def none_represent(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:null", "null")


def main():
    openapi_json = app.openapi()
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.representer.add_representer(str, str_represent)
    yaml.representer.add_representer(type(None), none_represent)

    with open(
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                os.path.pardir,
                "docs/ibet_prime.yaml",
            ),
        ),
        "w",
        encoding="utf-8",
    ) as f:
        yaml.dump(openapi_json, f)


if __name__ == "__main__":
    typer.run(main)
