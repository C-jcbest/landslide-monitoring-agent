"""Long-term memory service using mem0 and pgvector with optional cache layer."""

import time
from typing import Any

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_openai import ChatOpenAI
from mem0 import AsyncMemory
from pydantic import SecretStr

from app.core.cache import (
    cache_key,
    cache_service,
)
from app.core.config import settings
from app.core.logging import logger


class MemoryService:
    """Service for managing long-term memory using mem0 and pgvector."""

    def __init__(self):
        """Initialize the memory service."""
        self._memory: AsyncMemory | None = None

    async def _get_memory(self) -> AsyncMemory:
        if self._memory is None:
            started = time.monotonic()
            deepseek_llm_config: dict[str, Any] = {
                "model": settings.LONG_TERM_MEMORY_MODEL,
                "api_key": SecretStr(settings.DEEPSEEK_API_KEY),
                "base_url": settings.DEEPSEEK_BASE_URL,
                "temperature": settings.DEFAULT_LLM_TEMPERATURE,
                "max_tokens": settings.MAX_TOKENS,
            }
            self._memory = await AsyncMemory.from_config(
                config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": settings.LONG_TERM_MEMORY_COLLECTION_NAME,
                            "embedding_model_dims": settings.LONG_TERM_MEMORY_EMBEDDER_DIMENSIONS,
                            "dbname": settings.POSTGRES_DB,
                            "user": settings.POSTGRES_USER,
                            "password": settings.POSTGRES_PASSWORD,
                            "host": settings.POSTGRES_HOST,
                            "port": settings.POSTGRES_PORT,
                            # nv-embed-v1 returns 4096 dimensions, while pgvector's
                            # HNSW index supports at most 2000 dimensions.
                            "hnsw": False,
                        },
                    },
                    "llm": {
                        "provider": "langchain",
                        "config": {"model": ChatOpenAI(**deepseek_llm_config)},
                    },
                    "embedder": {
                        "provider": "langchain",
                        "config": {
                            "model": NVIDIAEmbeddings(
                                model=settings.LONG_TERM_MEMORY_EMBEDDER_MODEL,
                                api_key=settings.NVIDIA_API_KEY,
                                truncate="NONE",
                            )
                        },
                    },
                }
            )
            logger.info("memory_client_initialized", duration_ms=_elapsed_ms(started))
        return self._memory

    async def initialize(self) -> None:
        """Pre-warm the mem0 AsyncMemory instance and its pgvector connection pool.

        Call once at startup so the first search() or add() doesn't pay the
        ~130ms from_config + pgvector.list_cols() cold-init cost.
        """
        await self._get_memory()
        logger.info("memory_service_initialized")

    async def search(self, user_id: str | None, query: str) -> str:
        """Search relevant memories for a user.

        Checks cache first; on miss, queries mem0 and caches the result.

        Returns formatted memory string, or empty string on failure or when
        no user_id is supplied (anonymous sessions skip long-term memory
        rather than pooling under a shared partition).
        """
        started = time.monotonic()
        if user_id is None:
            logger.info(
                "memory_search_skipped",
                reason="missing_user_id",
                query_length=len(query),
                duration_ms=_elapsed_ms(started),
            )
            return ""
        try:
            # Check cache first
            key = cache_key("memory", str(user_id), query)
            cached = await cache_service.get(key)
            if cached is not None:
                logger.info(
                    "memory_search_finished",
                    user_id=user_id,
                    cache_hit=True,
                    query_length=len(query),
                    result_length=len(cached),
                    result_count=None,
                    duration_ms=_elapsed_ms(started),
                )
                return cached

            memory = await self._get_memory()
            results = await memory.search(user_id=str(user_id), query=query)
            result = "\n".join([f"* {r['memory']}" for r in results["results"]])
            result_count = len(results.get("results", []))

            # Cache successful results
            if result:
                await cache_service.set(key, result)

            logger.info(
                "memory_search_finished",
                user_id=user_id,
                cache_hit=False,
                query_length=len(query),
                result_length=len(result),
                result_count=result_count,
                duration_ms=_elapsed_ms(started),
            )
            return result
        except Exception as e:
            logger.error(
                "failed_to_get_relevant_memory",
                error=str(e),
                user_id=user_id,
                query_length=len(query),
                duration_ms=_elapsed_ms(started),
            )
            return ""

    async def add(self, user_id: str | None, messages: list[dict], metadata: dict | None = None) -> None:
        """Add messages to long-term memory for a user.

        No-op when ``user_id`` is ``None`` (see ``search`` for rationale).
        """
        started = time.monotonic()
        if user_id is None:
            logger.info(
                "memory_update_skipped",
                reason="missing_user_id",
                message_count=len(messages),
                duration_ms=_elapsed_ms(started),
            )
            return
        try:
            memory = await self._get_memory()
            await memory.add(messages, user_id=str(user_id), metadata=metadata)
            logger.info(
                "long_term_memory_updated_successfully",
                user_id=user_id,
                message_count=len(messages),
                duration_ms=_elapsed_ms(started),
            )
        except Exception as e:
            logger.exception(
                "failed_to_update_long_term_memory",
                user_id=user_id,
                error=str(e),
                message_count=len(messages),
                duration_ms=_elapsed_ms(started),
            )


memory_service = MemoryService()


def _elapsed_ms(started: float) -> float:
    """Return elapsed wall-clock milliseconds for structured logs."""
    return round((time.monotonic() - started) * 1000, 2)
