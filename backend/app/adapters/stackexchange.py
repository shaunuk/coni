import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


class StackExchangeAdapter(BaseAdapter):
    def __init__(self, site: str = "stackoverflow"):
        self.site = site
        self.base_url = "https://api.stackexchange.com/2.3/search/advanced"

    async def _call_api(self, question: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "order": "desc",
                    "sort": "relevance",
                    "q": question,
                    "site": self.site,
                    "filter": "withbody",
                    "pagesize": 5,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def query(self, question: str) -> SourceResponse | None:
        try:
            data = await self._call_api(question)
            items = data.get("items", [])

            claims = []
            raw_parts = []
            for item in items:
                body = item.get("body", "")
                score = item.get("score", 0)
                is_accepted = item.get("is_accepted", False)
                confidence = min(score / 50, 1.0)
                if is_accepted:
                    confidence = min(confidence + 0.2, 1.0)

                claims.append(Claim(
                    text=body[:500],
                    confidence=confidence,
                    evidence=item.get("link"),
                ))
                raw_parts.append(f"[score:{score}] {item.get('title', '')}\n{body[:300]}")

            return SourceResponse(
                source_name="stackexchange",
                raw_response="\n\n".join(raw_parts),
                claims=claims,
                confidence=sum(c.confidence for c in claims) / len(claims) if claims else 0.0,
                source_url=None,
            )
        except Exception:
            return None
