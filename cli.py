#!/usr/bin/env python3
"""
Command-line interface for document extraction and processing.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

from dotenv import load_dotenv
from openrouter import OpenRouterClient
from openrouter.manager import ModelManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('document_processor.log')
    ]
)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process documents using OpenRouter's vision models."""
    
    def __init__(self, api_key: str):
        """Initialize the document processor with API credentials."""
        self.openrouter = OpenRouterClient(api_key=api_key)
        self.model_manager = ModelManager(api_key=api_key)
        
    async def process_document(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        model: str = "meta-llama/llama-3.2-11b-vision-instruct:free",
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> Dict:
        """
        Process a single document image.
        
        Args:
            input_path: Path to the input image file
            output_path: Path to save the output JSON (optional)
            model: Model to use for processing
            max_tokens: Maximum tokens for the API response
            temperature: Temperature for model sampling
            
        Returns:
            Dict containing the extraction results
        """
        logger.info(f"Processing document: {input_path}")
        
        # Prepare the vision model prompt
        vision_prompt = """
        You are a document analysis assistant. Extract all text with precise coordinates and formatting.
        
        Analyze this document image and extract ALL text content with precise geometric information.
        Return ONLY a valid JSON array of text blocks with the following structure:
        
        [
            {
                "text": "The extracted text content",
                "bbox": {"x": 0, "y": 0, "width": 100, "height": 20},
                "type": "header|body|table_cell|footer|signature|date|amount|other",
                "confidence": 0.95,
                "font_properties": {
                    "estimated_size": 12,
                    "bold": false,
                    "italic": false
                }
            }
        ]
        """
        
        try:
            # Process the image using OpenRouterClient
            response = self.openrouter.process_image(
                image_path=input_path,
                prompt=vision_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = self._parse_response(response)
            
            # Save the results if output path is provided
            if output_path:
                self._save_results(result, output_path)
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    def _parse_response(self, response: str) -> List[Dict]:
        """Parse the model response into a structured format."""
        try:
            # Clean the response
            cleaned = response.strip()
            
            # Try to extract JSON from markdown code blocks
            if '```json' in cleaned:
                cleaned = cleaned.split('```json')[1].split('```')[0].strip()
            elif '```' in cleaned:
                cleaned = cleaned.split('```')[1].split('```')[0].strip()
            
            # Try to parse the JSON
            try:
                result = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to find any JSON array in the response
                import re
                json_match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    raise ValueError("No valid JSON array found in response")
            
            # Handle different response formats
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                # Look for common response keys
                for key in ['text', 'content', 'result', 'data', 'blocks', 'items', 'elements']:
                    if key in result and isinstance(result[key], list):
                        return result[key]
                
                # If no list found, return all list values
                list_values = [v for v in result.values() if isinstance(v, list)]
                if list_values:
                    return list_values[0]
            
            # If we get here, return the raw response as a single text block
            return [{
                "text": str(response)[:1000],
                "bbox": {"x": 0, "y": 0, "width": 0, "height": 0},
                "type": "raw_response",
                "confidence": 0.0,
                "font_properties": {"estimated_size": 0, "bold": False, "italic": False}
            }]
            
        except Exception as e:
            logger.error(f"Error parsing model response: {str(e)}")
            raise
    
    def _save_results(self, results: Union[Dict, List], output_path: str) -> None:
        """Save the extraction results to a file."""
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Save the results as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            raise

async def process_directory(
    input_dir: str,
    output_dir: str,
    api_key: str,
    model: str = "meta-llama/llama-3.2-11b-vision-instruct:free",
    max_tokens: int = 4000,
    temperature: float = 0.1
) -> None:
    """Process all supported images in a directory."""
    processor = DocumentProcessor(api_key=api_key)
    
    # Supported image extensions
    extensions = {'.png', '.jpg', '.jpeg', '.tiff', '.tif'}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each image in the directory
    for filename in os.listdir(input_dir):
        if any(filename.lower().endswith(ext) for ext in extensions):
            input_path = os.path.join(input_dir, filename)
            output_filename = os.path.splitext(filename)[0] + '.json'
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                await processor.process_document(
                    input_path=input_path,
                    output_path=output_path,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue

def main():
    """Main entry point for the CLI."""
    # Load environment variables
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Process documents using OpenRouter vision models.')
    
    # Required arguments
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory (default: output.json or output_dir/)')
    
    # Optional arguments
    parser.add_argument('--api-key', help='OpenRouter API key (default: from OPENROUTER_API_KEY environment variable)',
                      default=os.getenv('OPENROUTER_API_KEY'))
    parser.add_argument('--model', default='meta-llama/llama-3.2-11b-vision-instruct:free',
                      help='Model to use for processing')
    parser.add_argument('--max-tokens', type=int, default=4000,
                      help='Maximum tokens for the API response')
    parser.add_argument('--temperature', type=float, default=0.1,
                      help='Temperature for model sampling (0.0-2.0)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate API key
    if not args.api_key:
        logger.error("API key is required. Set OPENROUTER_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Set default output path if not provided
    if not args.output:
        if os.path.isfile(args.input):
            args.output = 'output.json'
        else:
            args.output = 'output'
    
    try:
        # Process a single file
        if os.path.isfile(args.input):
            processor = DocumentProcessor(api_key=args.api_key)
            asyncio.run(
                processor.process_document(
                    input_path=args.input,
                    output_path=args.output,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature
                )
            )
        # Process a directory
        elif os.path.isdir(args.input):
            asyncio.run(
                process_directory(
                    input_dir=args.input,
                    output_dir=args.output,
                    api_key=args.api_key,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature
                )
            )
        else:
            logger.error(f"Input path does not exist: {args.input}")
            sys.exit(1)
            
        logger.info("Document processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
