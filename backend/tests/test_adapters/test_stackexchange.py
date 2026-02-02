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
                "is_answered": True,
                "answer_count": 5,
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


@pytest.mark.asyncio
async def test_stackexchange_detects_physics_site():
    """Test that physics-related queries route to Physics Stack Exchange."""
    adapter = StackExchangeAdapter()
    sites = adapter._detect_sites_for_query("what is a quantum")

    assert len(sites) >= 1
    assert sites[0]["site"] == "physics"
    assert sites[0]["display_name"] == "Physics Stack Exchange"


@pytest.mark.asyncio
async def test_stackexchange_detects_programming_site():
    """Test that programming queries route to Stack Overflow."""
    adapter = StackExchangeAdapter()
    sites = adapter._detect_sites_for_query("how to fix python error")

    assert len(sites) >= 1
    assert sites[0]["site"] == "stackoverflow"


@pytest.mark.asyncio
async def test_stackexchange_formats_query():
    """Test that query formatting removes common prefixes."""
    adapter = StackExchangeAdapter()

    assert adapter._format_query("what is a quantum") == "quantum"
    assert adapter._format_query("How does gravity work") == "gravity work"
    assert adapter._format_query("explain the theory of relativity") == "theory of relativity"


@pytest.mark.asyncio
async def test_stackexchange_filters_low_score_results():
    """Test that results with score < MIN_SCORE_THRESHOLD are filtered out."""
    mock_data = {
        "items": [
            {
                "title": "Good answer",
                "body": "This is helpful.",
                "score": 10,
                "is_answered": True,
                "answer_count": 3,
                "link": "https://physics.stackexchange.com/q/123",
            },
            {
                "title": "Bad answer",
                "body": "Low quality.",
                "score": 0,
                "is_answered": False,
                "answer_count": 0,
                "link": "https://physics.stackexchange.com/q/456",
            },
        ]
    }

    adapter = StackExchangeAdapter()

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_data):
        result = await adapter.query("what is a quantum")

    # Only the high-score item should be included
    assert len(result.claims) == 1
    assert "Good answer" in result.raw_response
    assert "Bad answer" not in result.raw_response


@pytest.mark.asyncio
async def test_stackexchange_searches_multiple_sites():
    """Test that queries matching multiple categories search multiple sites."""
    adapter = StackExchangeAdapter()

    # "quantum energy" matches both physics and potentially others
    sites = adapter._detect_sites_for_query("quantum energy in physics")

    # Should return up to 2 sites
    assert len(sites) <= 2
    # Physics should be the primary match
    assert sites[0]["site"] == "physics"
