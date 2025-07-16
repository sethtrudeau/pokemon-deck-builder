import os
from typing import Optional
from supabase import create_client, Client
from decouple import config


class SupabaseClient:
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None

    def __new__(cls) -> 'SupabaseClient':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        supabase_url = config('SUPABASE_URL', default='')
        supabase_key = config('SUPABASE_ANON_KEY', default='')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self._client = create_client(supabase_url, supabase_key)

    @property
    def client(self) -> Client:
        if self._client is None:
            self._initialize_client()
        return self._client

    async def close(self):
        if self._client:
            self._client = None


# Singleton instance
supabase_client = SupabaseClient()


async def get_supabase_client() -> Client:
    return supabase_client.client