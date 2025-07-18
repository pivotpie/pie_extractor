from fastapi import APIRouter
from . import auth, oauth, openrouter, documents
# from . import chat  # Uncomment when chat module is implemented

# Create main API router
api_router = APIRouter()

# Include all API endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["OAuth"])
api_router.include_router(openrouter.router, prefix="/openrouter", tags=["OpenRouter"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
# api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])  # Uncomment when implemented
