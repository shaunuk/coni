# Consensus Engine

A multi-source AI consensus system that queries multiple AI models, runs structured debates, and synthesizes answers through cross-comparison and validation.

## Features

- **Multi-Model Querying**: Queries Claude, GPT-4o, Gemini and web sources in parallel
- **Cross-Comparison**: Each AI reviews and comments on others' answers
- **Structured Debate**: Counterarguments challenge positions and suggest mergers
- **Real-Time Visualization**: Watch sources converge toward consensus
- **Cross-Validation**: Final answer validated by all AI sources

## Quick Start

### 1. Start Redis
```bash
redis-server
```

### 2. Start Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 3. Start Celery Worker
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

### 4. Start Frontend
```bash
cd frontend
npm run dev
```

### 5. Open Browser
Navigate to http://localhost:3000

## Documentation

See [docs/CONSENSUS_ENGINE.md](docs/CONSENSUS_ENGINE.md) for detailed documentation.

## Project Structure

```
coni/
├── backend/
│   ├── app/
│   │   ├── adapters/      # Source adapters (OpenRouter, Wikipedia)
│   │   ├── api/           # REST & WebSocket endpoints
│   │   ├── core/          # Config, database
│   │   ├── lib/           # Progress emitter
│   │   ├── schemas/       # Pydantic models
│   │   ├── services/      # Debate engine, orchestrator
│   │   └── workers/       # Celery pipeline
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   └── lib/           # API client, utils
│   └── package.json
└── docs/
    └── CONSENSUS_ENGINE.md
```

## Environment Variables

### Backend
```
OPENROUTER_API_KEY=your_openrouter_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
REDIS_URL=redis://localhost:6379/0
```

### Frontend
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## License

MIT
