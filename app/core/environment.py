from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    twitch_enabled: bool
    twitch_client_id: str
    twitch_client_secret: SecretStr

    twitch_bot_id: str
    twitch_owner_id: str

    twitch_bot_login: str

    twitch_admin_redirect_uri: str
    session_secret: SecretStr
    session_cookie_secure: bool = False
    session_max_age_seconds: int = Field(default=28_800, gt=0)

    twitch_command_prefix: str = "!"

    psql_host: str = Field(min_length=1)
    psql_port: int = Field(default=5432, ge=1, le=65535)
    psql_db: str = Field(min_length=1)
    psql_user: str = Field(min_length=1)
    psql_password: SecretStr = Field(min_length=1)
    psql_sslmode: Literal[
        "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
    ] = "prefer"
    psql_sslrootcert: Path | None = None

    @field_validator("psql_host", "psql_db", "psql_user")
    @classmethod
    def validate_database_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("PostgreSQL connection fields must not be blank")
        return value

    giveaway_config_file: Path = PROJECT_ROOT / "data" / "settings.json"
