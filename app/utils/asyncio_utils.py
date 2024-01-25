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
from asyncio import Semaphore, TaskGroup
from typing import Any, Coroutine, TypeVar


class SemaphoreTaskGroup(TaskGroup):
    def __init__(self, *, max_concurrency: int = 0):
        """
        @param max_concurrency: the number of concurrent tasks running
        """
        super().__init__()
        if max_concurrency:
            self._semaphore = Semaphore(value=max_concurrency)
        else:
            self._semaphore = None

    T = TypeVar("T")

    @classmethod
    async def run(
        cls, *args: Coroutine[Any, Any, T], max_concurrency: int
    ) -> list[asyncio.Future[T]]:
        """

        @param args: coroutines
        @param max_concurrency: the number of concurrent tasks running
        @return: dispatched tasks
        """
        async with SemaphoreTaskGroup(max_concurrency=max_concurrency) as tg:
            dispatched = [tg.create_task(coro) for coro in args]
        return dispatched

    def create_task(self, coro, *args, **kwargs):
        """
        @param coro: awaitable object
        @param args: args
        @param kwargs: kwargs
        @return: future task
        """
        if self._semaphore:

            async def _wrapped_coro(sem, coro):
                async with sem:
                    return await coro

            coro = _wrapped_coro(self._semaphore, coro)

        return super().create_task(coro, *args, **kwargs)
