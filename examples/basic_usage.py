"""Basic usage example for the OpenRouter API Manager.

This example demonstrates how to initialize the API manager and make basic requests.
It follows the project's coding standards defined in CLAUDE.md.
"""

import logging
import os
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Demonstrate basic usage of the OpenRouter API Manager.
    
    This function shows how to:
    1. Initialize the API key manager
    2. Add API keys (from environment variables)
    3. Create an instance manager
    4. Process text and images using the OpenRouter client
    
    Environment Variables:
        OPENROUTER_API_KEY_1: First API key for OpenRouter
        OPENROUTER_API_KEY_2: Second API key for rotation
        
    Raises:
        EnvironmentError: If required environment variables are not set
        RuntimeError: If API operations fail
    """
    try:
        # Initialize the API key manager with database path
        db_path = "api_keys.db"
        logger.info("Initializing API key manager with database: %s", db_path)
        api_key_manager = APIKeyManager(db_path)
        
        # Get API keys from environment variables
        api_keys = [
            os.getenv("OPENROUTER_API_KEY_1"),
            os.getenv("OPENROUTER_API_KEY_2")
        ]
        
        # Add valid API keys
        for key in filter(None, api_keys):
            logger.debug("Adding API key to manager")
            api_key_manager.add_api_key(key)
            
        if not api_key_manager.has_api_keys():
            raise EnvironmentError(
                "No valid API keys found. Please set OPENROUTER_API_KEY_1 and/or "
                "OPENROUTER_API_KEY_2 environment variables."
            )
        
        # Create an instance manager
        logger.info("Creating instance manager")
        instance_manager = InstanceManager(api_key_manager)
        
        # Create an OpenRouter client
        logger.info("Initializing OpenRouter client")
        client = OpenRouterClient(instance_manager)
        
        # Example: Process text
        logger.info("Processing text example")
        response = client.process_text("Hello, world!")
        logger.info("Text processing completed successfully")
        print(f"Text processing result: {response}")
        
        # Example: Process image
        image_path = "path/to/image.jpg"
        if os.path.exists(image_path):
            logger.info("Processing image example")
            response = client.process_image(image_path)
            logger.info("Image processing completed successfully")
            print(f"Image processing result: {response}")
        else:
            logger.warning("Image file not found: %s. Skipping image processing.", image_path)
            
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)
        raise RuntimeError("Failed to complete the example. See logs for details.") from e

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("Fatal error in main: %s", str(e), exc_info=True)
        raise
