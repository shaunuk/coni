import pytest
from unittest.mock import AsyncMock, patch

from app.services.debate_engine import DebateEngine
from app.schemas.source import Claim, SourceResponse


def make_evidence(name: str, claim_text: str, confidence: float = 0.9) -> SourceResponse:
    return SourceResponse(
        source_name=name,
        raw_response=claim_text,
        claims=[Claim(text=claim_text, confidence=confidence, evidence=None)],
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_debate_engine_clusters_positions():
    evidence = [
        make_evidence("ai:claude", "Water boils at 100°C at sea level"),
        make_evidence("ai:gpt", "The boiling point is 100 degrees Celsius at 1 atm"),
        make_evidence("google", "Water boils at 100°C (212°F) at standard pressure"),
    ]

    engine = DebateEngine(openrouter_api_key="test-key")

    mock_clustering = [
        {
            "stance": "Water boils at 100°C at sea level",
            "supporting_sources": ["ai:claude", "ai:gpt", "google"],
            "claims": [
                "Water boils at 100°C at sea level",
                "The boiling point is 100 degrees Celsius at 1 atm",
                "Water boils at 100°C (212°F) at standard pressure",
            ],
        }
    ]

    with patch.object(engine, "_cluster_positions", new_callable=AsyncMock, return_value=mock_clustering):
        positions = await engine.identify_positions(evidence)

    assert len(positions) == 1
    assert len(positions[0]["supporting_sources"]) == 3


@pytest.mark.asyncio
async def test_debate_engine_calculates_convergence():
    engine = DebateEngine(openrouter_api_key="test-key")

    # All sources agree — high convergence
    positions = [
        {
            "stance": "Water boils at 100°C",
            "supporting_sources": ["ai:claude", "ai:gpt", "google"],
            "claims": ["100°C"],
        }
    ]
    score = engine.calculate_convergence(positions, total_sources=3)
    assert score >= 0.9

    # Sources split — low convergence
    split_positions = [
        {"stance": "A", "supporting_sources": ["ai:claude"], "claims": ["A"]},
        {"stance": "B", "supporting_sources": ["ai:gpt"], "claims": ["B"]},
        {"stance": "C", "supporting_sources": ["google"], "claims": ["C"]},
    ]
    score = engine.calculate_convergence(split_positions, total_sources=3)
    assert score < 0.5
