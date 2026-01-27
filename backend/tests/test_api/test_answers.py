import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_answer_for_question():
    mock_db = MagicMock()

    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": "v1",
            "question_id": "q1",
            "version": 1,
            "status": "sealed",
            "preliminary_answer": "Quick answer",
            "final_answer": "Full consensus answer",
            "confidence": 0.95,
            "sealed_at": "2026-01-27T12:00:00Z",
            "seal_hash": "abc123",
            "created_at": "2026-01-27T11:00:00Z",
        }
    ]

    with patch("app.api.answers.get_db", return_value=mock_db):
        response = client.get("/api/answers/q1")

    assert response.status_code == 200
    assert response.json()["status"] == "sealed"
    assert response.json()["final_answer"] == "Full consensus answer"


def test_get_debate_rounds():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {
            "id": "r1",
            "round_number": 1,
            "phase": "counterarguments",
            "positions": [],
            "arguments": [],
            "synthesis": None,
            "convergence_score": 0.7,
            "created_at": "2026-01-27T11:30:00Z",
        }
    ]

    with patch("app.api.answers.get_db", return_value=mock_db):
        response = client.get("/api/answers/v1/debate")

    assert response.status_code == 200
    assert len(response.json()) == 1
