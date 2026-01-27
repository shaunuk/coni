import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.reddit import RedditAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_reddit_returns_source_response():
    mock_data = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "What is the boiling point of water?",
                        "selftext": "It's 100C at sea level.",
                        "score": 42,
                        "permalink": "/r/askscience/comments/abc/what_is_the_boiling_point/",
                    }
                }
            ]
        }
    }

    adapter = RedditAdapter()

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_data):
        result = await adapter.query("boiling point of water")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "reddit"
    assert len(result.claims) == 1
