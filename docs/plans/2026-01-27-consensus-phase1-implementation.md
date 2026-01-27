# Consensus Engine — Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working end-to-end prototype where a user can ask a question, see a preliminary answer, watch a multi-AI debate unfold, and view the sealed consensus result.

**Architecture:** Next.js frontend with FastAPI backend. Supabase for database and auth. Redis + Celery for async orchestration. OpenRouter for multi-model AI access. WebSocket for real-time debate updates.

**Tech Stack:** Next.js 14 (TypeScript), FastAPI (Python 3.11+), Supabase (PostgreSQL), Redis, Celery, OpenRouter API

**Worktree:** `/Users/shaun/projects/coni/.worktrees/consensus-impl`

---

## Phase 1 Scope

Phase 1 delivers the core loop:
1. Ask a question via search box
2. Get a preliminary answer instantly
3. Watch AI debate unfold in real-time
4. View sealed consensus with full transparency

**Deferred to Phase 2:** Human participation (voting, contributing evidence), user auth, anti-gaming, SEO/ISR optimization, blockchain anchoring.

---

## Task 1: Backend Project Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "consensus-backend"
version = "0.1.0"
description = "Consensus Engine Backend"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Step 2: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
pydantic-settings==2.5.0
supabase==2.9.0
celery[redis]==5.4.0
redis==5.1.0
httpx==0.27.0
python-dotenv==1.0.1
websockets==13.0
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-httpx==0.32.0
```

**Step 3: Create .env.example**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
OPENROUTER_API_KEY=your-openrouter-key
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
```

**Step 4: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    openrouter_api_key: str
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    debate_max_rounds: int = 3
    consensus_threshold: float = 0.8

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 5: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="Consensus Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 6: Create __init__.py files**

Empty files for `backend/app/__init__.py` and `backend/app/core/__init__.py`.

**Step 7: Run the server to verify**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Visit http://localhost:8000/health → {"status": "ok"}
```

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with FastAPI, config, and health endpoint"
```

---

## Task 2: Database Schema (Supabase)

**Files:**
- Create: `database/schema.sql`
- Create: `database/seed/sample_data.sql`

**Step 1: Write the schema**

```sql
-- Questions table
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_questions_slug ON questions(slug);
CREATE INDEX idx_questions_text_search ON questions USING GIN (to_tsvector('english', text));

-- Answer versions (append-only)
CREATE TABLE answer_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id),
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'preliminary'
        CHECK (status IN ('preliminary', 'debating', 'consensus_reached', 'sealed', 'contested')),
    preliminary_answer TEXT,
    final_answer TEXT,
    confidence FLOAT,
    sealed_at TIMESTAMPTZ,
    seal_hash TEXT,
    previous_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(question_id, version)
);

CREATE INDEX idx_answer_versions_question ON answer_versions(question_id);
CREATE INDEX idx_answer_versions_status ON answer_versions(status);

-- Source responses (evidence from adapters)
CREATE TABLE source_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_version_id UUID NOT NULL REFERENCES answer_versions(id),
    source_name TEXT NOT NULL,
    raw_response TEXT NOT NULL,
    claims JSONB NOT NULL DEFAULT '[]',
    confidence FLOAT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_source_responses_answer ON source_responses(answer_version_id);

-- Debate rounds
CREATE TABLE debate_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_version_id UUID NOT NULL REFERENCES answer_versions(id),
    round_number INTEGER NOT NULL,
    phase TEXT NOT NULL
        CHECK (phase IN ('evidence_gathering', 'initial_positions', 'counterarguments', 'synthesis', 'convergence_check')),
    positions JSONB NOT NULL DEFAULT '[]',
    arguments JSONB NOT NULL DEFAULT '[]',
    synthesis JSONB,
    convergence_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(answer_version_id, round_number)
);

CREATE INDEX idx_debate_rounds_answer ON debate_rounds(answer_version_id);

-- Row-level security: sealed answer_versions cannot be updated
ALTER TABLE answer_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read answer versions"
    ON answer_versions FOR SELECT
    USING (true);

CREATE POLICY "Only non-sealed can be updated"
    ON answer_versions FOR UPDATE
    USING (status != 'sealed');

CREATE POLICY "Insert always allowed"
    ON answer_versions FOR INSERT
    WITH CHECK (true);
```

**Step 2: Write sample seed data**

```sql
INSERT INTO questions (id, slug, text) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'what-is-the-boiling-point-of-water', 'What is the boiling point of water at sea level?');

INSERT INTO answer_versions (id, question_id, version, status, final_answer, confidence) VALUES
    ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 1, 'sealed', 'The boiling point of water at sea level (1 atm) is 100 degrees Celsius (212 degrees Fahrenheit).', 0.99);
```

**Step 3: Commit**

```bash
git add database/
git commit -m "feat: add database schema for questions, answers, debates, and source responses"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/question.py`
- Create: `backend/app/schemas/answer.py`
- Create: `backend/app/schemas/debate.py`
- Create: `backend/app/schemas/source.py`

**Step 1: Create source schema**

```python
# backend/app/schemas/source.py
from pydantic import BaseModel


class Claim(BaseModel):
    text: str
    confidence: float
    evidence: str | None = None


class SourceResponse(BaseModel):
    source_name: str
    raw_response: str
    claims: list[Claim]
    confidence: float | None = None
    source_url: str | None = None
```

**Step 2: Create question schema**

