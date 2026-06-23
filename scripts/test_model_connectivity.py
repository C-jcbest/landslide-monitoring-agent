"""Test configured DeepSeek, NVIDIA embeddings, and mem0 connectivity without exposing secrets."""

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from rich.console import Console
from rich.table import Table

from app.core.config import settings
from app.services.llm.registry import LLMRegistry
from app.services.memory import MemoryService

console = Console()


def parse_args() -> argparse.Namespace:
    """Parse connectivity test options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deepseek", action="store_true", help="only test the configured DeepSeek model")
    parser.add_argument("--embedding", action="store_true", help="only test the configured NVIDIA embedding model")
    parser.add_argument("--memory", action="store_true", help="only test mem0 and pgvector initialization")
    parser.add_argument("--timeout", type=int, default=45, help="timeout per test in seconds (1-120, default: 45)")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error("--timeout must be between 1 and 120")
    return args


def error_summary(error: Exception) -> str:
    """Return a diagnostic that excludes secrets, request data, and vectors."""
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is not None:
        return f"HTTP {status_code} ({type(error).__name__})"
    if isinstance(error, TimeoutError):
        return "request timed out"
    if isinstance(error, RuntimeError):
        return str(error)
    return type(error).__name__


async def test_deepseek(timeout: int) -> str:
    """Send one bounded health-check request to the configured DeepSeek model."""
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    if settings.DEFAULT_LLM_MODEL not in LLMRegistry.get_all_names():
        raise RuntimeError("DEFAULT_LLM_MODEL is not registered")

    llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
    response = await asyncio.wait_for(llm.ainvoke("Reply with exactly: PING_OK"), timeout=timeout)
    if not isinstance(response.content, str) or response.content.strip() != "PING_OK":
        raise RuntimeError("unexpected health-check response")
    return f"{settings.DEFAULT_LLM_MODEL} responded"


async def test_embedding(timeout: int) -> str:
    """Request one configured NVIDIA embedding and validate its shape."""
    if not settings.NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    # Keep potential third-party SDK output out of the terminal because some
    # debug paths can include authorization headers.
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        embeddings = NVIDIAEmbeddings(
            model=settings.LONG_TERM_MEMORY_EMBEDDER_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            truncate="NONE",
        )
        vector = await asyncio.wait_for(
            asyncio.to_thread(embeddings.embed_query, "embedding connectivity check"), timeout=timeout
        )
    if not vector:
        raise RuntimeError("embedding response was empty")
    if len(vector) != settings.LONG_TERM_MEMORY_EMBEDDER_DIMENSIONS:
        raise RuntimeError(
            "embedding dimensions do not match LONG_TERM_MEMORY_EMBEDDER_DIMENSIONS "
            f"({len(vector)} != {settings.LONG_TERM_MEMORY_EMBEDDER_DIMENSIONS})"
        )
    return f"{settings.LONG_TERM_MEMORY_EMBEDDER_MODEL} returned {len(vector)} dimensions"


async def test_memory(timeout: int) -> str:
    """Initialize mem0 and its pgvector collection without adding test memories."""
    memory_service = MemoryService()
    await asyncio.wait_for(memory_service.initialize(), timeout=timeout)
    return f"pgvector collection {settings.LONG_TERM_MEMORY_COLLECTION_NAME} initialized"


async def run_test(name: str, test: Callable[[int], Awaitable[str]], timeout: int) -> tuple[str, bool, str]:
    """Run one check and convert errors into a secret-safe result row."""
    try:
        return name, True, await test(timeout)
    except Exception as error:
        return name, False, error_summary(error)


def render_results(results: list[tuple[str, bool, str]]) -> None:
    """Render concise connectivity results with Rich."""
    table = Table(title="Model Connectivity Test")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")
    for name, passed, detail in results:
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(name, status, detail)
    console.print(table)


async def main() -> int:
    """Run selected checks, or all checks when none are selected."""
    args = parse_args()
    selected = [
        ("DeepSeek", args.deepseek, test_deepseek),
        ("NVIDIA embedding", args.embedding, test_embedding),
        ("mem0 / pgvector", args.memory, test_memory),
    ]
    if not any(is_selected for _, is_selected, _ in selected):
        selected = [(name, True, test) for name, _, test in selected]

    results = [await run_test(name, test, args.timeout) for name, is_selected, test in selected if is_selected]
    render_results(results)
    return 0 if all(passed for _, passed, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
