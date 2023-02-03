import asyncio
import functools as ft
import inspect
import time
import typing as t

import wrapt

T = t.TypeVar("T")


# TODO: check if this proxy is necessary
# noinspection PyAbstractClass
class _AsyncMethodRateLimitingProxy(wrapt.ObjectProxy):  # type: ignore[misc]

    def __init__(self, instance: object, rps: float, cache_size: t.Optional[int] = None) -> None:
        super().__init__(instance)
        self.__rate_limit = 1.0 / rps
        self.__rps = rps

        if cache_size is None:
            self.__wrap_async: t.Callable[..., object] = self.__wrap_async_func_with_call_limiter
        else:
            self.__wrap_async = ft.lru_cache(maxsize=cache_size)(self.__wrap_async_func_with_call_limiter)

        self.__lock = asyncio.Lock()
        self.__cntr = 0.0
        self.__next_refresh_at = time.time()

    def __getattr__(self, name: str) -> object:
        obj = getattr(self.__wrapped__, name)
        if not inspect.iscoroutinefunction(obj):
            return obj

        return self.__wrap_async_func_with_call_limiter(obj)

    def __wrap_async_func_with_call_limiter(
            self,
            func: t.Callable[..., t.Awaitable[T]],
    ) -> t.Callable[..., t.Awaitable[T]]:
        @ft.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            await self.__control_rate_limit()
            return await func(*args, **kwargs)

        return wrapper

    async def __control_rate_limit(self) -> None:
        async with self.__lock:
            now = time.time()
            diff = self.__next_refresh_at - now

            if diff >= 0.0:
                if self.__cntr / diff > self.__rps:
                    await asyncio.sleep(self.__cntr / self.__rps)
                    self.__refresh_rates()

            else:
                self.__refresh_rates()

            self.__cntr += 1.0

    def __refresh_rates(self) -> None:
        self.__cntr = 0.0
        self.__next_refresh_at = time.time() + self.__rps


def wrap_with_rate_limiter(instance: T, rps: float, cache_size: t.Optional[int] = None) -> T:
    return t.cast(T, _AsyncMethodRateLimitingProxy(instance, rps, cache_size))
