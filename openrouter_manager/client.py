"""OpenRouter API client with model fallback support."""

import base64
import functools
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .model_manager import ModelManager

# Configure logging
logger = logging.getLogger(__name__)

# Default timeouts in seconds
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


class OpenRouterError(Exception):
    """Base exception for OpenRouter API errors."""
    pass


class OpenRouterClient:
    """Client for interacting with the OpenRouter API with model fallback support.
    
    This client handles:
    - Authentication and session management
    - Model selection and fallback
    - Request retries and error handling
    - Input validation and preprocessing
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            base_url: Base URL for the API (defaults to production)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize model manager
        self.model_manager = ModelManager(api_key=api_key, base_url=base_url)
        
        # Configure session with retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create and configure a requests session with retry logic.
        
        Returns:
            A configured requests.Session object with retry strategies
        """
        import time
        from urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter
        
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,  # Set to DEBUG for maximum verbosity
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger(__name__)
        
        # Enable HTTP request/response logging
        logging.getLogger('urllib3').setLevel(logging.DEBUG)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.DEBUG)
        
        # Configure the root logger to output to console
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        session = requests.Session()
        
        # Add request/response logging with timing
        def log_request_response(response, *args, **kwargs):
            request = response.request
            start_time = getattr(request, 'start_time', None)
            elapsed = f"{time.time() - start_time:.3f}s" if start_time else "unknown"
            
            # Log request
            logger.info(f"=== Request ===")
            logger.info(f"{request.method} {request.url} (elapsed: {elapsed})")
            
            # Log request headers (safely)
            headers = dict(request.headers)
            if 'Authorization' in headers:
                headers['Authorization'] = 'Bearer [REDACTED]'
            logger.debug(f"Request Headers: {json.dumps(headers, indent=2)}")
            
            # Log request body (safely)
            if request.body:
                try:
                    body = request.body
                    if isinstance(body, bytes):
                        body = body.decode('utf-8')
                    logger.debug(f"Request Body: {body}")
                except Exception as e:
                    logger.debug(f"Error logging request body: {str(e)}")
            
            # Log response
            logger.info(f"\n=== Response ===")
            logger.info(f"Status: {response.status_code} {response.reason}")
            
            # Log response headers
            logger.debug(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
            
            # Log response body (safely)
            try:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    logger.debug(f"Response Body: {json.dumps(response.json(), indent=2)}")
                else:
                    logger.debug(f"Response Body (first 500 chars): {response.text[:500]}")
            except Exception as e:
                logger.debug(f"Error logging response body: {str(e)}")
            
            logger.info("=" * 50)  # Add separator between requests
            return response
        
        # Register the hook
        session.hooks['response'] = [log_request_response]
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=self.max_retries,  # Total number of retries
            backoff_factor=1,  # Exponential backoff factor
            status_forcelist=[
                408,  # Request Timeout
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            ],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            respect_retry_after_header=True,  # Respect Retry-After header
            raise_on_status=False  # Don't raise on status codes in status_forcelist
        )
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools to cache
            pool_maxsize=10,  # Maximum number of connections to save in the pool
            pool_block=False  # Whether to block when no free connections are available
        )
        
        # Mount the retry adapter for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default timeout for all requests
        session.request = functools.partial(session.request, timeout=self.timeout)
        
        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "PieExtractor/1.0",
            "X-Title": "Pie Extractor"
        })
        
        # Configure session timeouts
        session.keep_alive = False  # Disable keep-alive to prevent connection issues
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            **self.session.headers,
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an API request with error handling and retries.
        
        Implements exponential backoff for rate limiting and server errors.
        """
        import time
        from requests.adapters import HTTPAdapter
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Set default timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
            
        # Configure retry strategy
        retry_delay = 1  # Start with 1 second delay
        max_retry_delay = 60  # Maximum 60 seconds between retries
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug("Making %s request to %s (attempt %d/%d)", 
                           method, url, attempt + 1, self.max_retries + 1)
                
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else None
                
                # Handle rate limiting (429) and server errors (5xx)
                if status_code in (429, 500, 502, 503, 504):
                    retry_after = int(e.response.headers.get('Retry-After', retry_delay))
                    wait_time = min(retry_after, max_retry_delay)
                    
                    logger.warning(
                        "API returned %s. Retrying in %d seconds... (attempt %d/%d)",
                        status_code, wait_time, attempt + 1, self.max_retries + 1
                    )
                    
                    if attempt < self.max_retries:
                        time.sleep(wait_time)
                        retry_delay = min(retry_delay * 2, max_retry_delay)  # Exponential backoff
                        continue
                
                # For other HTTP errors, try to extract error message
                error_msg = f"API request failed with status {status_code}"
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        error_msg = error_data.get('error', {}).get('message', error_msg)
                    except ValueError:
                        error_msg = e.response.text or error_msg
                
                raise OpenRouterError(error_msg) from e
                
            except (requests.exceptions.ConnectionError, 
                   requests.exceptions.Timeout) as e:
                if attempt < self.max_retries:
                    logger.warning(
                        "Connection error: %s. Retrying in %d seconds... (attempt %d/%d)",
                        str(e), retry_delay, attempt + 1, self.max_retries + 1
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)  # Exponential backoff
                    continue
                raise OpenRouterError(f"Connection failed after {self.max_retries} retries") from e
                
            except requests.exceptions.RequestException as e:
                raise OpenRouterError(f"Request failed: {str(e)}") from e
        
        # This should never be reached due to the for loop structure
        raise OpenRouterError("Max retries exceeded")
    
    def _get_model_chain(self, category: str) -> List[str]:
        """Get the model fallback chain for a category."""
        return self.model_manager.get_model_fallback_chain(category)
    
    def _process_image(self, image_path: Union[str, bytes, Path]) -> str:
        """Process an image file into a base64-encoded string."""
        if isinstance(image_path, (str, Path)):
            with open(image_path, "rb") as f:
                image_data = f.read()
        elif isinstance(image_path, bytes):
            image_data = image_path
        else:
            raise ValueError("image_path must be a file path or bytes")
            
        return f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        model_category: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a chat completion with automatic model fallback.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Specific model ID to use (optional)
            model_category: Model category to use for fallback (e.g., 'vision', 'reasoning')
            **kwargs: Additional parameters for the API request
            
        Returns:
            API response with the completion
            
        Raises:
            OpenRouterError: If all model attempts fail
        """
        # If a specific model is provided, use it directly
        if model:
            models_to_try = [model]
        # Otherwise, use the model fallback chain for the category
        elif model_category:
            models_to_try = self._get_model_chain(model_category)
            if not models_to_try:
                raise OpenRouterError(f"No available models found for category: {model_category}")
        else:
            raise ValueError("Either 'model' or 'model_category' must be provided")
        
        # Try each model in the fallback chain
        last_error = None
        for model_id in models_to_try:
            try:
                logger.info("Trying model: %s", model_id)
                print(f"DEBUG: Attempting to use model: {model_id}")
                
                # Prepare the request payload
                payload = {
                    "model": model_id,
                    "messages": messages,
                    **kwargs
                }
                print(f"DEBUG: Request payload: {json.dumps(payload, indent=2)}")
                
                # Make the API request
                print("DEBUG: Sending request to OpenRouter API...")
                response = self._make_request(
                    "POST",
                    "/chat/completions",
                    json=payload
                )
                
                # If we got here, the request was successful
                logger.info("Successfully completed request with model: %s", model_id)
                print(f"DEBUG: Received response: {json.dumps(response, indent=2)}")
                return response
                
            except OpenRouterError as e:
                last_error = e
                error_msg = f"Model {model_id} failed: {str(e)}"
                logger.warning(error_msg)
                print(f"ERROR: {error_msg}")
                continue
        
        # If we've tried all models and none worked, raise the last error
        raise OpenRouterError(
            f"All model attempts failed. Last error: {str(last_error)}"
        )
    
    def process_text(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Process text using the best available reasoning model.
        
        Args:
            text: Input text to process
            model: Specific model ID to use (optional)
            **kwargs: Additional parameters for the API request
            
        Returns:
            Processed text response
        """
        print(f"DEBUG: Processing text with model: {model or 'best reasoning model'}")
        messages = [{
            "role": "user",
            "content": text
        }]
        
        # Always use reasoning model category unless a specific model is provided
        model_category = None if model else "reasoning"
        print(f"DEBUG: Using model category: {model_category}")
        
        response = self.chat_completion(
            messages=messages,
            model=model,
            model_category=model_category,
            **kwargs
        )
        
        return response["choices"][0]["message"]["content"]
    
    def process_image(
        self,
        image_path: Union[str, bytes, Path],
        prompt: str = "Describe the content of this image.",
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Process an image using the best available vision model.
        
        Args:
            image_path: Path to the image file or image bytes
            prompt: Text prompt to accompany the image
            model: Specific model ID to use (optional)
            **kwargs: Additional parameters for the API request
            
        Returns:
            Text description or analysis of the image
        """
        print(f"DEBUG: Processing image with model: {model or 'best vision model'}")
        
        # Process the image
        image_data = self._process_image(image_path)
        
        # Prepare the message with image
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_data}
                }
            ]
        }]
        
        # Always use vision model category unless a specific model is provided
        model_category = None if model else "vision"
        print(f"DEBUG: Using model category: {model_category}")
        
        # Make the API request with model fallback
        response = self.chat_completion(
            messages=messages,
            model=model,
            model_category=model_category,
            **kwargs
        )
        
        return response["choices"][0]["message"]["content"]
    
    def get_available_models(self, refresh: bool = False) -> Dict[str, Any]:
        """Get the list of available models.
        
        Args:
            refresh: If True, force a refresh of the model cache
            
        Returns:
            Dictionary of available models
        """
        return self.model_manager.fetch_models(force_refresh=refresh)
    
    def get_best_model(self, category: str) -> Optional[str]:
        """Get the best available model for a category.
        
        Args:
            category: Model category (e.g., 'vision', 'reasoning')
            
        Returns:
            Model ID of the best available model, or None if none found
        """
        return self.model_manager.get_best_model(category)
    
    def close(self) -> None:
        """Close the client and release resources."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
