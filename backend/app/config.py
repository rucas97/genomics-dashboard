from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    # Deployment mode
    MODE: str = "cloud"

    # Cloud (Supabase)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None

    # Local (SQLite)
    LOCAL_DB_PATH: str = str(Path.home() / ".genomicsops" / "genomics.db")
    LOCAL_DATA_DIR: str = str(Path.home() / ".genomicsops" / "data")

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Backblaze B2 (cloud mode only)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET: Optional[str] = None
    R2_ENDPOINT: Optional[str] = None
    R2_REGION: str = "us-west-004"

    # ACMG engine versioning
    ACMG_ENGINE_VERSION: str = "1.0.0"
    ACMG_RULE_SET_VERSION: str = "ACMG-AMP-2015"

    class Config:
        env_file = ".env"

    @property
    def is_local(self) -> bool:
        return self.MODE.lower() == "local"

    @property
    def is_cloud(self) -> bool:
        return self.MODE.lower() == "cloud"

    @property
    def r2_enabled(self) -> bool:
        return all([
            self.R2_ACCESS_KEY_ID,
            self.R2_SECRET_ACCESS_KEY,
            self.R2_BUCKET,
            self.R2_ENDPOINT,
        ])


settings = Settings()
