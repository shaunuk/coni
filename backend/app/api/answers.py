from fastapi import APIRouter, HTTPException

from app.core.database import get_db
from app.schemas.answer import AnswerVersionResponse
from app.schemas.debate import DebateRoundResponse

router = APIRouter(prefix="/api/answers", tags=["answers"])


@router.get("/{question_id}", response_model=AnswerVersionResponse)
async def get_latest_answer(question_id: str):
    db = get_db()
    result = (
        db.table("answer_versions")
        .select("*")
        .eq("question_id", question_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No answer found")
    return AnswerVersionResponse(**result.data[0])


@router.get("/{version_id}/debate", response_model=list[DebateRoundResponse])
async def get_debate_rounds(version_id: str):
    db = get_db()
    result = (
        db.table("debate_rounds")
        .select("*")
        .eq("answer_version_id", version_id)
        .order("round_number")
        .execute()
    )
    return [DebateRoundResponse(**r) for r in result.data]


@router.get("/{version_id}/sources")
async def get_sources(version_id: str):
    db = get_db()
    result = (
        db.table("source_responses")
        .select("*")
        .eq("answer_version_id", version_id)
        .execute()
    )
    return result.data


@router.get("/{question_id}/history", response_model=list[AnswerVersionResponse])
async def get_answer_history(question_id: str):
    db = get_db()
    result = (
        db.table("answer_versions")
        .select("*")
        .eq("question_id", question_id)
        .order("version")
        .execute()
    )
    return [AnswerVersionResponse(**r) for r in result.data]
