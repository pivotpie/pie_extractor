"""Minimal FastAPI server for testing OpenRouter integration."""
import os
import sys
from pathlib import Path
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import OpenRouter client
try:
    from openrouter_manager.client import OpenRouterClient
except ImportError as e:
    logger.error(f"Failed to import OpenRouter client: {e}")
    raise

# Initialize FastAPI app
app = FastAPI(
    title="OpenRouter Test Server",
    description="Minimal server to test OpenRouter integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    model_category: Optional[str] = None

# Initialize OpenRouter client
openrouter_client = None

def get_openrouter_client():
    """Get or create OpenRouter client instance."""
    global openrouter_client
    if openrouter_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        openrouter_client = OpenRouterClient(api_key=api_key)
    return openrouter_client

# Middleware for request logging
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
            content={"detail": str(e)}
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Models endpoint
@app.get("/api/v1/models")
async def list_models():
    """List all available models."""
    try:
        client = get_openrouter_client()
        models = client.get_available_models()
        return {"models": list(models.values())}
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Chat completion endpoint
@app.post("/api/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    """Handle chat completion requests."""
    try:
        logger.info(f"Received chat completion request with model: {request.model}")
        logger.debug(f"Messages: {request.messages}")
        
        client = get_openrouter_client()
        
        # Convert messages to expected format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        logger.info("Calling OpenRouter API...")
        
        # Call OpenRouter with timeout
        response = client.chat_completion(
            messages=messages,
            model=request.model,
            model_category=request.model_category,
            timeout=30  # Add timeout to prevent hanging
        )
        
        logger.info("Successfully received response from OpenRouter")
        return response
        
    except requests.exceptions.Timeout:
        logger.error("OpenRouter API request timed out")
        raise HTTPException(status_code=504, detail="Request to OpenRouter timed out")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API request failed: {str(e)}")
        raise HTTPException(status_code=502, detail=f"OpenRouter API request failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Chat completion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    # Verify OpenRouter client can be initialized
    try:
        get_openrouter_client()
        logger.info("OpenRouter client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenRouter client: {e}")
        sys.exit(1)
    
    # Start the server
    port = 9001  # Changed from 9000 to 9001
    logger.info(f"Starting server on http://localhost:{port}")
    logger.info(f"API documentation available at http://localhost:{port}/docs")
    
    # Try to start the server with more detailed error handling
    try:
        import socket
        
        # Check if port is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            logger.error(f"Port {port} is already in use. Please close any other applications using this port.")
            sys.exit(1)
        sock.close()
        
        # Start the server
        uvicorn.run(
            "minimal_openrouter_server:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="debug",
            access_log=True,
            workers=1
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
