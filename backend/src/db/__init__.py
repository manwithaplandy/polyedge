"""Database module for Supabase integration."""

from src.db.client import get_supabase_client, SupabaseClient

__all__ = ["get_supabase_client", "SupabaseClient"]
