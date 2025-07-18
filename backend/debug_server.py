import logging
import uvicorn
from fastapi import FastAPI

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a minimal FastAPI app for testing
app = FastAPI()

@app.get("/test")
async def test_endpoint():
    return {"message": "Debug test endpoint working!"}

def main():
    try:
        # Test 1: Basic FastAPI app
        logger.info("Starting basic FastAPI test...")
        
        # Test 2: Import app modules
        logger.info("Testing imports...")
        try:
            from app.core.config import settings
            logger.info("Imported settings successfully")
            
            from app.database import init_db, engine
            logger.info("Imported database successfully")
            
            from app.api import api_router
            logger.info("Imported API router successfully")
            
            # If we get here, imports are working
            logger.info("All imports successful")
            
            # Start the actual application
            logger.info("Starting main application...")
            uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")
            
        except ImportError as e:
            logger.error(f"Import error: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
