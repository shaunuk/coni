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


def test_openrouter_supports_streaming():
    adapter = OpenRouterAdapter(api_key="test-key", model="anthropic/claude-3.5-sonnet")
    assert adapter.supports_streaming is True


@pytest.mark.asyncio
async def test_openrouter_query_streaming_returns_source_response():
    """Test that query_streaming returns a SourceResponse and calls the callback."""
    mock_content = "The boiling point of water at sea level is 100°C (212°F)."

    adapter = OpenRouterAdapter(
        api_key="test-key",
        model="anthropic/claude-3.5-sonnet"
    )

    # Track callback invocations
    callback_calls = []

    async def mock_callback(source_name: str, partial_content: str, is_complete: bool):
        callback_calls.append({
            "source_name": source_name,
            "partial_content": partial_content,
            "is_complete": is_complete,
        })

    with patch.object(
        adapter,
        "_call_api_streaming",
        new_callable=AsyncMock,
        return_value=mock_content
    ):
        result = await adapter.query_streaming(
            "What is the boiling point of water?",
            on_token=mock_callback,
        )

    assert isinstance(result, SourceResponse)
    assert result.source_name == "openrouter:anthropic/claude-3.5-sonnet"
    assert "100" in result.raw_response
    assert len(result.claims) > 0


@pytest.mark.asyncio
async def test_openrouter_query_streaming_handles_error():
    adapter = OpenRouterAdapter(api_key="test-key", model="anthropic/claude-3.5-sonnet")

    with patch.object(
        adapter,
        "_call_api_streaming",
        new_callable=AsyncMock,
        side_effect=Exception("Streaming Error")
    ):
        result = await adapter.query_streaming("test question")

    assert result is None
