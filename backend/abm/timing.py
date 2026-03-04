import functools
import time


def timed(func):
    """Decorator that logs execution time for sync and async functions."""
    if __import__("asyncio").iscoroutinefunction(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                print(f"[Timing] {func.__qualname__}: {time.perf_counter() - t0:.2f}s")
        return wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            print(f"[Timing] {func.__qualname__}: {time.perf_counter() - t0:.2f}s")
    return wrapper
