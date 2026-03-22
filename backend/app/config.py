from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://energy_user:energy_pass@localhost:5432/energy_db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    REDIS_URL: str = "redis://localhost:6379"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "energy-bills"
    OCR_SERVICE_URL: str = "http://localhost:8001"

    class Config:
        env_file = ".env"


settings = Settings()
