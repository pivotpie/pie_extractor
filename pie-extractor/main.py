from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import json
import logging
import sys
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Set SQLAlchemy logging to DEBUG for SQL queries
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO
)

from .core.config import settings
from .database import init_db, engine, Base
from .api import api_router

# Create necessary directories
for directory in ["data/uploads", "data/db"]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Document processing and chat API",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    # Listen on all interfaces by default
    servers=[{"url": "http://0.0.0.0:8000", "description": "Development server"}],
)

# Allow any localhost or 127.0.0.1 origin (any port) for local dev
import re

class LocalhostCORSMiddleware(CORSMiddleware):
    def is_allowed_origin(self, origin: str) -> bool:
        # Allow any localhost or 127.0.0.1 with any port
        return bool(re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin))

app.add_middleware(
    LocalhostCORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)



# Add Session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600,  # 1 hour
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Test endpoint
@app.get("/test")
async def test_endpoint():
    return {"status": "success", "message": "Test endpoint working"}

# Health check endpoint under API version prefix
@api_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Service is running"}

def log_routes(routes, prefix=""):
    """Helper function to log routes with proper formatting"""
    for route in routes:
        if hasattr(route, 'methods'):
            logger.info(f"{route.methods} {prefix}{route.path}")
        elif hasattr(route, 'routes'):
            # Handle Mount objects or other route groups
            logger.info(f"[MOUNT] {prefix}{route.path}")
            if hasattr(route, 'routes'):
                log_routes(route.routes, prefix + route.path)
        else:
            logger.info(f"[UNKNOWN] {prefix}{getattr(route, 'path', str(route))}")

# Log routes before including the API router
logger.info("Registered routes before API router:")
log_routes(app.routes)

# Include API routes with version prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# Log routes after including the API router
logger.info("\nRegistered routes after API router:")
log_routes(app.routes)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
        
        # Initialize database with default data if needed
        # await init_db()
        
    except Exception as e:
        print(f"Error during startup: {e}")
        raise


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic API information"""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/api/docs",
        "status": "running"
    }