```python
# backend/app/schemas/question.py
from pydantic import BaseModel
from datetime import datetime


class QuestionCreate(BaseModel):
    text: str


class QuestionResponse(BaseModel):
    id: str
    slug: str
    text: str
    created_at: datetime
```

**Step 3: Create answer schema**

```python
# backend/app/schemas/answer.py
from pydantic import BaseModel
from datetime import datetime

from app.schemas.source import SourceResponse


class AnswerVersionResponse(BaseModel):
    id: str
    question_id: str
    version: int
    status: str
    preliminary_answer: str | None = None
    final_answer: str | None = None
    confidence: float | None = None
    sealed_at: datetime | None = None
    seal_hash: str | None = None
    created_at: datetime
    sources: list[SourceResponse] = []
```

**Step 4: Create debate schema**

```python
# backend/app/schemas/debate.py
from pydantic import BaseModel
from datetime import datetime


class Position(BaseModel):
    stance: str
    supporting_sources: list[str]
    claims: list[str]


class Argument(BaseModel):
    source_name: str
    position: str
    argument: str
    evidence: list[str]


class DebateRoundResponse(BaseModel):
    id: str
    round_number: int
    phase: str
    positions: list[Position] = []
    arguments: list[Argument] = []
    synthesis: dict | None = None
    convergence_score: float | None = None
    created_at: datetime
```

**Step 5: Create __init__.py**

```python
# backend/app/schemas/__init__.py
```

**Step 6: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic schemas for questions, answers, debates, and sources"
```

---

## Task 4: Source Adapter Base + OpenRouter Adapter

**Files:**
- Create: `backend/app/adapters/__init__.py`
- Create: `backend/app/adapters/base.py`
- Create: `backend/app/adapters/openrouter.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_adapters/__init__.py`
- Create: `backend/tests/test_adapters/test_openrouter.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_adapters/test_openrouter.py
import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.openrouter import OpenRouterAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_openrouter_query_returns_source_response():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "The boiling point of water at sea level is 100°C (212°F). This is a well-established physical constant."
                }
            }
        ],
        "model": "anthropic/claude-3.5-sonnet",
        "usage": {"total_tokens": 50}
    }

    adapter = OpenRouterAdapter(
        api_key="test-key",
        model="anthropic/claude-3.5-sonnet"
    )

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_response):
        result = await adapter.query("What is the boiling point of water?")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "openrouter:anthropic/claude-3.5-sonnet"
    assert "100" in result.raw_response
    assert len(result.claims) > 0


@pytest.mark.asyncio
async def test_openrouter_query_handles_api_error():
    adapter = OpenRouterAdapter(api_key="test-key", model="anthropic/claude-3.5-sonnet")

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, side_effect=Exception("API Error")):
        result = await adapter.query("test question")

    assert result is None
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_adapters/test_openrouter.py -v
# Expected: FAIL — module not found
```

**Step 3: Write the base adapter**

```python
# backend/app/adapters/base.py
from abc import ABC, abstractmethod

from app.schemas.source import SourceResponse


class BaseAdapter(ABC):
    @abstractmethod
    async def query(self, question: str) -> SourceResponse | None:
        """Query this source with a question. Returns None on failure."""
        ...
```

**Step 4: Write the OpenRouter adapter**

```python
# backend/app/adapters/openrouter.py
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
```

**Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_adapters/test_openrouter.py -v
# Expected: 2 passed
```

**Step 6: Commit**

```bash
git add backend/app/adapters/ backend/tests/
git commit -m "feat: add base adapter interface and OpenRouter adapter with tests"
```

---

## Task 5: Google Search Adapter

**Files:**
- Create: `backend/app/adapters/google_search.py`
- Create: `backend/tests/test_adapters/test_google_search.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_adapters/test_google_search.py
import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.google_search import GoogleSearchAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_google_search_returns_source_response():
    mock_results = {
        "items": [
            {
                "title": "Boiling Point of Water",
                "snippet": "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
                "link": "https://example.com/boiling-point",
            },
            {
                "title": "Water Properties",
                "snippet": "The boiling point of pure water is 100°C or 212°F at 1 atmosphere.",
                "link": "https://example.com/water",
            },
        ]
    }

    adapter = GoogleSearchAdapter(api_key="test-key", cx="test-cx")

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_results):
        result = await adapter.query("What is the boiling point of water?")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "google_search"
    assert len(result.claims) == 2
    assert "100" in result.claims[0].text


@pytest.mark.asyncio
async def test_google_search_handles_no_results():
    adapter = GoogleSearchAdapter(api_key="test-key", cx="test-cx")

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value={"items": []}):
        result = await adapter.query("some obscure question")

    assert result is not None
    assert len(result.claims) == 0
```

**Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_adapters/test_google_search.py -v
# Expected: FAIL — module not found
```

**Step 3: Write the implementation**

```python
# backend/app/adapters/google_search.py
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
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_adapters/test_google_search.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/adapters/google_search.py backend/tests/test_adapters/test_google_search.py
git commit -m "feat: add Google Search adapter with tests"
```

---

## Task 6: Reddit + Stack Exchange Adapters

**Files:**
- Create: `backend/app/adapters/reddit.py`
- Create: `backend/app/adapters/stackexchange.py`
- Create: `backend/tests/test_adapters/test_reddit.py`
- Create: `backend/tests/test_adapters/test_stackexchange.py`

**Step 1: Write failing tests for Reddit**

```python
# backend/tests/test_adapters/test_reddit.py
import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.reddit import RedditAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_reddit_returns_source_response():
    mock_data = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "What is the boiling point of water?",
                        "selftext": "It's 100C at sea level.",
                        "score": 42,
                        "permalink": "/r/askscience/comments/abc/what_is_the_boiling_point/",
                    }
                }
            ]
        }
    }

    adapter = RedditAdapter()

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_data):
        result = await adapter.query("boiling point of water")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "reddit"
    assert len(result.claims) == 1
