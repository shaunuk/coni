import re

from fastapi import APIRouter, HTTPException

from app.core.database import get_db
from app.schemas.question import QuestionCreate, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:200].strip("-")


def trigger_pipeline(question_id: str, question_text: str):
    from app.workers.pipeline import run_pipeline_task
    run_pipeline_task.delay(question_id, question_text)


@router.post("", status_code=201, response_model=QuestionResponse)
async def submit_question(question: QuestionCreate):
    db = get_db()

    # Check for existing similar question
    existing = (
        db.table("questions")
        .select("*")
        .text_search("text", question.text)
        .execute()
    )
    if existing.data:
        return QuestionResponse(**existing.data[0])

    # Create new question
    slug = slugify(question.text)
    result = (
        db.table("questions")
        .insert({"text": question.text, "slug": slug})
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create question")

    q = result.data[0]
    trigger_pipeline(q["id"], q["text"])
    return QuestionResponse(**q)


@router.get("/{slug}", response_model=QuestionResponse)
async def get_question(slug: str):
    db = get_db()
    result = db.table("questions").select("*").eq("slug", slug).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionResponse(**result.data[0])
