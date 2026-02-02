from abc import ABC, abstractmethod
from typing import AsyncIterator, Callable, Awaitable, Optional

from app.schemas.source import SourceResponse


# Type alias for streaming callback
StreamingCallback = Callable[[str, str, bool], Awaitable[None]]


class BaseAdapter(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source."""
        ...

    @abstractmethod
    async def query(self, question: str) -> SourceResponse | None:
        """Query this source with a question. Returns None on failure."""
        ...

    @property
    def supports_streaming(self) -> bool:
        """Whether this adapter supports streaming responses."""
        return False

    async def query_streaming(
        self,
        question: str,
        on_token: Optional[StreamingCallback] = None,
    ) -> SourceResponse | None:
        """
        Query this source with streaming support.

        Args:
            question: The question to ask
            on_token: Callback called with (source_name, partial_content, is_complete)
                      for each chunk of streaming content

        Returns:
            SourceResponse when complete, or None on failure.

        Default implementation falls back to non-streaming query.
        """
        return await self.query(question)
