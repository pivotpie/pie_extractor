from pydantic import BaseModel
from typing import List

class Settings(BaseModel):
    # Minimal required settings
    APP_NAME: str = "IDP Document Extractor (Minimal)"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

# Create a minimal settings instance
settings = Settings()
