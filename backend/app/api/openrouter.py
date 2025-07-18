"""OpenRouter API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional

from app.core.openrouter import get_async_openrouter_client
from app.core.config import settings
from app.core.openrouter import OpenRouterClient

router = APIRouter()

@router.get("/models", response_model=List[Dict[str, Any]])
async def list_models(
    refresh: bool = False,
    client: OpenRouterClient = Depends(get_async_openrouter_client)
):
    """List all available models from OpenRouter.
    
    Args:
        refresh: If True, force refresh the model cache
        
    Returns:
        List of available models with their details
    """
    try:
        models = client.get_available_models(refresh=refresh)
        return list(models.values())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch models: {str(e)}"
        )

@router.get("/models/best")
async def get_best_model(
    category: str,
    client: OpenRouterClient = Depends(get_async_openrouter_client)
):
    """Get the best available model for a specific category.
    
    Args:
        category: Model category (e.g., 'vision', 'reasoning')
        
    Returns:
        Best model ID for the specified category
    """
    try:
        model_id = client.get_best_model(category)
        if not model_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No suitable model found for category: {category}"
            )
        return {"model_id": model_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get best model: {str(e)}"
        )

@router.post("/chat/completions")
async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    model_category: Optional[str] = None,
    client: OpenRouterClient = Depends(get_async_openrouter_client)
):
    """Generate a chat completion using OpenRouter.
    
    Args:
        messages: List of message objects with 'role' and 'content'
        model: Specific model ID to use (optional)
        model_category: Model category to use for fallback (e.g., 'vision', 'reasoning')
        
    Returns:
        Chat completion response from OpenRouter
    """
    try:
        response = client.chat_completion(
            messages=messages,
            model=model,
            model_category=model_category
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate completion: {str(e)}"
        )
