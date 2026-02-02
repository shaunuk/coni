import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


class WikipediaAdapter(BaseAdapter):
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"

    @property
    def source_name(self) -> str:
        return "Wikipedia"

    async def _search(self, query: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 5,
                    "format": "json",
                },
                headers={"User-Agent": "ConsensusEngine/1.0 (https://consensus.ai)"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("query", {}).get("search", [])

    async def _get_extract(self, title: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "format": "json",
                },
                headers={"User-Agent": "ConsensusEngine/1.0 (https://consensus.ai)"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                return page.get("extract", "")
            return ""

    async def query(self, question: str) -> SourceResponse | None:
        try:
            results = await self._search(question)
            if not results:
                return None

            claims = []
            raw_parts = []

            for result in results[:3]:
                title = result.get("title", "")
                snippet = result.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")

                # Get full extract for top result
                extract = ""
                if len(claims) == 0:
                    extract = await self._get_extract(title)

                text = extract if extract else snippet
                if text:
                    claims.append(Claim(
                        text=text[:500],
                        confidence=0.8,  # Wikipedia is generally reliable
                        evidence=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    ))
                    raw_parts.append(f"**{title}**\n{text[:300]}")

            if not claims:
                return None

            return SourceResponse(
                source_name="wikipedia",
                raw_response="\n\n".join(raw_parts),
                claims=claims,
                confidence=0.8,
                source_url=f"https://en.wikipedia.org/w/index.php?search={question.replace(' ', '+')}",
            )
        except Exception:
            return None
