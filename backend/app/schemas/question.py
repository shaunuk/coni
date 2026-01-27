from pydantic import BaseModel
from datetime import datetime


class QuestionCreate(BaseModel):
    text: str


class QuestionResponse(BaseModel):
    id: str
    slug: str
    text: str
    created_at: datetime
