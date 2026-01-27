import json
import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


class OpenRouterAdapter(BaseAdapter):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def _call_api(self, question: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a knowledge source participating in a consensus engine. "
                                "Answer the question factually. After your answer, list your key claims "
                                "as a JSON array under the heading CLAIMS: where each claim is an object "
                                'with "text" (string), "confidence" (float 0-1), and "evidence" (string or null).'
                            ),
                        },
                        {"role": "user", "content": question},
                    ],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def _parse_claims(self, content: str) -> list[Claim]:
        try:
            claims_marker = "CLAIMS:"
            if claims_marker in content:
                claims_text = content.split(claims_marker, 1)[1].strip()
                # Find JSON array
                start = claims_text.index("[")
                end = claims_text.rindex("]") + 1
                claims_data = json.loads(claims_text[start:end])
                return [Claim(**c) for c in claims_data]
        except (ValueError, json.JSONDecodeError, IndexError):
            pass
        # Fallback: treat entire response as single claim
        return [Claim(text=content[:500], confidence=0.5, evidence=None)]

    async def query(self, question: str) -> SourceResponse | None:
        try:
            response = await self._call_api(question)
            content = response["choices"][0]["message"]["content"]
            claims = self._parse_claims(content)
            return SourceResponse(
                source_name=f"openrouter:{self.model}",
                raw_response=content,
                claims=claims,
                confidence=sum(c.confidence for c in claims) / len(claims) if claims else 0.0,
                source_url=None,
            )
        except Exception:
            return None
