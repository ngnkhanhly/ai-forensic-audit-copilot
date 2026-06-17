from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    OPENAI_API_KEY: str = "placeholder_key"
    GEMINI_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./documents.db"
    
    # Model configs
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    EVALUATION_LLM_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
