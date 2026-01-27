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
