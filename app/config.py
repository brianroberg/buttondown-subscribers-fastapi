from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "Buttondown Engagement Tracker"
    environment: str = "development"
    debug: bool = False

    # Server
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./data/app.db"
    db_path: str = os.environ.get("DB_PATH", "./data/app.db")

    # Buttondown
    buttondown_api_key: str = ""
    buttondown_api_base_url: str = "https://api.buttondown.com/v1"
    buttondown_newsletter_name: str = "Brian & Carin Roberg's Ministry Updates"
    buttondown_initial_sync_lookback_days: int = 30

    # Security
    secret_key: str = "dev-secret-key-change-me"
    dashboard_username: str = "admin"
    dashboard_password_hash: str = ""  # Bcrypt hash

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("sqlite"):
            return f"sqlite:///{self.db_path}"
        return self.database_url

@lru_cache()
def get_settings() -> Settings:
    return Settings()
