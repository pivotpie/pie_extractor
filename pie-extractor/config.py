from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "IDP Document Extractor"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api/v1"
    API_BASE_URL: str = "http://localhost:8000"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    SQLITE_DB_DIR: str = "data/db"
    SQLITE_DB_NAME: str = "app.db"
    SQLITE_TEST_DB_NAME: str = "test.db"
    
    # File Storage
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: list = ["application/pdf", "image/jpeg", "image/png", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"]
    
    # Database URL for SQLAlchemy
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # Ensure the database directory exists
        db_dir = Path(self.SQLITE_DB_DIR)
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Format the SQLite URL
        db_path = db_dir / self.SQLITE_DB_NAME
        return f"sqlite+aiosqlite:///{db_path.absolute()}"

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create necessary directories
for directory in [Settings().SQLITE_DB_DIR, Settings().UPLOAD_DIR]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Create settings instance
settings = Settings()
