"""
Final Debug Script for FastAPI Server Issues
This script will help identify and resolve the server binding issue.
"""
import socket
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

def check_port_availability(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def run_server(port: int):
    """Run a minimal FastAPI server on the specified port."""
    app = FastAPI()
    
    @app.get("/")
    async def root():
        return {"status": "success", "message": "Server is running!"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )
    
    server = uvicorn.Server(config)
    
    try:
        logger.info(f"Starting server on port {port}...")
        server.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    PORT = 9000  # Using a high port number to avoid conflicts
    
    # Check if port is available
    if not check_port_availability(PORT):
        logger.warning(f"Port {PORT} is already in use. Trying to find an available port...")
        for p in range(9001, 9010):
            if check_port_availability(p):
                PORT = p
                logger.info(f"Found available port: {PORT}")
                break
        else:
            logger.error("Could not find an available port. Please close other applications using ports 9000-9010.")
            sys.exit(1)
    
    # Run the server
    try:
        logger.info(f"Attempting to start server on port {PORT}...")
        run_server(PORT)
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.info("Troubleshooting steps:")
        logger.info("1. Check if another process is using the port")
        logger.info("2. Try running as administrator")
        logger.info("3. Check your firewall settings")
        logger.info("4. Try a different port number")
        sys.exit(1)
