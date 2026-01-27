import pytest
from app.services.seal import SealService


def test_seal_generates_deterministic_hash():
    service = SealService()
    data = {
        "question": "What is the boiling point of water?",
        "answer": "100°C at sea level",
        "debate_transcript": [{"round": 1, "content": "all agree"}],
        "sources": ["claude", "gpt"],
        "timestamp": "2026-01-27T12:00:00Z",
    }

    hash1 = service.generate_hash(data)
    hash2 = service.generate_hash(data)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest


def test_seal_chain_includes_previous_hash():
    service = SealService()
    data1 = {"question": "Q1", "answer": "A1", "timestamp": "2026-01-27T12:00:00Z"}
    hash1 = service.generate_hash(data1)

    data2 = {"question": "Q2", "answer": "A2", "timestamp": "2026-01-27T13:00:00Z"}
    hash2 = service.generate_hash(data2, previous_hash=hash1)

    # Hash should be different with vs without previous hash
    hash2_no_chain = service.generate_hash(data2)
    assert hash2 != hash2_no_chain


def test_seal_verify_detects_tampering():
    service = SealService()
    data = {"question": "Q1", "answer": "A1", "timestamp": "2026-01-27T12:00:00Z"}
    original_hash = service.generate_hash(data)

    assert service.verify(data, original_hash) is True

    # Tamper with data
    data["answer"] = "TAMPERED"
    assert service.verify(data, original_hash) is False
