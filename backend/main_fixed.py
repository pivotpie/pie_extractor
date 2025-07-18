"""
Fixed Main Application Entry Point
This version uses the working configuration from final_debug.py
"""
import logging
import sys
import os
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

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
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Creating FastAPI application...")
    
    # Create FastAPI app with minimal configuration
    app = FastAPI(
        title="IDP Document Extractor",
        description="Document Management System API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        debug=True
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url}")
        try:
            response = await call_next(request)
            logger.info(f"Response status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Request error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development only
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import and include routers
    try:
        logger.info("Attempting to import API router...")
        from app.api import api_router
        logger.info("API router imported successfully")
        
        # List all routes for debugging
        logger.info("Registering API router with prefix /api/v1")
        app.include_router(api_router, prefix="/api/v1")
        
        # Log all registered routes
        logger.info("Registered routes:")
        for route in app.routes:
            if hasattr(route, 'path'):
                logger.info(f"  {route.path} - {route.methods}")
        
        logger.info("API router included successfully")
    except Exception as e:
        logger.error(f"Failed to include API router: {e}", exc_info=True)
        raise
    
    # Add test endpoint
    @app.get("/")
    async def root():
        return {
            "app": "IDP Document Extractor",
            "status": "running",
            "version": "1.0.0"
        }
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    logger.info("Application setup complete")
    return app

def run_server():
    """Run the FastAPI server with Uvicorn."""
    app = create_app()
    
    # Server configuration
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=9000,  # Using the working port
        log_level="info",
        reload=True
    )
    
    server = uvicorn.Server(config)
    
    try:
        logger.info(f"Starting server on http://0.0.0.0:9000")
        logger.info(f"API documentation available at http://localhost:9000/api/docs")
        server.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Create necessary directories
    for directory in ["data/uploads", "data/db"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Run the server
    run_server()
