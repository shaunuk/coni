import asyncio
import re

import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


# Site selection based on query topic keywords
SITE_KEYWORDS = {
    "physics": {
        "keywords": [
            "quantum", "photon", "electron", "proton", "neutron", "atom",
            "relativity", "gravity", "mass", "energy", "force", "velocity",
            "acceleration", "momentum", "wave", "particle", "field",
            "thermodynamics", "entropy", "electromagnetic", "nuclear",
            "physics", "mechanics", "optics", "magnetism", "radiation",
        ],
        "site": "physics",
        "display_name": "Physics Stack Exchange",
    },
    "math": {
        "keywords": [
            "integral", "derivative", "equation", "theorem", "proof",
            "algebra", "calculus", "geometry", "topology", "matrix",
            "vector", "function", "polynomial", "logarithm", "trigonometry",
            "mathematics", "mathematical",
        ],
        "site": "math",
        "display_name": "Math Stack Exchange",
    },
    "chemistry": {
        "keywords": [
            "molecule", "compound", "reaction", "bond", "element",
            "periodic", "acid", "base", "organic", "inorganic",
            "chemistry", "chemical", "ion", "catalyst", "oxidation",
        ],
        "site": "chemistry",
        "display_name": "Chemistry Stack Exchange",
    },
    "biology": {
        "keywords": [
            "cell", "gene", "dna", "rna", "protein", "evolution",
            "organism", "species", "ecology", "photosynthesis",
            "biology", "biological", "bacteria", "virus", "enzyme",
        ],
        "site": "biology",
        "display_name": "Biology Stack Exchange",
    },
    "astronomy": {
        "keywords": [
            "star", "planet", "galaxy", "universe", "cosmos", "solar",
            "lunar", "orbit", "black hole", "supernova", "nebula",
            "astronomy", "astronomical", "celestial", "telescope",
        ],
        "site": "astronomy",
        "display_name": "Astronomy Stack Exchange",
    },
    "electronics": {
        "keywords": [
            "circuit", "resistor", "capacitor", "transistor", "diode",
            "voltage", "current", "amplifier", "oscillator", "pcb",
            "electronics", "electrical", "arduino", "microcontroller",
        ],
        "site": "electronics",
        "display_name": "Electrical Engineering Stack Exchange",
    },
    "programming": {
        "keywords": [
            "code", "programming", "software", "algorithm", "function",
            "variable", "loop", "array", "class", "object", "api",
            "database", "server", "python", "javascript", "java", "c++",
            "bug", "error", "exception", "debug", "compile",
        ],
        "site": "stackoverflow",
        "display_name": "Stack Overflow",
    },
}

# Minimum score threshold for including results
MIN_SCORE_THRESHOLD = 1


class StackExchangeAdapter(BaseAdapter):
    def __init__(self, default_site: str = "stackoverflow"):
        self.default_site = default_site
        self.base_url = "https://api.stackexchange.com/2.3"

    @property
    def source_name(self) -> str:
        return "Stack Exchange"

    def _detect_sites_for_query(self, question: str) -> list[dict]:
        """
        Detect which Stack Exchange sites are most relevant for this query.
        Returns a list of site configs sorted by relevance.
        """
        question_lower = question.lower()
        site_scores = []

        for category, config in SITE_KEYWORDS.items():
            score = sum(1 for kw in config["keywords"] if kw in question_lower)
            if score > 0:
                site_scores.append({
                    "site": config["site"],
                    "display_name": config["display_name"],
                    "score": score,
                })

        # Sort by score descending
        site_scores.sort(key=lambda x: x["score"], reverse=True)

        # If no matches, use default
        if not site_scores:
            site_scores = [{
                "site": self.default_site,
                "display_name": "Stack Overflow",
                "score": 0,
            }]

        # Return top 2 most relevant sites
        return site_scores[:2]

    def _format_query(self, question: str) -> str:
        """
        Format the query for better Stack Exchange search results.
        - Remove common question words
        - Extract key terms
        """
        # Remove common question prefixes
        question = re.sub(
            r"^(what is|what are|how do|how does|why is|why are|can you explain|explain)\s+",
            "",
            question.lower(),
        )

        # Remove articles
        question = re.sub(r"\b(a|an|the)\b", "", question)

        # Clean up extra whitespace
        question = " ".join(question.split())

        return question

    async def _call_api(self, query: str, site: str) -> dict:
        """Call the Stack Exchange API for a specific site."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search/advanced",
                params={
                    "order": "desc",
                    "sort": "votes",  # Sort by votes for quality
                    "q": query,
                    "site": site,
                    "filter": "withbody",
                    "pagesize": 5,
                    "accepted": "True",  # Prefer questions with accepted answers
                },
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def _search_site(self, query: str, site_config: dict) -> list[dict]:
        """Search a single site and return processed results."""
        try:
            data = await self._call_api(query, site_config["site"])
            items = data.get("items", [])

            # Filter by minimum score and add site info
            results = []
            for item in items:
                score = item.get("score", 0)
                if score >= MIN_SCORE_THRESHOLD:
                    item["_site_name"] = site_config["display_name"]
                    item["_site"] = site_config["site"]
                    results.append(item)

            return results
        except Exception:
            return []

    async def query(self, question: str) -> SourceResponse | None:
        try:
            # Detect relevant sites
            sites = self._detect_sites_for_query(question)

            # Format the query
            formatted_query = self._format_query(question)

            # Search all relevant sites concurrently
            tasks = [self._search_site(formatted_query, site) for site in sites]
            results_by_site = await asyncio.gather(*tasks)

            # Flatten and sort all results by score
            all_items = []
            for results in results_by_site:
                all_items.extend(results)

            # Sort by score descending
            all_items.sort(key=lambda x: x.get("score", 0), reverse=True)

            # Take top results
            top_items = all_items[:5]

            if not top_items:
                return None

            claims = []
            raw_parts = []
            sites_used = set()

            for item in top_items:
                body = item.get("body", "")
                score = item.get("score", 0)
                is_answered = item.get("is_answered", False)
                answer_count = item.get("answer_count", 0)
                site_name = item.get("_site_name", "Stack Exchange")
                sites_used.add(site_name)

                # Calculate confidence based on multiple factors
                # Base confidence from score (higher scores = more community validation)
                confidence = min(score / 30, 0.7)

                # Bonus for having answers
                if is_answered:
                    confidence = min(confidence + 0.15, 1.0)
                if answer_count > 3:
                    confidence = min(confidence + 0.1, 1.0)

                # High score bonus
                if score >= 50:
                    confidence = min(confidence + 0.1, 1.0)

                claims.append(Claim(
                    text=body[:500],
                    confidence=confidence,
                    evidence=item.get("link"),
                ))
                raw_parts.append(
                    f"[{site_name}] [score:{score}] {item.get('title', '')}\n{body[:300]}"
                )

            # Source name reflects which sites were actually used
            source_display = " & ".join(sorted(sites_used)) if sites_used else "Stack Exchange"

            return SourceResponse(
                source_name="stackexchange",
                raw_response="\n\n".join(raw_parts),
                claims=claims,
                confidence=sum(c.confidence for c in claims) / len(claims) if claims else 0.0,
                source_url=None,
            )
        except Exception:
            return None
