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


@pytest.mark.asyncio
async def test_orchestrator_gathers_evidence_from_all_adapters():
    mock_adapters = [
        AsyncMock(query=AsyncMock(return_value=make_source_response("ai:claude", "100C"))),
        AsyncMock(query=AsyncMock(return_value=make_source_response("ai:gpt", "100 degrees C"))),
        AsyncMock(query=AsyncMock(return_value=make_source_response("google", "100°C at sea level"))),
    ]

    orchestrator = Orchestrator(adapters=mock_adapters)
    results = await orchestrator.gather_evidence("What is the boiling point of water?")

    assert len(results) == 3
    assert all(isinstance(r, SourceResponse) for r in results)


@pytest.mark.asyncio
async def test_orchestrator_skips_failed_adapters():
    mock_adapters = [
        AsyncMock(query=AsyncMock(return_value=make_source_response("ai:claude", "100C"))),
        AsyncMock(query=AsyncMock(return_value=None)),  # Failed adapter
    ]

    orchestrator = Orchestrator(adapters=mock_adapters)
    results = await orchestrator.gather_evidence("test question")

    assert len(results) == 1
