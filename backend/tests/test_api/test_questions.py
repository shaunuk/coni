import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_question():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.text_search.return_value.execute.return_value.data = []
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": "test-uuid",
            "slug": "what-is-the-boiling-point-of-water",
            "text": "What is the boiling point of water?",
            "created_at": "2026-01-27T12:00:00Z",
        }
    ]

    with patch("app.api.questions.get_db", return_value=mock_db):
        with patch("app.api.questions.trigger_pipeline") as mock_trigger:
            response = client.post(
                "/api/questions",
                json={"text": "What is the boiling point of water?"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "what-is-the-boiling-point-of-water"
    mock_trigger.assert_called_once()


def test_get_question_by_slug():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "test-uuid",
            "slug": "what-is-the-boiling-point-of-water",
            "text": "What is the boiling point of water?",
            "created_at": "2026-01-27T12:00:00Z",
        }
    ]

    with patch("app.api.questions.get_db", return_value=mock_db):
        response = client.get("/api/questions/what-is-the-boiling-point-of-water")

    assert response.status_code == 200
    assert response.json()["text"] == "What is the boiling point of water?"
