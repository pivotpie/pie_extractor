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
    logger.info("Starting minimal main application...")
    
    # Import FastAPI
    from fastapi import FastAPI
    import uvicorn
    
    logger.info("Imported FastAPI and uvicorn")
    
    # Create FastAPI app
    app = FastAPI()
    logger.info("Created FastAPI app")
    
    # Add a simple test endpoint
    @app.get("/")
    async def root():
        logger.info("Root endpoint accessed")
        return {"message": "Minimal main application is running"}
    
    # Start the server
    if __name__ == "__main__":
        port = 8004  # Use a different port to avoid conflicts
        logger.info(f"Starting minimal main application server on port {port}...")
        uvicorn.run(
            "minimal_main:app",
            host="0.0.0.0",
            port=port,
            log_level="debug"
        )

except Exception as e:
    logger.error(f"Error during application setup: {e}", exc_info=True)
    raise
