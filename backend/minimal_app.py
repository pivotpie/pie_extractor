import logging
from fastapi import FastAPI
import uvicorn

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create minimal FastAPI app
app = FastAPI()

@app.get("/test")
async def test():
    return {"message": "Minimal app working!"}

def main():
    # Start with minimal configuration
    uvicorn.run(
        "minimal_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )

if __name__ == "__main__":
    main()
