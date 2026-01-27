from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.questions import router as questions_router
from app.api.answers import router as answers_router

app = FastAPI(title="Consensus Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(questions_router)
app.include_router(answers_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
