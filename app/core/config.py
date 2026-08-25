from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Real-Time Code Collaboration Platform"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False
    max_history: int = 1000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