```

**Step 2: Write failing tests for Stack Exchange**

```python
# backend/tests/test_adapters/test_stackexchange.py
import pytest
from unittest.mock import AsyncMock, patch

from app.adapters.stackexchange import StackExchangeAdapter
from app.schemas.source import SourceResponse


@pytest.mark.asyncio
async def test_stackexchange_returns_source_response():
    mock_data = {
        "items": [
            {
                "title": "What is the boiling point of water?",
                "body": "Water boils at 100°C at 1 atm.",
                "score": 15,
                "is_accepted": True,
                "link": "https://stackoverflow.com/q/123",
            }
        ]
    }

    adapter = StackExchangeAdapter()

    with patch.object(adapter, "_call_api", new_callable=AsyncMock, return_value=mock_data):
        result = await adapter.query("boiling point of water")

    assert isinstance(result, SourceResponse)
    assert result.source_name == "stackexchange"
    assert len(result.claims) == 1
```

**Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_adapters/test_reddit.py tests/test_adapters/test_stackexchange.py -v
# Expected: FAIL
```

**Step 4: Implement Reddit adapter**

```python
# backend/app/adapters/reddit.py
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
```

**Step 5: Implement Stack Exchange adapter**

```python
# backend/app/adapters/stackexchange.py
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
```

**Step 6: Run all adapter tests**

```bash
cd backend && python -m pytest tests/test_adapters/ -v
# Expected: all passed
```

**Step 7: Commit**

```bash
git add backend/app/adapters/reddit.py backend/app/adapters/stackexchange.py backend/tests/test_adapters/
git commit -m "feat: add Reddit and Stack Exchange adapters with tests"
```

---

## Task 7: Orchestrator Service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/orchestrator.py`
- Create: `backend/tests/test_services/__init__.py`
- Create: `backend/tests/test_services/test_orchestrator.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.orchestrator import Orchestrator
from app.schemas.source import Claim, SourceResponse


def make_source_response(name: str, text: str) -> SourceResponse:
    return SourceResponse(
        source_name=name,
        raw_response=text,
        claims=[Claim(text=text, confidence=0.9, evidence=None)],
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_orchestrator_gathers_evidence_from_all_adapters():
    mock_adapters = [
        AsyncMock(query=AsyncMock(return_value=make_source_response("ai:claude", "100C"))),
        AsyncMock(query=AsyncMock(return_value=make_source_response("ai:gpt", "100 degrees C"))),
        AsyncMock(query=AsyncMock(return_value=make_source_response("google", "100°C at sea level"))),
    ]

    orchestrator = Orchestrator(adapters=mock_adapters)
    results = await orchestrator.gather_evidence("What is the boiling point of water?")

    assert len(results) == 3
    assert all(isinstance(r, SourceResponse) for r in results)


@pytest.mark.asyncio
async def test_orchestrator_skips_failed_adapters():
    mock_adapters = [
        AsyncMock(query=AsyncMock(return_value=make_source_response("ai:claude", "100C"))),
        AsyncMock(query=AsyncMock(return_value=None)),  # Failed adapter
    ]

    orchestrator = Orchestrator(adapters=mock_adapters)
    results = await orchestrator.gather_evidence("test question")

    assert len(results) == 1
```

**Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_services/test_orchestrator.py -v
# Expected: FAIL
```

**Step 3: Implement orchestrator**

```python
# backend/app/services/orchestrator.py
import asyncio

from app.adapters.base import BaseAdapter
from app.schemas.source import SourceResponse


