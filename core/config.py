from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Creatorly"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "creatorly"
    # Optional full URL; overrides the DB_* parts (e.g. for tests).
    database_url: str | None = None

    encryption_key: str = ""

    # Instagram Graph API (Business Discovery for competitors). Off until Meta App Review:
    # with it off, a new competitor is saved by username only and filled by the nightly sync later.
    instagram_sync: bool = False
    graph_api_version: str = "v27.0"

    # Instagram API with Unified login (own account: OAuth, insights, nightly sync).
    # App ID / Secret: developers.facebook.com → App settings → Basic. Config ID: API setup with
    # Unified login. The connect button is hidden until all three are set.
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_config_id: str = ""
    # Local testing without OAuth (scripts/instagram_local.py): a token generated in the dashboard.
    instagram_account_id: str = ""
    instagram_access_token: str = ""
    instagram_redirect_uri: str = "http://localhost:8000/auth/instagram/callback"
    instagram_backfill_days: int = 30  # first sync after connecting (API keeps ~90 days)
    instagram_resync_days: int = 3  # nightly sync re-reads the last N days (late-arriving data)
    instagram_media_limit: int = 50  # newest posts whose insights are refreshed each sync

    @property
    def instagram_configured(self) -> bool:
        return bool(self.meta_app_id and self.meta_app_secret and self.meta_config_id)

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
