import logging
import sys
import os
from pathlib import Path

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
    logger.info("Starting enhanced minimal application...")
    
    # Import FastAPI and core components
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    logger.info("Imported FastAPI and core components")
    
    # Import application modules
    try:
        from app.core.config import settings
        logger.info("Successfully imported app.core.config")
    except ImportError as e:
        logger.error(f"Failed to import app.core.config: {e}")
        raise
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        description="Enhanced Minimal Application",
        version="0.1.0"
    )
    logger.info("Created FastAPI app with settings")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("Added CORS middleware")
    
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
        return {"status": "ok", "message": "Enhanced minimal server is healthy"}
    
    logger.info("Application setup complete")

    # Start the server
    if __name__ == "__main__":
        port = 8005  # Use a different port to avoid conflicts
        logger.info(f"Starting enhanced minimal application server on port {port}...")
        uvicorn.run(
            "enhanced_minimal:app",
            host="0.0.0.0",
            port=port,
            log_level="debug"
        )

except Exception as e:
    logger.error(f"Error during application setup: {e}", exc_info=True)
    raise
