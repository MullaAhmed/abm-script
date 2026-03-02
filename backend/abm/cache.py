import json
import time
from pathlib import Path
from typing import Protocol

from .models import PersonalizationCache


class Cache(Protocol):
    async def get(self, visitor_id: str) -> PersonalizationCache | None: ...
    async def set(self, visitor_id: str, data: PersonalizationCache) -> None: ...
    async def delete(self, visitor_id: str) -> None: ...


class MemoryCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._store: dict[str, PersonalizationCache] = {}
        self._ttl = ttl_seconds

    async def get(self, visitor_id: str) -> PersonalizationCache | None:
        entry = self._store.get(visitor_id)
        if not entry:
            return None
        if time.time() - entry.created_at > self._ttl:
            del self._store[visitor_id]
            return None
        return entry

    async def set(self, visitor_id: str, data: PersonalizationCache) -> None:
        self._store[visitor_id] = data

    async def delete(self, visitor_id: str) -> None:
        self._store.pop(visitor_id, None)


class FileCache:
    def __init__(self, cache_dir: str = ".abm-cache", ttl_seconds: int = 3600) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds

    def _path(self, visitor_id: str) -> Path:
        safe = visitor_id.replace("/", "_").replace("\\", "_")
        return self._dir / f"{safe}.json"

    async def get(self, visitor_id: str) -> PersonalizationCache | None:
        path = self._path(visitor_id)
        if not path.exists():
            return None
        try:
            raw = path.read_text()
            entry = PersonalizationCache.model_validate_json(raw)
            if time.time() - entry.created_at > self._ttl:
                path.unlink(missing_ok=True)
                return None
            return entry
        except Exception:
            return None

    async def set(self, visitor_id: str, data: PersonalizationCache) -> None:
        path = self._path(visitor_id)
        path.write_text(data.model_dump_json(indent=2))

    async def delete(self, visitor_id: str) -> None:
        self._path(visitor_id).unlink(missing_ok=True)


def create_cache(storage_type: str, ttl_seconds: int, cache_dir: str = ".abm-cache") -> Cache:
    match storage_type:
        case "file":
            return FileCache(cache_dir, ttl_seconds)
        case _:
            return MemoryCache(ttl_seconds)
