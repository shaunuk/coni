import asyncio

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_db
from app.adapters.openrouter import OpenRouterAdapter
from app.adapters.reddit import RedditAdapter
from app.adapters.stackexchange import StackExchangeAdapter
from app.adapters.wikipedia import WikipediaAdapter
from app.services.orchestrator import Orchestrator
from app.services.debate_engine import DebateEngine
from app.services.seal import SealService
from app.lib.progress import ProgressEmitter


def _build_adapters() -> list:
    """Build adapters for sources - using fast/cheap models only for testing."""
    adapters = []

    # AI Models via OpenRouter - fast & cheap only for testing
    models = [
        "anthropic/claude-3-5-haiku",
        "openai/gpt-4o-mini",
        "google/gemini-2.5-flash",
    ]

    for model in models:
        adapters.append(OpenRouterAdapter(api_key=settings.openrouter_api_key, model=model))

    # Web sources
    adapters.append(WikipediaAdapter())

    return adapters


async def _run_pipeline(question_id: str, question_text: str):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Pipeline started for question: {question_id}")

    db = get_db()
    progress = ProgressEmitter(question_id)

    try:
        # Build adapters and get source names
        adapters = _build_adapters()
        source_names = [adapter.source_name for adapter in adapters]

        logger.info(f"Built {len(adapters)} adapters: {source_names}")

        # Small delay to let WebSocket clients connect before emitting events
        await asyncio.sleep(1)

        # Emit pipeline started
        progress.pipeline_started(source_names)
        logger.info("Emitted pipeline_started event")

        # Get existing answer version (created by question submission endpoint)
        version_result = db.table("answer_versions").select("*").eq(
            "question_id", question_id
        ).order("version", desc=True).limit(1).execute()

        if not version_result.data:
            # Fallback: create if not exists
            version_result = db.table("answer_versions").insert({
                "question_id": question_id,
                "version": 1,
                "status": "preliminary",
            }).execute()

        version_id = version_result.data[0]["id"]

        # Get quick preliminary answer from fast model
        preliminary_adapter = OpenRouterAdapter(
            api_key=settings.openrouter_api_key,
            model="anthropic/claude-3-5-haiku",
        )
        prelim_response = await preliminary_adapter.query(question_text)
        if prelim_response:
            db.table("answer_versions").update({
                "preliminary_answer": prelim_response.raw_response,
            }).eq("id", version_id).execute()

        # Update status to debating
        db.table("answer_versions").update({"status": "debating"}).eq("id", version_id).execute()

        # Phase 1: Gather evidence from all sources with progress callbacks
        async def on_source_started(source_name: str):
            progress.source_started(source_name)

        async def on_source_streaming(source_name: str, partial_content: str, is_complete: bool):
            progress.source_streaming(source_name, partial_content, is_complete)

        async def on_source_completed(source_name: str, confidence: float, claims_count: int):
            progress.source_completed(source_name, confidence, claims_count)

        async def on_source_failed(source_name: str, error: str):
            progress.source_failed(source_name, error)

        orchestrator = Orchestrator(
            adapters=adapters,
            on_source_started=on_source_started,
            on_source_streaming=on_source_streaming,
            on_source_completed=on_source_completed,
            on_source_failed=on_source_failed,
            enable_streaming=True,
        )
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

        # Phase 2: Cross-comparison - each AI reviews the others' answers
        debate = DebateEngine(openrouter_api_key=settings.openrouter_api_key)

        # Filter to AI sources only for cross-comparison
        ai_evidence = [e for e in evidence if e.source_name.startswith("openrouter:")]

        if len(ai_evidence) >= 2:
            progress.comparison_started()

            async def on_comparison_complete(reviewer: str, comparison: dict):
                progress.comparison_complete(
                    reviewer,
                    comparison.get("comparisons", []),
                    comparison.get("overall_assessment", ""),
                )

            comparison_results = await debate.cross_compare_answers(
                ai_evidence,
                on_comparison_complete=on_comparison_complete,
            )
            progress.comparison_finished(comparison_results)

            # Note: Cross-comparison results shown via real-time events, not stored in DB
            # (would need to add 'cross_comparison' to debate_rounds_phase_check constraint)

        # Phase 3-4: Run debate
        positions = await debate.identify_positions(evidence)

        all_arguments = []
        convergence_score = debate.calculate_convergence(positions, len(evidence))

        for round_num in range(1, settings.debate_max_rounds + 1):
            if convergence_score >= settings.consensus_threshold:
                break

            # Emit debate round started
            progress.debate_round_started(round_num)

            arguments = await debate.run_counterarguments(positions, round_num)
            all_arguments.append(arguments)

            # Emit the counterarguments so frontend can display them
            progress.debate_arguments(round_num, arguments)

            # Store pre-update positions and convergence for this round
            db.table("debate_rounds").insert({
                "answer_version_id": version_id,
                "round_number": round_num,
                "phase": "counterarguments",
                "positions": positions,
                "arguments": arguments,
                "convergence_score": convergence_score,
            }).execute()

            # Update positions based on how they held up against counterarguments
            # This allows positions to merge or sources to shift when counterarguments are compelling
            # Pass current convergence to enable aggressive merging toward consensus
            positions = await debate.update_positions_after_debate(
                positions,
                arguments,
                round_num,
                current_convergence=convergence_score,
                total_sources=len(evidence)
            )
            convergence_score = debate.calculate_convergence(positions, len(evidence))

            # Emit position update for convergence visualization
            progress.position_update(positions, convergence_score)

            # Emit debate round completed with updated convergence
            progress.debate_round_completed(round_num, convergence_score)

        # Force merge if convergence is still too low after all rounds
        if convergence_score < 0.8 and len(positions) > 1:
            logger.info(f"Force merging positions (convergence={convergence_score:.0%}, positions={len(positions)})")
            positions = debate.force_merge_positions(positions, len(evidence))
            convergence_score = debate.calculate_convergence(positions, len(evidence))
            logger.info(f"After force merge: convergence={convergence_score:.0%}, positions={len(positions)}")
            # Emit final position update after force merge
            progress.position_update(positions, convergence_score)

        # Phase 4: Synthesize
        progress.synthesis_started()
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

        final_confidence = synthesis.get("confidence", convergence_score)
        progress.synthesis_completed(final_confidence)

        # Phase 5: Cross-validation - ask each AI source if they agree with consensus
        progress.validation_started()

        # Filter to only AI sources (OpenRouter models) for validation
        ai_evidence = [e for e in evidence if e.source_name.startswith("openrouter:")]

        async def on_source_validated(source_name: str, agrees: bool, objection: str | None):
            progress.source_validated(source_name, agrees, objection)

        validation_result = await debate.validate_consensus(
            final_answer=synthesis.get("final_answer", ""),
            original_responses=ai_evidence,
            on_source_validated=on_source_validated,
        )

        progress.validation_completed(validation_result["agreement_percentage"])

        # Note: validation_results not stored in DB - shown via real-time progress events

        # Determine final status
        final_status = "consensus_reached" if convergence_score >= settings.consensus_threshold else "contested"

        # Seal the answer
        seal_service = SealService()
        seal_data = {
            "question_id": question_id,
            "question_text": question_text,
            "final_answer": synthesis.get("final_answer", ""),
            "confidence": final_confidence,
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
            "confidence": final_confidence,
            "sealed_at": "now()",
            "seal_hash": seal_hash,
            "previous_hash": previous_hash,
        }).eq("id", version_id).execute()

        # Emit pipeline completed
        progress.pipeline_completed(
            status=final_status,
            confidence=final_confidence,
            final_answer=synthesis.get("final_answer", ""),
        )

    except Exception as e:
        progress.pipeline_failed(str(e))
        raise
    finally:
        progress.close()


@celery_app.task(name="consensus.pipeline")
def run_pipeline_task(question_id: str, question_text: str):
    asyncio.run(_run_pipeline(question_id, question_text))
