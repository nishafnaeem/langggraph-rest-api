from dotenv import load_dotenv
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(".env")


class Configurations(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    llm_provider: Literal["openai", "anthropic"] = "anthropic"
    llm_model: str = "claude-3-7-sonnet-latest"


settings = Configurations()
