# Consensus Engine

A multi-source AI consensus system that queries multiple AI models and web sources, runs structured debates, and synthesizes answers through cross-comparison and validation.

## Overview

The Consensus Engine aggregates answers from multiple AI models (Claude, GPT-4o, Gemini) and web sources (Wikipedia), then uses a debate-based approach to find consensus. The system provides real-time visibility into the decision-making process.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  - Search interface                                              │
│  - Real-time progress via WebSocket                              │
│  - Convergence visualization                                     │
│  - Cross-comparison display                                      │
│  - Debate arguments display                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  - REST API endpoints                                            │
│  - WebSocket for progress events                                 │
│  - Celery task queue                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │  Redis   │   │ Supabase │   │OpenRouter│
        │ Pub/Sub  │   │    DB    │   │   API    │
        └──────────┘   └──────────┘   └──────────┘
```

## Pipeline Phases

### Phase 1: Evidence Gathering
- Queries all configured AI models via OpenRouter
- Fetches relevant Wikipedia articles
- Streams responses in real-time
- Extracts claims with confidence scores

### Phase 2: Cross-Comparison
Each AI model reviews the other models' answers and provides:
- Agreement/disagreement assessment
- Specific comments on what others got right/wrong
- Overall assessment of answer quality

**Example Output:**
```
Claude Haiku reviewed:
  + GPT-4o-mini: Their answer aligns with mine on key points about
    antioxidants. However, they didn't address potential risks.
  + Gemini-2.5-flash: Their answer seems incomplete but emphasizes
    moderation and benefits similar to mine.
```

### Phase 3: Debate Rounds
Multiple rounds of structured debate where:
1. **Counterarguments** are generated challenging each position
2. Arguments have **strength indicators** (weak/medium/strong)
3. Arguments suggest **merger opportunities** between compatible positions
4. Positions are updated based on how well they withstand challenges

**Example Counterargument:**
```
!!! Challenging: "Coffee has health benefits when consumed in moderation..."

The health impacts cannot be fully understood without considering the
historical context and commercial factors that have shaped coffee
consumption patterns.

