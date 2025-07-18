"""
Vision-based document extractor service using OpenRouter models.

This module provides document extraction capabilities using vision and reasoning models
through OpenRouter API. It extracts text and geometric information from document images
and processes them into structured JSON output.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
from functools import wraps
from pathlib import Path
import mimetypes
from PIL import Image, ImageOps
import numpy as np
import requests
from pydantic import BaseModel, Field, validator

from ..core.config import settings
from ..core.openrouter import OpenRouterClient

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases
BoundingBox = Dict[str, float]
TextBlock = Dict[str, Any]
DocumentElements = Dict[str, Any]

# Constants
SUPPORTED_IMAGE_TYPES = {
    'image/png', 'image/jpeg', 'image/jpg', 'image/tiff', 'image/tif'
}

# Vision model configuration
VISION_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free"
REASONING_MODEL = "deepseek/deepseek-r1-0528:free"

# Timeout and retry settings
REQUEST_TIMEOUT = 300  # 5 minutes
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

class TimingDecorator:
    """Decorator to measure and log function execution time."""
    
    def __init__(self, name: str):
        self.name = name
        self.timings = {}
    
    def __call__(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                self.timings[self.name] = elapsed
                logger.debug(f"{self.name} completed in {elapsed:.2f}ms")
                return result
            except Exception as e:
                logger.error(f"Error in {self.name}: {str(e)}", exc_info=True)
                raise
        return wrapper

class DocumentExtractor:
    """Extracts and processes document content using vision and reasoning models."""
    
    def __init__(self, openrouter_client: Optional[OpenRouterClient] = None):
        """Initialize the document extractor with an optional OpenRouter client."""
        self.openrouter = openrouter_client or OpenRouterClient()
        self.timings = {}
        
    @TimingDecorator("vision_processing")
    async def extract_with_vision_model(self, image_path: str) -> List[TextBlock]:
        """
        Extract text and geometry from a document image using the vision model.
        
        Args:
            image_path: Path to the image file to process
            
        Returns:
            List of text blocks with extracted information
        """
        # Validate image format
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type not in SUPPORTED_IMAGE_TYPES:
            raise ValueError(f"Unsupported image type: {mime_type}")
        
        # Prepare the vision prompt
        vision_prompt = """
        Analyze this document image and extract ALL text content with precise geometric information.

        For each text element, provide:
        1. The exact text content
        2. Bounding box coordinates (x, y, width, height) in pixels
        3. Text type classification (header, body, table_cell, footer, etc.)
        4. Confidence level (0.0-1.0)
        5. Font characteristics (size estimate, bold/italic if detectable)

        Output format should be a structured list of text blocks:
        [
          {
            "text": "extracted text",
            "bbox": {"x": 0, "y": 0, "width": 100, "height": 20},
            "type": "header|body|table_cell|footer|signature|date|amount",
            "confidence": 0.95,
            "font_properties": {"estimated_size": 12, "bold": false, "italic": false}
          }
        ]
        """
        
        try:
            # Read and preprocess image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get image dimensions
                width, height = img.size
                
                # Prepare the payload for the vision model
                payload = {
                    "model": VISION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": vision_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{self._image_to_base64(img)}"}}
                            ]
                        }
                    ],
                    "max_tokens": 4096
                }
                
                # Call the vision model
                response = await self._call_openrouter_api(payload)
                
                # Parse and validate the response
                text_blocks = self._parse_vision_response(response)
                
                # Add page dimensions to each block
                for block in text_blocks:
                    block['page_dimensions'] = {"width": width, "height": height}
                
                return text_blocks
                
        except Exception as e:
            logger.error(f"Error in vision model processing: {str(e)}")
            raise
    
    @TimingDecorator("reasoning_processing")
    async def process_with_reasoning_model(self, text_blocks: List[TextBlock]) -> DocumentElements:
        """
        Process extracted text blocks with the reasoning model to create structured output.
        
        Args:
            text_blocks: List of text blocks from vision processing
            
        Returns:
            Structured document elements
        """
        reasoning_prompt = """
        You are an expert document analysis system. Analyze the provided text blocks with coordinates 
        and create a structured representation of the document.

        Input: List of text blocks with coordinates, text content, and metadata
        Task: Create a comprehensive JSON structure representing the document

        Requirements:
        1. Document Classification: Identify document type and purpose
        2. Logical Grouping: Group related text blocks into sections
        3. Table Reconstruction: Rebuild tables from individual cell extractions
        4. Coordinate Optimization: Adjust coordinates to encompass grouped elements
        5. Content Validation: Check for completeness and logical consistency
        6. Hierarchy Detection: Identify headers, subheaders, and content relationships

        Output JSON Structure:
        {
          "document_metadata": {
            "type": "invoice|receipt|form|letter|other",
            "confidence": 0.95,
            "page_dimensions": {"width": 2480, "height": 3508},
            "total_elements": 25
          },
          "elements": [
            {
              "id": "element_1",
              "type": "header|company_info|customer_info|table|total|signature|date",
              "content": "text or structured data",
              "bbox": {"x": 0, "y": 0, "width": 0, "height": 0},
              "confidence": 0.95,
              "children": [],
              "properties": {}
            }
          ]
        }
        """
        
        try:
            # Prepare the payload for the reasoning model
            payload = {
                "model": REASONING_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": reasoning_prompt
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"text_blocks": text_blocks}, indent=2)
                    }
                ],
                "max_tokens": 4096
            }
            
            # Call the reasoning model
            response = await self._call_openrouter_api(payload)
            
            # Parse and validate the response
            return self._parse_reasoning_response(response)
            
        except Exception as e:
            logger.error(f"Error in reasoning model processing: {str(e)}")
            raise
    
    async def extract_document(self, image_path: str) -> Dict[str, Any]:
        """
        Process a document image and return structured data.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted document data
        """
        start_time = time.time()
        
        try:
            # Step 1: Extract text and geometry with vision model
            text_blocks = await self.extract_with_vision_model(image_path)
            
            # Step 2: Process with reasoning model
            document_structure = await self.process_with_reasoning_model(text_blocks)
            
            # Prepare the final result
            result = {
                "extraction_metadata": {
                    "source_file": os.path.basename(image_path),
                    "extraction_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "processing_time": {
                        "vision": self.timings.get("vision_processing", 0) / 1000,  # Convert ms to seconds
                        "reasoning": self.timings.get("reasoning_processing", 0) / 1000,
                        "total": time.time() - start_time
                    },
                    "model_versions": {
                        "vision": VISION_MODEL,
                        "reasoning": REASONING_MODEL
                    }
                },
                "document": document_structure
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Document extraction failed: {str(e)}")
            raise
    
    # Helper methods
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        import base64
        from io import BytesIO
        
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=90)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    async def _call_openrouter_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call to OpenRouter with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.openrouter.chat.completions.create(**payload)
                return response
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    
    def _parse_vision_response(self, response: Dict[str, Any]) -> List[TextBlock]:
        """Parse and validate the vision model response."""
        try:
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Parse the JSON content
            text_blocks = json.loads(content)
            
            # Validate the structure
            if not isinstance(text_blocks, list):
                raise ValueError("Expected a list of text blocks")
                
            # Validate each block
            for block in text_blocks:
                if not all(key in block for key in ["text", "bbox", "type", "confidence"]):
                    raise ValueError("Invalid text block structure")
                    
                # Validate bbox structure
                bbox = block["bbox"]
                if not all(key in bbox for key in ["x", "y", "width", "height"]):
                    raise ValueError("Invalid bbox structure")
            
            return text_blocks
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision model response: {str(e)}")
            raise ValueError("Invalid JSON response from vision model")
        except Exception as e:
            logger.error(f"Error parsing vision response: {str(e)}")
            raise
    
    def _parse_reasoning_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the reasoning model response."""
        try:
            # Extract the content from the response
            content = response.choices[0].message.content
            
            # Parse the JSON content
            document_data = json.loads(content)
            
            # Validate the structure
            if not isinstance(document_data, dict) or "document_metadata" not in document_data:
                raise ValueError("Invalid document structure")
                
            # Add validation for required fields
            metadata = document_data["document_metadata"]
            if not all(key in metadata for key in ["type", "confidence"]):
                raise ValueError("Missing required document metadata")
                
            return document_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reasoning model response: {str(e)}")
            raise ValueError("Invalid JSON response from reasoning model")
        except Exception as e:
            logger.error(f"Error parsing reasoning response: {str(e)}")
            raise

# Example usage
async def main():
    # Initialize the extractor
    extractor = DocumentExtractor()
    
    # Process a document
    try:
        result = await extractor.extract_document("path/to/your/document.jpg")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
