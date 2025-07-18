import logging
import sys
import os
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting main application with debug logging...")
    
    # Import FastAPI and other dependencies
    from fastapi import FastAPI, Depends, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import JSONResponse
    import uvicorn
    
    logger.info("Imported FastAPI and dependencies")
    
    # Import application modules
    from app.core.config import settings
    from app.database import init_db, engine, Base
    
    logger.info("Imported application modules")
    
    # Create necessary directories
    for directory in ["data/uploads", "data/db"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    logger.info("Created necessary directories")
    
    # Initialize FastAPI app with minimal configuration
    logger.info("Initializing FastAPI application...")
    app = FastAPI(
        title=settings.APP_NAME,
        description="IDP Document Extractor & Chatbot API (Debug Mode)",
        version="0.1.0"
    )
    
    # Basic CORS middleware
    logger.info("Adding CORS middleware...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Test endpoint
    @app.get("/")
    async def root():
        logger.info("Root endpoint accessed")
        return {
            "app": settings.APP_NAME,
            "version": "0.1.0",
            "status": "running",
            "debug": True
        }
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        logger.info("Health check endpoint accessed")
        return {"status": "ok", "message": "Debug server is healthy"}
    
    logger.info("Application setup complete")

    # Start the server
    if __name__ == "__main__":
        port = 8003
        logger.info(f"Starting main application server on port {port}...")
        uvicorn.run(
            "debug_main_app:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="debug"
        )

except Exception as e:
    logger.error(f"Error during application setup: {e}", exc_info=True)
    raise
