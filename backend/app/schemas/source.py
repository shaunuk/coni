from pydantic import BaseModel


class Claim(BaseModel):
    text: str
    confidence: float
    evidence: str | None = None


class SourceResponse(BaseModel):
    source_name: str
    raw_response: str
    claims: list[Claim]
    confidence: float | None = None
    source_url: str | None = None
