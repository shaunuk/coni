import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.openrouter import OpenRouterAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_openrouter_query_returns_source_response():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "The boiling point of water at sea level is 100°C (212°F). This is a well-established physical constant."
                }
            }
        ],
        "model": "anthropic/claude-3.5-sonnet",
        "usage": {"total_tokens": 50}
    }

    adapter = OpenRouterAdapter(
        api_key="test-key",
        model="anthropic/claude-3.5-sonnet"
    )

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_response):
        result = await adapter.query("What is the boiling point of water?")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "openrouter:anthropic/claude-3.5-sonnet"
    assert "100" in result.raw_response
    assert len(result.claims) > 0


@pytest.mark.asyncio
async def test_openrouter_query_handles_api_error():
    adapter = OpenRouterAdapter(api_key="test-key", model="anthropic/claude-3.5-sonnet")

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, side_effect=Exception("API Error")):
        result = await adapter.query("test question")

    assert result is None
