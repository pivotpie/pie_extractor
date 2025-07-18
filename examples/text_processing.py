"""
Text processing example using OpenRouter's text models.

This example demonstrates how to process text using different models.
"""
import os
from openrouter_manager import OpenRouterClient, APIKeyManager, InstanceManager

def process_text(text, model="deepseek-ai/deepseek-r1"):
    """Process text using the specified model."""
    # Initialize managers
    api_key_manager = APIKeyManager("api_keys.db")
    instance_manager = InstanceManager(api_key_manager)
    client = OpenRouterClient(instance_manager)
    
    try:
        # Process the text
        result = client.process_text(
            text=text,
            model=model,
            max_tokens=150,
            temperature=0.7
        )
        return result
    except Exception as e:
        print(f"Error processing text: {e}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m examples.text_processing <text_to_process> [model_name]")
        print("Example: python -m examples.text_processing \"Hello, world!\" deepseek-ai/deepseek-r1")
        sys.exit(1)
        
    text = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "deepseek-ai/deepseek-r1"
    
    result = process_text(text, model)
    print("Processing result:")
    print(result['text'])
