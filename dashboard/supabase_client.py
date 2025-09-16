from supabase import create_client, Client
from django.conf import settings

def get_supabase_client():
    """Initialize and return Supabase client"""
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return supabase
