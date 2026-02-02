import re

from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError

from app.core.database import get_db
from app.schemas.question import QuestionCreate, QuestionResponse
from app.lib.embeddings import generate_embedding

router = APIRouter(prefix="/api/questions", tags=["questions"])

SIMILARITY_THRESHOLD = 0.75  # 75% similarity = same question


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

    # Generate embedding for the question
    embedding = await generate_embedding(question.text)

    # Check for semantically similar questions using vector search
    similar = db.rpc(
        "match_questions",
        {
            "query_embedding": embedding,
            "match_threshold": SIMILARITY_THRESHOLD,
            "match_count": 1,
        },
    ).execute()

    if similar.data:
        # Return existing similar question
        match = similar.data[0]
        existing = (
            db.table("questions")
            .select("*")
            .eq("id", match["id"])
            .execute()
        )
        if existing.data:
            return QuestionResponse(**existing.data[0])

    # Create new question with embedding
    slug = slugify(question.text)

    try:
        result = (
            db.table("questions")
            .insert({
                "text": question.text,
                "slug": slug,
                "embedding": embedding,
            })
            .execute()
        )
    except APIError as e:
        # Handle duplicate slug - return existing question
        if "23505" in str(e) or "duplicate" in str(e).lower():
            existing = db.table("questions").select("*").eq("slug", slug).execute()
            if existing.data:
                return QuestionResponse(**existing.data[0])
        raise HTTPException(status_code=500, detail=str(e))

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create question")

    q = result.data[0]

    # Create initial answer_version immediately so frontend doesn't get 404
    db.table("answer_versions").insert({
        "question_id": q["id"],
        "version": 1,
        "status": "preliminary",
    }).execute()

    trigger_pipeline(q["id"], q["text"])
    return QuestionResponse(**q)


@router.get("/recent", response_model=list)
async def get_recent_questions(limit: int = 20):
    """Get recent questions for the background cloud display."""
    db = get_db()

    # Get recent questions with their answer status
    result = db.table("questions").select(
        "id, text, slug, created_at"
    ).order("created_at", desc=True).limit(limit).execute()

    questions = []
    for q in result.data:
        # Get the latest answer version status for this question
        answer = db.table("answer_versions").select(
            "status, confidence"
        ).eq("question_id", q["id"]).order(
            "version", desc=True
        ).limit(1).execute()

        status = None
        confidence = None
        if answer.data:
            status = answer.data[0]["status"]
            confidence = answer.data[0].get("confidence")

        questions.append({
            "id": q["id"],
            "text": q["text"],
            "slug": q["slug"],
            "created_at": q["created_at"],
            "status": status,
            "confidence": confidence,
        })

    return questions


@router.get("/{slug}", response_model=QuestionResponse)
async def get_question(slug: str):
    db = get_db()
    result = db.table("questions").select("*").eq("slug", slug).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionResponse(**result.data[0])
