from pydantic import BaseModel
from datetime import datetime

from app.schemas.source import SourceResponse


class AnswerVersionResponse(BaseModel):
    id: str
    question_id: str
    version: int
    status: str
    preliminary_answer: str | None = None
    final_answer: str | None = None
    confidence: float | None = None
    sealed_at: datetime | None = None
    seal_hash: str | None = None
    created_at: datetime
    sources: list[SourceResponse] = []
