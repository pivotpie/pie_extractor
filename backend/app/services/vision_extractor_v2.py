"""
Vision-based document extractor service using OpenRouter models with dynamic model selection.

This module provides document extraction capabilities using vision and reasoning models
through OpenRouter API with dynamic model selection and fallback. It extracts text and 
geometric information from document images and processes them into structured JSON output.
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from functools import wraps
from pathlib import Path
import mimetypes
from PIL import Image, ImageOps
import base64
from io import BytesIO

# Add project root to path to import openrouter_manager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from openrouter_manager.client import OpenRouterClient
from openrouter_manager.model_manager import ModelManager

from ..core.config import settings

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

class TimingDecorator:
    """Decorator to measure and log function execution time."""
    
    def __init__(self, name: str):
        self.name = name
        self.timings = {}
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                self.timings[self.name] = elapsed
                logger.debug(f"{self.name} completed in {elapsed:.2f}ms")
                return result
            except Exception as e:
                logger.error(f"Error in {self.name}: {str(e)}", exc_info=True)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
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
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class DocumentExtractor:
    """
    Extracts and processes document content using vision and reasoning models
    with dynamic model selection and fallback.
    """
    
    def __init__(self, openrouter_client: Optional[OpenRouterClient] = None):
        """
        Initialize the document extractor with an optional OpenRouter client.
        
        Args:
            openrouter_client: Optional pre-configured OpenRouterClient instance.
                            If not provided, a default one will be created.
        """
        self.openrouter = openrouter_client or self._create_default_client()
        self.model_manager = ModelManager(api_key=self.openrouter.api_key)
        self.timings = {}
    
    def _create_default_client(self) -> OpenRouterClient:
        """Create a default OpenRouter client with configuration from settings."""
        return OpenRouterClient(
            api_key=settings.OPENROUTER_API_KEY,
            timeout=getattr(settings, 'OPENROUTER_TIMEOUT', 30),
            max_retries=getattr(settings, 'OPENROUTER_MAX_RETRIES', 3)
        )
    
    @TimingDecorator("vision_processing")
    async def extract_with_vision_model(self, image_path: str) -> List[TextBlock]:
        """
        Extract text and geometry from a document image using the vision model.
        
        Args:
            image_path: Path to the image file to process
            
        Returns:
            List of text blocks with extracted information
        
        Raises:
            ValueError: If the image format is not supported
            Exception: For any errors during processing
        """
        # Validate image format
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type not in SUPPORTED_IMAGE_TYPES:
            raise ValueError(f"Unsupported image type: {mime_type}")
        
        # Get the best vision model
        vision_model = self.model_manager.get_best_model("vision")
        if not vision_model:
            raise RuntimeError("No suitable vision model available")
        
        logger.info(f"Using vision model: {vision_model}")
        
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
                
                # Convert image to base64
                img_base64 = self._image_to_base64(img)
                
                # Prepare the messages for the vision model
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": vision_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ]
                
                # Call the vision model with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = await asyncio.to_thread(
                            self.openrouter.chat.completions.create,
                            model=vision_model,
                            messages=messages,
                            max_tokens=4000
                        )
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
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
            
        Raises:
            RuntimeError: If no suitable reasoning model is available
            Exception: For any errors during processing
        """
        # Get the best reasoning model
        reasoning_model = self.model_manager.get_best_model("reasoning")
        if not reasoning_model:
            raise RuntimeError("No suitable reasoning model available")
        
        logger.info(f"Using reasoning model: {reasoning_model}")
        
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
            # Prepare the messages for the reasoning model
            messages = [
                {"role": "system", "content": reasoning_prompt},
                {"role": "user", "content": json.dumps({"text_blocks": text_blocks}, indent=2)}
            ]
            
            # Call the reasoning model with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await asyncio.to_thread(
                        self.openrouter.chat.completions.create,
                        model=reasoning_model,
                        messages=messages,
                        max_tokens=4000,
                        response_format={"type": "json_object"}
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
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
            
        Raises:
            Exception: If any error occurs during processing
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting document extraction for: {image_path}")
            
            # Validate image file exists and is readable
            if not os.path.isfile(image_path):
                error_msg = f"Image file not found: {image_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
                
            # Check file permissions
            if not os.access(image_path, os.R_OK):
                error_msg = f"Cannot read image file (permission denied): {image_path}"
                logger.error(error_msg)
                raise PermissionError(error_msg)
            
            # Step 1: Extract text and geometry with vision model
            logger.info("Starting vision model processing...")
            try:
                text_blocks = await self.extract_with_vision_model(image_path)
                logger.info(f"Vision model processing completed. Extracted {len(text_blocks)} text blocks.")
            except Exception as e:
                logger.error(f"Vision model processing failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Vision model processing failed: {str(e)}") from e
            
            # Step 2: Process with reasoning model
            logger.info("Starting reasoning model processing...")
            try:
                document_structure = await self.process_with_reasoning_model(text_blocks)
                logger.info("Reasoning model processing completed successfully.")
            except Exception as e:
                logger.error(f"Reasoning model processing failed: {str(e)}", exc_info=True)
                # Include the text blocks in the error for debugging
                error_info = {
                    "error": str(e),
                    "text_blocks_sample": text_blocks[:3] if text_blocks else []
                }
                logger.debug(f"Error context: {json.dumps(error_info, indent=2)}")
                raise RuntimeError(f"Reasoning model processing failed: {str(e)}") from e
            
            # Prepare the final result
            total_time = time.time() - start_time
            logger.info(f"Document extraction completed in {total_time:.2f} seconds")
            
            result = {
                "extraction_metadata": {
                    "source_file": os.path.basename(image_path),
                    "extraction_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "processing_time": {
                        "vision": self.timings.get("vision_processing", 0) / 1000,  # Convert ms to seconds
                        "reasoning": self.timings.get("reasoning_processing", 0) / 1000,
                        "total": total_time
                    },
                    "model_versions": {
                        "vision": self.model_manager.get_best_model("vision"),
                        "reasoning": self.model_manager.get_best_model("reasoning")
                    },
                    "text_blocks_count": len(text_blocks) if text_blocks else 0
                },
                "document": document_structure
            }
            
            logger.debug(f"Extraction result metadata: {json.dumps(result['extraction_metadata'], indent=2)}")
            return result
            
        except Exception as e:
            # Log the full error with traceback
            logger.error(f"Document extraction failed after {time.time() - start_time:.2f} seconds: {str(e)}", exc_info=True)
            
            # Include additional context in the error message
            error_context = {
                "error": str(e),
                "image_path": image_path,
                "elapsed_time": time.time() - start_time,
                "vision_model": self.model_manager.get_best_model("vision") if hasattr(self, 'model_manager') else 'N/A',
                "reasoning_model": self.model_manager.get_best_model("reasoning") if hasattr(self, 'model_manager') else 'N/A'
            }
            logger.error(f"Error context: {json.dumps(error_context, indent=2)}")
            
            # Re-raise with more context if it's not already a specific error
            if not isinstance(e, (FileNotFoundError, PermissionError, RuntimeError)):
                raise RuntimeError(f"Document extraction failed: {str(e)}") from e
            raise
    
    # Helper methods
    
    def _image_to_base64(self, image: Image.Image, format: str = "JPEG", quality: int = 90) -> str:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            format: Output format (JPEG, PNG, etc.)
            quality: Quality for JPEG (1-100)
            
        Returns:
            Base64 encoded string of the image
        """
        buffered = BytesIO()
        image.save(buffered, format=format, quality=quality)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def _parse_vision_response(self, response: Any) -> List[TextBlock]:
        """
        Parse and validate the vision model response.
        
        Args:
            response: Raw response from the vision model
            
        Returns:
            List of validated text blocks
            
        Raises:
            ValueError: If the response format is invalid
        """
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
            raise ValueError("Invalid JSON response from vision model") from e
        except Exception as e:
            logger.error(f"Error parsing vision response: {str(e)}")
            raise
    
    def _parse_reasoning_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse and validate the reasoning model response.
        
        Args:
            response: Raw response from the reasoning model
            
        Returns:
            Parsed document structure
            
        Raises:
            ValueError: If the response format is invalid
        """
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
            raise ValueError("Invalid JSON response from reasoning model") from e
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
