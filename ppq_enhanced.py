"""Enhanced PPQ.ai script for document extraction with JSON-only responses.

Usage:
    python ppq_enhanced.py --vision '@vision_extract.json' --instructions '@prompt_text.txt' --api-key "your-key"
"""

import argparse
import base64
import json
import logging
import os
import requests
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from PIL import Image
except ImportError:
    print("Error: PIL (Pillow) is required for image processing.")
    print("Install it with: pip install pillow")
    sys.exit(1)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
except UnicodeDecodeError:
    print("Warning: Could not load .env file due to encoding issues.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_file_content(file_path: str) -> str:
    """Load content from a file with proper error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{file_path}' not found.")
    except Exception as e:
        raise Exception(f"Error reading file '{file_path}': {e}")

def process_file_parameter(param_value: str) -> str:
    """Process parameter that might be a file reference."""
    if not param_value or not param_value.startswith('@'):
        return param_value
    
    file_path = param_value[1:]  # Remove @ symbol
    try:
        content = load_file_content(file_path)
        print(f"✓ Loaded content from file: {file_path}")
        return content
    except Exception as e:
        print(f"Error: {e}")
        raise

class PPQEnhancedClient:
    """Enhanced PPQ.ai client for document extraction."""
    
    def __init__(self, api_key: str, timeout: int = 180):
        self.api_key = api_key
        self.base_url = "https://api.ppq.ai"
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models from PPQ.ai."""
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to get available models: %s", str(e))
            raise
    
    def extract_json_from_response(self, response: str) -> str:
        """Extract JSON from response that might contain extra text."""
        import re
        
        # Remove any markdown formatting
        response = response.replace('```json', '').replace('```', '').strip()
        
        # Try to find JSON pattern - look for content between first { and last }
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            potential_json = response[start_idx:end_idx + 1]
            
            # Validate it's proper JSON
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                pass
        
        # If no valid JSON found, return original response
        return response
    
    def process_document_extraction(self, vision_data: str, instructions: str) -> str:
        """Process document extraction with strict JSON-only output."""
        
        def make_request():
            url = f"{self.base_url}/chat/completions"
            
            # Create system message that enforces JSON-only response
            system_message = """You are a JSON document extraction system. You MUST respond with VALID JSON ONLY.

CRITICAL RULES:
1. Output ONLY valid JSON - no explanations, no markdown, no extra text
2. Start your response with { and end with }
3. Do not use ```json or any code block formatting
4. Fill all fields with actual extracted data from the input
5. Use real bbox coordinates from the vision data
6. If data is missing, use empty string "" not null

You will be given vision extraction data and instructions. Follow the instructions to create the JSON output."""

            user_message = f"""{instructions}

VISION EXTRACTION DATA:
{vision_data}"""

            data = {
                "model": "gpt-4.1", 
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.0,  # Maximum consistency
                "max_tokens": 50000,  # Increased token limit
                "top_p": 1.0
            }
            
            response = requests.post(url, json=data, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        try:
            raw_response = make_request()
            # Clean the response to extract only JSON
            clean_json = self.extract_json_from_response(raw_response)
            return clean_json
        except Exception as e:
            logger.error("Failed to process document: %s", str(e))
            raise

def process_document_with_validation(client: PPQEnhancedClient, vision_data: str, instructions: str) -> None:
    """Process document extraction with full validation and error handling."""
    print("\n=== Enhanced Document Extraction ===")
    print(f"Vision data length: {len(vision_data)} characters")
    print(f"Instructions length: {len(instructions)} characters")
    
    try:
        print("🔄 Processing document extraction...")
        response = client.process_document_extraction(vision_data, instructions)
        
        print("\n📄 Raw Response:")
        print(response)
        
        # Validate JSON
        try:
            parsed_json = json.loads(response)
            print("\n✅ SUCCESS: Valid JSON response received!")
            
            # Display key extracted information
            if 'document_classification' in parsed_json:
                doc_type = parsed_json['document_classification'].get('specific_type', 'unknown')
                print(f"📊 Document Type: {doc_type}")
            
            if 'tab1_content' in parsed_json:
                fields = parsed_json['tab1_content'].get('fields_and_values', {})
                if fields:
                    print(f"📋 Extracted Fields: {len(fields)} sections")
            
            # Save to file
            output_file = "extracted_document.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_json, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved structured data to: {output_file}")
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            print(f"\n❌ ERROR: Invalid JSON response")
            print(f"JSON Error: {e}")
            print(f"Response length: {len(response)} characters")
            
            # Save raw response for debugging
            with open("debug_response.txt", 'w', encoding='utf-8') as f:
                f.write(response)
            print("💾 Raw response saved to: debug_response.txt")
            
            # Try to extract partial JSON
            print("\n🔧 Attempting to extract partial JSON...")
            try:
                # Look for any JSON-like structure
                import re
                json_matches = re.findall(r'\{[^{}]*\}', response)
                for i, match in enumerate(json_matches):
                    try:
                        partial = json.loads(match)
                        print(f"Found valid JSON fragment {i+1}: {match[:100]}...")
                    except:
                        continue
            except Exception as extract_error:
                print(f"Could not extract partial JSON: {extract_error}")
            
            return None
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        logger.error("Document processing failed: %s", str(e), exc_info=True)
        return None

def main():
    """Main function for enhanced document extraction."""
    parser = argparse.ArgumentParser(
        description="Enhanced PPQ.ai document extraction with JSON-only output",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--vision",
        type=str,
        help="Vision extraction data file. Use @filename.json to load from file",
        required=True
    )
    parser.add_argument(
        "--instructions",
        type=str,
        help="Processing instructions file. Use @filename.txt to load from file",
        required=True
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="PPQ.ai API key",
        default=os.environ.get("PPQ_API_KEY"),
        required=True
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout in seconds (default: 180)",
        default=180
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Process file parameters
    try:
        vision_data = process_file_parameter(args.vision)
        instructions = process_file_parameter(args.instructions)
    except Exception as e:
        print(f"Error loading files: {e}")
        return 1
    
    # Validate vision data is JSON
    try:
        json.loads(vision_data)
        print("✅ Vision data is valid JSON")
    except json.JSONDecodeError:
        print("❌ Error: Vision data is not valid JSON")
        return 1
    
    # Initialize client
    try:
        client = PPQEnhancedClient(api_key=args.api_key, timeout=args.timeout)
        client.get_available_models()
        print("✅ Successfully connected to PPQ.ai API")
    except Exception as e:
        print(f"❌ Failed to connect to PPQ.ai: {e}")
        return 1
    
    # Process the document
    result = process_document_with_validation(client, vision_data, instructions)
    
    if result:
        print("\n🎉 Document extraction completed successfully!")
        return 0
    else:
        print("\n💥 Document extraction failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())