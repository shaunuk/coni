import asyncio
from typing import Optional, Callable, Awaitable

from app.adapters.base import BaseAdapter, StreamingCallback
from app.schemas.source import SourceResponse


class Orchestrator:
    def __init__(
        self,
        adapters: list[BaseAdapter],
        on_source_started: Optional[Callable[[str], Awaitable[None]]] = None,
        on_source_streaming: Optional[StreamingCallback] = None,
        on_source_completed: Optional[Callable[[str, float, int], Awaitable[None]]] = None,
        on_source_failed: Optional[Callable[[str, str], Awaitable[None]]] = None,
        enable_streaming: bool = True,
    ):
        self.adapters = adapters
        self.on_source_started = on_source_started
        self.on_source_streaming = on_source_streaming
        self.on_source_completed = on_source_completed
        self.on_source_failed = on_source_failed
        self.enable_streaming = enable_streaming

    async def _query_with_callbacks(
        self,
        adapter: BaseAdapter,
        question: str,
    ) -> Optional[SourceResponse]:
        """Query a single adapter with progress callbacks."""
        source_name = adapter.source_name

        # Notify source started
        if self.on_source_started:
            await self.on_source_started(source_name)

        try:
            # Use streaming if enabled and supported by the adapter
            if self.enable_streaming and adapter.supports_streaming:
                result = await adapter.query_streaming(
                    question,
                    on_token=self.on_source_streaming,
                )
            else:
                result = await adapter.query(question)

            if result:
                # Notify source completed successfully
                if self.on_source_completed:
                    await self.on_source_completed(
                        source_name,
                        result.confidence,
                        len(result.claims),
                    )
                return result
            else:
                # Notify source failed (no result)
                if self.on_source_failed:
                    await self.on_source_failed(source_name, "No response received")
                return None

        except Exception as e:
            # Notify source failed
            if self.on_source_failed:
                await self.on_source_failed(source_name, str(e))
            return None

    async def gather_evidence(self, question: str) -> list[SourceResponse]:
        """Gather evidence from all sources with progress tracking."""
        tasks = [
            self._query_with_callbacks(adapter, question)
            for adapter in self.adapters
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        evidence = []
        for result in results:
            if isinstance(result, SourceResponse):
                evidence.append(result)
        return evidence

    def get_source_names(self) -> list[str]:
        """Get list of all source names."""
        return [adapter.source_name for adapter in self.adapters]
