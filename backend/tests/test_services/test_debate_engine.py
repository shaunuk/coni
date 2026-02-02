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

    import json
    with patch.object(engine, "_call_llm", new_callable=AsyncMock, return_value=f"```json\n{json.dumps(mock_clustering)}\n```"):
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


@pytest.mark.asyncio
async def test_debate_engine_updates_positions_after_debate():
    """Test that positions can merge/shift based on counterarguments."""
    engine = DebateEngine(openrouter_api_key="test-key")

    # Initial split positions
    initial_positions = [
        {"stance": "Water boils at 100°C", "supporting_sources": ["ai:claude"], "claims": ["100°C at sea level"]},
        {"stance": "Water boils at 212°F", "supporting_sources": ["ai:gpt"], "claims": ["212°F at 1 atm"]},
        {"stance": "Boiling point varies with pressure", "supporting_sources": ["google"], "claims": ["Altitude affects boiling point"]},
    ]

    # Counterarguments showing positions 1 & 2 are equivalent
    counterarguments = [
        {"target_stance": "Water boils at 212°F", "counterargument": "212°F equals 100°C, these are the same claim", "strength": "strong"},
    ]

    # Mock merged positions (what the LLM should return)
    merged_positions = [
        {
            "stance": "Water boils at 100°C/212°F at standard pressure",
            "supporting_sources": ["ai:claude", "ai:gpt"],
            "claims": ["100°C at sea level", "212°F at 1 atm"],
            "changed_from_round": True,
        },
        {
            "stance": "Boiling point varies with pressure",
            "supporting_sources": ["google"],
            "claims": ["Altitude affects boiling point"],
            "changed_from_round": False,
        },
    ]

    with patch.object(engine, "_call_llm", new_callable=AsyncMock) as mock_llm:
        import json
        mock_llm.return_value = f"```json\n{json.dumps(merged_positions)}\n```"
        initial_convergence = engine.calculate_convergence(initial_positions, total_sources=3)
        updated = await engine.update_positions_after_debate(
            initial_positions,
            counterarguments,
            round_number=1,
            current_convergence=initial_convergence,
            total_sources=3
        )

    # Should have merged from 3 positions to 2
    assert len(updated) == 2
    # First position should have both sources
    assert len(updated[0]["supporting_sources"]) == 2
    # Convergence should increase (2/3 vs 1/3 before)
    updated_convergence = engine.calculate_convergence(updated, total_sources=3)
    assert updated_convergence > initial_convergence


@pytest.mark.asyncio
async def test_force_merge_positions():
    """Test that force_merge_positions aggressively merges low-convergence positions."""
    engine = DebateEngine(openrouter_api_key="test-key")

    # Split positions with low convergence (33% each)
    positions = [
        {"stance": "Position A", "supporting_sources": ["source1"], "claims": ["claim A"]},
        {"stance": "Position B", "supporting_sources": ["source2"], "claims": ["claim B"]},
        {"stance": "Position C", "supporting_sources": ["source3"], "claims": ["claim C"]},
    ]

    initial_convergence = engine.calculate_convergence(positions, total_sources=3)
    assert initial_convergence < 0.5  # 33%

    # Force merge should combine positions
    merged = engine.force_merge_positions(positions, total_sources=3)

    # Should have fewer positions
    assert len(merged) < len(positions)

    # Convergence should improve
    final_convergence = engine.calculate_convergence(merged, total_sources=3)
    assert final_convergence > initial_convergence


@pytest.mark.asyncio
async def test_force_merge_preserves_high_convergence():
    """Test that force_merge_positions doesn't touch already-converged positions."""
    engine = DebateEngine(openrouter_api_key="test-key")

    # Already converged - one dominant position
    positions = [
        {"stance": "Consensus view", "supporting_sources": ["s1", "s2", "s3", "s4"], "claims": ["main claim"]},
        {"stance": "Minority view", "supporting_sources": ["s5"], "claims": ["minor claim"]},
    ]

    initial_convergence = engine.calculate_convergence(positions, total_sources=5)
    assert initial_convergence >= 0.8  # 80%

    # Force merge should not change anything
    merged = engine.force_merge_positions(positions, total_sources=5)

    assert len(merged) == len(positions)
    assert merged == positions
