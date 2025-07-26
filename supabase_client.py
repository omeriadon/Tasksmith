import os
from flask import g  #type: ignore
from werkzeug.local import LocalProxy #type: ignore
from supabase.client import Client, ClientOptions #type: ignore
from flask_storage import FlaskSessionStorage

# Global singleton client
_supabase_client = None

def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        _supabase_client = Client(
            url,
            key,
            options=ClientOptions(
                storage=FlaskSessionStorage(),
                flow_type="pkce"
            ),
        )
    return _supabase_client

# Use lazy initialization - only create when first accessed
supabase: Client = LocalProxy(get_supabase)
