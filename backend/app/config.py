from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "CTec General Ledger"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://ctec:ctec_local_only@localhost:15432/ctec_gl"
    jwt_secret: str = Field(default="development-secret-change-before-use-123456", min_length=32)
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    cors_origins: str = "http://localhost:5173"
    inline_operation_jobs: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @model_validator(mode="after")
    def production_secrets_are_explicit(self) -> "Settings":
        if self.environment == "production":
            if "development-secret" in self.jwt_secret or "change-before-use" in self.jwt_secret:
                raise ValueError("Production requires an independently generated JWT_SECRET")
            if "*" in self.cors_origin_list:
                raise ValueError("Production CORS_ORIGINS cannot contain a wildcard")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
