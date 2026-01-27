import json
import httpx

from app.schemas.source import SourceResponse


class DebateEngine:
    def __init__(self, openrouter_api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = openrouter_api_key
        self.model = model

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def _cluster_positions(self, evidence: list[SourceResponse]) -> list[dict]:
        evidence_text = "\n\n".join(
            f"Source: {e.source_name}\nClaims: {json.dumps([c.text for c in e.claims])}"
            for e in evidence
        )
        prompt = (
            "Given the following evidence from multiple sources, identify distinct positions "
            "(stances) and group the sources by their stance. Return JSON with format: "
            '[{"stance": "...", "supporting_sources": ["source1", ...], "claims": ["claim1", ...]}]'
        )
        result = await self._call_llm(prompt, evidence_text)
        return json.loads(result) if isinstance(result, str) else result

    async def identify_positions(self, evidence: list[SourceResponse]) -> list[dict]:
        return await self._cluster_positions(evidence)

    async def run_counterarguments(
        self, positions: list[dict], round_number: int
    ) -> list[dict]:
        positions_text = json.dumps(positions, indent=2)
        prompt = (
            f"Debate round {round_number}. Review these positions and provide counterarguments "
            "for each. Identify weaknesses, missing evidence, and logical gaps. "
            "Return JSON array: "
            '[{"source_name": "debate_engine", "position": "...", "argument": "...", "evidence": [...]}]'
        )
        result = await self._call_llm(prompt, positions_text)
        return json.loads(result) if isinstance(result, str) else result

    async def synthesize(self, positions: list[dict], arguments: list[list[dict]]) -> dict:
        context = json.dumps({"positions": positions, "argument_rounds": arguments}, indent=2)
        prompt = (
            "Synthesize the debate. Identify areas of agreement, areas of disagreement, "
            "the strength of each side, and produce a final synthesis answer. "
            'Return JSON: {"final_answer": "...", "agreement_areas": [...], '
            '"disagreement_areas": [...], "confidence": 0.0-1.0}'
        )
        result = await self._call_llm(prompt, context)
        return json.loads(result) if isinstance(result, str) else result

    def calculate_convergence(self, positions: list[dict], total_sources: int) -> float:
        if not positions or total_sources == 0:
            return 0.0
        largest_group = max(len(p["supporting_sources"]) for p in positions)
        return largest_group / total_sources
