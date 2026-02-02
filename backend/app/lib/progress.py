"""Progress event emitter using Redis pub/sub for real-time updates."""
import json
from typing import Literal, Optional
from datetime import datetime

import redis

from app.core.config import settings


ProgressEventType = Literal[
    "pipeline_started",
    "source_started",
    "source_streaming",
    "source_completed",
    "source_failed",
    "debate_round_started",
    "debate_round_completed",
    "position_update",
    "synthesis_started",
    "synthesis_completed",
    "validation_started",
    "source_validated",
    "validation_completed",
    "pipeline_completed",
    "pipeline_failed",
]


class ProgressEmitter:
    """Emits progress events to Redis pub/sub for WebSocket delivery."""

    def __init__(self, question_id: str):
        self.question_id = question_id
        self.channel = f"progress:{question_id}"
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url)
        return self._redis

    def emit(
        self,
        event_type: ProgressEventType,
        data: Optional[dict] = None,
    ) -> None:
        """Publish a progress event to Redis."""
        message = {
            "type": event_type,
            "question_id": self.question_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        self.redis.publish(self.channel, json.dumps(message))

    def pipeline_started(self, sources: list[str]) -> None:
        """Pipeline has started processing."""
        self.emit("pipeline_started", {"sources": sources})

    def source_started(self, source_name: str) -> None:
        """A source has begun querying."""
        self.emit("source_started", {"source_name": source_name})

    def source_streaming(
        self,
        source_name: str,
        partial_content: str,
        is_complete: bool = False,
    ) -> None:
        """A source is streaming tokens."""
        self.emit("source_streaming", {
            "source_name": source_name,
            "partial_content": partial_content,
            "is_complete": is_complete,
        })

    def source_completed(
        self,
        source_name: str,
        confidence: float,
        claims_count: int,
    ) -> None:
        """A source has completed successfully."""
        self.emit("source_completed", {
            "source_name": source_name,
            "confidence": confidence,
            "claims_count": claims_count,
        })

    def source_failed(self, source_name: str, error: str) -> None:
        """A source failed to respond."""
        self.emit("source_failed", {
            "source_name": source_name,
            "error": error,
        })

    def debate_round_started(self, round_number: int) -> None:
        """A debate round has started."""
        self.emit("debate_round_started", {"round_number": round_number})

    def debate_round_completed(
        self,
        round_number: int,
        convergence_score: float,
    ) -> None:
        """A debate round has completed."""
        self.emit("debate_round_completed", {
            "round_number": round_number,
            "convergence_score": convergence_score,
        })

    def debate_arguments(
        self,
        round_number: int,
        arguments: list[dict],
    ) -> None:
        """Counterarguments generated during debate round."""
        self.emit("debate_arguments", {
            "round_number": round_number,
            "arguments": arguments,
        })

    def position_merged(
        self,
        merged_from: list[str],
        merged_into: str,
        reason: str,
    ) -> None:
        """A position was merged into another."""
        self.emit("position_merged", {
            "merged_from": merged_from,
            "merged_into": merged_into,
            "reason": reason,
        })

    def position_update(
        self,
        positions: list[dict],
        convergence_score: float,
    ) -> None:
        """Positions have been updated (sources may have shifted)."""
        self.emit("position_update", {
            "positions": positions,
            "convergence_score": convergence_score,
        })

    def synthesis_started(self) -> None:
        """Final synthesis has started."""
        self.emit("synthesis_started")

    def synthesis_completed(self, confidence: float) -> None:
        """Final synthesis has completed."""
        self.emit("synthesis_completed", {"confidence": confidence})

    def validation_started(self) -> None:
        """Validation phase has started."""
        self.emit("validation_started")

    def source_validated(
        self,
        source_name: str,
        agrees: bool,
        objection: str | None = None,
    ) -> None:
        """A source has validated the consensus answer."""
        self.emit("source_validated", {
            "source_name": source_name,
            "agrees": agrees,
            "objection": objection,
        })

    def validation_completed(self, agreement_percentage: float) -> None:
        """Validation phase has completed."""
        self.emit("validation_completed", {
            "agreement_percentage": agreement_percentage,
        })

    def comparison_started(self) -> None:
        """Cross-comparison phase has started."""
        self.emit("comparison_started", {})

    def comparison_complete(
        self,
        reviewer: str,
        comparisons: list[dict],
        overall_assessment: str,
    ) -> None:
        """A source has completed comparing its answer to others."""
        self.emit("comparison_complete", {
            "reviewer": reviewer,
            "comparisons": comparisons,
            "overall_assessment": overall_assessment,
        })

    def comparison_finished(self, results: list[dict]) -> None:
        """All cross-comparisons are complete."""
        self.emit("comparison_finished", {
            "results": results,
        })

    def pipeline_completed(
        self,
        status: str,
        confidence: float,
        final_answer: str,
    ) -> None:
        """Pipeline has completed successfully."""
        self.emit("pipeline_completed", {
            "status": status,
            "confidence": confidence,
            "final_answer": final_answer,
        })

    def pipeline_failed(self, error: str) -> None:
        """Pipeline has failed."""
        self.emit("pipeline_failed", {"error": error})

    def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
            self._redis = None
