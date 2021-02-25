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

from uvicorn.workers import UvicornWorker

# uvicorn parameters
WORKER_CONNECTIONS = int(os.environ.get('WORKER_CONNECTIONS')) \
    if os.environ.get('WORKER_CONNECTIONS') else 100


# Worker class to load by gunicorn when server run
class AppUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "loop": "asyncio",
        "http": "h11",
        # NOTE: gunicorn don't support '--worker-connections' to uvicorn
        "limit_concurrency": WORKER_CONNECTIONS
    }
