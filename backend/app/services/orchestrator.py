import asyncio

from app.adapters.base import BaseAdapter
from app.schemas.source import SourceResponse


class Orchestrator:
    def __init__(self, adapters: list[BaseAdapter]):
        self.adapters = adapters

    async def gather_evidence(self, question: str) -> list[SourceResponse]:
        tasks = [adapter.query(question) for adapter in self.adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        evidence = []
        for result in results:
            if isinstance(result, SourceResponse):
                evidence.append(result)
        return evidence
