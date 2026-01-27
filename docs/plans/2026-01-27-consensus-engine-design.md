# Consensus Engine — Design Document

**Date:** 2026-01-27
**Status:** Approved
**Working Name:** Consensus

## Vision

Consensus is a global knowledge engine where questions are answered through multi-source AI debate, human participation, and evidence-based convergence. Every finalized answer is cryptographically locked in time, creating an immutable record of what humanity agreed was true at that moment.

The system combats misinformation by replacing editorial authority with transparent, auditable consensus. Answers cannot be silently changed — only versioned with full history preserved.

## Core User Flow

1. User types a question into a central search box
2. System checks for existing consensus on this question (semantic match) — if found, display immediately as a static page
3. If no existing consensus, return a **preliminary answer** within seconds (fast AI call) with a "Preliminary — consensus in progress" status badge
4. Backend fans out to 8-10+ sources concurrently: multiple AI models (via OpenRouter), Google Search, Reddit, Quora, Stack Exchange
5. Evidence is gathered, an AI debate process runs in structured rounds, and the answer page updates live via WebSocket
6. Any registered user can join the debate, add evidence, or vote
7. Once convergence criteria are met (or a human moderator closes the topic), the answer is finalized and cryptographically sealed
8. The full debate transcript, all sources, votes, and the decision trail are permanently visible

**Answer states:** `preliminary` → `debating` → `consensus reached` → `sealed`

A sealed answer can be `reopened` if new evidence warrants it, creating a new version while preserving the original.

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Next.js + TypeScript | SSR for SEO, ISR for static answer pages, WebSocket support |
| Backend | Python + FastAPI | Async support, AI/ML ecosystem, clean API design |
| Database | Supabase (PostgreSQL) | Managed, real-time subscriptions, row-level security, JSONB for flexible debate data |
| Queue | Redis + Celery | Fan-out orchestration for concurrent source queries |
| Real-time | WebSocket (Supabase real-time + backend) | Live debate updates to the frontend |
| AI Models | OpenRouter | Single integration for Claude, GPT, Gemini, Llama, Mistral, etc. |
| Hosting (frontend) | Vercel or Cloudflare Pages | CDN-served static pages, edge rendering |
| Hosting (backend) | Independently deployed | Celery workers scale based on debate workload |

## Architecture

### System Components

**Frontend (Next.js + TypeScript):**
- Single-page search interface with central search box
- Answer pages with live-updating debate view (WebSocket)
- Status badges showing answer state
- Debate participation panel for registered users
- Full transparency view: every source, every AI response, every vote, the complete decision trail
- ISR (Incremental Static Regeneration) for sealed answers — served as static files from CDN

**Backend (FastAPI + Python):**
- **Query API** — Receives questions, checks for existing consensus, triggers the pipeline
- **Orchestrator** — Fans out source queries concurrently via Celery + Redis
- **Source adapters** — Pluggable modules for each source (see Source Adapters section)
- **Debate engine** — Manages structured debate rounds
- **Consensus evaluator** — Determines convergence based on agreement thresholds and evidence quality
- **Seal service** — Cryptographic hashing and immutability enforcement

**Database (Supabase / PostgreSQL):**
- Questions, answers, debate rounds, votes, user accounts
- Append-only audit tables — finalized records are never updated, only new versions created
- Full-text search for semantic question matching
- Row-level security policies enforcing immutability on sealed records

**Infrastructure:**
- Redis for task queue and pub/sub
- Celery workers scaled independently from the web layer

### Traffic Split

- ~95% of traffic (reading sealed answers) → static files from CDN, near-zero server cost
- ~5% of traffic (active debates, participation) → SSR + WebSocket, hits the backend

## The Debate Engine

### Phase 1 — Evidence Gathering (concurrent)

All source adapters fire simultaneously. Each returns structured data: the answer/claim, supporting evidence, confidence level, and source citation.

### Phase 2 — Initial Positions

