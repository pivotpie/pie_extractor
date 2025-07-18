import os
import shutil
import uuid
from typing import List, Optional, BinaryIO, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import magic

from ..models.document import Document as DocumentModel, DocumentChunk, DocumentType, DocumentStatus
from ..schemas.document import DocumentCreate, DocumentUpdate, DocumentWithChunks
from ..core.config import settings

# Supported MIME types and their corresponding document types
SUPPORTED_MIME_TYPES = {
    'application/pdf': DocumentType.PDF,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocumentType.DOCX,
    'image/jpeg': DocumentType.IMAGE,
    'image/png': DocumentType.IMAGE,
    'image/gif': DocumentType.IMAGE,
    'text/plain': DocumentType.TEXT,
}

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    def _get_document_type(self, mime_type: str) -> DocumentType:
        """Get document type from MIME type."""
        doc_type = SUPPORTED_MIME_TYPES.get(mime_type.lower())
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {mime_type}"
            )
        return doc_type

    def _save_uploaded_file(self, file: UploadFile, user_id: int) -> str:
        """Save uploaded file to disk and return the file path."""
        # Create user-specific directory if it doesn't exist
        user_dir = os.path.join(self.upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(user_dir, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return file_path

    async def upload_document(
        self, 
        file: UploadFile, 
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> DocumentModel:
        """Upload and save a document."""
        # Read first chunk to detect MIME type
        file_content = await file.read(1024)
        await file.seek(0)  # Reset file pointer
        
        # Detect MIME type
        mime_type = magic.from_buffer(file_content, mime=True)
        file_type = self._get_document_type(mime_type)
        
        # Get file size
        file_size = 0
        if hasattr(file, 'size'):
            file_size = file.size
        else:
            # For in-memory files, we need to read to get size
            file_content_full = await file.read()
            file_size = len(file_content_full)
            await file.seek(0)  # Reset file pointer
        
        # Save file to disk
        file_path = self._save_uploaded_file(file, user_id)
        
        # Create document record
        doc_data = DocumentCreate(
            title=title or os.path.splitext(file.filename)[0],
            description=description,
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
            page_count=1  # Default, can be updated later
        )
        
        db_document = DocumentModel(
            **doc_data.dict(),
            file_path=file_path,
            owner_id=user_id,
            status=DocumentStatus.UPLOADED
        )
        
        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)
        
        # TODO: Start background task for document processing
        
        return db_document

    def get_document(self, document_id: int, user_id: int) -> DocumentModel:
        """Get a document by ID if the user has access to it.
        
        Args:
            document_id: The ID of the document to retrieve
            user_id: The ID of the user making the request
            
        Returns:
            The requested document if found and accessible
            
        Raises:
            HTTPException: If document is not found or access is denied
        """
        try:
            with self.db.begin():
                document = self.db.query(DocumentModel).filter(
                    DocumentModel.id == document_id,
                    DocumentModel.owner_id == user_id
                ).with_for_update(skip_locked=True).first()
                
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Document not found or access denied"
                    )
                    
                return document
                
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving document"
            )

    def list_documents(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DocumentModel]:
        """List all documents for a user.
        
        Args:
            user_id: The ID of the user
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of documents belonging to the user
        """
        try:
            with self.db.begin():
                return self.db.query(DocumentModel)\
                    .filter(DocumentModel.owner_id == user_id)\
                    .order_by(DocumentModel.created_at.desc())\
                    .offset(skip)\
                    .limit(limit)\
                    .all()
                    
        except Exception as e:
            logger.error(f"Error listing documents for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving documents"
            )

    def update_document(
        self, 
        document_id: int, 
        user_id: int, 
        update_data: DocumentUpdate
    ) -> DocumentModel:
        """Update document metadata.
        
        Args:
            document_id: The ID of the document to update
            user_id: The ID of the user making the request
            update_data: The fields to update
            
        Returns:
            The updated document
            
        Raises:
            HTTPException: If document is not found or access is denied
        """
        try:
            with self.db.begin():
                document = self.get_document(document_id, user_id)
                
                # Only allow updating certain fields
                allowed_fields = {
                    'title', 'description', 'status', 
                    'processing_errors', 'structure'
                }
                
                update_dict = update_data.dict(exclude_unset=True)
                for field, value in update_dict.items():
                    if field in allowed_fields:
                        setattr(document, field, value)
                
                document.updated_at = datetime.utcnow()
                self.db.add(document)
                
            # Refresh to get updated values
            self.db.refresh(document)
            return document
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating document {document_id}: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating document"
            )

    def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a document and its associated file.
        
        Args:
            document_id: The ID of the document to delete
            user_id: The ID of the user making the request
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            HTTPException: If document is not found or access is denied
        """
        try:
            with self.db.begin():
                # Get document with lock to prevent concurrent modifications
                document = self.db.query(DocumentModel).filter(
                    DocumentModel.id == document_id,
                    DocumentModel.owner_id == user_id
                ).with_for_update().first()
                
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Document not found or access denied"
                    )
                
                file_path = document.file_path
                
                # Delete document from database first
                self.db.delete(document)
                
                # If database deletion succeeds, delete the file
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        # Try to remove the user's directory if it's empty
                        user_dir = os.path.dirname(file_path)
                        try:
                            os.rmdir(user_dir)
                        except OSError:
                            # Directory not empty, which is fine
                            pass
                    except OSError as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
                        # Don't fail the request if file deletion fails
                
                return True
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error deleting document"
            )

    def get_document_chunks(
        self, 
        document_id: int, 
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """Get chunks for a document."""
        # Verify document exists and user has access
        self.get_document(document_id, user_id)
        
        return self.db.query(DocumentChunk)\
            .filter(DocumentChunk.document_id == document_id)\
            .offset(skip)\
            .limit(limit)\
            .all()

    def get_document_with_chunks(
        self, 
        document_id: int, 
        user_id: int,
        skip_chunks: int = 0,
        limit_chunks: int = 100
    ) -> DocumentWithChunks:
        """Get a document with its chunks."""
        document = self.get_document(document_id, user_id)
        chunks = self.get_document_chunks(document_id, user_id, skip_chunks, limit_chunks)
        
        # Convert to Pydantic model with chunks
        document_dict = {c.name: getattr(document, c.name) for c in document.__table__.columns}
        document_with_chunks = DocumentWithChunks(**document_dict, chunks=chunks)
        
        return document_with_chunks
