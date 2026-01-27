import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.stackexchange import StackExchangeAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_stackexchange_returns_source_response():
    mock_data = {
        "items": [
            {
                "title": "What is the boiling point of water?",
                "body": "Water boils at 100°C at 1 atm.",
                "score": 15,
                "is_accepted": True,
                "link": "https://stackoverflow.com/q/123",
            }
        ]
    }

    adapter = StackExchangeAdapter()

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_data):
        result = await adapter.query("boiling point of water")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "stackexchange"
    assert len(result.claims) == 1
