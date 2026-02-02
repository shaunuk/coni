import json
from typing import Optional

import httpx

from app.adapters.base import BaseAdapter, StreamingCallback
from app.schemas.source import Claim, SourceResponse


class OpenRouterAdapter(BaseAdapter):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self._system_prompt = (
            "You are a knowledge source participating in a consensus engine. "
            "Answer the question factually. After your answer, list your key claims "
            "as a JSON array under the heading CLAIMS: where each claim is an object "
            'with "text" (string), "confidence" (float 0-1), and "evidence" (string or null).'
        )

    @property
    def source_name(self) -> str:
        # Extract friendly name from model path
        model_lower = self.model.lower()
        if "claude-3-haiku" in model_lower:
            return "Claude Haiku"
        elif "claude-3.5-sonnet" in model_lower:
            return "Claude Sonnet"
        elif "gpt-4o-mini" in model_lower:
            return "GPT-4o Mini"
        elif "gpt-4o" in model_lower:
            return "GPT-4o"
        elif "gemini-flash" in model_lower:
            return "Gemini Flash"
        elif "gemini-pro" in model_lower:
            return "Gemini Pro"
        elif "llama" in model_lower:
            return "Llama 3.1"
        elif "mistral" in model_lower:
            return "Mistral"
        return self.model.split("/")[-1]

    @property
    def supports_streaming(self) -> bool:
        """OpenRouter supports streaming via SSE."""
        return True

    async def _call_api(self, question: str, stream: bool = False) -> dict:
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
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": question},
                    ],
                    "stream": stream,
                },
                timeout=60.0 if stream else 30.0,
            )
            response.raise_for_status()
            return response.json()

    async def _call_api_streaming(
        self,
        question: str,
        on_token: Optional[StreamingCallback] = None,
    ) -> str:
        """
        Call the OpenRouter API with streaming enabled.

        Yields tokens as they arrive via SSE and returns the complete response.
        """
        accumulated_content = ""

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": question},
                    ],
                    "stream": True,
                },
                timeout=120.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    # SSE format: "data: {...}" or "data: [DONE]"
                    if not line:
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str.strip() == "[DONE]":
                            # Stream complete, emit final callback
                            if on_token:
                                await on_token(
                                    self.source_name,
                                    accumulated_content,
                                    True,  # is_complete
                                )
                            break

                        try:
                            data = json.loads(data_str)
                            # Extract the delta content
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    accumulated_content += content

                                    # Emit streaming callback
                                    if on_token:
                                        await on_token(
                                            self.source_name,
                                            accumulated_content,
                                            False,  # is_complete
                                        )
                        except json.JSONDecodeError:
                            # Skip malformed JSON lines
                            continue

        return accumulated_content

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

    async def query_streaming(
        self,
        question: str,
        on_token: Optional[StreamingCallback] = None,
    ) -> SourceResponse | None:
        """
        Query OpenRouter with streaming support.

        Streams tokens via SSE and calls on_token callback for each chunk.
        Returns the complete SourceResponse when finished.
        """
        try:
            content = await self._call_api_streaming(question, on_token)
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
