from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.security import SecuritySettings


class Settings(BaseSettings):
    app_name: str = "Vendfy API"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://vendfy:vendfy@localhost:5432/vendfy"
    whatsapp_graph_api_version: str = Field(
        default="v23.0", pattern=r"^v\d+\.\d+$"
    )
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
