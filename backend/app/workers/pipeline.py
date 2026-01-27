import asyncio

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_db
from app.adapters.openrouter import OpenRouterAdapter
from app.adapters.google_search import GoogleSearchAdapter
from app.adapters.reddit import RedditAdapter
from app.adapters.stackexchange import StackExchangeAdapter
from app.services.orchestrator import Orchestrator
from app.services.debate_engine import DebateEngine
from app.services.seal import SealService


def _build_adapters() -> list:
    adapters = []
    models = [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "google/gemini-pro-1.5",
    ]
    for model in models:
        adapters.append(OpenRouterAdapter(api_key=settings.openrouter_api_key, model=model))
    adapters.append(RedditAdapter())
    adapters.append(StackExchangeAdapter())
    return adapters


async def _run_pipeline(question_id: str, question_text: str):
    db = get_db()

    # Create preliminary answer version
    version_result = db.table("answer_versions").insert({
        "question_id": question_id,
        "version": 1,
        "status": "preliminary",
    }).execute()
    version_id = version_result.data[0]["id"]

    # Get quick preliminary answer
    preliminary_adapter = OpenRouterAdapter(
        api_key=settings.openrouter_api_key,
        model="anthropic/claude-3.5-sonnet",
    )
    prelim_response = await preliminary_adapter.query(question_text)
    if prelim_response:
        db.table("answer_versions").update({
            "preliminary_answer": prelim_response.raw_response,
        }).eq("id", version_id).execute()

    # Update status to debating
    db.table("answer_versions").update({"status": "debating"}).eq("id", version_id).execute()

    # Phase 1: Gather evidence from all sources
    orchestrator = Orchestrator(adapters=_build_adapters())
    evidence = await orchestrator.gather_evidence(question_text)

    # Store source responses
    for e in evidence:
        db.table("source_responses").insert({
            "answer_version_id": version_id,
            "source_name": e.source_name,
            "raw_response": e.raw_response,
            "claims": [c.model_dump() for c in e.claims],
            "confidence": e.confidence,
            "source_url": e.source_url,
        }).execute()

    # Phase 2-4: Run debate
    debate = DebateEngine(openrouter_api_key=settings.openrouter_api_key)
    positions = await debate.identify_positions(evidence)

    all_arguments = []
    convergence_score = debate.calculate_convergence(positions, len(evidence))

    for round_num in range(1, settings.debate_max_rounds + 1):
        if convergence_score >= settings.consensus_threshold:
            break

        arguments = await debate.run_counterarguments(positions, round_num)
        all_arguments.append(arguments)

        db.table("debate_rounds").insert({
            "answer_version_id": version_id,
            "round_number": round_num,
            "phase": "counterarguments",
            "positions": positions,
            "arguments": arguments,
            "convergence_score": convergence_score,
        }).execute()

        # Re-evaluate positions after counterarguments
        positions = await debate.identify_positions(evidence)
        convergence_score = debate.calculate_convergence(positions, len(evidence))

    # Phase 4: Synthesize
    synthesis = await debate.synthesize(positions, all_arguments)

    db.table("debate_rounds").insert({
        "answer_version_id": version_id,
        "round_number": settings.debate_max_rounds + 1,
        "phase": "synthesis",
        "positions": positions,
        "arguments": [],
        "synthesis": synthesis,
        "convergence_score": convergence_score,
    }).execute()

    # Determine final status
    final_status = "consensus_reached" if convergence_score >= settings.consensus_threshold else "contested"

    # Seal the answer
    seal_service = SealService()
    seal_data = {
        "question_id": question_id,
        "question_text": question_text,
        "final_answer": synthesis.get("final_answer", ""),
        "confidence": synthesis.get("confidence", convergence_score),
        "positions": positions,
        "evidence_count": len(evidence),
    }

    # Get previous hash for chain
    prev = db.table("answer_versions").select("seal_hash").eq(
        "status", "sealed"
    ).order("sealed_at", desc=True).limit(1).execute()
    previous_hash = prev.data[0]["seal_hash"] if prev.data else None

    seal_hash = seal_service.generate_hash(seal_data, previous_hash=previous_hash)

    db.table("answer_versions").update({
        "status": final_status,
        "final_answer": synthesis.get("final_answer", ""),
        "confidence": synthesis.get("confidence", convergence_score),
        "sealed_at": "now()",
        "seal_hash": seal_hash,
        "previous_hash": previous_hash,
    }).eq("id", version_id).execute()


@celery_app.task(name="consensus.pipeline")
def run_pipeline_task(question_id: str, question_text: str):
    asyncio.run(_run_pipeline(question_id, question_text))
