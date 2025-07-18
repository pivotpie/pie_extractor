from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"
    TEXT = "text"

class DocumentBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    file_type: DocumentType
    mime_type: str = Field(..., max_length=100)
    file_size: int = Field(..., gt=0)
    page_count: int = Field(default=1, ge=1)

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[DocumentStatus] = None
    processing_errors: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None

class DocumentInDBBase(DocumentBase):
    id: int
    status: DocumentStatus
    owner_id: int
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    processing_errors: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class Document(DocumentInDBBase):
    pass

class DocumentInDB(DocumentInDBBase):
    file_path: str

class DocumentChunkBase(BaseModel):
    content: str
    chunk_index: int
    chunk_metadata: Optional[Dict[str, Any]] = None

class DocumentChunkCreate(DocumentChunkBase):
    document_id: int

class DocumentChunkInDB(DocumentChunkBase):
    id: int
    document_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentChunk(DocumentChunkInDB):
    pass

class DocumentWithChunks(Document):
    chunks: List[DocumentChunk] = []

class DocumentUploadResponse(BaseModel):
    document: Document
    upload_url: Optional[HttpUrl] = None
    message: str = "Document uploaded successfully"

# Vision Extraction Models
class BoundingBox(BaseModel):
    x: float = Field(..., ge=0, description="X coordinate of the top-left corner")
    y: float = Field(..., ge=0, description="Y coordinate of the top-left corner")
    width: float = Field(..., gt=0, description="Width of the bounding box")
    height: float = Field(..., gt=0, description="Height of the bounding box")

class FontProperties(BaseModel):
    estimated_size: Optional[float] = Field(None, gt=0, description="Estimated font size in points")
    bold: bool = Field(False, description="Whether the text is bold")
    italic: bool = Field(False, description="Whether the text is italic")
    color: Optional[str] = Field(None, description="Text color if detectable")

class TextBlock(BaseModel):
    text: str = Field(..., description="Extracted text content")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    type: str = Field(..., description="Type of text (header, body, table_cell, etc.)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    font_properties: Optional[FontProperties] = Field(None, description="Font characteristics")
    page_dimensions: Optional[Dict[str, float]] = Field(None, description="Page width and height in pixels")

class DocumentElement(BaseModel):
    id: str = Field(..., description="Unique identifier for the element")
    type: str = Field(..., description="Type of element (header, table, etc.)")
    content: Union[str, Dict[str, Any]] = Field(..., description="Content of the element")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    children: List[str] = Field(default_factory=list, description="IDs of child elements")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")

class DocumentMetadata(BaseModel):
    type: str = Field(..., description="Document type (invoice, receipt, etc.)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    page_dimensions: Dict[str, float] = Field(..., description="Page width and height in pixels")
    total_elements: int = Field(..., ge=0, description="Total number of elements")

class ExtractionMetadata(BaseModel):
    source_file: str = Field(..., description="Name of the source file")
    extraction_timestamp: str = Field(..., description="ISO 8601 timestamp of extraction")
    processing_time: Dict[str, float] = Field(..., description="Processing times in seconds")
    model_versions: Dict[str, str] = Field(..., description="Versions of models used")

class VisionExtractionResult(BaseModel):
    extraction_metadata: ExtractionMetadata = Field(..., description="Metadata about the extraction process")
    document: Dict[str, Any] = Field(..., description="Structured document data")

class VisionExtractionResponse(BaseModel):
    status: Literal["completed", "processing", "failed"] = Field(..., description="Status of the extraction")
    result: Optional[Dict[str, Any]] = Field(None, description="Extraction result (if completed)")
    processing_time: Optional[float] = Field(None, description="Total processing time in seconds (if completed)")
    message: Optional[str] = Field(None, description="Status message or error details")

class VisionExtractionRequest(BaseModel):
    file_url: Optional[HttpUrl] = Field(None, description="URL of the file to process")
    file_content: Optional[bytes] = Field(None, description="File content as bytes (alternative to file_url)")
    mime_type: Optional[str] = Field(None, description="MIME type of the file")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional processing options")

    @validator('file_content', always=True)
    def check_file_or_url(cls, v, values):
        if v is None and values.get('file_url') is None:
            raise ValueError('Either file_url or file_content must be provided')
        return v
