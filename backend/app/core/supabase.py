from __future__ import annotations

from app.core.settings import settings


class SupabaseClient:
    def __init__(self) -> None:
        self._client = None
        if settings.supabase_url and settings.supabase_service_key:
            from supabase import create_client

            self._client = create_client(settings.supabase_url, settings.supabase_service_key)

    @property
    def client(self):
        return self._client


supabase = SupabaseClient()
