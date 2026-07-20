import os

from pydantic import BaseModel


class AppConfig(BaseModel):
    app_name: str
    app_env: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str


def load_config() -> AppConfig:
    return AppConfig(
        app_name=os.getenv("APP_NAME", "agent-lab"),
        app_env=os.getenv("APP_ENV", "development"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
    )


settings = load_config()
