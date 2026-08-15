import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Gubera"
    ENVIRONMENT: str = "development"
    
    # Databases
    DATABASE_URL: str
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "gubera_mongo"
    REDIS_URL: str
    
    # JWT Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # SMS Configuration
    SMS_OTP_API_URL: str
    SMS_API_KEY: str
    SMS_SENDER_ID: str
    SUPPORT_CONTACT: str

    # Vercel Blob
    VERCEL_BLOB_READ_WRITE_TOKEN: str | None = None

    # Pydantic configuration to load from .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        extra="ignore"
    )

settings = Settings()
# Trigger reload
