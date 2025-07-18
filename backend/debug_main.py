import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
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

# Create necessary directories
for directory in ["data/uploads", "data/db"]:
    Path(directory).mkdir(parents=True, exist_ok=True)

try:
    # Initialize FastAPI app with minimal configuration
    logger.info("Initializing FastAPI application...")
    app = FastAPI(
        title="IDP Document Extractor (Debug)",
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
        return {"message": "Debug server is running!"}

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        logger.info("Health check endpoint accessed")
        return {"status": "ok", "message": "Debug server is healthy"}

    logger.info("Application setup complete")

except Exception as e:
    logger.error(f"Error during application setup: {e}", exc_info=True)
    raise

if __name__ == "__main__":
    port = 8003
    logger.info(f"Starting debug server on port {port}...")
    uvicorn.run(
        "debug_main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="debug"
    )
