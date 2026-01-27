from supabase import create_client

from app.core.config import settings


def get_db():
    return create_client(settings.supabase_url, settings.supabase_service_key)
