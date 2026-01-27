from abc import ABC, abstractmethod

from app.schemas.source import SourceResponse


class BaseAdapter(ABC):
    @abstractmethod
    async def query(self, question: str) -> SourceResponse | None:
        """Query this source with a question. Returns None on failure."""
        ...
