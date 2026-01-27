import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


class RedditAdapter(BaseAdapter):
    def __init__(self):
        self.base_url = "https://www.reddit.com/search.json"

    async def _call_api(self, question: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={"q": question, "sort": "relevance", "limit": 10},
                headers={"User-Agent": "ConsensusEngine/0.1"},
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def query(self, question: str) -> SourceResponse | None:
        try:
            data = await self._call_api(question)
            posts = data.get("data", {}).get("children", [])

            claims = []
            raw_parts = []
            for post in posts:
                p = post["data"]
                text = p.get("selftext", "") or p.get("title", "")
                if text.strip():
                    score = p.get("score", 0)
                    confidence = min(score / 100, 1.0)
                    permalink = p.get("permalink", "")
                    claims.append(Claim(
                        text=text[:500],
                        confidence=confidence,
                        evidence=f"https://reddit.com{permalink}" if permalink else None,
                    ))
                    raw_parts.append(f"[score:{score}] {p.get('title', '')}\n{text[:300]}")

            return SourceResponse(
                source_name="reddit",
                raw_response="\n\n".join(raw_parts),
                claims=claims,
                confidence=sum(c.confidence for c in claims) / len(claims) if claims else 0.0,
                source_url=f"https://www.reddit.com/search?q={question.replace(' ', '+')}",
            )
        except Exception:
            return None