Suggests merging with: Historical and commercial information about coffee...
```

### Phase 4: Position Merging
- Positions with similar stances are merged
- Sources shift to the stronger position
- Convergence score increases toward 100%
- Force merge if convergence stays below 80%

### Phase 5: Synthesis
- Final answer synthesized from merged positions
- Incorporates key claims from all sources
- Confidence score calculated

### Phase 6: Cross-Validation
Each AI source validates the final consensus:
- Checks if they agree with the synthesized answer
- Can raise objections with specific concerns
- Agreement percentage calculated

## AI Models (Current Configuration)

Using fast/cheap models for testing:
- `anthropic/claude-3-5-haiku`
- `openai/gpt-4o-mini`
- `google/gemini-2.5-flash`

Plus web source:
- Wikipedia (via MediaWiki API)

## Real-Time Progress Events

Events emitted via Redis pub/sub and delivered via WebSocket:

| Event | Data | Description |
|-------|------|-------------|
| `pipeline_started` | sources[] | Pipeline begins, lists all sources |
| `source_started` | source_name | A source begins querying |
| `source_streaming` | source_name, partial_content | Token streaming |
| `source_completed` | source_name, confidence, claims_count | Source finished |
| `comparison_started` | - | Cross-comparison phase begins |
| `comparison_complete` | reviewer, comparisons[], overall_assessment | One AI completed review |
| `comparison_finished` | results[] | All comparisons done |
| `debate_round_started` | round_number | Debate round begins |
| `debate_arguments` | round_number, arguments[] | Counterarguments generated |
| `position_update` | positions[], convergence_score | Positions updated |
| `debate_round_completed` | round_number, convergence_score | Round finished |
| `synthesis_started` | - | Final synthesis begins |
| `synthesis_completed` | confidence | Synthesis finished |
| `validation_started` | - | Cross-validation begins |
| `source_validated` | source_name, agrees, objection | One source validated |
| `validation_completed` | agreement_percentage | All validation done |
| `pipeline_completed` | status, confidence, final_answer | Pipeline finished |
| `pipeline_failed` | error | Pipeline error |

## Frontend Components

### ConvergenceVisualization
SVG-based visualization showing:
- Colored dots for each source (CH, G4, GF, W)
- Dots cluster together as positions merge
- Current stance displayed below
- Convergence percentage

### ComparisonResults
Displays cross-comparison "chatter":
- Each AI reviewer in its own card
- Reviews of other AIs with agree/disagree indicators
- Overall assessment in italics

### DebateArguments
Expandable debate round display:
- Collapsible rounds (click to expand)
- Strength indicators (!, !!, !!!)
- Target stance being challenged
- Counterargument text
- Merger suggestions highlighted in purple

### ValidationResults
Final validation display:
- Agreement percentage badge
- Source cards with checkmark/X
- Click to see objection details

## Database Schema (Supabase)

### questions
- `id` (uuid)
- `slug` (text) - URL-friendly identifier
- `question_text` (text)
- `created_at` (timestamp)

### answer_versions
- `id` (uuid)
- `question_id` (uuid, FK)
- `version` (integer)
- `status` (enum: preliminary, debating, consensus_reached, contested, sealed)
- `preliminary_answer` (text)
- `final_answer` (text)
- `confidence` (float)
- `seal_hash` (text)
- `previous_hash` (text)
- `sealed_at` (timestamp)

### source_responses
- `id` (uuid)
- `answer_version_id` (uuid, FK)
- `source_name` (text)
- `raw_response` (text)
- `claims` (jsonb)
- `confidence` (float)
- `source_url` (text)

### debate_rounds
- `id` (uuid)
- `answer_version_id` (uuid, FK)
- `round_number` (integer)
- `phase` (enum: counterarguments, synthesis)
- `positions` (jsonb)
- `arguments` (jsonb)
- `synthesis` (jsonb)
- `convergence_score` (float)

## Running Locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- Redis
- Supabase account (or local instance)
- OpenRouter API key

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export OPENROUTER_API_KEY=your_key
export SUPABASE_URL=your_url
export SUPABASE_KEY=your_key
export REDIS_URL=redis://localhost:6379/0

# Start FastAPI
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Configuration

### Backend Settings (`app/core/config.py`)
- `debate_max_rounds`: Maximum debate rounds (default: 3)
- `consensus_threshold`: Convergence needed for consensus (default: 0.8)
- `openrouter_api_key`: API key for OpenRouter
- `redis_url`: Redis connection URL
- `supabase_url`: Supabase project URL
- `supabase_key`: Supabase anon key

## Key Files

### Backend
- `app/workers/pipeline.py` - Main consensus pipeline
- `app/services/debate_engine.py` - Debate logic, position merging
- `app/services/orchestrator.py` - Source querying orchestration
- `app/adapters/openrouter.py` - OpenRouter API adapter
- `app/adapters/wikipedia.py` - Wikipedia API adapter
- `app/lib/progress.py` - Progress event emitter
- `app/api/ws.py` - WebSocket endpoint

### Frontend
- `src/app/q/[slug]/page.tsx` - Main answer page
- `src/components/ConvergenceVisualization.tsx` - Source clustering viz
- `src/components/ComparisonResults.tsx` - AI cross-comparison
- `src/components/DebateArguments.tsx` - Debate round display
- `src/components/ValidationResults.tsx` - Final validation display
- `src/components/StreamingText.tsx` - Typing animation

## Future Enhancements

- [ ] Add more AI models (Llama, Mistral, etc.)
- [ ] Add more web sources (Reddit, Stack Exchange)
- [ ] Implement position change animations in convergence viz
- [ ] Add debate round timeline/history view
- [ ] Enable users to ask follow-up questions
- [ ] Add source citations in final answer
- [ ] Implement answer caching
- [ ] Add user authentication
- [ ] Create shareable answer links
