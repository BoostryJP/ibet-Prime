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
import inspect
from typing import (
    Optional,
    Any,
    KeysView,
    ValuesView,
    ItemsView,
    Iterator
)
import threading
import pickle
import mmap

from shared_memory_dict import SharedMemoryDict
from shared_memory_dict.lock import lock

from app.log import get_logger

LOG = get_logger()


class DictCache:
    # NOTE: is_extend_size=True is deprecated.(Unverified)
    USE_CACHE = {
        "e2ee": {
            # NOTE: The maximum RSA key length is assumed to be 10240.
            "default_size": 10000,
            "is_extend_size": False,
            "extend_incremental": 0,
        },
    }
    MEMORY_CACHE = False
    caches = {}
    cache_sizes = None

    @staticmethod
    def initialize():
        if "pytest" in sys.modules or \
                inspect.getfile(inspect.stack()[-1][0]).startswith("batch/") or \
                os.environ.get("SHARED_MEMORY_USE_LOCK") != "1":
            DictCache.MEMORY_CACHE = True

        if DictCache.MEMORY_CACHE is False:

            # NOTE: Create an SharedMemoryDict to share the current cache size between processes.
            DictCache.cache_sizes = SharedMemoryDict(name="cache_sizes", size=128)

            is_first_init = False
            if len(DictCache.cache_sizes) == 0:
                is_first_init = True
            for k, v in DictCache.USE_CACHE.items():
                if v["is_extend_size"] is True:
                    if is_first_init is True:
                        DictCache.cache_sizes[k] = v["default_size"]
                        shm_dict = SharedMemoryDict(name=k, size=v["default_size"])
                    else:
                        shm_dict = SharedMemoryDict(name=k, size=DictCache.cache_sizes[k])
                else:
                    shm_dict = SharedMemoryDict(name=k, size=v["default_size"])
                DictCache.caches[k] = {
                    "data": shm_dict,
                    "lock": threading.Lock()
                }
        else:
            for k in DictCache.USE_CACHE.keys():
                DictCache.caches[k] = {
                    "data": {},
                    "lock": threading.Lock()
                }

    def __init__(self, name):
        _ = DictCache.USE_CACHE[name]  # check name
        self.name = name
        self.cache = DictCache.caches[name]

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        if key in self.cache["data"]:
            return self.cache["data"][key]
        else:
            return default

    def keys(self) -> KeysView[Any]:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return self.cache["data"].keys()

    def values(self) -> ValuesView[Any]:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return self.cache["data"].values()

    def items(self) -> ItemsView:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return self.cache["data"].items()

    def pop(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size()
            return self.cache["data"].pop(key, default)
        else:
            def _func():
                return self.cache["data"].pop(key, default)

            return self._thread_safe(_func)

    def update(self, other=(), /, **kwargs) -> None:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size()
            self.cache["data"].update(other, **kwargs)
        else:
            def _func():
                return self.cache["data"].update(other, **kwargs)

            self._thread_safe(_func)

    def __getitem__(self, key: str) -> Any:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return self.cache["data"][key]

    def __setitem__(self, key: str, value: Any) -> None:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size()
            self.cache["data"][key] = value
        else:
            def _func():
                self.cache["data"][key] = value

            self._thread_safe(_func)

    def __len__(self) -> int:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return len(self.cache["data"])

    def __delitem__(self, key: str) -> None:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size()
            del self.cache["data"][key]
        else:
            def _func():
                del self.cache["data"][key]

            return self._thread_safe(_func)

    def __iter__(self) -> Iterator:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return iter(self.cache["data"])

    def __reversed__(self):
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return reversed(self.cache["data"])

    def __contains__(self, key: str) -> bool:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return key in self.cache["data"]

    def __eq__(self, other: Any) -> bool:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return self.cache["data"] == other

    def __ne__(self, other: Any) -> bool:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return self.cache["data"] != other

    def __str__(self) -> str:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return str(self.cache["data"])

    def __repr__(self) -> str:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size()
        return repr(self.cache["data"])

    def _thread_safe(self, func):
        self.cache["lock"].acquire()
        func()
        self.cache["lock"].release()

    @lock
    def _extend_size(self):
        """
        If the cache size becomes large due to updating by another process, reading and writing may fail,
        so extends the size when accessing the shared memory.
        """

        # NOTE: Deprecated.(Unverified)
        import warnings
        warnings.warn("Unverified", DeprecationWarning)

        # Check Need Extend
        tmp_cache = {}
        data = pickle.dumps(tmp_cache, pickle.HIGHEST_PROTOCOL)
        update_size = len(data)
        now_size = DictCache.cache_sizes[self.name]
        if now_size >= update_size:
            return

        # Get Extend Size
        mod_size = now_size + DictCache.USE_CACHE[self.name]["extend_incremental"]
        while mod_size < update_size:
            mod_size += DictCache.USE_CACHE[self.name]["extend_incremental"]

        # Extend Shared Memory Object Size
        memory_block = self.cache["data"]._memory_block
        os.ftruncate(memory_block._fd, mod_size)
        stats = os.fstat(memory_block._fd)
        size = stats.st_size
        memory_block._mmap = mmap.mmap(memory_block._fd, size)
        memory_block._size = size
        memory_block._buf = memoryview(memory_block._mmap)


DictCache.initialize()
