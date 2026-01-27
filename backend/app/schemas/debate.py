from pydantic import BaseModel
from datetime import datetime


class Position(BaseModel):
    stance: str
    supporting_sources: list[str]
    claims: list[str]


class Argument(BaseModel):
    source_name: str
    position: str
    argument: str
    evidence: list[str]


class DebateRoundResponse(BaseModel):
    id: str
    round_number: int
    phase: str
    positions: list[Position] = []
    arguments: list[Argument] = []
    synthesis: dict | None = None
    convergence_score: float | None = None
    created_at: datetime
