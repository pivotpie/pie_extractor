import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    # Stage 1: Basic FastAPI app with OpenAPI docs
    logger.info("Creating basic FastAPI app...")
    app = FastAPI(
        title="IDP Document Extractor API",
        description="Staged API for debugging",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    @app.get("/test")
    async def test():
        return {"message": "Staged app working!"}
        
    @app.get("/api/health", status_code=status.HTTP_200_OK)
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": "0.1.0"
        }
    
    # Stage 2: Add CORS middleware
    logger.info("Adding CORS middleware...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Stage 3: Add database initialization
    logger.info("Initializing database...")
    try:
        from app.database import init_db, engine
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Stage 4: Add API routes
    logger.info("Adding API routes...")
    try:
        from app.api import api_router
        from app.core.config import settings
        app.include_router(api_router, prefix=settings.API_V1_STR)
        logger.info("API routes added successfully")
    except Exception as e:
        logger.error(f"Failed to add API routes: {e}")
        raise
    
    return app

# Create app instance in global scope
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "staged_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
