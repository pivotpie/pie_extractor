from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, JSON, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from .base import Base

class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class DocumentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    TEXT = "text"

class Document(Base):
    """Document model for storing document metadata"""
    __tablename__ = "documents"
    
    # Document metadata
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(Enum(DocumentType), nullable=False)
    mime_type = Column(String(100), nullable=False)
    page_count = Column(Integer, nullable=False, default=1)
    
    # Processing status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)
    processing_errors = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Document structure (for RAG)
    structure = Column(JSON, nullable=True)  # Stores document structure (sections, headers, etc.)
    
    # Relationships
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    """Chunks of text extracted from documents for RAG system"""
    __tablename__ = "document_chunks"
    
    # Chunk content
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    
    # Embeddings and metadata
    embedding = Column(JSON, nullable=True)  # Vector embedding of the chunk
    chunk_metadata = Column('metadata', JSON, nullable=True)   # Additional metadata (e.g., position, font info)
    
    # Relationships
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    document = relationship("Document", back_populates="chunks")
