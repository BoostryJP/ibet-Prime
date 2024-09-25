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

import asyncio
import signal
from asyncio import Event
from logging import Logger


async def shutdown(logger: Logger, sig: signal.Signals, is_shutdown: Event) -> None:
    """Shutdown"""
    logger.info(f"Service is shutting down due to {sig.name}")

    # trigger is_shutdown event
    is_shutdown.set()


def setup_signal_handler(logger: Logger, is_shutdown: Event) -> None:
    """Setup signal handler"""
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(logger, s, is_shutdown))
        )
