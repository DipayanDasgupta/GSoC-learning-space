"""Mesa-LLM PoC — Pillar 3: Async Batch LLM Engine.

Implements:
  - TokenBucket: rolling-window rate limiter (O(1) amortised per request)
  - ExponentialBackoff: retry policy on HTTP 429 / transient failures
  - AsyncLLMEngine: batch all agent prompts per step, fire concurrently

Performance model:
  Synchronous:  latency = O(N * L)
  Async batched: latency ≈ O(ceil(N / max_parallel) * L)

For N=100, max_parallel=20, L=1s:
  Sync  ≥ 100 s   vs.   Async ≈ 5 s  (20× improvement)

Integration with Mesa's synchronous step():
  responses = engine.batch_invoke(prompts)   # blocks until all done
  # Internally uses asyncio.run() — no event-loop changes to Mesa required.
"""
from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable


# ── Rate limiter ──────────────────────────────────────────────────────────────

class TokenBucket:
    """Rolling-window rate limiter: at most max_rpm requests per 60-second window.

    Uses a deque of monotonic timestamps. O(1) amortised acquire().
    Drift-safe: uses time.monotonic(), not wall-clock time.
    """

    def __init__(self, max_rpm: int):
        self.max_rpm = max_rpm
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            # Evict timestamps older than 60 seconds
            while self._timestamps and self._timestamps[0] < now - 60.0:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.max_rpm:
                # Wait until the oldest request falls outside the window
                wait_time = 60.0 - (now - self._timestamps[0]) + 0.01
                await asyncio.sleep(wait_time)
                # Re-evict after sleeping
                now = time.monotonic()
                while self._timestamps and self._timestamps[0] < now - 60.0:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())


# ── Retry policy ─────────────────────────────────────────────────────────────

@dataclass
class ExponentialBackoff:
    """Exponential backoff with full jitter for HTTP 429 / transient failures.

    delay = min(base_delay * 2^attempt, max_delay) * random.uniform(0.5, 1.5)
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0

    def delay_for(self, attempt: int) -> float:
        raw = min(self.base_delay * (2 ** attempt), self.max_delay)
        return raw * random.uniform(0.5, 1.5)


# ── Async engine ─────────────────────────────────────────────────────────────

class AsyncLLMEngine:
    """Batches all agent LLM calls within a model step and fires them concurrently.

    Usage:
        engine = AsyncLLMEngine(llm_client=client, max_rpm=500, max_parallel=20)

        class MyModel(mesa.Model):
            def step(self):
                prompts   = [a.build_prompt() for a in self.agents]
                responses = engine.batch_invoke(prompts)   # concurrent, rate-limited
                for agent, resp in zip(self.agents, responses):
                    agent.process_response(resp)
    """

    def __init__(
        self,
        llm_client: Any,                       # Any object with .invoke(prompt) -> str
        max_rpm: int = 60,
        max_parallel: int = 20,
        retry_policy: ExponentialBackoff | None = None,
    ):
        self.client = llm_client
        self.max_parallel = max_parallel
        self.retry_policy = retry_policy or ExponentialBackoff()
        self._bucket = TokenBucket(max_rpm)
        print(f"Pillar 3: AsyncLLMEngine initialised "
              f"(max_rpm={max_rpm}, max_parallel={max_parallel})")

    def batch_invoke(self, prompts: list[str]) -> list[str]:
        """Synchronous entry point: blocks until all prompts are resolved.

        Internally uses asyncio.run() — no changes to Mesa's sync model loop.
        Returns responses in the same order as prompts.
        """
        return asyncio.run(self._batch_async(prompts))

    async def _batch_async(self, prompts: list[str]) -> list[str]:
        semaphore = asyncio.Semaphore(self.max_parallel)
        tasks = [self._call_one(p, i, semaphore) for i, p in enumerate(prompts)]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _call_one(
        self, prompt: str, idx: int, sem: asyncio.Semaphore
    ) -> str:
        async with sem:
            await self._bucket.acquire()
            for attempt in range(self.retry_policy.max_retries + 1):
                try:
                    # Support both sync .invoke() and async .ainvoke()
                    if asyncio.iscoroutinefunction(getattr(self.client, "ainvoke", None)):
                        response = await self.client.ainvoke(prompt)
                    else:
                        # Run sync call in thread pool to avoid blocking the loop
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(
                            None, self.client.invoke, prompt
                        )
                    return str(response)
                except Exception as e:
                    if attempt < self.retry_policy.max_retries:
                        delay = self.retry_policy.delay_for(attempt)
                        await asyncio.sleep(delay)
                    else:
                        # Return error string rather than crashing the whole batch
                        return f"[ERROR agent {idx}: {e}]"
        return ""   # unreachable but satisfies type checker


# ── Mock LLM client (for demo / CI) ──────────────────────────────────────────

class MockLLMClient:
    """Mocks an LLM client. Returns a canned response after a short delay.

    Swap for langchain_openai.ChatOpenAI or any provider client.
    Interface: .invoke(prompt: str) -> str
    """

    def __init__(self, latency: float = 0.05):
        self.latency = latency

    def invoke(self, prompt: str) -> str:
        time.sleep(self.latency)   # simulate network round-trip
        if "false" in prompt.lower() or "misinformation" in prompt.lower():
            return "I am sceptical of this claim based on what I know."
        return "This information seems credible."
