"""Mesa-LLM PoC — Pillar 3: Async Batch LLM Engine  (Mesa 3.5.1 compatible)

FIX 3: asyncio.Lock removed from TokenBucket.
        asyncio.run() creates a new event loop on every call, so any Lock
        created at __init__ time is bound to a different (or no) loop and
        raises RuntimeError on acquire(). Since batch_invoke() is called
        synchronously from model.step() — never concurrently — there is no
        shared-state race to protect against; the lock was unnecessary.
"""
from __future__ import annotations
import asyncio, random, time
from collections import deque
from dataclasses import dataclass
from typing import Any


class TokenBucket:
    """Rolling-window rate limiter (max_rpm requests / 60 s).
    FIX: no asyncio.Lock — safe for synchronous callers using asyncio.run().
    """
    def __init__(self, max_rpm: int):
        self.max_rpm = max_rpm
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        now = time.monotonic()
        while self._timestamps and self._timestamps[0] < now - 60.0:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_rpm:
            wait_time = 60.0 - (now - self._timestamps[0]) + 0.01
            await asyncio.sleep(wait_time)
            now = time.monotonic()
            while self._timestamps and self._timestamps[0] < now - 60.0:
                self._timestamps.popleft()
        self._timestamps.append(time.monotonic())


@dataclass
class ExponentialBackoff:
    max_retries: int = 3
    base_delay:  float = 1.0
    max_delay:   float = 60.0
    def delay_for(self, attempt: int) -> float:
        return min(self.base_delay * (2 ** attempt), self.max_delay) * random.uniform(0.5, 1.5)


class AsyncLLMEngine:
    """Batches all agent LLM calls per step and fires them concurrently."""

    def __init__(self, llm_client: Any, max_rpm: int = 60,
                 max_parallel: int = 20,
                 retry_policy: ExponentialBackoff | None = None):
        self.client       = llm_client
        self.max_parallel = max_parallel
        self.retry_policy = retry_policy or ExponentialBackoff()
        self._bucket      = TokenBucket(max_rpm)
        print(f"Pillar 3: AsyncLLMEngine initialised "
              f"(max_rpm={max_rpm}, max_parallel={max_parallel})")

    def batch_invoke(self, prompts: list[str]) -> list[str]:
        """Synchronous entry point — creates a fresh event loop each call."""
        return asyncio.run(self._batch_async(prompts))

    async def _batch_async(self, prompts: list[str]) -> list[str]:
        semaphore = asyncio.Semaphore(self.max_parallel)
        tasks = [self._call_one(p, i, semaphore) for i, p in enumerate(prompts)]
        return list(await asyncio.gather(*tasks))

    async def _call_one(self, prompt: str, idx: int,
                        sem: asyncio.Semaphore) -> str:
        async with sem:
            await self._bucket.acquire()
            for attempt in range(self.retry_policy.max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(getattr(self.client, "ainvoke", None)):
                        response = await self.client.ainvoke(prompt)
                    else:
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(
                            None, self.client.invoke, prompt)
                    return str(response)
                except Exception as e:
                    if attempt < self.retry_policy.max_retries:
                        await asyncio.sleep(self.retry_policy.delay_for(attempt))
                    else:
                        return f"[ERROR agent {idx}: {e}]"
        return ""


class MockLLMClient:
    def __init__(self, latency: float = 0.05): self.latency = latency
    def invoke(self, prompt: str) -> str:
        time.sleep(self.latency)
        if "false" in prompt.lower() or "misinformation" in prompt.lower():
            return "I am sceptical of this claim based on what I know."
        return "This information seems credible."
