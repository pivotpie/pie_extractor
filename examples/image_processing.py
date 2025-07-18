"""
Image processing example using OpenRouter's vision models.

This example shows how to process images using the vision capabilities.
"""
import os
from openrouter_manager import OpenRouterClient, APIKeyManager, InstanceManager

def process_image(image_path):
    """Process an image and extract text using vision models."""
    # Initialize managers
    api_key_manager = APIKeyManager("api_keys.db")
    instance_manager = InstanceManager(api_key_manager)
    client = OpenRouterClient(instance_manager)
    
    try:
        # Process the image
        result = client.process_image(
            image_path=image_path,
            model="meta-llama/llama-3.2-90b-vision-instruct",
            prompt="Extract all text from this image."
        )
        return result
    except Exception as e:
        print(f"Error processing image: {e}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m examples.image_processing <path_to_image>")
        sys.exit(1)
        
    result = process_image(sys.argv[1])
    print("Extracted text:")
    print(result['text'])
