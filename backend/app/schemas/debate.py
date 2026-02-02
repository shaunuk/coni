from pydantic import BaseModel
from datetime import datetime
from typing import Any


class ValidationResult(BaseModel):
    """Result of a single source's validation of the consensus answer."""
    source_name: str
    agrees: bool
    objection: str | None = None


class ValidationResults(BaseModel):
    """Results of consensus cross-validation."""
    validation_results: list[ValidationResult] = []
    agreement_percentage: float = 0.0


class DebateRoundResponse(BaseModel):
    id: str
    round_number: int
    phase: str
    positions: list[dict[str, Any]] = []
    arguments: list[dict[str, Any]] = []
    synthesis: dict[str, Any] | None = None
    convergence_score: float | None = None
    validation_results: ValidationResults | None = None
    created_at: datetime
