"""
Simple Main Application
A minimal version to help debug API documentation issues
"""
import logging
import sys
import uvicorn
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logger.info("Creating FastAPI application...")
    
    # Create FastAPI app with documentation enabled
    app = FastAPI(
        title="IDP Document Extractor",
        description="Document Management System API",
        version="1.0.0",
        docs_url="/docs",  # Changed from /api/docs to /docs
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add a simple test endpoint
    @app.get("/")
    async def root():
        return {"message": "Simple main application is running"}
    
    # Add a test API endpoint
    @app.get("/api/test")
    async def test_endpoint():
        return {"status": "success", "message": "API is working"}
    
    logger.info("Application setup complete")
    return app

def run_server():
    """Run the FastAPI server with Uvicorn."""
    app = create_app()
    
    # Server configuration
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=9001,  # Using a different port
        log_level="info",
        reload=True
    )
    
    server = uvicorn.Server(config)
    
    try:
        logger.info(f"Starting server on http://0.0.0.0:9001")
        logger.info(f"API documentation available at http://localhost:9001/docs")
        server.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()
