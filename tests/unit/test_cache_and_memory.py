"""Unit tests for cache semantics and isolated long-term memory access."""

from typing import Any

import pytest

from app.core import cache
from app.core.cache import InMemoryCacheService, cache_key
from app.services.memory import MemoryService

pytestmark = pytest.mark.unit


class FakeCache:
    """Minimal async cache recording calls for memory service assertions."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, str]] = []

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value
        self.set_calls.append((key, value))


class FakeMemory:
    """Async mem0 replacement with explicit search and add call records."""

    def __init__(self, results: list[dict[str, str]] | None = None) -> None:
        self.results = results if results is not None else []
        self.search_calls: list[tuple[str, str]] = []
        self.add_calls: list[tuple[list[dict[str, Any]], str, dict[str, Any] | None]] = []

    async def search(self, *, user_id: str, query: str) -> dict[str, list[dict[str, str]]]:
        self.search_calls.append((user_id, query))
        return {"results": self.results}

    async def add(self, messages: list[dict[str, Any]], *, user_id: str, metadata: dict[str, Any] | None) -> None:
        self.add_calls.append((messages, user_id, metadata))


async def test_in_memory_cache_expires_and_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired values are not returned and delete is idempotent."""
    cache = InMemoryCacheService(default_ttl=10)
    now = 100.0
    monkeypatch.setattr("app.core.cache.time.monotonic", lambda: now)
    await cache.set("key", "value")

    assert await cache.get("key") == "value"

    now = 111.0
    assert await cache.get("key") is None
    await cache.delete("missing")


def test_cache_key_does_not_expose_raw_values() -> None:
    """Cache keys remain deterministic while not leaking user input."""
    key = cache_key("memory", "user-1", "secret query")

    assert key == cache_key("memory", "user-1", "secret query")
    assert key.startswith("memory:")
    assert "secret" not in key


def test_cache_factory_uses_memory_when_valkey_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default deployment remains functional without an optional cache server."""
    monkeypatch.setattr(cache.settings, "VALKEY_HOST", "")

    assert isinstance(cache._create_cache_service(), InMemoryCacheService)  # pyright: ignore[reportPrivateUsage]


async def test_memory_search_uses_user_scoped_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memory results are cached only under the requesting user's key."""
    fake_cache = FakeCache()
    fake_memory = FakeMemory(results=[{"memory": "User prefers concise responses."}])
    service = MemoryService()
    service._memory = fake_memory  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr("app.services.memory.cache_service", fake_cache)

    first = await service.search("user-1", "preferences")
    second = await service.search("user-1", "preferences")

    assert first == "* User prefers concise responses."
    assert second == first
    assert fake_memory.search_calls == [("user-1", "preferences")]
    assert len(fake_cache.set_calls) == 1


async def test_memory_search_skips_anonymous_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anonymous requests must not share a long-term-memory partition."""
    service = MemoryService()
    fake_memory = FakeMemory(results=[{"memory": "must not be read"}])
    service._memory = fake_memory  # pyright: ignore[reportPrivateUsage]

    assert await service.search(None, "preferences") == ""
    assert fake_memory.search_calls == []


async def test_memory_add_keeps_metadata_scoped_to_user() -> None:
    """Background memory writes carry the caller identity and metadata."""
    fake_memory = FakeMemory()
    service = MemoryService()
    service._memory = fake_memory  # pyright: ignore[reportPrivateUsage]
    messages = [{"role": "user", "content": "remember this"}]

    await service.add("user-1", messages, {"session_id": "session-1"})

    assert fake_memory.add_calls == [(messages, "user-1", {"session_id": "session-1"})]
