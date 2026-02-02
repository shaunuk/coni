import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.orchestrator import Orchestrator
from app.schemas.source import Claim, SourceResponse


def make_source_response(name: str, text: str) -> SourceResponse:
    return SourceResponse(
        source_name=name,
        raw_response=text,
        claims=[Claim(text=text, confidence=0.9, evidence=None)],
        confidence=0.9,
    )


def make_mock_adapter(name: str, response: SourceResponse | None, supports_streaming: bool = False):
    """Create a mock adapter with required properties."""
    mock = MagicMock()
    mock.source_name = name
    mock.supports_streaming = supports_streaming
    mock.query = AsyncMock(return_value=response)
    mock.query_streaming = AsyncMock(return_value=response)
    return mock


@pytest.mark.asyncio
async def test_orchestrator_gathers_evidence_from_all_adapters():
    mock_adapters = [
        make_mock_adapter("ai:claude", make_source_response("ai:claude", "100C")),
        make_mock_adapter("ai:gpt", make_source_response("ai:gpt", "100 degrees C")),
        make_mock_adapter("google", make_source_response("google", "100°C at sea level")),
    ]

    orchestrator = Orchestrator(adapters=mock_adapters)
    results = await orchestrator.gather_evidence("What is the boiling point of water?")

    assert len(results) == 3
    assert all(isinstance(r, SourceResponse) for r in results)


@pytest.mark.asyncio
async def test_orchestrator_skips_failed_adapters():
    mock_adapters = [
        make_mock_adapter("ai:claude", make_source_response("ai:claude", "100C")),
        make_mock_adapter("ai:gpt", None),  # Failed adapter
    ]

    orchestrator = Orchestrator(adapters=mock_adapters)
    results = await orchestrator.gather_evidence("test question")

    assert len(results) == 1


@pytest.mark.asyncio
async def test_orchestrator_uses_streaming_when_enabled():
    """Test that orchestrator uses streaming for adapters that support it."""
    streaming_response = make_source_response("ai:claude", "Streaming response")
    mock_adapter = make_mock_adapter("ai:claude", streaming_response, supports_streaming=True)

    orchestrator = Orchestrator(adapters=[mock_adapter], enable_streaming=True)
    results = await orchestrator.gather_evidence("test question")

    assert len(results) == 1
    mock_adapter.query_streaming.assert_called_once()
    mock_adapter.query.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_falls_back_to_query_when_streaming_disabled():
    """Test that orchestrator uses query when streaming is disabled."""
    response = make_source_response("ai:claude", "Non-streaming response")
    mock_adapter = make_mock_adapter("ai:claude", response, supports_streaming=True)

    orchestrator = Orchestrator(adapters=[mock_adapter], enable_streaming=False)
    results = await orchestrator.gather_evidence("test question")

    assert len(results) == 1
    mock_adapter.query.assert_called_once()
    mock_adapter.query_streaming.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_calls_streaming_callback():
    """Test that orchestrator passes streaming callback to adapter."""
    response = make_source_response("ai:claude", "Streaming response")
    mock_adapter = make_mock_adapter("ai:claude", response, supports_streaming=True)

    streaming_calls = []

    async def on_streaming(source_name: str, partial_content: str, is_complete: bool):
        streaming_calls.append((source_name, partial_content, is_complete))

    orchestrator = Orchestrator(
        adapters=[mock_adapter],
        on_source_streaming=on_streaming,
        enable_streaming=True,
    )
    await orchestrator.gather_evidence("test question")

    # Verify the callback was passed to query_streaming
    call_args = mock_adapter.query_streaming.call_args
    assert call_args is not None
    assert call_args.kwargs.get("on_token") == on_streaming
