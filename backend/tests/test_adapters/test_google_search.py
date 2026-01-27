import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.google_search import GoogleSearchAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_google_search_returns_source_response():
    mock_results = {
        "items": [
            {
                "title": "Boiling Point of Water",
                "snippet": "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
                "link": "https://example.com/boiling-point",
            },
            {
                "title": "Water Properties",
                "snippet": "The boiling point of pure water is 100°C or 212°F at 1 atmosphere.",
                "link": "https://example.com/water",
            },
        ]
    }

    adapter = GoogleSearchAdapter(api_key="test-key", cx="test-cx")

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_results):
        result = await adapter.query("What is the boiling point of water?")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "google_search"
    assert len(result.claims) == 2
    assert "100" in result.claims[0].text


@pytest.mark.asyncio
async def test_google_search_handles_no_results():
    adapter = GoogleSearchAdapter(api_key="test-key", cx="test-cx")

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value={"items": []}):
        result = await adapter.query("some obscure question")

    assert result is not None
    assert len(result.claims) == 0
