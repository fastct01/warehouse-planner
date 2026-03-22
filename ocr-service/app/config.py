from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MINDEE_API_KEY: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
