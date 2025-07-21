"""Example of dynamic model selection with fallback in OpenRouter.

This script demonstrates how to use the OpenRouterClient with automatic model
selection and fallback for different types of tasks (vision and reasoning).
"""

import argparse
import logging
import os
import sys
import json
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv

try:
    load_dotenv()
except UnicodeDecodeError:
    print("Warning: Could not load .env file due to encoding issues. Using command line arguments.")

# Add parent directory to path to allow importing from openrouter_manager
sys.path.append(str(Path(__file__).parent.parent))

from openrouter_manager.client import OpenRouterClient

# Add this after the imports
print(f"Current directory: {os.getcwd()}")
print(f"File exists: {os.path.exists('.env')}")
print(f"Before load: {os.environ.get('OPENROUTER_API_KEY')}")
try:
    load_dotenv()
    print(f"After load: {os.environ.get('OPENROUTER_API_KEY')}")
except UnicodeDecodeError:
    print("Warning: Could not load .env file due to encoding issues.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_file_content(file_path: str) -> str:
    """Load content from a file with proper error handling.
    
    Args:
        file_path: Path to the file to load
        
    Returns:
        Content of the file as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: For other file reading errors
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{file_path}' not found.")
    except Exception as e:
        raise Exception(f"Error reading file '{file_path}': {e}")

def process_file_parameter(param_value: str) -> str:
    """Process parameter that might be a file reference or combined files.
    
    Supports:
    - @file.txt - Load single file
    - @file1.json+file2.txt - Load and combine multiple files  
    - @vision_extract.json+prompt_text.txt - Specific for vision+prompt combination
    
    Args:
        param_value: Parameter value to process
        
    Returns:
        Processed content (either original value or file content)
    """
    if not param_value or not param_value.startswith('@'):
        return param_value
    
    # Remove the @ symbol
    file_spec = param_value[1:]
    
    # Handle multiple files separated by +
    if '+' in file_spec:
        file_paths = file_spec.split('+')
        combined_content = []
        
        for i, file_path in enumerate(file_paths):
            file_path = file_path.strip()
            try:
                content = load_file_content(file_path)
                
                # Add appropriate labels for common combinations
                if file_path.endswith('.json') and any(f.endswith('.txt') for f in file_paths):
                    combined_content.append(f"VISION EXTRACTION DATA:\n{content}")
                elif file_path.endswith('.txt') and any(f.endswith('.json') for f in file_paths):
                    combined_content.append(f"PROCESSING INSTRUCTIONS:\n{content}")
                else:
                    combined_content.append(f"FILE {i+1} ({file_path}):\n{content}")
                    
                print(f"✓ Loaded content from file: {file_path}")
                
            except Exception as e:
                print(f"Error loading file '{file_path}': {e}")
                raise
        
        return '\n\n'.join(combined_content)
    
    # Handle single file
    else:
        try:
            content = load_file_content(file_spec)
            print(f"✓ Loaded content from file: {file_spec}")
            return content
        except Exception as e:
            print(f"Error: {e}")
            raise

def process_text_example(client: OpenRouterClient, prompt: str) -> None:
    """Example of processing text with automatic model selection.
    
    Args:
        client: Initialized OpenRouterClient
        prompt: Text to process
    """
    print("\n=== Processing Text ===")
    print(f"Input length: {len(prompt)} characters")
    print(f"Input preview: {prompt[:200]}{'...' if len(prompt) > 200 else ''}")
    
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
    
    parser = argparse.ArgumentParser(
        description="OpenRouter dynamic model selection example",
        epilog="""
File Loading Examples:
  --text @file.txt                        Load text from single file
  --text @vision_extract.json+prompt_text.txt   Combine vision data and prompt
  --prompt @prompt_instructions.txt       Load prompt from file
  --text @data.json                       Load JSON data as text
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Text to process. Use @file.txt to load from file, or @file1+file2 to combine files",
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
        help="Custom prompt. Use @file.txt to load from file",
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
    
    # Process file parameters for both --text and --prompt
    try:
        # Handle text file loading (supports single files and combinations)
        if args.text and args.text.startswith('@'):
            args.text = process_file_parameter(args.text)
        
        # Handle prompt file loading (existing functionality extended)
        if args.prompt and args.prompt.startswith('@'):
            args.prompt = process_file_parameter(args.prompt)
            
    except Exception as e:
        print(f"Error processing file parameters: {e}")
        return 1
    
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