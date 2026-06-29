"""Async batch execution infrastructure: concurrency primitives and operation contract."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Self

from anyio import CapacityLimiter, create_task_group

# @TODO: add two generic hooks for callers that need structured fatal handling:
#   - evaluate_fatal(outcome, is_fatal) -> bool  — pure predicate, no side effects; lets
#     callers inspect an outcome without coupling to the abort mechanism
#   - cancel_siblings(abort)  — thin named wrapper around abort() so call sites read
#     as intent ("cancel siblings") rather than implementation ("call abort")


@dataclass
class BatchResults:
    """Self-contained outcome accumulator.

    ``is_fatal`` classifies outcomes into the buckets it owns.
    ``fatal`` holds the single outcome that triggered cancellation, if any.
    Each list bucket holds ``(item, result_or_exception)`` pairs.
    """

    is_fatal: Callable[[object], bool]
    successes: list[tuple[Any, Any]] = field(default_factory=list)
    failures: list[tuple[Any, Any]] = field(default_factory=list)
    fatal: tuple[Any, Any] | None = None

    def record(self, item: Any, result: Any, *, fatal: bool) -> None:
        """File ``(item, result)`` into the correct bucket; first fatal wins."""
        if fatal and self.fatal is None:
            self.fatal = (item, result)
        elif not fatal:
            succeeded = not isinstance(result, Exception) and getattr(result, "ok", True)
            (self.successes if succeeded else self.failures).append((item, result))


@dataclass
class BatchRun:
    """One concurrent batch execution: its items, concurrency cap, and results.

    Standard use: ``BatchRun.create(func, items).run_sync()`` — ``process`` calls
    ``func`` per item under the concurrency cap. Subclasses override ``process``
    (and optionally ``batch_and_run`` for setup/teardown) for custom execution.
    """

    max_concurrent: int
    pending: list[Any]
    results: BatchResults
    func: Callable[[Any], Awaitable[Any]] | None = field(default=None, kw_only=True)

    @classmethod
    def create(
        cls,
        func: Callable[[Any], Awaitable[Any]],
        items: Iterable[Any],
        *,
        max_concurrent: int = 20,
        is_fatal: Callable[[object], bool] = lambda _: False,
    ) -> Self:
        """Construct an op over ``items`` with a fresh ``BatchResults``. No execution."""
        return cls(
            func=func,
            max_concurrent=max_concurrent,
            pending=list(items),
            results=BatchResults(is_fatal=is_fatal),
        )

    def run_sync(self) -> BatchResults:
        """Sync→async boundary: ``asyncio.run`` the batch, return the results.

        Blocks the calling thread; must not be called from inside a running event loop.
        """
        asyncio.run(self.batch_and_run())
        return self.results

    async def batch_and_run(self) -> None:
        """Public entry point — owns the full lifecycle. Override to wrap setup/teardown around build."""
        await self.build()

    async def build(self) -> None:
        """Schedule and run ``process`` for every pending item under the concurrency cap."""
        limiter = CapacityLimiter(self.max_concurrent)
        async with create_task_group() as tg:
            for item in self.pending[:]:
                tg.start_soon(self.process, item, limiter, tg.cancel_scope.cancel)

    async def process(self, item: Any, limiter: CapacityLimiter, abort: Callable[[], None]) -> None:
        """Execute ``func(item)`` under the concurrency cap; capture, classify, and record the outcome."""
        async with limiter:
            try:
                result = await self.func(item)  # type: ignore[misc]
            except Exception as exc:
                result = exc
        fatal = self.results.is_fatal(result)
        self.pending.remove(item)
        self.results.record(item, result, fatal=fatal)
        if fatal:
            abort()
