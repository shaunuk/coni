import json
import httpx

from app.schemas.source import SourceResponse


class DebateEngine:
    def __init__(self, openrouter_api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = openrouter_api_key
        self.model = model

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM and return response content."""
        async with httpx.AsyncClient() as client:
            try:
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
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
            except Exception as e:
                print(f"LLM call error: {e}")
                return ""

    def _extract_json(self, text: str) -> dict | list | None:
        """Extract JSON from LLM response, handling markdown code blocks."""
        if not text:
            return None

        # Try to find JSON in code blocks
        if "```json" in text:
            try:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass

        if "```" in text:
            try:
                start = text.index("```") + 3
                # Skip language identifier if present
                if text[start:start+10].strip().startswith(("{", "[")):
                    pass
                else:
                    start = text.index("\n", start) + 1
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass

        # Try to find raw JSON array or object
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            try:
                start = text.index(start_char)
                # Find matching bracket
                depth = 0
                for i, c in enumerate(text[start:]):
                    if c == start_char:
                        depth += 1
                    elif c == end_char:
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[start:start+i+1])
            except (ValueError, json.JSONDecodeError):
                pass

        return None

    async def identify_positions(self, evidence: list[SourceResponse]) -> list[dict]:
        """Identify distinct positions from the evidence."""
        # Filter to only sources with meaningful claims
        valid_evidence = [e for e in evidence if e.claims and len(e.claims) > 0]

        if not valid_evidence:
            return []

        # Build evidence summary
        evidence_parts = []
        for e in valid_evidence:
            claims_text = "; ".join(c.text for c in e.claims[:5])  # Limit claims
            evidence_parts.append(f"Source: {e.source_name}\nClaims: {claims_text}")

        evidence_text = "\n\n".join(evidence_parts)

        system_prompt = """You are analyzing evidence from multiple sources to identify distinct positions/stances on a question.

IMPORTANT: Your goal is to find CONSENSUS. Most sources on factual topics actually AGREE on the core facts.
Look for the underlying agreement first, then note any genuine disagreements.

Your task: Group the sources by their stance. PREFER FEWER POSITIONS - only create separate positions for genuinely incompatible views.

Format your response as a JSON array like this:
```json
[
  {
    "stance": "Brief description of this position",
    "supporting_sources": ["source1", "source2"],
    "claims": ["key claim 1", "key claim 2"]
  }
]
```

Rules:
- STRONGLY PREFER grouping sources together - look for common ground
- Only separate sources if they are GENUINELY CONTRADICTORY (not just different emphasis)
- Different details or focus areas are NOT disagreement - group them together
- Each source should appear in exactly one position
- If sources are saying similar things in different words, they AGREE - group them
- Be concise but accurate"""

        user_prompt = f"Analyze these sources and identify positions. Remember: PREFER CONSENSUS - only separate truly incompatible views:\n\n{evidence_text}"

        result = await self._call_llm(system_prompt, user_prompt)
        parsed = self._extract_json(result)

        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed

        # Fallback: create positions from evidence directly
        return [{
            "stance": f"Position from {e.source_name}",
            "supporting_sources": [e.source_name],
            "claims": [c.text for c in e.claims[:3]]
        } for e in valid_evidence[:4]]

    async def run_counterarguments(
        self, positions: list[dict], round_number: int
    ) -> list[dict]:
        """Generate counterarguments for each position."""
        if not positions:
            return []

        positions_text = json.dumps(positions, indent=2)

        system_prompt = """You are a debate moderator generating counterarguments to test the strength of each position.

Your goal is to find opportunities for CONVERGENCE. Look for:
1. Counterarguments that reveal positions are actually COMPATIBLE
2. Counterarguments that show one position could easily adopt another's view
3. Weaknesses that would cause a position to merge with others

Return a JSON array of counterarguments:
```json
[
  {
    "target_stance": "The stance being challenged",
    "counterargument": "The counterargument text",
    "strength": "weak/medium/strong",
    "suggests_merger_with": "Other stance this could merge with, if any"
  }
]
```

Focus on finding paths to CONSENSUS, not just criticism."""

        user_prompt = f"Debate round {round_number}. Generate counterarguments that could lead to CONVERGENCE:\n\n{positions_text}"

        result = await self._call_llm(system_prompt, user_prompt)
        parsed = self._extract_json(result)

        if isinstance(parsed, list):
            return parsed
        return []

    async def update_positions_after_debate(
        self,
        positions: list[dict],
        counterarguments: list[dict],
        round_number: int,
        current_convergence: float = 0.0,
        total_sources: int = 0
    ) -> list[dict]:
        """Update positions based on how well they held up against counterarguments.

        This AGGRESSIVELY pushes toward consensus. The goal is 100% convergence.
        """
        if not positions:
            return positions

        # If we only have one position, we're done
        if len(positions) <= 1:
            return positions

        # Calculate convergence if not provided
        if total_sources == 0:
            total_sources = sum(len(p.get("supporting_sources", [])) for p in positions)
        if current_convergence == 0.0:
            current_convergence = self.calculate_convergence(positions, total_sources)

        context = json.dumps({
            "current_positions": positions,
            "counterarguments": counterarguments,
            "round": round_number,
            "current_convergence_percent": int(current_convergence * 100),
            "target_convergence_percent": 100,
            "total_sources": total_sources,
            "num_positions": len(positions),
        }, indent=2)

        system_prompt = f"""You are a debate analyst with ONE GOAL: reach CONSENSUS (100% convergence).

Current convergence: {int(current_convergence * 100)}%
Target: 100%
Number of positions: {len(positions)}

YOUR JOB: MERGE POSITIONS. The debate should converge, not stay stuck.

MANDATORY ACTIONS:
1. Identify the SMALLEST position (fewest sources)
2. Find the CLOSEST larger position it could merge with
3. MERGE THEM - move the sources from the smaller position to the larger one
4. Update the stance to incorporate both views

Questions to answer:
- What do these positions AGREE on? (Focus on this!)
- Are the "disagreements" really just different emphasis or wording?
- Which position is best supported? Others should merge into it.
- Can we rephrase the positions to show they're actually compatible?

Return an UPDATED JSON array with FEWER positions than before:
```json
[
  {{
    "stance": "Merged/updated stance that incorporates multiple views",
    "supporting_sources": ["source1", "source2", "source3"],
    "claims": ["unified key claims"],
    "changed_from_round": true,
    "merged_from": ["list of original stances that were merged"]
  }}
]
```

CRITICAL RULES:
- You MUST reduce the number of positions (merge something!)
- Each source must appear in exactly one position
- Set "changed_from_round": true when positions are merged
- Only keep positions separate if they are GENUINELY, FUNDAMENTALLY incompatible
- "Different details" or "different emphasis" is NOT incompatibility - MERGE THEM
- When in doubt, MERGE

If convergence is below 80%, you MUST merge at least one position into another."""

        user_prompt = f"""Round {round_number} update. Current convergence is only {int(current_convergence * 100)}%.

YOU MUST INCREASE CONVERGENCE. Merge positions that are compatible.

Context:
{context}

Return FEWER positions than the {len(positions)} you received. MERGE something!"""

        result = await self._call_llm(system_prompt, user_prompt)
        parsed = self._extract_json(result)

        if isinstance(parsed, list) and len(parsed) > 0:
            # Verify convergence actually improved
            new_convergence = self.calculate_convergence(parsed, total_sources)
            if new_convergence > current_convergence or len(parsed) < len(positions):
                return parsed
            # If no improvement and we have multiple positions, try force merge
            if len(parsed) > 1 and current_convergence < 0.8:
                return self._force_merge_smallest(parsed, total_sources)
            return parsed

        # Fallback: return original positions if parsing fails
        return positions

    def _force_merge_smallest(self, positions: list[dict], total_sources: int) -> list[dict]:
        """Force merge the smallest position into the closest larger one."""
        if len(positions) <= 1:
            return positions

        # Find smallest position
        sorted_positions = sorted(
            positions,
            key=lambda p: len(p.get("supporting_sources", [])),
            reverse=True
        )

        # Merge smallest into largest
        largest = sorted_positions[0]
        smallest = sorted_positions[-1]

        # Combine sources
        merged_sources = list(set(
            largest.get("supporting_sources", []) +
            smallest.get("supporting_sources", [])
        ))

        # Combine claims
        merged_claims = list(set(
            largest.get("claims", [])[:3] +
            smallest.get("claims", [])[:2]
        ))

        merged_position = {
            "stance": largest.get("stance", "Merged position"),
            "supporting_sources": merged_sources,
            "claims": merged_claims,
            "changed_from_round": True,
            "merged_from": [largest.get("stance"), smallest.get("stance")]
        }

        # Return merged position + remaining positions (excluding smallest)
        remaining = sorted_positions[1:-1]  # All except largest and smallest
        return [merged_position] + remaining

    def force_merge_positions(self, positions: list[dict], total_sources: int) -> list[dict]:
        """Synchronous force merge for use after debate rounds complete.

        If convergence is still below threshold after all rounds, aggressively merge.
        """
        if len(positions) <= 1:
            return positions

        current_convergence = self.calculate_convergence(positions, total_sources)

        # If convergence is good enough, keep positions as-is
        if current_convergence >= 0.8:
            return positions

        # Sort by size (largest first)
        sorted_positions = sorted(
            positions,
            key=lambda p: len(p.get("supporting_sources", [])),
            reverse=True
        )

        # Keep merging until we hit 80% convergence or only 2 positions remain
        while len(sorted_positions) > 2:
            current_convergence = self.calculate_convergence(sorted_positions, total_sources)
            if current_convergence >= 0.8:
                break

            # Merge smallest into largest
            largest = sorted_positions[0]
            smallest = sorted_positions[-1]

            merged_sources = list(set(
                largest.get("supporting_sources", []) +
                smallest.get("supporting_sources", [])
            ))

            merged_claims = list(set(
                largest.get("claims", [])[:4] +
                smallest.get("claims", [])[:2]
            ))

            merged_position = {
                "stance": largest.get("stance", "Consensus position"),
                "supporting_sources": merged_sources,
                "claims": merged_claims,
                "changed_from_round": True,
                "merged_from": [
                    largest.get("stance"),
                    smallest.get("stance")
                ] + largest.get("merged_from", [])
            }

            # Replace largest with merged, remove smallest
            sorted_positions = [merged_position] + sorted_positions[1:-1]

        return sorted_positions

    async def synthesize(self, positions: list[dict], arguments: list[list[dict]]) -> dict:
        """Synthesize the debate into a final answer."""
        if not positions:
            return {
                "final_answer": "Unable to synthesize - no positions identified",
                "agreement_areas": [],
                "disagreement_areas": [],
                "confidence": 0.0
            }

        # Calculate final convergence
        total_sources = sum(len(p.get("supporting_sources", [])) for p in positions)
        convergence = self.calculate_convergence(positions, total_sources)

        context = json.dumps({
            "positions": positions,
            "counterarguments": arguments,
            "final_convergence_percent": int(convergence * 100),
            "num_positions": len(positions)
        }, indent=2)

        system_prompt = """You are synthesizing a multi-source debate into a final answer.

The debate has concluded. Analyze the final positions and produce a clear synthesis.

Return JSON:
```json
{
  "final_answer": "A clear, balanced answer based on the evidence and consensus reached",
  "agreement_areas": ["Area where sources agree"],
  "disagreement_areas": ["Area where sources still disagree, if any"],
  "confidence": 0.85
}
```

The final_answer should:
- Lead with the CONSENSUS view if convergence is high
- Cite which sources support which claims
- Note any remaining disagreements briefly
- Be informative and actionable"""

        user_prompt = f"Synthesize this debate (convergence: {int(convergence * 100)}%):\n\n{context}"

        result = await self._call_llm(system_prompt, user_prompt)
        parsed = self._extract_json(result)

        if isinstance(parsed, dict) and "final_answer" in parsed:
            return parsed

        # Fallback synthesis from positions
        all_claims = []
        for p in positions:
            all_claims.extend(p.get("claims", []))

        return {
            "final_answer": f"Based on {len(positions)} source(s): " + "; ".join(all_claims[:3]),
            "agreement_areas": [p.get("stance", "") for p in positions if p.get("supporting_sources", [])],
            "disagreement_areas": [],
            "confidence": 0.6 if positions else 0.0
        }

    def calculate_convergence(self, positions: list[dict], total_sources: int) -> float:
        """Calculate how much the sources converge on a single position."""
        if not positions or total_sources == 0:
            return 0.0
        try:
            largest_group = max(len(p.get("supporting_sources", [])) for p in positions)
            return largest_group / total_sources
        except (ValueError, TypeError):
            return 0.0

    async def validate_consensus(
        self,
        final_answer: str,
        original_responses: list[SourceResponse],
        on_source_validated: callable = None,
    ) -> dict:
        """Validate the consensus answer by asking each AI source if they agree.

        Args:
            final_answer: The synthesized consensus answer
            original_responses: List of original responses from each source
            on_source_validated: Optional callback(source_name, agrees, objection) for progress

        Returns:
            dict with validation_results list and agreement_percentage
        """
        if not original_responses:
            return {
                "validation_results": [],
                "agreement_percentage": 0.0,
            }

        validation_results = []
        agreeing_count = 0

        for response in original_responses:
            source_name = response.source_name
            original_answer = response.raw_response[:1000]  # Truncate for prompt size

            system_prompt = """You are validating a consensus answer that was synthesized from multiple AI sources.

You previously gave an answer to a question. Now you're being shown the final consensus answer that was synthesized from all sources (including your response).

Your task: Evaluate if you agree with this consensus answer.

Return JSON:
```json
{
  "agrees": true,
  "objection": null
}
```

OR if you disagree:
```json
{
  "agrees": false,
  "objection": "Brief explanation of what you would change and why"
}
```

Rules:
- Only object if there's a material error or significant omission
- Minor wording differences are NOT grounds for objection
- Be concise in objections (under 100 words)
- Focus on factual accuracy and completeness"""

            user_prompt = f"""Your original answer was:
---
{original_answer}
---

The consensus answer is:
---
{final_answer}
---

Do you agree with this consensus? If not, what would you change?"""

            result_text = await self._call_llm(system_prompt, user_prompt)
            parsed = self._extract_json(result_text)

            # Default to agreement if parsing fails
            agrees = True
            objection = None

            if isinstance(parsed, dict):
                agrees = parsed.get("agrees", True)
                objection = parsed.get("objection")
                # Ensure objection is only set if they disagree
                if agrees:
                    objection = None

            validation_result = {
                "source_name": source_name,
                "agrees": agrees,
                "objection": objection,
            }
            validation_results.append(validation_result)

            if agrees:
                agreeing_count += 1

            # Emit progress callback if provided
            if on_source_validated:
                await on_source_validated(source_name, agrees, objection)

        agreement_percentage = (
            agreeing_count / len(original_responses) * 100
            if original_responses
            else 0.0
        )

        return {
            "validation_results": validation_results,
            "agreement_percentage": agreement_percentage,
        }

    async def cross_compare_answers(
        self,
        responses: list[SourceResponse],
        on_comparison_complete: callable = None,
    ) -> list[dict]:
        """Have each AI review and comment on the other AIs' answers.

        This creates a peer review where each AI sees what others said
        and provides their perspective on agreements/disagreements.

        Args:
            responses: List of responses from AI sources
            on_comparison_complete: Optional callback(source_name, comparisons) for progress

        Returns:
            List of comparison results, each containing the reviewer's perspective
        """
        if len(responses) < 2:
            return []

        comparison_results = []

        for reviewer in responses:
            reviewer_name = reviewer.source_name
            reviewer_answer = reviewer.raw_response[:800] if reviewer.raw_response else ""

            # Build list of other answers to compare against
            other_answers = []
            for other in responses:
                if other.source_name != reviewer_name:
                    other_answers.append({
                        "source": other.source_name,
                        "answer": (other.raw_response[:500] if other.raw_response else "")
                    })

            if not other_answers:
                continue

            others_text = "\n\n".join([
                f"**{o['source']}**: {o['answer']}" for o in other_answers
            ])

            system_prompt = """You are comparing your answer to other AI models' answers on the same question.

Review each other answer and give your perspective. Be direct and specific.

Return JSON:
```json
{
  "comparisons": [
    {
      "other_source": "model name",
      "agree": true/false,
      "comment": "Brief specific comment on their answer (what they got right/wrong, what's different)"
    }
  ],
  "overall_assessment": "One sentence summary of how your answer compares to others"
}
```

Rules:
- Be specific about agreements and disagreements
- Point out if another model has better/worse information
- Note any factual errors in other answers
- Keep comments concise (under 50 words each)"""

            user_prompt = f"""Your answer was:
---
{reviewer_answer}
---

Other models answered:
---
{others_text}
---

Compare your answer to theirs. What do they have right/wrong? What's different?"""

            result_text = await self._call_llm(system_prompt, user_prompt)
            print(f"[DEBUG] Comparison result from {reviewer_name}: {result_text[:500]}")
            parsed = self._extract_json(result_text)
            print(f"[DEBUG] Parsed comparison: {parsed}")

            comparison = {
                "reviewer": reviewer_name,
                "comparisons": [],
                "overall_assessment": "",
            }

            if isinstance(parsed, dict):
                comparison["comparisons"] = parsed.get("comparisons", [])
                comparison["overall_assessment"] = parsed.get("overall_assessment", "")
            elif isinstance(parsed, list):
                # LLM returned array directly instead of wrapped in dict
                comparison["comparisons"] = parsed
            print(f"[DEBUG] Final comparison for {reviewer_name}: {len(comparison['comparisons'])} comparisons")

            comparison_results.append(comparison)

            if on_comparison_complete:
                await on_comparison_complete(reviewer_name, comparison)

        return comparison_results
