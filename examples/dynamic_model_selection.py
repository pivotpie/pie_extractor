"""Example of dynamic model selection with fallback in OpenRouter.

This script demonstrates how to use the OpenRouterClient with automatic model
selection and fallback for different types of tasks (vision and reasoning).
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path to allow importing from openrouter_manager
sys.path.append(str(Path(__file__).parent.parent))

from openrouter_manager.client import OpenRouterClient

# Add this after the imports
print(f"Current directory: {os.getcwd()}")
print(f"File exists: {os.path.exists('.env')}")
print(f"Before load: {os.environ.get('OPENROUTER_API_KEY')}")
load_dotenv()
print(f"After load: {os.environ.get('OPENROUTER_API_KEY')}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_text_example(client: OpenRouterClient, prompt: str) -> None:
    """Example of processing text with automatic model selection.
    
    Args:
        client: Initialized OpenRouterClient
        prompt: Text to process
    """
    print("\n=== Processing Text ===")
    print(f"Input: {prompt}")
    
    try:
        print("DEBUG: Getting best model for reasoning...")
        # Get the best model for reasoning
        best_model = client.get_best_model("reasoning")
        print(f"Selected model: {best_model}")
        
        print("DEBUG: Processing text...")
        # Process the text
        response = client.process_text(prompt)
        
        print("\nResponse:")
        # Encode the response to handle special characters in Windows console
        try:
            print(response)
        except UnicodeEncodeError:
            # If encoding fails, replace or ignore problematic characters
            import sys
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
            print(response)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        logger.error("Failed to process text: %s", str(e), exc_info=True)
        raise

def process_image_example(client: OpenRouterClient, image_path: str, prompt: Optional[str] = None) -> None:
    """Example of processing an image with automatic model selection.
    
    Args:
        client: Initialized OpenRouterClient
        image_path: Path to the image file
        prompt: Optional custom prompt for the image
    """
    if not os.path.exists(image_path):
        logger.warning("Image file not found: %s. Skipping image processing.", image_path)
        return
    
    print("\n=== Processing Image ===")
    print(f"Image: {image_path}")
    
    try:
        # Get the best model for vision
        best_model = client.get_best_model("vision")
        print(f"Selected model: {best_model}")
        
        # Process the image
        response = client.process_image(
            image_path=image_path,
            prompt=prompt or "Describe the content of this image in detail."
        )
        
        print("\nResponse:")
        print(response)
        
    except Exception as e:
        logger.error("Failed to process image: %s", str(e), exc_info=True)
        raise

def list_available_models(client: OpenRouterClient, category: Optional[str] = None) -> None:
    """List available models, optionally filtered by category.
    
    Args:
        client: Initialized OpenRouterClient
        category: Optional category to filter by (e.g., 'vision', 'reasoning')
    """
    print(f"\n=== Available Models{f' ({category})' if category else ''} ===")
    
    try:
        # Get all available models
        models = client.get_available_models(refresh=True)
        
        if not models:
            print("No models found.")
            return
        
        # Filter by category if specified
        if category:
            models = {
                model_id: model 
                for model_id, model in models.items()
                if category.lower() in (model.get("name", "") + " " + model.get("description", "")).lower()
            }
        
        # Print model information
        for i, (model_id, model) in enumerate(models.items(), 1):
            print(f"\n{i}. {model_id}")
            print(f"   Name: {model.get('name', 'N/A')}")
            print(f"   Description: {model.get('description', 'N/A')}")
            print(f"   Context Length: {model.get('context_length', 'N/A')}")
            print(f"   Pricing: {model.get('pricing', {}).get('prompt', 'N/A')} per 1K tokens")
            
    except Exception as e:
        logger.error("Failed to list models: %s", str(e), exc_info=True)
        raise

def main():
    """Main function to demonstrate dynamic model selection."""
    # Load environment variables first
    load_dotenv(override=True)  # Force reload to ensure we have the latest
    
    parser = argparse.ArgumentParser(description="OpenRouter dynamic model selection example")
    parser.add_argument(
        "--text",
        type=str,
        help="Text to process (for text processing example)",
        default="Explain the concept of quantum entanglement in simple terms."
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Path to image file (for vision example)",
        default=None
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Custom prompt for image processing",
        default=None
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Filter models by category (e.g., 'vision', 'reasoning')",
        default=None
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenRouter API key (default: from OPENROUTER_API_KEY environment variable)",
        default=os.environ.get("OPENROUTER_API_KEY")  # Default from env
    )
    
    args = parser.parse_args()
    
    # Debug: Print environment and args
    logger.debug("Environment variables loaded: %s", 
                {k: v for k, v in os.environ.items() if "OPENROUTER" in k})
    logger.debug("Command line args: %s", args)
    
    # Initialize the client
    api_key = args.api_key
    if not api_key:
        print("Error: No API key provided. Set OPENROUTER_API_KEY environment variable or use --api-key")
        print("Current working directory:", os.getcwd())
        print("Environment variables:", 
              {k: v for k, v in os.environ.items() if "OPENROUTER" in k})
        return 1
        
    try:
        client = OpenRouterClient(api_key=api_key)
        # Test the connection
        client.get_available_models(refresh=False)
    except Exception as e:
        logger.error("Failed to initialize OpenRouter client: %s", str(e))
        print(f"Error: Failed to initialize OpenRouter client - {str(e)}")
        return 1
    
    try:
        # List models if requested
        if args.list_models:
            list_available_models(client, args.category)
            return 0
            
        # Process image if provided (exclusive)
        if args.image:
            process_image_example(client, args.image, args.prompt)
        # Otherwise process text
        else:
            process_text_example(client, args.text)
            
    except Exception as e:
        logger.critical("Fatal error: %s", str(e), exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
