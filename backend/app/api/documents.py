from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import logging
import os
import uuid
from pathlib import Path

from ..database import get_db
from ..models.user import User
from ..models.document import DocumentStatus
from ..schemas.document import (
    Document, DocumentCreate, DocumentUpdate, 
    DocumentWithChunks, DocumentChunk, DocumentUploadResponse,
    VisionExtractionRequest, VisionExtractionResponse
)
from ..services.document_service import DocumentService
from ..services.vision_extractor_v2 import DocumentExtractor, SUPPORTED_IMAGE_TYPES
from ..core.security import get_current_active_user
from ..core.config import settings

# Import OpenRouter client for direct usage if needed
from openrouter_manager.client import OpenRouterClient

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document.
    
    Supported file types: PDF, DOCX, Images (JPEG, PNG, GIF), Text
    """
    try:
        service = DocumentService(db)
        document = await service.upload_document(
            file=file,
            user_id=current_user.id,
            title=title,
            description=description
        )
        
        return {
            "document": document,
            "message": "Document uploaded successfully"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing document upload"
        )

@router.get("", response_model=List[Document])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all documents for the current user."""
    service = DocumentService(db)
    return service.list_documents(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

@router.get("/{document_id}", response_model=Document)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a document by ID."""
    service = DocumentService(db)
    return service.get_document(document_id, current_user.id)

@router.get("/{document_id}/with-chunks", response_model=DocumentWithChunks)
def get_document_with_chunks(
    document_id: int,
    skip_chunks: int = 0,
    limit_chunks: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a document with its chunks."""
    service = DocumentService(db)
    return service.get_document_with_chunks(
        document_id=document_id,
        user_id=current_user.id,
        skip_chunks=skip_chunks,
        limit_chunks=limit_chunks
    )

@router.patch("/{document_id}", response_model=Document)
def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update document metadata."""
    service = DocumentService(db)
    return service.update_document(
        document_id=document_id,
        user_id=current_user.id,
        update_data=document_update
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    service = DocumentService(db)
    service.delete_document(document_id, current_user.id)
    return None

@router.get("/{document_id}/chunks", response_model=List[DocumentChunk])
def list_document_chunks(
    document_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List chunks for a document."""
    service = DocumentService(db)
    return service.get_document_chunks(
        document_id=document_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

@router.post("/extract/vision", response_model=VisionExtractionResponse)
async def extract_document_vision(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Extract structured data from a document image using vision and reasoning models
    with dynamic model selection and fallback.
    
    Supported image types: PNG, JPEG, JPG, TIFF
    """
    start_time = time.time()
    file_path = None
    
    try:
        # Log the start of the request
        logger.info(f"Starting document extraction request for user {current_user.id}")
        
        # Check file type
        mime_type = file.content_type
        if mime_type not in SUPPORTED_IMAGE_TYPES:
            error_msg = f"Unsupported file type: {mime_type}. Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file.file.seek(0, 2)  # Seek to end of file
        file_size = file.file.tell()
        file.file.seek(0)  # Reset file pointer
        
        if file_size > max_size:
            error_msg = f"File too large. Maximum size is {max_size/(1024*1024):.1f}MB, got {file_size/(1024*1024):.1f}MB"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except Exception as e:
            error_msg = f"Failed to create upload directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # Generate a unique filename with original extension
        file_ext = Path(file.filename).suffix.lower() if file.filename else '.bin'
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save the uploaded file with error handling
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            logger.info(f"Saved uploaded file to {file_path} ({len(content)} bytes)")
        except Exception as e:
            error_msg = f"Failed to save uploaded file: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # Initialize the OpenRouter client and extractor
        try:
            logger.info("Initializing OpenRouter client and DocumentExtractor")
            openrouter_client = OpenRouterClient(api_key=settings.OPENROUTER_API_KEY)
            extractor = DocumentExtractor(openrouter_client=openrouter_client)
            logger.info("Successfully initialized OpenRouter client and DocumentExtractor")
        except Exception as e:
            error_msg = f"Failed to initialize OpenRouter client: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # Process the document
        try:
            logger.info("Starting document extraction process")
            result = await extractor.extract_document(file_path)
            logger.info(f"Document extraction completed in {time.time() - start_time:.2f} seconds")
        except Exception as e:
            error_msg = f"Document extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # Prepare the response
        response_data = {
            "status": "completed",
            "result": result,
            "processing_time": result["extraction_metadata"]["processing_time"]["total"],
            "model_used": {
                "vision": result["extraction_metadata"]["model_versions"]["vision"],
                "reasoning": result["extraction_metadata"]["model_versions"]["reasoning"]
            }
        }
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = f"Unexpected error during document extraction: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
        
    finally:
        # Clean up the temporary file if it was created
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {file_path}: {str(e)}")

# Background task for async processing
async def process_document_async(
    file_path: str,
    user_id: int,
    document_id: int,
    db: Session,
    openrouter_api_key: str
):
    """
    Background task to process a document asynchronously.
    
    Args:
        file_path: Path to the file to process
        user_id: ID of the user who owns the document
        document_id: ID of the document in the database
        db: Database session
        openrouter_api_key: API key for OpenRouter
    """
    doc_service = DocumentService(db)
    
    try:
        # Initialize OpenRouter client and extractor
        openrouter_client = OpenRouterClient(api_key=openrouter_api_key)
        extractor = DocumentExtractor(openrouter_client=openrouter_client)
        
        # Process the document
        result = await extractor.extract_document(file_path)
        
        # Update the document status and store the result
        await doc_service.update_document_extraction_result(
            document_id=document_id,
            status=DocumentStatus.PROCESSED,
            extraction_result=result
        )
        
        logger.info(f"Successfully processed document {document_id}")
        
    except Exception as e:
        logger.error(f"Async document processing failed: {str(e)}", exc_info=True)
        # Update status to failed
        if 'doc_service' in locals():
            await doc_service.update_document_status(
                document_id=document_id,
                status=DocumentStatus.FAILED,
                error_message=str(e)
            )
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Deleted temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {str(e)}")

@router.post("/extract/vision/async", response_model=Dict[str, Any])
async def extract_document_vision_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start an async document extraction task with dynamic model selection.
    
    This endpoint queues the document for processing and returns immediately.
    It uses the OpenRouter manager for dynamic model selection and fallback.
    
    Use the returned task_id to check the status later.
    """
    # Check file type
    mime_type = file.content_type
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {mime_type}. Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
        )
    
    try:
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate a unique filename and task ID
        file_ext = Path(file.filename).suffix if file.filename else '.bin'
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, filename)
        task_id = str(uuid.uuid4())
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create a document record
        doc_service = DocumentService(db)
        document = await doc_service.create_document(
            document=DocumentCreate(
                title=file.filename or "Untitled Document",
                file_path=file_path,
                mime_type=mime_type,
                status=DocumentStatus.PROCESSING
            ),
            user_id=current_user.id
        )
        
        # Start the background task with the OpenRouter API key
        background_tasks.add_task(
            process_document_async,
            file_path=file_path,
            user_id=current_user.id,
            document_id=document.id,
            db=db,
            openrouter_api_key=settings.OPENROUTER_API_KEY
        )
        
        return {
            "status": "processing",
            "task_id": task_id,
            "document_id": document.id,
            "message": "Document is being processed in the background with dynamic model selection"
        }
        
    except Exception as e:
        logger.error(f"Error starting async extraction: {str(e)}", exc_info=True)
        # Clean up the file if it was created
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up file {file_path}: {str(cleanup_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start document processing: {str(e)}"
        )