The system clusters responses by stance. For factual questions where sources converge immediately, the debate is short. For contested topics, distinct positions emerge and are labeled (e.g., "Position A: supported by Claude, GPT, 3 Reddit threads" vs "Position B: supported by Gemini, 2 Quora answers").

### Phase 3 — Counterarguments

AI models are shown opposing positions and asked to critique them with evidence. This runs for a configurable number of rounds (default: 3). Each round's arguments are stored and visible to users.

### Phase 4 — Synthesis & Scoring

The system produces a synthesis mapping:
- Areas of agreement
- Areas of disagreement with the strength of each side
- Overall confidence level

Each claim is scored by:
- Number of independent sources corroborating it
- Quality/reliability of sources
- Strength of evidence cited
- Human votes (if any have come in)

### Phase 5 — Convergence Check

Consensus is reached when:
- Agreement across sources exceeds a threshold (e.g., 80%), OR
- A human moderator closes the debate, OR
- Maximum rounds are exhausted (answer marked as "contested" rather than "consensus")

The entire debate transcript is permanently stored and visible.

## Immutability & Sealing

### Layer 1 — Append-Only Database Pattern

No finalized record is ever updated or deleted. Every answer version is a new row with a timestamp and a reference to the previous version. Supabase row-level security policies enforce this at the database level.

### Layer 2 — Cryptographic Hashing

When an answer is sealed, the system generates a SHA-256 hash of the complete record: the question, the final answer, the full debate transcript, all sources, all votes, and the timestamp. This hash is stored alongside the record. Anyone can independently verify integrity by recomputing the hash.

### Layer 3 — Hash Chain

Each sealed answer's hash includes the hash of the previously sealed answer, forming a chain. Tampering with any historical record breaks the chain from that point forward.

### Layer 4 — External Anchoring (future)

Periodically (e.g., daily), the latest hash in the chain is published to a public blockchain or transparency log. This creates external, independent proof that the chain existed in that state at that time. This layer is designed as a pluggable interface — implemented later.

### Versioning

Reopening a sealed answer creates a new version. The original stays permanently sealed and visible. History shows: v1 (sealed date) → v2 (reopened, new evidence, sealed date). Both versions and their full debate trails remain accessible.

## Source Adapters

Each external source is a pluggable adapter with a common interface: receives a question, returns structured evidence.

### AI Models (via OpenRouter)
- Single integration point for Claude, GPT-4, Gemini, Llama, Mistral, etc.
- Each model is an independent debate participant
- Models provide independent responses — no model sees another's answer during evidence gathering
- Cost tracking per query via OpenRouter usage data

### Web Search
- Google Custom Search API or SerpAPI
- Extract key claims and citations from top results
- Serve as evidence that AI models can reference during debate

### Community Platforms
- **Reddit** — Reddit API, search relevant subreddits, extract top-voted answers
- **Quora** — Web scraping, extract answers with upvote counts
- **Stack Exchange** — Public API, structured Q&A with accepted answers and votes

### Adapter Interface (standardized)

Every adapter returns:
- Source name
- Raw response
- Extracted claims (list)
- Confidence/vote score
- Source URL for citation

New sources (Wikipedia, academic papers, news outlets) can be added without changing the debate engine.

### Rate Limiting & Cost Control
- Per-query budget caps via OpenRouter
- Community platform API rate limits handled with queuing
- Failed sources don't block the debate — proceeds with available responses

## User System & Human Participation

### Registration & Identity
- Email-based registration
- Every human action (vote, comment, flag, moderation) tied to a user account and permanently recorded

### Public Access
- All sealed answers and debate trails are publicly accessible without login
- Login required only to participate (ask, vote, contribute, moderate)

### User Actions
- **Ask questions** — Submit new questions
- **Watch debates** — View live debate progress (no login needed)
- **Contribute evidence** — Add links, citations, or arguments to active debates (fed into next debate round)
- **Vote** — Upvote/downvote specific claims or positions
- **Flag** — Flag duplicates, unreliable sources, or debates needing moderation
- **Moderate** — Close a debate (triggers sealing) or reopen a sealed answer with justification

