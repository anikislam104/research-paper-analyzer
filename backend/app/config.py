from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PA_")

    ollama_url: str = "http://localhost:11434"
    model: str = "llama3.1:8b-instruct-q4_K_M"
    num_ctx: int = 4096
    chunk_chars: int = 7000
    max_upload_mb: int = 20
    cache_ttl_seconds: int = 3600
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
