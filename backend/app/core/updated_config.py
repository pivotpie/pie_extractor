from pydantic import BaseModel, Field
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseModel):
    # Application
    APP_NAME: str = "IDP Document Extractor"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    SQLITE_DB_DIR: str = "data/db"
    SQLITE_DB_NAME: str = "app.db"
    SQLITE_TEST_DB_NAME: str = "test.db"
    
    # File Storage
    UPLOAD_DIR: str = "data/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
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
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"]

    def __init__(self, **data):
        # Load environment variables if needed
        env_vars = {}
        for field in self.__annotations__:
            env_value = os.getenv(field)
            if env_value is not None:
                # Convert string to appropriate type based on annotation
                field_type = self.__annotations__[field]
                try:
                    if field_type == bool:
                        env_vars[field] = env_value.lower() in ('true', '1', 't')
                    elif field_type == int:
                        env_vars[field] = int(env_value)
                    elif field_type == float:
                        env_vars[field] = float(env_value)
                    elif field_type == list:
                        env_vars[field] = [x.strip() for x in env_value.split(',')]
                    else:
                        env_vars[field] = env_value
                except (ValueError, AttributeError):
                    env_vars[field] = env_value
        
        # Update with environment variables
        data.update(env_vars)
        
        # Call parent constructor
        super().__init__(**data)
        
        # Create necessary directories
        for directory in [self.SQLITE_DB_DIR, self.UPLOAD_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)

# Create settings instance
settings = Settings()
