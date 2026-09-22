from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str
    FRONTEND_URL: str = "http://localhost:3000"

    # Backblaze B2 (S3-compatible) — optional, falls back to Supabase Storage
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET: Optional[str] = None
    R2_ENDPOINT: Optional[str] = None
    R2_REGION: str = "us-west-004"

    class Config:
        env_file = ".env"

    @property
    def r2_enabled(self) -> bool:
        return all([
            self.R2_ACCESS_KEY_ID,
            self.R2_SECRET_ACCESS_KEY,
            self.R2_BUCKET,
            self.R2_ENDPOINT,
        ])


settings = Settings()
