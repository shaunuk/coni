from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database - supports both Supabase (hosted) and local PostgreSQL
    # Option 1: Use Supabase (set these three)
    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_service_key: str | None = None

    # Option 2: Use local PostgreSQL (set this)
    database_url: str | None = None

    # Required
    openrouter_api_key: str
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    debate_max_rounds: int = 3
    consensus_threshold: float = 0.8

    @property
    def use_supabase(self) -> bool:
        """Check if we should use Supabase or local Postgres."""
        return bool(self.supabase_url and self.supabase_service_key)

    class Config:
        env_file = ".env"


settings = Settings()
