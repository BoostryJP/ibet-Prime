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
from multiprocessing.shared_memory import SharedMemory

from shared_memory_dict import SharedMemoryDict
from shared_memory_dict.lock import lock
from shared_memory_dict.templates import MEMORY_NAME


class DictCache:
    """Cache Utilities

    This class is used to cache data.
    API uses a shared memory object to share the cache data between worker processes, and other is cached on-memory.
    Shared memory objects are saved as physical files, so expand the disk space of Docker container as needed.
    As reference, Docker daemon's default disk space is 10GB, AWS Fargate's is 20GB.
    """

    # NOTE: default_size and extend_incremental is a multiple of 4096.
    USE_CACHE = {
        "e2ee": {
            # NOTE: The maximum RSA key length is assumed to be 10240.
            "default_size": 12288,
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
            DictCache.cache_sizes = SharedMemoryDict(name="cache_sizes", size=4096)

            is_first_init = False
            if len(DictCache.cache_sizes) == 0:
                is_first_init = True
                DictCache.cache_sizes.clear()
            for k, v in DictCache.USE_CACHE.items():
                if v["is_extend_size"] is True:
                    if is_first_init is True:
                        DictCache.cache_sizes[k] = v["default_size"]
                        shm_dict = SharedMemoryDict(name=k, size=v["default_size"])
                    else:
                        shm_dict = SharedMemoryDict(name=k, size=DictCache.cache_sizes[k])
                else:
                    shm_dict = SharedMemoryDict(name=k, size=v["default_size"])
                if is_first_init is True:
                    shm_dict.clear()
                DictCache.caches[k] = {
                    "data": shm_dict,
                    "lock": None
                }
        else:
            for k in DictCache.USE_CACHE.keys():
                DictCache.caches[k] = {
                    "data": {},
                    "lock": threading.Lock()
                }

    def __init__(self, name: str):
        _ = DictCache.USE_CACHE[name]  # check name
        self.name = name
        self.cache = DictCache.caches[name]

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        if key in self.cache["data"]:
            return self.cache["data"][key]
        else:
            return default

    def keys(self) -> KeysView[Any]:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return self.cache["data"].keys()

    def values(self) -> ValuesView[Any]:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return self.cache["data"].values()

    def items(self) -> ItemsView:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return self.cache["data"].items()

    def pop(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write()
            return self.cache["data"].pop(key, default)  # Lock with SharedMemoryDict
        else:
            def _func():
                return self.cache["data"].pop(key, default)

            return self._thread_safe(_func)

    def update(self, other=(), /, **kwargs) -> None:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write(other=other, **kwargs)
            else:
                self.cache["data"].update(other, **kwargs)  # Lock with SharedMemoryDict
        else:
            def _func():
                self.cache["data"].update(other, **kwargs)

            self._thread_safe(_func)

    def __getitem__(self, key: str) -> Any:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return self.cache["data"][key]

    def __setitem__(self, key: str, value: Any) -> None:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write(key=key, value=value)
            else:
                self.cache["data"][key] = value  # Lock with SharedMemoryDict
        else:
            def _func():
                self.cache["data"][key] = value

            self._thread_safe(_func)

    def __len__(self) -> int:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return len(self.cache["data"])

    def __delitem__(self, key: str) -> None:
        if DictCache.MEMORY_CACHE is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write()
            del self.cache["data"][key]  # Lock with SharedMemoryDict
        else:
            def _func():
                del self.cache["data"][key]

            return self._thread_safe(_func)

    def __iter__(self) -> Iterator:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return iter(self.cache["data"])

    def __reversed__(self):
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return reversed(self.cache["data"])

    def __contains__(self, key: str) -> bool:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return key in self.cache["data"]

    def __eq__(self, other: Any) -> bool:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return self.cache["data"] == other

    def __ne__(self, other: Any) -> bool:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return self.cache["data"] != other

    def __str__(self) -> str:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return str(self.cache["data"])

    def __repr__(self) -> str:
        if DictCache.MEMORY_CACHE is False and DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
            self._extend_size_and_write()
        return repr(self.cache["data"])

    def _thread_safe(self, func):
        with self.cache["lock"]:
            result = func()
        return result

    @lock
    def _extend_size_and_write(self, *, key: str = None, value: Any = None, other=(), **kwargs):
        """
        If the cache size becomes large due to updating by another process, reading or writing may fail,
        so extends the size when accessing the shared memory.
        """

        # Check Need Extend
        shm_cache_size = DictCache.cache_sizes[self.name]
        mapped_size = self.cache["data"]._memory_block.size
        if mapped_size != shm_cache_size:
            # Extend Shared Memory Object Mapping Size When READ
            old_shared_memory = self.cache["data"]._memory_block
            # NOTE: Re-open shared memory object and extend mapping memory size.
            old_shared_memory.close()
            new_shared_memory = SharedMemory(name=MEMORY_NAME.format(name=self.name))
            self.cache["data"]._memory_block = new_shared_memory

        if key is None and other == () and kwargs == {}:  # When READ
            return

        # Get Update Data Size
        update_data = {}
        update_data.update(**self.cache["data"])
        if key is not None:
            update_data[key] = value
        else:
            update_data.update(other, **kwargs)
        bin_update_data = pickle.dumps(update_data, pickle.HIGHEST_PROTOCOL)
        update_size = len(bin_update_data)

        # Check Need Extend
        if shm_cache_size >= update_size:
            # NOTE: Save update data independent of @lock decorator.(Avoid deadlock)
            self.cache["data"]._save_memory(update_data)
            return

        # Get Extend Size
        mod_size = shm_cache_size + DictCache.USE_CACHE[self.name]["extend_incremental"]
        while mod_size < update_size:
            mod_size += DictCache.USE_CACHE[self.name]["extend_incremental"]

        # Extend Shared Memory Object Mapping Size When WRITE
        old_shared_memory = self.cache["data"]._memory_block
        # NOTE: Re-create shared memory object.
        old_shared_memory.close()
        old_shared_memory.unlink()
        new_shared_memory = SharedMemory(name=MEMORY_NAME.format(name=self.name), create=True, size=mod_size)
        self.cache["data"]._memory_block = new_shared_memory
        # NOTE: Save update data independent of @lock decorator.(Avoid deadlock)
        self.cache["data"]._save_memory(update_data)

        # Update Cache Sizes
        tmp_cache_sizes = {}
        tmp_cache_sizes.update(**DictCache.cache_sizes)
        tmp_cache_sizes[self.name] = mod_size
        # NOTE: Save cache sizes data independent of @lock decorator.(Avoid deadlock)
        DictCache.cache_sizes._save_memory(tmp_cache_sizes)


DictCache.initialize()
