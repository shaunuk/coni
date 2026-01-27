import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


class GoogleSearchAdapter(BaseAdapter):
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def _call_api(self, question: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={"key": self.api_key, "cx": self.cx, "q": question},
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def query(self, question: str) -> SourceResponse | None:
        try:
            data = await self._call_api(question)
            items = data.get("items", [])

            claims = [
                Claim(
                    text=item["snippet"],
                    confidence=0.6,
                    evidence=item["link"],
                )
                for item in items
                if "snippet" in item
            ]

            raw_text = "\n\n".join(
                f"**{item['title']}**\n{item.get('snippet', '')}\n{item['link']}"
                for item in items
            )

            return SourceResponse(
                source_name="google_search",
                raw_response=raw_text,
                claims=claims,
                confidence=0.6 if claims else 0.0,
                source_url="https://www.google.com/search?q=" + question.replace(" ", "+"),
            )
        except Exception:
            return None