class Orchestrator:
    def __init__(self, adapters: list[BaseAdapter]):
        self.adapters = adapters

    async def gather_evidence(self, question: str) -> list[SourceResponse]:
        tasks = [adapter.query(question) for adapter in self.adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        evidence = []
        for result in results:
            if isinstance(result, SourceResponse):
                evidence.append(result)
        return evidence
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_services/test_orchestrator.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_services/
git commit -m "feat: add orchestrator service for concurrent evidence gathering"
```

---

## Task 8: Debate Engine

**Files:**
- Create: `backend/app/services/debate_engine.py`
- Create: `backend/tests/test_services/test_debate_engine.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_debate_engine.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.debate_engine import DebateEngine
from app.schemas.source import Claim, SourceResponse


def make_evidence(name: str, claim_text: str, confidence: float = 0.9) -> SourceResponse:
    return SourceResponse(
        source_name=name,
        raw_response=claim_text,
        claims=[Claim(text=claim_text, confidence=confidence, evidence=None)],
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_debate_engine_clusters_positions():
    evidence = [
        make_evidence("ai:claude", "Water boils at 100°C at sea level"),
        make_evidence("ai:gpt", "The boiling point is 100 degrees Celsius at 1 atm"),
        make_evidence("google", "Water boils at 100°C (212°F) at standard pressure"),
    ]

    engine = DebateEngine(openrouter_api_key="test-key")

    mock_clustering = [
        {
            "stance": "Water boils at 100°C at sea level",
            "supporting_sources": ["ai:claude", "ai:gpt", "google"],
            "claims": [
                "Water boils at 100°C at sea level",
                "The boiling point is 100 degrees Celsius at 1 atm",
                "Water boils at 100°C (212°F) at standard pressure",
            ],
        }
    ]

    with patch.object(engine, "_cluster_positions", new_callable=AsyncMock, return_value=mock_clustering):
        positions = await engine.identify_positions(evidence)

    assert len(positions) == 1
    assert len(positions[0]["supporting_sources"]) == 3


@pytest.mark.asyncio
async def test_debate_engine_calculates_convergence():
    engine = DebateEngine(openrouter_api_key="test-key")

    # All sources agree — high convergence
    positions = [
        {
            "stance": "Water boils at 100°C",
            "supporting_sources": ["ai:claude", "ai:gpt", "google"],
            "claims": ["100°C"],
        }
    ]
    score = engine.calculate_convergence(positions, total_sources=3)
    assert score >= 0.9

    # Sources split — low convergence
    split_positions = [
        {"stance": "A", "supporting_sources": ["ai:claude"], "claims": ["A"]},
        {"stance": "B", "supporting_sources": ["ai:gpt"], "claims": ["B"]},
        {"stance": "C", "supporting_sources": ["google"], "claims": ["C"]},
    ]
    score = engine.calculate_convergence(split_positions, total_sources=3)
    assert score < 0.5
```

**Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_services/test_debate_engine.py -v
# Expected: FAIL
```

**Step 3: Implement debate engine**

```python
# backend/app/services/debate_engine.py
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
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_services/test_debate_engine.py -v
# Expected: 2 passed
```

**Step 5: Commit**

```bash
git add backend/app/services/debate_engine.py backend/tests/test_services/test_debate_engine.py
git commit -m "feat: add debate engine with position clustering, counterarguments, and convergence scoring"
```

---

## Task 9: Seal Service (Cryptographic Immutability)

**Files:**
- Create: `backend/app/services/seal.py`
- Create: `backend/tests/test_services/test_seal.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_seal.py
import pytest
from app.services.seal import SealService


def test_seal_generates_deterministic_hash():
    service = SealService()
    data = {
        "question": "What is the boiling point of water?",
        "answer": "100°C at sea level",
        "debate_transcript": [{"round": 1, "content": "all agree"}],
        "sources": ["claude", "gpt"],
        "timestamp": "2026-01-27T12:00:00Z",
    }

    hash1 = service.generate_hash(data)
    hash2 = service.generate_hash(data)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest


def test_seal_chain_includes_previous_hash():
    service = SealService()
    data1 = {"question": "Q1", "answer": "A1", "timestamp": "2026-01-27T12:00:00Z"}
    hash1 = service.generate_hash(data1)

    data2 = {"question": "Q2", "answer": "A2", "timestamp": "2026-01-27T13:00:00Z"}
    hash2 = service.generate_hash(data2, previous_hash=hash1)

    # Hash should be different with vs without previous hash
    hash2_no_chain = service.generate_hash(data2)
    assert hash2 != hash2_no_chain


def test_seal_verify_detects_tampering():
    service = SealService()
    data = {"question": "Q1", "answer": "A1", "timestamp": "2026-01-27T12:00:00Z"}
    original_hash = service.generate_hash(data)

    assert service.verify(data, original_hash) is True

    # Tamper with data
    data["answer"] = "TAMPERED"
    assert service.verify(data, original_hash) is False
```

**Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_services/test_seal.py -v
# Expected: FAIL
```

**Step 3: Implement seal service**

```python
# backend/app/services/seal.py
import hashlib
import json


class SealService:
    def generate_hash(self, data: dict, previous_hash: str | None = None) -> str:
        payload = json.dumps(data, sort_keys=True, ensure_ascii=True)
        if previous_hash:
            payload = previous_hash + payload
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def verify(self, data: dict, expected_hash: str, previous_hash: str | None = None) -> bool:
        actual_hash = self.generate_hash(data, previous_hash)
        return actual_hash == expected_hash
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_services/test_seal.py -v
# Expected: 3 passed
```

**Step 5: Commit**

```bash
git add backend/app/services/seal.py backend/tests/test_services/test_seal.py
git commit -m "feat: add seal service for cryptographic hashing and verification"
```

---

## Task 10: Question API Endpoints

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/questions.py`
- Create: `backend/app/core/database.py`
- Modify: `backend/app/main.py` (add router)
- Create: `backend/tests/test_api/__init__.py`
- Create: `backend/tests/test_api/test_questions.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_api/test_questions.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_question():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.text_search.return_value.execute.return_value.data = []
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [
        {
            "id": "test-uuid",
            "slug": "what-is-the-boiling-point-of-water",
            "text": "What is the boiling point of water?",
            "created_at": "2026-01-27T12:00:00Z",
        }
    ]

    with patch("app.api.questions.get_db", return_value=mock_db):
        with patch("app.api.questions.trigger_pipeline") as mock_trigger:
            response = client.post(
                "/api/questions",
                json={"text": "What is the boiling point of water?"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "what-is-the-boiling-point-of-water"
    mock_trigger.assert_called_once()


def test_get_question_by_slug():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "test-uuid",
            "slug": "what-is-the-boiling-point-of-water",
            "text": "What is the boiling point of water?",
            "created_at": "2026-01-27T12:00:00Z",
        }
    ]

    with patch("app.api.questions.get_db", return_value=mock_db):
        response = client.get("/api/questions/what-is-the-boiling-point-of-water")

    assert response.status_code == 200
    assert response.json()["text"] == "What is the boiling point of water?"
```

**Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_questions.py -v
# Expected: FAIL
```

**Step 3: Create database helper**

```python
# backend/app/core/database.py
from supabase import create_client

from app.core.config import settings


def get_db():
    return create_client(settings.supabase_url, settings.supabase_service_key)
```

**Step 4: Create questions API**

```python
# backend/app/api/questions.py
import re

from fastapi import APIRouter, HTTPException

from app.core.database import get_db
from app.schemas.question import QuestionCreate, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:200].strip("-")


def trigger_pipeline(question_id: str, question_text: str):
    # TODO: Task 11 — trigger Celery task
    pass


@router.post("", status_code=201, response_model=QuestionResponse)
async def submit_question(question: QuestionCreate):
    db = get_db()

    # Check for existing similar question
    existing = (
        db.table("questions")
        .select("*")
        .text_search("text", question.text)
        .execute()
    )
    if existing.data:
        return QuestionResponse(**existing.data[0])

    # Create new question
    slug = slugify(question.text)
    result = (
        db.table("questions")
        .insert({"text": question.text, "slug": slug})
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create question")

    q = result.data[0]
    trigger_pipeline(q["id"], q["text"])
    return QuestionResponse(**q)


@router.get("/{slug}", response_model=QuestionResponse)
async def get_question(slug: str):
    db = get_db()
    result = db.table("questions").select("*").eq("slug", slug).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionResponse(**result.data[0])
```

**Step 5: Register router in main.py**

Add to `backend/app/main.py` after the CORS middleware:

```python
from app.api.questions import router as questions_router

app.include_router(questions_router)
```

**Step 6: Run tests**

```bash
cd backend && python -m pytest tests/test_api/test_questions.py -v
# Expected: 3 passed
```

**Step 7: Commit**

```bash
git add backend/app/api/ backend/app/core/database.py backend/tests/test_api/
git commit -m "feat: add question API endpoints (submit, get by slug, text search)"
```

---

## Task 11: Celery Pipeline Worker

**Files:**
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/celery_app.py`
- Create: `backend/app/workers/pipeline.py`
- Modify: `backend/app/api/questions.py` (wire trigger_pipeline)

**Step 1: Create Celery app**

```python
# backend/app/workers/celery_app.py
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "consensus",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)
```

**Step 2: Create pipeline task**

```python
# backend/app/workers/pipeline.py
import asyncio

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_db
from app.adapters.openrouter import OpenRouterAdapter
from app.adapters.google_search import GoogleSearchAdapter
from app.adapters.reddit import RedditAdapter
from app.adapters.stackexchange import StackExchangeAdapter
from app.services.orchestrator import Orchestrator
from app.services.debate_engine import DebateEngine
from app.services.seal import SealService


def _build_adapters() -> list:
    adapters = []
    models = [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "google/gemini-pro-1.5",
    ]
    for model in models:
        adapters.append(OpenRouterAdapter(api_key=settings.openrouter_api_key, model=model))
    adapters.append(RedditAdapter())
    adapters.append(StackExchangeAdapter())
    return adapters


async def _run_pipeline(question_id: str, question_text: str):
    db = get_db()

    # Create preliminary answer version
    version_result = db.table("answer_versions").insert({
        "question_id": question_id,
        "version": 1,
        "status": "preliminary",
    }).execute()
    version_id = version_result.data[0]["id"]

    # Get quick preliminary answer
    preliminary_adapter = OpenRouterAdapter(
        api_key=settings.openrouter_api_key,
        model="anthropic/claude-3.5-sonnet",
    )
    prelim_response = await preliminary_adapter.query(question_text)
    if prelim_response:
        db.table("answer_versions").update({
            "preliminary_answer": prelim_response.raw_response,
        }).eq("id", version_id).execute()

    # Update status to debating
    db.table("answer_versions").update({"status": "debating"}).eq("id", version_id).execute()

    # Phase 1: Gather evidence from all sources
    orchestrator = Orchestrator(adapters=_build_adapters())
    evidence = await orchestrator.gather_evidence(question_text)

    # Store source responses
    for e in evidence:
        db.table("source_responses").insert({
            "answer_version_id": version_id,
            "source_name": e.source_name,
            "raw_response": e.raw_response,
            "claims": [c.model_dump() for c in e.claims],
            "confidence": e.confidence,
            "source_url": e.source_url,
        }).execute()

    # Phase 2-4: Run debate
    debate = DebateEngine(openrouter_api_key=settings.openrouter_api_key)
    positions = await debate.identify_positions(evidence)

    all_arguments = []
    convergence_score = debate.calculate_convergence(positions, len(evidence))

    for round_num in range(1, settings.debate_max_rounds + 1):
        if convergence_score >= settings.consensus_threshold:
            break

        arguments = await debate.run_counterarguments(positions, round_num)
        all_arguments.append(arguments)

        db.table("debate_rounds").insert({
            "answer_version_id": version_id,
            "round_number": round_num,
            "phase": "counterarguments",
            "positions": positions,
            "arguments": arguments,
            "convergence_score": convergence_score,
        }).execute()

        # Re-evaluate positions after counterarguments
        positions = await debate.identify_positions(evidence)
        convergence_score = debate.calculate_convergence(positions, len(evidence))

    # Phase 4: Synthesize
    synthesis = await debate.synthesize(positions, all_arguments)

    db.table("debate_rounds").insert({
        "answer_version_id": version_id,
        "round_number": settings.debate_max_rounds + 1,
        "phase": "synthesis",
        "positions": positions,
        "arguments": [],
        "synthesis": synthesis,
        "convergence_score": convergence_score,
    }).execute()

    # Determine final status
    final_status = "consensus_reached" if convergence_score >= settings.consensus_threshold else "contested"

    # Seal the answer
    seal_service = SealService()
    seal_data = {
        "question_id": question_id,
        "question_text": question_text,
        "final_answer": synthesis.get("final_answer", ""),
        "confidence": synthesis.get("confidence", convergence_score),
        "positions": positions,
        "evidence_count": len(evidence),
    }

    # Get previous hash for chain
    prev = db.table("answer_versions").select("seal_hash").eq(
        "status", "sealed"
    ).order("sealed_at", desc=True).limit(1).execute()
    previous_hash = prev.data[0]["seal_hash"] if prev.data else None

    seal_hash = seal_service.generate_hash(seal_data, previous_hash=previous_hash)

    db.table("answer_versions").update({
        "status": final_status,
        "final_answer": synthesis.get("final_answer", ""),
        "confidence": synthesis.get("confidence", convergence_score),
        "sealed_at": "now()",
        "seal_hash": seal_hash,
        "previous_hash": previous_hash,
    }).eq("id", version_id).execute()


@celery_app.task(name="consensus.pipeline")
def run_pipeline_task(question_id: str, question_text: str):
    asyncio.run(_run_pipeline(question_id, question_text))
```

**Step 3: Wire trigger_pipeline in questions.py**

Replace the `trigger_pipeline` function in `backend/app/api/questions.py`:

```python
def trigger_pipeline(question_id: str, question_text: str):
    from app.workers.pipeline import run_pipeline_task
    run_pipeline_task.delay(question_id, question_text)
```

**Step 4: Commit**

```bash
git add backend/app/workers/ backend/app/api/questions.py
git commit -m "feat: add Celery pipeline worker for end-to-end question processing"
```

---

## Task 12: Answer & Debate API Endpoints

**Files:**
- Create: `backend/app/api/answers.py`
- Modify: `backend/app/main.py` (add router)
- Create: `backend/tests/test_api/test_answers.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_api/test_answers.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_answer_for_question():
    mock_db = MagicMock()

    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": "v1",
            "question_id": "q1",
            "version": 1,
            "status": "sealed",
            "preliminary_answer": "Quick answer",
            "final_answer": "Full consensus answer",
            "confidence": 0.95,
            "sealed_at": "2026-01-27T12:00:00Z",
            "seal_hash": "abc123",
            "created_at": "2026-01-27T11:00:00Z",
        }
    ]

    with patch("app.api.answers.get_db", return_value=mock_db):
        response = client.get("/api/answers/q1")

    assert response.status_code == 200
    assert response.json()["status"] == "sealed"
    assert response.json()["final_answer"] == "Full consensus answer"


def test_get_debate_rounds():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {
            "id": "r1",
            "round_number": 1,
            "phase": "counterarguments",
            "positions": [],
            "arguments": [],
            "synthesis": None,
            "convergence_score": 0.7,
            "created_at": "2026-01-27T11:30:00Z",
        }
    ]

    with patch("app.api.answers.get_db", return_value=mock_db):
        response = client.get("/api/answers/v1/debate")

    assert response.status_code == 200
    assert len(response.json()) == 1
```

**Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_api/test_answers.py -v
```

**Step 3: Implement answers API**

```python
# backend/app/api/answers.py
from fastapi import APIRouter, HTTPException

from app.core.database import get_db
from app.schemas.answer import AnswerVersionResponse
from app.schemas.debate import DebateRoundResponse

router = APIRouter(prefix="/api/answers", tags=["answers"])


@router.get("/{question_id}", response_model=AnswerVersionResponse)
async def get_latest_answer(question_id: str):
    db = get_db()
    result = (
        db.table("answer_versions")
        .select("*")
        .eq("question_id", question_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No answer found")
    return AnswerVersionResponse(**result.data[0])


@router.get("/{version_id}/debate", response_model=list[DebateRoundResponse])
async def get_debate_rounds(version_id: str):
    db = get_db()
    result = (
        db.table("debate_rounds")
        .select("*")
        .eq("answer_version_id", version_id)
        .order("round_number")
        .execute()
    )
    return [DebateRoundResponse(**r) for r in result.data]


@router.get("/{version_id}/sources")
async def get_sources(version_id: str):
    db = get_db()
    result = (
        db.table("source_responses")
        .select("*")
        .eq("answer_version_id", version_id)
        .execute()
    )
    return result.data


@router.get("/{question_id}/history", response_model=list[AnswerVersionResponse])
async def get_answer_history(question_id: str):
    db = get_db()
    result = (
        db.table("answer_versions")
        .select("*")
        .eq("question_id", question_id)
        .order("version")
        .execute()
    )
    return [AnswerVersionResponse(**r) for r in result.data]
```

**Step 4: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.api.answers import router as answers_router

app.include_router(answers_router)
```

**Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_api/ -v
# Expected: all passed
```

**Step 6: Commit**

```bash
git add backend/app/api/answers.py backend/tests/test_api/test_answers.py backend/app/main.py
git commit -m "feat: add answer and debate API endpoints"
```

---

## Task 13: Frontend Scaffold (Next.js)

**Files:**
- Create: `frontend/` (via create-next-app)
- Modify: `frontend/src/app/page.tsx` (homepage with search box)
- Create: `frontend/src/lib/api.ts`

**Step 1: Scaffold Next.js project**

```bash
cd /Users/shaun/projects/coni/.worktrees/consensus-impl
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

Accept defaults when prompted.

**Step 2: Create API client**

```typescript
// frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function submitQuestion(text: string) {
  const res = await fetch(`${API_BASE}/api/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("Failed to submit question");
  return res.json();
}

export async function getQuestion(slug: string) {
  const res = await fetch(`${API_BASE}/api/questions/${slug}`);
  if (!res.ok) throw new Error("Question not found");
  return res.json();
}

export async function getLatestAnswer(questionId: string) {
  const res = await fetch(`${API_BASE}/api/answers/${questionId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getDebateRounds(versionId: string) {
  const res = await fetch(`${API_BASE}/api/answers/${versionId}/debate`);
  if (!res.ok) return [];
  return res.json();
}

export async function getSources(versionId: string) {
  const res = await fetch(`${API_BASE}/api/answers/${versionId}/sources`);
  if (!res.ok) return [];
  return res.json();
}
```

**Step 3: Create homepage with search box**

```tsx
// frontend/src/app/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitQuestion } from "@/lib/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const question = await submitQuestion(query);
      router.push(`/q/${question.slug}`);
    } catch (err) {
      console.error("Failed to submit question:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-white">
      <div className="text-center mb-12">
        <h1 className="text-6xl font-bold text-gray-900 mb-4">Consensus</h1>
        <p className="text-xl text-gray-500">
          Humanity&apos;s Knowledge, Verified
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-2xl px-4">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
            className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-full
                       focus:outline-none focus:border-blue-500 text-gray-900
                       placeholder-gray-400 shadow-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2
                       bg-blue-600 text-white rounded-full hover:bg-blue-700
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? "Asking..." : "Ask"}
          </button>
        </div>
      </form>
    </main>
  );
}
```

**Step 4: Add environment variable**

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 5: Verify it runs**

```bash
cd frontend && npm run dev
# Visit http://localhost:3000 — should see search box
```

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with homepage search box and API client"
```

---

## Task 14: Answer Page

**Files:**
- Create: `frontend/src/app/q/[slug]/page.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/DebateTimeline.tsx`
- Create: `frontend/src/components/SourcesPanel.tsx`

**Step 1: Create StatusBadge component**

```tsx
// frontend/src/components/StatusBadge.tsx
const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  preliminary: { label: "Preliminary", color: "bg-yellow-100 text-yellow-800" },
  debating: { label: "Debating", color: "bg-blue-100 text-blue-800" },
  consensus_reached: { label: "Consensus Reached", color: "bg-green-100 text-green-800" },
  sealed: { label: "Sealed", color: "bg-purple-100 text-purple-800" },
  contested: { label: "Contested", color: "bg-red-100 text-red-800" },
};

export default function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || { label: status, color: "bg-gray-100 text-gray-800" };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}
```

**Step 2: Create SourcesPanel component**

```tsx
// frontend/src/components/SourcesPanel.tsx
interface Source {
  source_name: string;
  raw_response: string;
  confidence: number | null;
  source_url: string | null;
}

export default function SourcesPanel({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3">Sources ({sources.length})</h3>
      <div className="space-y-3">
        {sources.map((source, i) => (
          <div key={i} className="border-l-2 border-gray-200 pl-3">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{source.source_name}</span>
              {source.confidence !== null && (
                <span className="text-xs text-gray-500">
                  {Math.round(source.confidence * 100)}% confidence
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 mt-1 line-clamp-3">
              {source.raw_response}
            </p>
            {source.source_url && (
              <a
                href={source.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                View source
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 3: Create DebateTimeline component**

```tsx
// frontend/src/components/DebateTimeline.tsx
interface DebateRound {
  round_number: number;
  phase: string;
  positions: { stance: string; supporting_sources: string[] }[];
  arguments: { source_name: string; argument: string }[];
  synthesis: { final_answer: string; confidence: number } | null;
  convergence_score: number | null;
}

export default function DebateTimeline({ rounds }: { rounds: DebateRound[] }) {
  if (!rounds.length) return null;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3">Debate Timeline</h3>
      <div className="space-y-4">
        {rounds.map((round) => (
          <details key={round.round_number} className="border rounded p-3">
            <summary className="cursor-pointer font-medium">
              Round {round.round_number} — {round.phase}
              {round.convergence_score !== null && (
                <span className="ml-2 text-sm text-gray-500">
                  ({Math.round(round.convergence_score * 100)}% convergence)
                </span>
              )}
            </summary>
            <div className="mt-3 space-y-2">
              {round.positions.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Positions:</h4>
                  {round.positions.map((pos, i) => (
                    <div key={i} className="ml-3 text-sm text-gray-600">
                      <strong>{pos.stance}</strong>
                      <span className="text-xs text-gray-400 ml-1">
                        ({pos.supporting_sources.join(", ")})
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {round.arguments.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Arguments:</h4>
                  {round.arguments.map((arg, i) => (
                    <div key={i} className="ml-3 text-sm text-gray-600">
                      <strong>{arg.source_name}:</strong> {arg.argument}
                    </div>
                  ))}
                </div>
              )}
              {round.synthesis && (
                <div className="bg-green-50 rounded p-2">
                  <h4 className="text-sm font-medium text-green-800">Synthesis:</h4>
                  <p className="text-sm text-green-700">{round.synthesis.final_answer}</p>
                </div>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
```

**Step 4: Create answer page**

```tsx
// frontend/src/app/q/[slug]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getQuestion, getLatestAnswer, getDebateRounds, getSources } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import DebateTimeline from "@/components/DebateTimeline";
import SourcesPanel from "@/components/SourcesPanel";

export default function AnswerPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [question, setQuestion] = useState<any>(null);
  const [answer, setAnswer] = useState<any>(null);
  const [rounds, setRounds] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const q = await getQuestion(slug);
        setQuestion(q);

        const a = await getLatestAnswer(q.id);
        if (a) {
          setAnswer(a);
          const [r, s] = await Promise.all([
            getDebateRounds(a.id),
            getSources(a.id),
          ]);
          setRounds(r);
          setSources(s);
        }
      } catch (err) {
        setError("Failed to load question");
      }
    }
    load();
  }, [slug]);

  // Poll for updates while debating
  useEffect(() => {
    if (!answer || !["preliminary", "debating"].includes(answer.status)) return;

    const interval = setInterval(async () => {
      if (!question) return;
      const a = await getLatestAnswer(question.id);
      if (a) {
        setAnswer(a);
        const [r, s] = await Promise.all([
          getDebateRounds(a.id),
          getSources(a.id),
        ]);
        setRounds(r);
        setSources(s);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [answer, question]);

  if (error) return <div className="p-8 text-red-600">{error}</div>;
  if (!question) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">{question.text}</h1>

      {answer && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <StatusBadge status={answer.status} />
            {answer.confidence !== null && (
              <div className="flex items-center gap-2">
                <div className="w-32 h-2 bg-gray-200 rounded-full">
                  <div
                    className="h-2 bg-green-500 rounded-full"
                    style={{ width: `${answer.confidence * 100}%` }}
                  />
                </div>
                <span className="text-sm text-gray-500">
                  {Math.round(answer.confidence * 100)}%
                </span>
              </div>
            )}
          </div>

          <div className="bg-gray-50 rounded-lg p-6">
            <p className="text-lg text-gray-800">
              {answer.final_answer || answer.preliminary_answer || "Awaiting response..."}
            </p>
          </div>

          {answer.seal_hash && (
            <div className="text-xs text-gray-400 font-mono break-all">
              Seal: {answer.seal_hash}
            </div>
          )}

          <DebateTimeline rounds={rounds} />
          <SourcesPanel sources={sources} />
        </div>
      )}

      {!answer && (
        <div className="text-gray-500">Processing your question...</div>
      )}
    </main>
  );
}
```

**Step 5: Verify it runs**

```bash
cd frontend && npm run dev
# Visit http://localhost:3000/q/test-slug — should render (with API errors expected)
```

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add answer page with status badge, debate timeline, and sources panel"
```

---

## Task 15: Docker Compose for Local Development

**Files:**
- Create: `docker-compose.yml`

**Step 1: Create docker-compose.yml**

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file:
      - ./backend/.env
    depends_on:
      - redis
    command: celery -A app.workers.celery_app worker --loglevel=info
    volumes:
      - ./backend:/app

volumes:
  redis_data:
```

**Step 2: Create backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Commit**

```bash
git add docker-compose.yml backend/Dockerfile
git commit -m "feat: add Docker Compose for local dev (Redis, backend, Celery worker)"
```

---

## Task 16: Run All Tests & Verify

**Step 1: Run full backend test suite**

```bash
cd backend && python -m pytest tests/ -v
# Expected: all tests pass
```

**Step 2: Run frontend build check**

```bash
cd frontend && npm run build
# Expected: build succeeds
```

**Step 3: If all pass, commit any remaining changes and tag**

```bash
git tag v0.1.0-phase1
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | Backend scaffold | FastAPI, config, health endpoint |
| 2 | Database schema | Questions, answers, debates, sources, RLS |
| 3 | Pydantic schemas | Request/response models |
| 4 | OpenRouter adapter | Multi-model AI integration + tests |
| 5 | Google Search adapter | Web search integration + tests |
| 6 | Reddit + Stack Exchange | Community platform adapters + tests |
| 7 | Orchestrator | Concurrent evidence gathering + tests |
| 8 | Debate engine | Position clustering, counterarguments, synthesis + tests |
| 9 | Seal service | SHA-256 hashing, chain, verification + tests |
| 10 | Question API | Submit and retrieve questions + tests |
| 11 | Celery pipeline | End-to-end async question processing |
| 12 | Answer API | Retrieve answers, debates, sources + tests |
| 13 | Frontend scaffold | Next.js, homepage, search box, API client |
| 14 | Answer page | Status badge, debate timeline, sources panel |
| 15 | Docker Compose | Local dev environment |
| 16 | Full verification | Run all tests, build check, tag release |

**Phase 2 (next):** User auth, human participation (voting, evidence), WebSocket real-time updates, ISR/SEO, anti-gaming measures.