### Anti-Gaming

**Phase 1 (launch):**
- Rate limiting on submissions and votes
- One vote per user per claim
- Account age minimum before moderation powers (e.g., 7 days)
- All actions public and auditable — transparency as deterrent
- Community flagging system

**Phase 2 (later):**
- Reputation scoring based on contribution quality
- Weighted voting (higher reputation = more influence)
- Anomaly detection on voting patterns

## Frontend & UI

### Homepage
- Clean, minimal — single search box centered on the page
- Below: trending questions, recently sealed answers, active debates

### Search & Question Flow
- Autocomplete with existing questions (semantic search)
- Existing consensus → go to answer page
- No match → prompt to submit as new question

### Answer Page
- **Top:** Current best answer + status badge (preliminary / debating / consensus / sealed)
- **Confidence bar:** Visual consensus strength indicator
- **Sources panel:** Every contributing source with links and citations
- **Debate timeline:** Expandable phases — evidence, positions, counterarguments, synthesis
- **Participation panel:** Contribute evidence, vote, flag (logged-in users)
- **Version history:** All previous versions accessible if answer was reopened

### Real-Time Updates
- Active debates update live via WebSocket / Supabase real-time
- Sources arriving, positions forming, rounds progressing
- Status badge animates through states

### SEO
- Server-side rendering for all pages
- Schema.org QAPage structured data markup (enables Google rich results)
- Clean URLs: `consensus.com/q/what-is-the-boiling-point-of-water`
- Auto-generated sitemap, updated on each new sealed answer
- Google Search Console API integration for re-indexing requests

## Project Structure

```
consensus/
├── frontend/                  # Next.js application
│   ├── src/
│   │   ├── app/               # Next.js app router
│   │   │   ├── page.tsx       # Homepage — search box
│   │   │   ├── q/[slug]/      # Answer pages (ISR static generation)
│   │   │   ├── debate/[id]/   # Live debate view (SSR + WebSocket)
│   │   │   ├── ask/           # Submit new question
│   │   │   └── auth/          # Login/register
│   │   ├── components/        # Reusable UI components
│   │   ├── hooks/             # React hooks (WebSocket, auth, etc.)
│   │   └── lib/               # Client utilities, API client
│   ├── public/                # Static assets
│   ├── next.config.js
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── api/               # API route handlers
│   │   ├── core/              # Config, security, dependencies
│   │   ├── models/            # Database models (SQLAlchemy)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── orchestrator.py    # Question pipeline coordinator
│   │   │   ├── debate_engine.py   # Debate round management
│   │   │   ├── consensus.py       # Convergence evaluation
│   │   │   └── seal.py            # Hashing & immutability
│   │   ├── adapters/          # Source adapters
│   │   │   ├── openrouter.py  # Multi-model AI via OpenRouter
│   │   │   ├── google.py      # Google Search API
│   │   │   ├── reddit.py      # Reddit API
│   │   │   ├── quora.py       # Quora scraper
│   │   │   └── stackexchange.py
│   │   ├── workers/           # Celery async tasks
│   │   └── websocket/         # Real-time debate updates
│   ├── requirements.txt
│   └── pyproject.toml
│
├── database/
│   ├── migrations/            # Alembic migrations
│   └── seed/                  # Initial data
│
├── docs/
│   └── plans/                 # Design documents
│
├── docker-compose.yml         # Local dev: backend, Redis, etc.
└── README.md
```

## Open Questions

- **Domain/branding:** Working name is "Consensus" — final name TBD
- **Monetization:** Open/free for now, business model to be determined
- **External anchoring:** Blockchain selection and implementation deferred to later phase
- **Moderation governance:** All registered users can moderate initially; may need tighter controls based on real usage patterns
