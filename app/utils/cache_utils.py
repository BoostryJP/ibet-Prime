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

import inspect
import os
import pickle
import sys
import threading
from collections.abc import Callable, Iterable, Mapping
from multiprocessing.shared_memory import SharedMemory
from typing import (
    Any,
    ItemsView,
    Iterator,
    KeysView,
    TypeAlias,
    TypedDict,
    ValuesView,
    cast,
)

from shared_memory_dict import SharedMemoryDict
from shared_memory_dict.lock import lock
from shared_memory_dict.templates import MEMORY_NAME

UpdateOther: TypeAlias = Mapping[str, Any] | Iterable[tuple[str, Any]] | tuple[()]


class CacheConfig(TypedDict):
    default_size: int
    is_extend_size: bool
    extend_incremental: int


class CacheEntry(TypedDict):
    data: SharedMemoryDict | dict[str, Any]
    lock: Any | None


class DictCache:
    """Cache Utilities

    This class is used to cache data.
    API uses a shared memory object to share the cache data between worker processes, and other is cached on-memory.
    Shared memory objects are saved as physical files, so expand the disk space of Docker container as needed.
    As reference, Docker daemon's default disk space is 10GB, AWS Fargate's is 20GB.
    """

    # NOTE: default_size and extend_incremental is a multiple of 4096.
    USE_CACHE: dict[str, CacheConfig] = {
        "e2ee": {
            # NOTE: The maximum RSA key length is assumed to be 10240.
            "default_size": 12288,
            "is_extend_size": False,
            "extend_incremental": 0,
        },
    }
    memory_cache: bool = False
    caches: dict[str, CacheEntry] = {}
    cache_sizes: SharedMemoryDict | None = None

    @staticmethod
    def initialize() -> None:
        if (
            "pytest" in sys.modules
            or inspect.getfile(inspect.stack()[-1][0]).startswith("batch/")
            or os.environ.get("SHARED_MEMORY_USE_LOCK") != "1"
        ):
            DictCache.memory_cache = True

        if DictCache.memory_cache is False:
            # NOTE: Create an SharedMemoryDict to share the current cache size between processes.
            DictCache.cache_sizes = SharedMemoryDict(name="cache_sizes", size=4096)
            cache_sizes = DictCache.cache_sizes
            assert cache_sizes is not None

            is_first_init = False
            if len(cache_sizes) == 0:
                is_first_init = True
                cache_sizes.clear()
            for k, v in DictCache.USE_CACHE.items():
                if v["is_extend_size"] is True:
                    if is_first_init is True:
                        cache_sizes[k] = v["default_size"]
                        shm_dict = SharedMemoryDict(name=k, size=v["default_size"])
                    else:
                        shm_dict = SharedMemoryDict(
                            name=k, size=cast(int, cache_sizes[k])
                        )
                else:
                    shm_dict = SharedMemoryDict(name=k, size=v["default_size"])
                if is_first_init is True:
                    shm_dict.clear()
                DictCache.caches[k] = {"data": shm_dict, "lock": None}
        else:
            for k in DictCache.USE_CACHE.keys():
                DictCache.caches[k] = {"data": {}, "lock": threading.Lock()}

    def __init__(self, name: str):
        _ = DictCache.USE_CACHE[name]  # check name
        self.name = name
        self.cache: CacheEntry = DictCache.caches[name]

    def get(self, key: str, default: Any | None = None) -> Any | None:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        if key in self.cache["data"]:
            return self.cache["data"][key]
        else:
            return default

    def keys(self) -> KeysView[Any]:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return self.cache["data"].keys()

    def values(self) -> ValuesView[Any]:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return self.cache["data"].values()

    def items(self) -> ItemsView[str, Any]:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return self.cache["data"].items()

    def pop(self, key: str, default: Any | None = None) -> Any | None:
        if DictCache.memory_cache is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write()
            return self.cache["data"].pop(key, default)  # Lock with SharedMemoryDict
        else:

            def _func():
                return self.cache["data"].pop(key, default)

            return self._thread_safe(_func)

    def update(self, other: UpdateOther = (), /, **kwargs: Any) -> None:
        if DictCache.memory_cache is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write(other=other, **kwargs)
            else:
                self.cache["data"].update(other, **kwargs)  # Lock with SharedMemoryDict
        else:

            def _func():
                self.cache["data"].update(other, **kwargs)

            self._thread_safe(_func)

    def __getitem__(self, key: str) -> Any:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return self.cache["data"][key]

    def __setitem__(self, key: str, value: Any) -> None:
        if DictCache.memory_cache is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write(key=key, value=value)
            else:
                self.cache["data"][key] = value  # Lock with SharedMemoryDict
        else:

            def _func():
                self.cache["data"][key] = value

            self._thread_safe(_func)

    def __len__(self) -> int:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return len(self.cache["data"])

    def __delitem__(self, key: str) -> None:
        if DictCache.memory_cache is False:
            if DictCache.USE_CACHE[self.name]["is_extend_size"] is True:
                self._extend_size_and_write()
            del self.cache["data"][key]  # Lock with SharedMemoryDict
        else:

            def _func():
                del self.cache["data"][key]

            self._thread_safe(_func)

    def __iter__(self) -> Iterator[str]:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return iter(self.cache["data"])

    def __reversed__(self) -> Iterator[str]:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return reversed(list(self.cache["data"]))

    def __contains__(self, key: str) -> bool:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return key in self.cache["data"]

    def __eq__(self, other: Any) -> bool:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return self.cache["data"] == other

    def __ne__(self, other: Any) -> bool:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return self.cache["data"] != other

    def __str__(self) -> str:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return str(self.cache["data"])

    def __repr__(self) -> str:
        if (
            DictCache.memory_cache is False
            and DictCache.USE_CACHE[self.name]["is_extend_size"] is True
        ):
            self._extend_size_and_write()
        return repr(self.cache["data"])

    def _thread_safe[T](self, func: Callable[[], T]) -> T:
        lock_obj = self.cache["lock"]
        assert lock_obj is not None
        with lock_obj:
            result = func()
        return result

    @lock
    def _extend_size_and_write(
        self,
        *,
        key: str | None = None,
        value: Any = None,
        other: UpdateOther = (),
        **kwargs: Any,
    ) -> None:
        """
        If the cache size becomes large due to updating by another process, reading or writing may fail,
        so extends the size when accessing the shared memory.
        """

        # Check Need Extend
        cache_sizes = DictCache.cache_sizes
        assert cache_sizes is not None
        shm_cache_size = cast(int, cache_sizes[self.name])
        cache_data = cast(SharedMemoryDict, self.cache["data"])
        mapped_size = cache_data._memory_block.size
        if mapped_size != shm_cache_size:
            # Extend Shared Memory Object Mapping Size When READ
            old_shared_memory = cache_data._memory_block
            # NOTE: Re-open shared memory object and extend mapping memory size.
            old_shared_memory.close()
            new_shared_memory = SharedMemory(name=MEMORY_NAME.format(name=self.name))
            cache_data._memory_block = new_shared_memory

        if key is None and other == () and kwargs == {}:  # When READ
            return

        # Get Update Data Size
        update_data: dict[str, Any] = dict(cache_data.items())
        if key is not None:
            update_data[key] = value
        else:
            if other != ():
                update_data.update(other, **kwargs)
            else:
                update_data.update(**kwargs)
        bin_update_data = pickle.dumps(update_data, pickle.HIGHEST_PROTOCOL)
        update_size = len(bin_update_data)

        # Check Need Extend
        if shm_cache_size >= update_size:
            # NOTE: Save update data independent of @lock decorator.(Avoid deadlock)
            cache_data._save_memory(update_data)
            return

        # Get Extend Size
        mod_size = shm_cache_size + DictCache.USE_CACHE[self.name]["extend_incremental"]
        while mod_size < update_size:
            mod_size += DictCache.USE_CACHE[self.name]["extend_incremental"]

        # Extend Shared Memory Object Mapping Size When WRITE
        old_shared_memory = cache_data._memory_block
        # NOTE: Re-create shared memory object.
        old_shared_memory.close()
        old_shared_memory.unlink()
        new_shared_memory = SharedMemory(
            name=MEMORY_NAME.format(name=self.name), create=True, size=mod_size
        )
        cache_data._memory_block = new_shared_memory
        # NOTE: Save update data independent of @lock decorator.(Avoid deadlock)
        cache_data._save_memory(update_data)

        # Update Cache Sizes
        tmp_cache_sizes: dict[str, Any] = dict(cache_sizes.items())
        tmp_cache_sizes[self.name] = mod_size
        # NOTE: Save cache sizes data independent of @lock decorator.(Avoid deadlock)
        cache_sizes._save_memory(tmp_cache_sizes)


DictCache.initialize()
