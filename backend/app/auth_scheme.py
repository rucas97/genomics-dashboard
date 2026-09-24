from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

# Only create the Supabase client in cloud mode
_auth_client = None
if settings.is_cloud and settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
    from supabase import create_client
    _auth_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
