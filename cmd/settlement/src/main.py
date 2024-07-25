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

import base64
import json
import logging
import sys
from typing import Annotated

import click
import httpx
import typer
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from rich import print
from rich.console import Console
from rich.table import Table

from app.model.db import DeliveryStatus
from app.model.schema import (
    AbortDVPDeliveryRequest,
    CreateDVPAgentAccountRequest,
    FinishDVPDeliveryRequest,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command(name="list")
def list_deliveries(
    exchange_address: str,
    agent_address: str,
    status: Annotated[
        str,
        typer.Argument(
            click_type=click.Choice(
                [DeliveryStatus(d).name for d in DeliveryStatus], case_sensitive=False
            )
        ),
    ] = "delivery_confirmed",
    api_url: Annotated[
        str, typer.Argument(..., envvar="API_URL")
    ] = "http://localhost:5000",
):
    resp = httpx.get(
        url=f"{api_url}/settlement/dvp/agent/{exchange_address}/deliveries",
        params={
            "agent_address": agent_address,
            "status": DeliveryStatus[status.upper()].value,
        },
    )

    if resp.status_code != 200:
        typer.echo(typer.style("Failed to get deliveries", fg="red"), err=True)
        print(resp.json())
        sys.exit(1)

    console = Console()

    delivery_table = Table()
    delivery_table.add_column("Delivery ID")
    delivery_table.add_column("Token Address")
    delivery_table.add_column("Buyer")
    delivery_table.add_column("Seller")
    delivery_table.add_column("Amount")
    delivery_table.add_column("Agent")
    delivery_table.add_column("Data")
    delivery_table.add_column("Status")

    for idx_delivery in resp.json()["deliveries"]:
        match idx_delivery["status"]:
            case DeliveryStatus.DELIVERY_CREATED:
                status = "Created"
            case DeliveryStatus.DELIVERY_CANCELED:
                status = "Canceled"
            case DeliveryStatus.DELIVERY_CONFIRMED:
                status = "Confirmed"
            case DeliveryStatus.DELIVERY_FINISHED:
                status = "Finished"
            case DeliveryStatus.DELIVERY_ABORTED:
                status = "Aborted"
            case _:
                status = None

        delivery_table.add_row(
            str(idx_delivery["delivery_id"]),
            idx_delivery["token_address"],
            idx_delivery["buyer_address"],
            idx_delivery["seller_address"],
            str(idx_delivery["amount"]),
            idx_delivery["agent_address"],
            idx_delivery["data"],
            status,
        )

    console.print(delivery_table)


@app.command(name="finish")
def finish(
    exchange_address: str,
    agent_address: str,
    delivery_id: int,
    eoa_password: Annotated[str, typer.Argument(..., envvar="EOA_PASSWORD")] = None,
    api_url: Annotated[
        str, typer.Argument(..., envvar="API_URL")
    ] = "http://localhost:5000",
):
    resp = httpx.get(url=f"{api_url}/e2ee")

    if resp.status_code != 200:
        print("Failed to get e2ee pubkey")
        print(resp.json())
        sys.exit(1)

    if resp.json()["public_key"] is not None:
        rsa_publickey = RSA.importKey(resp.json()["public_key"])
        cipher = PKCS1_OAEP.new(rsa_publickey)
        eoa_password = base64.encodebytes(cipher.encrypt(eoa_password.encode("utf-8")))

    finish_params = FinishDVPDeliveryRequest(
        operation_type="Finish",
        account_address=agent_address,
        eoa_password=eoa_password,
    )

    resp = httpx.post(
        url=f"{api_url}/settlement/dvp/agent/{exchange_address}/delivery/{delivery_id}",
        json=json.loads(finish_params.model_dump_json()),
    )

    if resp.status_code != 200:
        typer.echo(typer.style("Failed to finish the delivery", fg="red"), err=True)
        print(resp.json())
        sys.exit(1)

    typer.echo(typer.style("Successfully finished the delivery", fg="blue"))
    print(f"delivery_id: {delivery_id}")


@app.command(name="abort")
def abort(
    exchange_address: str,
    agent_address: str,
    delivery_id: int,
    eoa_password: Annotated[str, typer.Argument(..., envvar="EOA_PASSWORD")] = None,
    api_url: Annotated[
        str, typer.Argument(..., envvar="API_URL")
    ] = "http://localhost:5000",
):
    resp = httpx.get(url=f"{api_url}/e2ee")

    if resp.status_code != 200:
        print("Failed to get e2ee pubkey")
        print(resp.json())
        sys.exit(1)

    if resp.json()["public_key"] is not None:
        rsa_publickey = RSA.importKey(resp.json()["public_key"])
        cipher = PKCS1_OAEP.new(rsa_publickey)
        eoa_password = base64.encodebytes(cipher.encrypt(eoa_password.encode("utf-8")))

    abort_params = AbortDVPDeliveryRequest(
        operation_type="Abort", account_address=agent_address, eoa_password=eoa_password
    )

    resp = httpx.post(
        url=f"{api_url}/settlement/dvp/agent/{exchange_address}/delivery/{delivery_id}",
        json=json.loads(abort_params.model_dump_json()),
    )

    if resp.status_code != 200:
        typer.echo(typer.style("Failed to abort the delivery", fg="red"), err=True)
        print(resp.json())
        sys.exit(1)

    typer.echo(typer.style("Successfully aborted the delivery", fg="blue"))
    print(f"delivery_id: {delivery_id}")


@app.command(name="create_agent")
def create_agent(
    eoa_password: Annotated[str, typer.Argument(..., envvar="EOA_PASSWORD")],
    api_url: Annotated[
        str, typer.Argument(..., envvar="API_URL")
    ] = "http://localhost:5000",
):
    resp = httpx.get(url=f"{api_url}/e2ee")

    if resp.status_code != 200:
        print("Failed to get e2ee pubkey")
        print(resp.json())
        sys.exit(1)

    if resp.json()["public_key"] is not None:
        rsa_publickey = RSA.importKey(resp.json()["public_key"])
        cipher = PKCS1_OAEP.new(rsa_publickey)
        eoa_password = base64.encodebytes(cipher.encrypt(eoa_password.encode("utf-8")))

    create_agent_param = CreateDVPAgentAccountRequest(eoa_password=eoa_password)

    resp = httpx.post(
        url=f"{api_url}/settlement/dvp/agent/accounts",
        json=json.loads(create_agent_param.model_dump_json()),
    )

    if resp.status_code != 200:
        typer.echo(typer.style("Failed to create agent account", fg="red"), err=True)
        print(resp.json())
        sys.exit(1)

    typer.echo(typer.style("Successfully created agent account", fg="blue"))
    print(f"account_address: {resp.json()['account_address']}")


if __name__ == "__main__":
    app()
