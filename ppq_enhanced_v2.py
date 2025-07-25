"""Enhanced PPQ.ai document processing script with integrated vision extraction.

Features:
- Complete pipeline: Document → Vision Extraction → Chunk Processing → Database Storage
- PDF page-by-page processing with compression
- Image compression for optimal API performance
- Split processing: Immediate (chunks 1-4) + Background (chunks 5-6)
- SQLite database with full-text search
- Semantic search capabilities

Dependencies:
    pip install requests pillow pymupdf sqlite3

Usage:
    # Complete pipeline from PDF/image document
    python ppq_enhanced_v2.py --document contract.pdf --api-key "your-key" --mode pipeline
    
    # Traditional approach with pre-extracted vision data
    python ppq_enhanced_v2.py --vision @vision.json --api-key "your-key" --mode immediate
"""

import argparse
import json
import logging
import os
import requests
import sys
import time
import sqlite3
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    import io
except ImportError:
    print("Error: PIL (Pillow) is required for image processing.")
    print("Install it with: pip install pillow")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Warning: PyMuPDF not installed. PDF processing will be limited.")
    print("Install it with: pip install pymupdf")
    fitz = None

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

class ChunkExtractionDB:
    """SQLite database manager for chunk extraction results with full-text search support."""
    
    def __init__(self, db_path: str = "chunk_extraction.db"):
        self.db_path = db_path
        self.create_database()
    
    def create_database(self):
        """Create all necessary tables for storing extraction results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Document Metadata Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    document_type TEXT,
                    primary_type TEXT,
                    specific_type TEXT,
                    confidence REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    immediate_completed_at TEXT,
                    background_completed_at TEXT,
                    status TEXT DEFAULT 'processing',
                    vision_data_length INTEGER,
                    processing_mode TEXT DEFAULT 'complete'
                );
            """)
            
            # 2. Extracted Fields Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extracted_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    field_value TEXT,
                    field_type TEXT,
                    confidence REAL DEFAULT 1.0,
                    bbox TEXT,
                    category TEXT,
                    section_name TEXT,
                    FOREIGN KEY (document_id) REFERENCES document_metadata (id)
                );
            """)
            
            # 3. Semantic Index Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    entity_type TEXT,
                    context TEXT,
                    category TEXT,
                    keyword_type TEXT,
                    relevance REAL DEFAULT 0.9,
                    FOREIGN KEY (document_id) REFERENCES document_metadata (id)
                );
            """)
            
            # 4. FTS Table for Semantic Search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS semantic_index_fts 
                USING fts5(term, document_id, entity_type, context, category, content='semantic_index', content_rowid='id');
            """)
            
            # 5. Summary Insights
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS summary_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    main_purpose TEXT,
                    key_parties TEXT,
                    critical_information TEXT,
                    action_items TEXT,
                    time_sensitive_elements TEXT,
                    document_status TEXT,
                    comprehensive_overview TEXT,
                    extraction_confidence REAL,
                    data_completeness_percentage INTEGER,
                    FOREIGN KEY (document_id) REFERENCES document_metadata (id)
                );
            """)
            
            # 6. Search Category Items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_category_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    category TEXT,
                    item_text TEXT,
                    item_type TEXT,
                    confidence REAL DEFAULT 1.0,
                    FOREIGN KEY (document_id) REFERENCES document_metadata (id)
                );
            """)
            
            # Create FTS triggers
            cursor.executescript("""
                CREATE TRIGGER IF NOT EXISTS semantic_index_ai AFTER INSERT ON semantic_index
                BEGIN
                    INSERT INTO semantic_index_fts(rowid, term, document_id, entity_type, context, category)
                    VALUES (new.id, new.term, new.document_id, new.entity_type, new.context, new.category);
                END;
                
                CREATE TRIGGER IF NOT EXISTS semantic_index_ad AFTER DELETE ON semantic_index
                BEGIN
                    INSERT INTO semantic_index_fts(semantic_index_fts, rowid, term, document_id, entity_type, context, category)
                    VALUES('delete', old.id, old.term, old.document_id, old.entity_type, old.context, old.category);
                END;
                
                CREATE TRIGGER IF NOT EXISTS semantic_index_au AFTER UPDATE ON semantic_index
                BEGIN
                    INSERT INTO semantic_index_fts(semantic_index_fts, rowid, term, document_id, entity_type, context, category)
                    VALUES('delete', old.id, old.term, old.document_id, old.entity_type, old.context, old.category);
                    INSERT INTO semantic_index_fts(rowid, term, document_id, entity_type, context, category)
                    VALUES (new.id, new.term, new.document_id, new.entity_type, new.context, new.category);
                END;
            """)
            
            # Create indexes for better performance
            cursor.executescript("""
                CREATE INDEX IF NOT EXISTS idx_extracted_fields_doc_id ON extracted_fields(document_id);
                CREATE INDEX IF NOT EXISTS idx_extracted_fields_session ON extracted_fields(session_id);
                CREATE INDEX IF NOT EXISTS idx_semantic_index_doc_id ON semantic_index(document_id);
                CREATE INDEX IF NOT EXISTS idx_semantic_index_term ON semantic_index(term);
                CREATE INDEX IF NOT EXISTS idx_document_metadata_session ON document_metadata(session_id);
                CREATE INDEX IF NOT EXISTS idx_search_category_items_doc ON search_category_items(document_id);
            """)
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_immediate_results(self, session_id: str, immediate_result: Dict[str, Any]) -> str:
        """Save immediate processing results (chunks 1-4) to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            extraction_data = immediate_result.get('immediate_result', {})
            document_id = f"doc_{session_id}"
            
            # 1. Save document metadata
            doc_classification = extraction_data.get('document_classification', {})
            cursor.execute("""
                INSERT OR REPLACE INTO document_metadata 
                (id, session_id, document_type, primary_type, specific_type, confidence, 
                 created_at, processed_at, immediate_completed_at, status, processing_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id, session_id,
                doc_classification.get('specific_type', 'unknown'),
                doc_classification.get('primary_type', 'unknown'),
                doc_classification.get('specific_type', 'unknown'),
                doc_classification.get('confidence', 0.0),
                datetime.now().isoformat(),
                doc_classification.get('processing_timestamp', datetime.now().isoformat()),
                datetime.now().isoformat(),
                'immediate_complete',
                'split_processing'
            ))
            
            # 2. Save extracted fields from all categories
            tab1_content = extraction_data.get('tab1_content', {})
            for category_name, category_data in tab1_content.items():
                if isinstance(category_data, dict):
                    for field_name, field_info in category_data.items():
                        if isinstance(field_info, dict) and 'value' in field_info:
                            bbox_str = self._format_bbox_for_db(field_info.get('bbox', {}))
                            cursor.execute("""
                                INSERT INTO extracted_fields 
                                (document_id, session_id, field_name, field_value, field_type, 
                                 confidence, bbox, category, section_name)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                document_id, session_id, field_name,
                                field_info.get('value', ''),
                                self._infer_field_type_db(field_info.get('value', '')),
                                field_info.get('confidence', 0.0),
                                bbox_str, category_name, 'tab1_content'
                            ))
            
            # 3. Save summary insights
            tab2_summary = extraction_data.get('tab2_summary_insights', {})
            exec_summary = tab2_summary.get('executive_summary', {})
            processing_metadata = tab2_summary.get('processing_metadata', {})
            
            cursor.execute("""
                INSERT INTO summary_insights 
                (document_id, session_id, main_purpose, key_parties, critical_information,
                 action_items, time_sensitive_elements, document_status, comprehensive_overview,
                 extraction_confidence, data_completeness_percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id, session_id,
                exec_summary.get('main_purpose', ''),
                json.dumps(exec_summary.get('key_parties', [])),
                json.dumps(exec_summary.get('critical_information', [])),
                json.dumps(exec_summary.get('action_items', [])),
                json.dumps(exec_summary.get('time_sensitive_elements', [])),
                exec_summary.get('document_status', 'unknown'),
                tab2_summary.get('detailed_analysis', {}).get('comprehensive_overview', ''),
                processing_metadata.get('extraction_confidence', 0.0),
                processing_metadata.get('data_completeness_percentage', 0)
            ))
            
            conn.commit()
            return document_id
            
        except Exception as e:
            print(f"❌ Error saving immediate results to DB: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_background_results(self, session_id: str, background_result: Dict[str, Any]) -> bool:
        """Save background processing results (chunks 5-6) to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            document_id = f"doc_{session_id}"
            background_data = background_result.get('background_result', {})
            
            # Update document metadata
            cursor.execute("""
                UPDATE document_metadata 
                SET background_completed_at = ?, status = ?
                WHERE id = ? AND session_id = ?
            """, (
                datetime.now().isoformat(), 'complete', document_id, session_id
            ))
            
            # Save semantic search data
            semantic_data = background_data.get('semantic_search_data', {})
            searchable_content = semantic_data.get('searchable_content', {})
            
            # Save structured entities
            structured_entities = searchable_content.get('structured_entities', [])
            for entity in structured_entities:
                cursor.execute("""
                    INSERT INTO semantic_index 
                    (term, document_id, session_id, entity_type, context, relevance)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entity.get('entity_text', ''), document_id, session_id,
                    entity.get('entity_type', 'unknown'),
                    entity.get('context', ''), 0.9
                ))
            
            # Save search categories
            search_categories = semantic_data.get('search_categories', {})
            for category, items in search_categories.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and 'text' in item:
                            cursor.execute("""
                                INSERT INTO search_category_items 
                                (document_id, session_id, category, item_text, item_type)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                document_id, session_id, category,
                                item['text'], item.get('type', 'unknown')
                            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error saving background results to DB: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def semantic_search(self, query: str, limit: int = 10, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Perform semantic search using FTS."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            base_query = """
                SELECT si.term, si.document_id, si.entity_type, si.context, 
                       si.category, si.relevance, dm.document_type, dm.session_id
                FROM semantic_index_fts fts
                JOIN semantic_index si ON si.id = fts.rowid
                JOIN document_metadata dm ON dm.id = si.document_id
                WHERE semantic_index_fts MATCH ?
            """
            
            params = [query]
            
            if document_id:
                base_query += " AND si.document_id = ?"
                params.append(document_id)
            
            base_query += " ORDER BY si.relevance DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            return [
                {
                    'term': row[0], 'document_id': row[1], 'entity_type': row[2],
                    'context': row[3], 'category': row[4], 'relevance': row[5],
                    'document_type': row[6], 'session_id': row[7]
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"❌ Error performing semantic search: {e}")
            return []
        finally:
            conn.close()
    
    def _format_bbox_for_db(self, bbox: Dict) -> str:
        """Format bbox dictionary to database string."""
        if isinstance(bbox, dict):
            return f"{bbox.get('x', 0)},{bbox.get('y', 0)},{bbox.get('width', 0)},{bbox.get('height', 0)}"
        return "0,0,0,0"
    
    def _infer_field_type_db(self, value: str) -> str:
        """Infer field type from value for database."""
        if not value:
            return "string"
        
        value_str = str(value).strip()
        
        if value_str.replace(".", "").replace(",", "").replace("-", "").isdigit():
            return "decimal" if "." in value_str else "integer"
        
        if any(pattern in value_str.lower() for pattern in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]):
            return "date"
        
        if any(pattern in value_str for pattern in ["-", "/"]) and any(char.isdigit() for char in value_str):
            return "date"
        
        if value_str.lower() in ["true", "false", "yes", "no"]:
            return "boolean"
            
        return "string"

class PPQChunkedClient:
    """PPQ.ai client with chunked processing and self-contained prompts."""
    
    def __init__(self, api_key: str, timeout: int = 200, db_path: str = "chunk_extraction.db", enable_db: bool = True):
        self.api_key = api_key
        self.base_url = "https://api.ppq.ai"
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.retry_count = 3
        self.retry_delay = 15  # seconds between retries
        self.backoff_multiplier = 1.5  # exponential backoff
        self.chunk_save_path = "."  # Default save path for chunks
        
        # Database integration
        self.enable_db = enable_db
        if enable_db:
            self.db_path = db_path
            self._init_database()
        else:
            self.db = None
    
    def _init_database(self):
        """Initialize the SQLite database."""
        try:
            self.db = ChunkExtractionDB(self.db_path)
            print(f"✅ Database initialized: {self.db_path}")
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")
            print("   Continuing without database integration...")
            self.db = None
            self.enable_db = False
    
    def compress_image(self, image_data: bytes, max_size_mb: float = 2.0, quality: int = 85) -> bytes:
        """Compress image data to reduce size while maintaining quality."""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG compression)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Calculate target size in bytes
            target_size = max_size_mb * 1024 * 1024
            
            # If image is already small enough, return as is
            if len(image_data) <= target_size:
                return image_data
            
            # Compress with decreasing quality until size is acceptable
            for attempt_quality in range(quality, 20, -10):
                output_buffer = io.BytesIO()
                image.save(output_buffer, format='JPEG', quality=attempt_quality, optimize=True)
                compressed_data = output_buffer.getvalue()
                
                if len(compressed_data) <= target_size:
                    print(f"  📦 Compressed image: {len(image_data)} → {len(compressed_data)} bytes (quality: {attempt_quality})")
                    return compressed_data
            
            # If still too large, resize the image
            original_size = image.size
            scale_factor = 0.8
            
            while len(compressed_data) > target_size and scale_factor > 0.3:
                new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
                resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
                
                output_buffer = io.BytesIO()
                resized_image.save(output_buffer, format='JPEG', quality=75, optimize=True)
                compressed_data = output_buffer.getvalue()
                
                scale_factor -= 0.1
            
            print(f"  📦 Resized and compressed: {len(image_data)} → {len(compressed_data)} bytes")
            return compressed_data
            
        except Exception as e:
            print(f"  ⚠️ Compression failed: {e}, using original")
            return image_data

    def pdf_to_images(self, pdf_path: str, dpi: int = 150) -> List[bytes]:
        """Convert PDF pages to compressed images."""
        if not fitz:
            raise Exception("PyMuPDF is required for PDF processing. Install with: pip install pymupdf")
        
        try:
            print(f"  📄 Opening PDF: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            page_images = []
            
            print(f"  📊 PDF has {len(pdf_document)} pages")
            
            for page_num in range(len(pdf_document)):
                print(f"  🔄 Processing page {page_num + 1}/{len(pdf_document)}...")
                
                # Get page
                page = pdf_document[page_num]
                
                # Create transformation matrix for desired DPI
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                
                # Render page to image
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Compress the image
                compressed_img = self.compress_image(img_data, max_size_mb=2.0)
                page_images.append(compressed_img)
                
                print(f"    ✅ Page {page_num + 1} processed: {len(compressed_img)} bytes")
            
            pdf_document.close()
            print(f"  📋 Converted {len(page_images)} pages to images")
            return page_images
            
        except Exception as e:
            raise Exception(f"PDF conversion failed: {e}")

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

    def vision_extract_document(self, document_path: str, document_type: str = "auto", debug_mode: bool = False) -> str:
        """Extract text and structure from document using PPQ.ai chat/completions with vision capabilities."""
        print(f"🔍 Starting enhanced vision extraction for: {document_path}")
        
        # Determine document type if auto
        if document_type == "auto":
            ext = document_path.lower().split('.')[-1]
            if ext in ['pdf']:
                document_type = "pdf"
            elif ext in ['jpg', 'jpeg', 'png', 'tiff', 'bmp']:
                document_type = "image"
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        
        try:
            # Process document based on type
            if document_type == "pdf":
                print("  📄 Processing PDF document page by page...")
                page_images = self.pdf_to_images(document_path)
                
                # Process each page and combine results
                all_vision_data = []
                
                for page_num, image_data in enumerate(page_images, 1):
                    print(f"  🔍 Extracting vision data from page {page_num}...")
                    
                    encoded_image = base64.b64encode(image_data).decode('utf-8')
                    page_vision = self._extract_vision_from_image(encoded_image, page_num)
                    all_vision_data.append(page_vision)
                
                # Combine all pages into single vision data structure
                combined_vision = self._combine_page_visions(all_vision_data, document_path)
                
            elif document_type == "image":
                print("  🖼️ Processing image document...")
                
                with open(document_path, 'rb') as f:
                    image_data = f.read()
                
                # Compress image
                compressed_image = self.compress_image(image_data)
                encoded_image = base64.b64encode(compressed_image).decode('utf-8')
                
                # Extract vision data
                combined_vision = self._extract_vision_from_image(encoded_image, 1)
            
            vision_json = json.dumps(combined_vision, indent=2)
            print(f"  ✅ Vision extraction completed ({len(vision_json)} characters)")
            return vision_json
            
        except Exception as e:
            raise Exception(f"Enhanced vision extraction failed: {e}")

    def _extract_vision_from_image(self, encoded_image: str, page_num: int = 1) -> Dict[str, Any]:
        """Extract vision data from a single image using chat/completions with proper image transmission."""
        
        # Enhanced vision extraction instructions (user's specific prompt)
        vision_instructions = """Analyze this document image and extract text content organized as logical semantic units (paragraphs, headings, items, etc.) with precise geometric information.

EXTRACTION RULES:
1. **Semantic Grouping**: Group related words into complete logical units:
   - Complete paragraphs (not individual words)
   - Full headings and titles
   - Document Tables as table_header and table_rows
   - Complete invoice line items line by line with its quantity and price
   - Other Sections (Invoice Number, Date, etc.) as single blocks
   - Entire addresses as single blocks
   - Full sentences and phrases

2. **Document Type Identification**: Automatically classify document type first
3. **Bounding Box Calculation**: Calculate encompassing bounding box for each complete logical unit
4. **Hierarchy Detection**: Identify text hierarchy and relationships

For each semantic text unit, provide:
1. Complete text content (full paragraphs/sentences/items)
2. Encompassing bounding box coordinates (x, y, width, height) in pixels
3. Semantic type classification
4. Confidence level (0.0-1.0)
5. Font characteristics and formatting
6. Reading order sequence
7. Relationship to other elements

Output format:
{
  "document_type": "invoice|receipt|contract|letter|form|report|other",
  "document_confidence": 0.95,
  "page_dimensions": {"width": 2480, "height": 3508},
  "text_blocks": [
    {
      "id": "block_1",
      "text": "complete semantic text unit",
      "bbox": {"x": 100, "y": 50, "width": 400, "height": 60},
      "type": "document_title|company_name|address|paragraph|table_header|table_row|invoice_item|total_amount|date|signature|footer",
      "confidence": 0.95,
      "reading_order": 1,
      "font_properties": {
        "estimated_size": 12,
        "bold": true,
        "italic": false,
        "alignment": "left|center|right"
      },
      "semantic_role": "header|body|metadata|table_data|summary",
      "parent_section": "header|body|footer|table_1|address_block",
      "relationships": ["follows:block_0", "contains:sub_block_2"]
    }
  ]
}

CRITICAL REQUIREMENTS:
- Extract COMPLETE semantic units, not fragmented words
- Calculate accurate encompassing bounding boxes for grouped content
- Identify document type with confidence score
- Maintain logical reading flow and hierarchy
- Group table cells into complete rows/items
- Preserve formatting context (bold, size, alignment)
- NO explanatory text - JSON response only"""

        try:
            print(f"    📡 Calling vision API for page {page_num}...")
            print(f"    📊 Image data size: {len(encoded_image)} characters")
            
            # Verify base64 encoding integrity
            try:
                # Test decode to verify integrity
                import base64
                decoded_test = base64.b64decode(encoded_image[:100])  # Test first 100 chars
                print(f"    ✅ Base64 encoding verified")
            except Exception as e:
                print(f"    ❌ Base64 encoding issue: {e}")
                raise
            
            # Prepare chat completion request with proper image format
            url = f"{self.base_url}/chat/completions"
            
            system_message = """You are a specialized document vision analysis system. You must analyze the provided document image and extract all text content organized as complete logical semantic units with precise geometric information. Return ONLY valid JSON in the exact format specified in the instructions."""
            
            # FIXED: Send the complete base64 image data, not truncated
            user_message = [
                {
                    "type": "text",
                    "text": vision_instructions
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    }
                }
            ]
            
            data = {
                "model": "gpt-4.1",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.0,
                "max_tokens": 20000,  # Increased for detailed extraction
                "top_p": 1.0
            }
            
            print(f"    🔍 Sending vision request to PPQ.ai...")
            print(f"    📏 Request payload size: ~{len(json.dumps(data))} characters")
            
            response = requests.post(url, json=data, headers=self.headers, timeout=self.timeout)
            
            # Debug response status
            print(f"    📡 Response status: {response.status_code}")
            
            if not response.ok:
                print(f"    ❌ API Error: {response.status_code}")
                print(f"    📄 Error response: {response.text[:500]}...")
                response.raise_for_status()
            
            result = response.json()
            raw_response = result["choices"][0]["message"]["content"]
            
            print(f"    📄 Raw response length: {len(raw_response)} characters")
            print(f"    🔍 Response preview: {raw_response[:200]}...")
            
            # Clean and parse JSON response
            clean_json = self.extract_json_from_response(raw_response)
            
            # Debug the cleaned JSON
            print(f"    🧹 Cleaned JSON length: {len(clean_json)} characters")
            
            try:
                vision_data = json.loads(clean_json)
                print(f"    ✅ JSON parsing successful")
            except json.JSONDecodeError as e:
                print(f"    ❌ JSON parsing failed: {e}")
                print(f"    📄 Problematic JSON preview: {clean_json[:500]}...")
                raise
            
            # Add page number if not present
            vision_data["page_number"] = page_num
            
            # Validate essential fields
            if "text_blocks" not in vision_data:
                print(f"    ⚠️ Warning: No text_blocks found in response")
                vision_data["text_blocks"] = []
            
            if "document_type" not in vision_data:
                print(f"    ⚠️ Warning: No document_type found in response")
                vision_data["document_type"] = "unknown"
            
            text_block_count = len(vision_data.get("text_blocks", []))
            doc_confidence = vision_data.get("document_confidence", 0.0)
            
            print(f"    ✅ Page {page_num} extracted: {text_block_count} text blocks, confidence: {doc_confidence:.2f}")
            
            return vision_data
            
        except json.JSONDecodeError as e:
            print(f"    ❌ Invalid JSON response for page {page_num}: {e}")
            print(f"    📄 Raw response snippet: {raw_response[:1000] if 'raw_response' in locals() else 'No response received'}")
            
            # Save problematic response for debugging
            debug_file = f"debug_page_{page_num}_response.txt"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(raw_response if 'raw_response' in locals() else "No response data")
                print(f"    💾 Debug response saved to: {debug_file}")
            except:
                pass
            
            # Return minimal structure if JSON parsing fails
            return {
                "document_type": "unknown",
                "page_number": page_num,
                "document_confidence": 0.0,
                "page_dimensions": {"width": 0, "height": 0},
                "text_blocks": [],
                "error": f"JSON parsing failed: {str(e)}"
            }
            
        except requests.exceptions.RequestException as e:
            print(f"    ❌ API request failed for page {page_num}: {e}")
            raise
            
        except Exception as e:
            print(f"    ❌ Vision extraction failed for page {page_num}: {e}")
            raise

    def _combine_page_visions(self, page_visions: List[Dict[str, Any]], document_path: str) -> Dict[str, Any]:
        """Combine enhanced vision data from multiple pages into a single structure."""
        
        if not page_visions:
            raise Exception("No page vision data to combine")
        
        print(f"  🔄 Combining enhanced vision data from {len(page_visions)} pages...")
        
        # Initialize combined structure for enhanced format
        combined = {
            "document_type": "pdf",
            "source_file": os.path.basename(document_path),
            "total_pages": len(page_visions),
            "document_confidence": 0.0,
            "page_dimensions": {"width": 0, "height": 0},
            "text_blocks": [],
            "document_structure": {
                "headers": [],
                "body_content": [],
                "tables": [],
                "metadata_blocks": [],
                "footer_content": []
            },
            "pages": page_visions,  # Keep individual page data
            "processing_metadata": {
                "processed_pages": 0,
                "failed_pages": 0,
                "average_confidence": 0.0,
                "total_text_blocks": 0
            }
        }
        
        # Combine data from all pages
        total_confidence = 0
        valid_pages = 0
        total_text_blocks = 0
        max_width = 0
        max_height = 0
        
        for page_data in page_visions:
            page_num = page_data.get("page_number", 1)
            
            if page_data.get("error"):
                print(f"    ⚠️ Skipping page {page_num} due to error: {page_data.get('error')}")
                combined["processing_metadata"]["failed_pages"] += 1
                continue
            
            valid_pages += 1
            combined["processing_metadata"]["processed_pages"] += 1
            
            # Update document type from first valid page
            if valid_pages == 1:
                combined["document_type"] = page_data.get("document_type", "unknown")
            
            # Update page dimensions (use maximum dimensions found)
            page_dims = page_data.get("page_dimensions", {})
            if page_dims.get("width", 0) > max_width:
                max_width = page_dims.get("width", 0)
            if page_dims.get("height", 0) > max_height:
                max_height = page_dims.get("height", 0)
            
            # Combine text blocks with page offset for multi-page documents
            page_offset = (page_num - 1) * (max_height or 3508)  # Default page height if not available
            
            page_text_blocks = page_data.get("text_blocks", [])
            total_text_blocks += len(page_text_blocks)
            
            for text_block in page_text_blocks:
                # Adjust bbox for multi-page document
                if "bbox" in text_block and isinstance(text_block["bbox"], dict):
                    text_block["bbox"]["y"] += page_offset
                
                # Add page reference
                text_block["page"] = page_num
                text_block["source_page"] = page_num
                
                # Add to combined text blocks
                combined["text_blocks"].append(text_block)
                
                # Categorize by semantic role for document structure
                semantic_role = text_block.get("semantic_role", "body")
                block_type = text_block.get("type", "paragraph")
                
                if semantic_role == "header" or block_type in ["document_title", "company_name"]:
                    combined["document_structure"]["headers"].append(text_block)
                elif semantic_role == "metadata" or block_type in ["date", "invoice_item", "total_amount"]:
                    combined["document_structure"]["metadata_blocks"].append(text_block)
                elif block_type in ["table_header", "table_row"]:
                    combined["document_structure"]["tables"].append(text_block)
                elif semantic_role == "summary" or block_type == "footer":
                    combined["document_structure"]["footer_content"].append(text_block)
                else:
                    combined["document_structure"]["body_content"].append(text_block)
            
            # Accumulate confidence
            page_confidence = page_data.get("document_confidence", 0.0)
            total_confidence += page_confidence
            
            print(f"    ✅ Page {page_num}: {len(page_text_blocks)} blocks, confidence: {page_confidence:.2f}")
        
        # Finalize combined data
        combined["page_dimensions"] = {"width": max_width, "height": max_height}
        combined["processing_metadata"]["total_text_blocks"] = total_text_blocks
        
        if valid_pages > 0:
            combined["document_confidence"] = total_confidence / valid_pages
            combined["processing_metadata"]["average_confidence"] = total_confidence / valid_pages
        
        # Sort text blocks by reading order and page
        combined["text_blocks"].sort(key=lambda x: (x.get("page", 1), x.get("reading_order", 999)))
        
        print(f"  ✅ Enhanced combination complete:")
        print(f"    📄 Document type: {combined['document_type']}")
        print(f"    📊 {valid_pages} pages processed, {total_text_blocks} total text blocks")
        print(f"    🎯 Average confidence: {combined['document_confidence']:.2f}")
        print(f"    📏 Document dimensions: {max_width}x{max_height}")
        
        return combined

    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat() + "Z"

    def process_document_from_source(self, document_path: str, document_type: str = "auto", session_id: Optional[str] = None, debug_mode: bool = False) -> Dict[str, Any]:
        """Complete pipeline: Document → Enhanced Vision Extraction → Immediate Processing."""
        
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        print(f"\n🚀 Starting ENHANCED PIPELINE - Session: {session_id}")
        print(f"📄 Document: {document_path}")
        print(f"🔍 Debug mode: {'enabled' if debug_mode else 'disabled'}")
        
        try:
            # Step 1: Enhanced Vision Extraction
            print("\n" + "="*60)
            print("🔍 STEP 1: Enhanced Vision Extraction")
            vision_data = self.vision_extract_document(document_path, document_type, debug_mode)
            
            # Save vision extraction result
            vision_file = f"{session_id}_vision_extraction.json"
            with open(vision_file, 'w', encoding='utf-8') as f:
                f.write(vision_data)
            print(f"💾 Enhanced vision extraction saved: {vision_file}")
            
            # Validate vision data
            try:
                vision_obj = json.loads(vision_data)
                text_blocks = len(vision_obj.get("text_blocks", []))
                doc_type = vision_obj.get("document_type", "unknown")
                confidence = vision_obj.get("document_confidence", 0.0)
                
                print(f"  ✅ Vision validation: {text_blocks} text blocks, type: {doc_type}, confidence: {confidence:.2f}")
                
                if text_blocks == 0:
                    print(f"  ⚠️ WARNING: No text blocks extracted! This may indicate an issue with image processing.")
                    if debug_mode:
                        print(f"  🐛 Vision data preview: {vision_data[:500]}...")
                
            except json.JSONDecodeError as e:
                print(f"  ❌ Vision data validation failed: {e}")
                if debug_mode:
                    print(f"  🐛 Invalid vision data: {vision_data[:1000]}...")
                raise
            
            # Step 2: Immediate Processing (using enhanced vision data)
            print("\n" + "="*60)
            print("🔍 STEP 2: Immediate Processing (Chunks 1-4)")
            immediate_result = self.process_immediate_chunks(vision_data, session_id)
            
            return {
                "session_id": session_id,
                "vision_extraction_file": vision_file,
                "immediate_result": immediate_result,
                "document_path": document_path,
                "document_type": document_type,
                "debug_mode": debug_mode,
                "vision_validation": {
                    "text_blocks_count": text_blocks,
                    "document_type": doc_type,
                    "confidence": confidence
                }
            }
            
        except Exception as e:
            print(f"\n❌ Error in enhanced pipeline: {e}")
            
            if debug_mode:
                import traceback
                print(f"🐛 Full error traceback:")
                traceback.print_exc()
            
            raise

    def process_document_background_from_source(self, session_id: str, use_saved_vision: bool = True) -> Dict[str, Any]:
        """Background processing using saved vision data from source processing."""
        
        print(f"\n🔄 Starting BACKGROUND processing for source document - Session: {session_id}")
        
        try:
            # Load saved vision data
            if use_saved_vision:
                vision_file = f"{session_id}_vision_extraction.json"
                try:
                    with open(vision_file, 'r', encoding='utf-8') as f:
                        vision_data = f.read()
                    print(f"✅ Loaded saved vision data: {vision_file}")
                except FileNotFoundError:
                    raise FileNotFoundError(f"Vision data not found: {vision_file}. Run immediate processing first.")
            else:
                raise ValueError("Vision data required for background processing")
            
            # Step 3: Background Processing
            print("\n" + "="*60)
            print("🔍 STEP 3: Background Processing (Chunks 5-6)")
            background_result = self.process_background_chunks(session_id, vision_data)
            
            return background_result
            
        except Exception as e:
            print(f"\n❌ Error in background processing from source: {e}")
            raise
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat() + "Z"
    
    def extract_json_from_response(self, response: str) -> str:
        """Extract JSON from response that might contain extra text."""
        # Remove markdown formatting
        response = response.replace('```json', '').replace('```', '').strip()
        
        # Try to find JSON pattern
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            potential_json = response[start_idx:end_idx + 1]
            
            # Validate JSON
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                pass
        
        return response
    
    def make_api_request_with_retry(self, system_message: str, user_message: str, max_tokens: int = 15000, chunk_name: str = "unknown") -> str:
        """Make API request with exponential backoff retry logic."""
        
        current_delay = self.retry_delay
        
        for attempt in range(self.retry_count):
            try:
                print(f"  📡 {chunk_name} - Attempt {attempt + 1}/{self.retry_count}")
                
                url = f"{self.base_url}/chat/completions"
                data = {
                    "model": "gpt-4.1", 
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.0,
                    "max_tokens": max_tokens,
                    "top_p": 1.0
                }
                
                response = requests.post(url, json=data, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Check if response was complete
                finish_reason = result["choices"][0].get("finish_reason")
                if finish_reason == "length":
                    print(f"  ⚠️ Response truncated, retrying with higher token limit...")
                    max_tokens = min(int(max_tokens * 1.3), 32000)
                    if attempt < self.retry_count - 1:
                        continue
                
                print(f"  ✅ {chunk_name} Success ({len(content)} chars, finish: {finish_reason})")
                return content
                
            except requests.exceptions.Timeout:
                print(f"  ⏱️ {chunk_name} - Timeout on attempt {attempt + 1}")
                if attempt < self.retry_count - 1:
                    print(f"  🔄 Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay = int(current_delay * self.backoff_multiplier)
                else:
                    raise Exception(f"{chunk_name} - All retry attempts timed out")
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [504, 502, 503]:  # Gateway/Server errors
                    print(f"  🕐 {chunk_name} - Gateway error {e.response.status_code} on attempt {attempt + 1}")
                    if attempt < self.retry_count - 1:
                        print(f"  🔄 Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay = int(current_delay * self.backoff_multiplier)
                        continue
                    else:
                        raise Exception(f"{chunk_name} - Gateway errors on all attempts")
                else:
                    raise Exception(f"{chunk_name} - HTTP Error: {e}")
            
            except Exception as e:
                if attempt < self.retry_count - 1:
                    print(f"  ❌ {chunk_name} - Error on attempt {attempt + 1}: {str(e)[:100]}")
                    print(f"  🔄 Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay = int(current_delay * self.backoff_multiplier)
                    continue
                else:
                    raise Exception(f"{chunk_name} - Failed after all attempts: {e}")
        
        raise Exception(f"{chunk_name} - Exhausted all retry attempts")
    
    def chunk_1_document_classification(self, vision_data: str) -> Dict[str, Any]:
        """Chunk 1: Document Classification"""
        
        system_msg = "You are a document classification expert. Return ONLY valid JSON with the exact structure requested."
        
        user_prompt = f"""Analyze the vision data and classify this document. Return EXACTLY this JSON structure:

{{
  "document_classification": {{
    "primary_type": "business|legal|forms|financial|general",
    "specific_type": "invoice|contract|receipt|purchase_order|bank_statement|etc",
    "confidence": 0.95,
    "supported_tabs": ["tab1_content", "tab2_summary", "tab3_tables", "semantic_search"],
    "processing_timestamp": "{self.get_current_timestamp()}"
  }}
}}

Rules:
- Analyze the document_type and text_blocks to determine classification
- For business documents like invoices, use "business" as primary_type
- Use specific document terminology (invoice, receipt, etc.)
- Confidence should reflect how certain you are of the classification

Vision Data to analyze:
{vision_data}

Return ONLY the JSON structure above with accurate classification data."""

        print("🔄 Chunk 1: Document Classification...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=2000, chunk_name="Classification")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def chunk_2_structured_content(self, vision_data: str, doc_type: str) -> Dict[str, Any]:
        """Chunk 2: Structured Content Extraction"""
        
        system_msg = "You are a data extraction specialist. Extract structured fields and return ONLY the requested JSON format."
        
        # Dynamic content based on document type
        if doc_type in ['invoice', 'receipt', 'purchase_order', 'quotation']:
            content_structure = '''
    "fields_and_values": {
      "header_fields": {
        "document_number": {"value": "extracted_number", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "document_date": {"value": "YYYY-MM-DD", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "due_date": {"value": "", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.0}
      },
      "vendor_info": {
        "company_name": {"value": "extracted_vendor", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "address": {"value": "extracted_address", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "contact_info": {"value": "phone/email", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.85}
      },
      "customer_info": {
        "company_name": {"value": "extracted_customer", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "address": {"value": "customer_address", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.90}
      },
      "financial_totals": {
        "subtotal": {"value": "amount", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "tax_amount": {"value": "tax", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95},
        "total_amount": {"value": "total", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.95}
      },
      "payment_terms": {
        "payment_method": {"value": "Cash/Credit", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.85},
        "currency": {"value": "USD/AED", "bbox": {"x": 0, "y": 0, "width": 0, "height": 0}, "confidence": 0.90}
      }
    },
    "financial_dashboard": {},
    "form_fields": {},
    "legal_summary": {},
    "general_summary": {}'''
        else:
            # Generic structure for other document types
            content_structure = '''
    "fields_and_values": {},
    "financial_dashboard": {},
    "form_fields": {},
    "legal_summary": {},
    "general_summary": {}'''
        
        user_prompt = f"""Extract structured content from this {doc_type}. Return EXACTLY this JSON structure:

{{
  "tab1_content": {{{content_structure}
  }}
}}

Instructions:
- Extract ALL relevant data from the vision text_blocks
- Use ACTUAL coordinates from the vision data bbox values
- Fill in extracted values, not placeholder text
- For missing data, use empty strings and confidence 0.0
- Match text exactly as it appears in the document
- Return ONLY valid JSON. Escape all line breaks and special characters properly using JSON syntax. Do NOT include unescaped newlines or tabs inside string values.

Vision Data:
{vision_data}

Return ONLY the complete tab1_content JSON structure filled with extracted data."""

        print("🔄 Chunk 2: Structured Content Extraction...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=20000, chunk_name="Structured Content")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def chunk_3_summary_insights(self, vision_data: str, doc_type: str) -> Dict[str, Any]:
        """Chunk 3: Summary and Business Insights"""
        
        system_msg = "You are a business analyst. Generate comprehensive insights and return ONLY the requested JSON structure."
        
        user_prompt = f"""Analyze this {doc_type} and generate comprehensive insights. Return EXACTLY this JSON:

{{
  "tab2_summary_insights": {{
    "executive_summary": {{
      "main_purpose": "Primary purpose of this document in 1-2 sentences",
      "key_parties": ["List", "of", "involved", "entities"],
      "critical_information": ["Most", "important", "facts", "with", "amounts"],
      "action_items": ["Required", "actions", "or", "next", "steps"],
      "time_sensitive_elements": ["Important", "dates", "deadlines"],
      "document_status": "complete|incomplete|requires_action|pending_review"
    }},
    "detailed_analysis": {{
      "comprehensive_overview": "Detailed 3-4 paragraph analysis covering document purpose, key content, business implications, and significance",
      "section_breakdown": [
        {{
          "section_name": "Header|Body|Table|Footer",
          "content_summary": "What this section contains",
          "key_insights": ["Important", "observations"],
          "data_quality": "Quality assessment of this section"
        }}
      ]
    }},
    "business_insights": {{
      "compliance_status": "Assessment of regulatory compliance",
      "risk_indicators": ["Any", "risks", "or", "concerns"],
      "opportunities": ["Positive", "indicators", "or", "opportunities"],
      "data_confidence": "Overall confidence assessment"
    }},
    "processing_metadata": {{
      "extraction_confidence": 0.92,
      "missing_information": ["Any", "gaps", "identified"],
      "data_completeness_percentage": 95,
      "recommendations": ["Suggestions", "for", "improvement"]
    }}
  }}
}}

Instructions:
- Analyze the complete document context
- Provide actionable business insights
- Identify compliance and risk factors
- Give honest assessment of data quality
- Focus on practical implications
- Return ONLY valid JSON. Escape all line breaks and special characters properly using JSON syntax. Do NOT include unescaped newlines or tabs inside string values.

Vision Data to analyze:
{vision_data}

Return ONLY the complete tab2_summary_insights JSON structure."""

        print("🔄 Chunk 3: Summary and Insights...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=18000, chunk_name="Summary Insights")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def chunk_4_table_extraction(self, vision_data: str) -> Dict[str, Any]:
        """Chunk 4: Table Extraction and Reconstruction"""
        
        system_msg = "You are a table extraction specialist. Identify and reconstruct all tabular data with precision."
        
        user_prompt = f"""Extract ALL tables from this document. Return EXACTLY this JSON structure:

{{
  "tab3_tables": {{
    "identified_tables": [
      {{
        "table_id": "table_1",
        "table_type": "invoice_items|transaction_list|specifications|other",
        "table_title": "Descriptive title",
        "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}},
        "column_headers": ["Column1", "Column2", "Column3"],
        "rows": [
          {{"Column1": "value1", "Column2": "value2", "Column3": "value3"}},
          {{"Column1": "value4", "Column2": "value5", "Column3": "value6"}}
        ],
        "table_metadata": {{
          "total_rows": 2,
          "total_columns": 3,
          "has_totals_row": true,
          "data_types": {{"Column1": "text", "Column2": "numeric", "Column3": "currency"}}
        }}
      }}
    ],
    "table_relationships": [
      {{
        "primary_table": "table_1",
        "related_fields": ["Fields that reference totals"],
        "calculation_validation": "Status of calculations"
      }}
    ]
  }}
}}

Instructions:
- Identify ALL tabular structures in the vision data
- Extract complete table content with all rows and columns
- Use actual coordinates from vision data
- Validate numerical calculations where possible
- Include table relationships and references
- Return ONLY valid JSON. Escape all line breaks and special characters properly using JSON syntax. Do NOT include unescaped newlines or tabs inside string values.


Vision Data containing tables:
{vision_data}

Return ONLY the complete tab3_tables JSON structure with all identified tables."""

        print("🔄 Chunk 4: Table Extraction...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=15000, chunk_name="Table Extraction")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def chunk_5_semantic_search(self, vision_data: str, doc_type: str) -> Dict[str, Any]:
        """Chunk 5: Optimized Semantic Search Data Generation (No spatial metadata)"""

        system_msg = "You are a search optimization expert. Generate structured, searchable content based on the document's extracted text. Focus only on what improves semantic matching."

        user_prompt = f"""Generate semantic search data for a {doc_type}. Use ONLY this simplified structure:

{{
  "semantic_search_data": {{
    "searchable_content": {{
      "full_text_index": "Concatenated clean text from the entire document",
      "structured_entities": [
        {{
          "entity_text": "Company Name",
          "entity_type": "organization",
          "context": "Vendor information",
          "related_terms": ["Company", "Corp", "LLC"]
        }},
        {{
          "entity_text": "$1,500.00",
          "entity_type": "currency",
          "context": "Total amount",
          "related_terms": ["total", "amount", "1500", "fifteen hundred"]
        }}
      ]
    }},
    "search_categories": {{
      "contact_information": [
        {{"text": "email@example.com", "type": "email"}},
        {{"text": "(555) 123-4567", "type": "phone"}}
      ],
      "financial_data": [
        {{"text": "$1,500.00", "type": "total_amount"}},
        {{"text": "$150.00", "type": "tax_amount"}}
      ],
      "dates_and_deadlines": [
        {{"text": "2025-01-15", "type": "document_date"}},
        {{"text": "2025-02-15", "type": "due_date"}}
      ],
      "identifiers_and_references": [
        {{"text": "INV-2025-001", "type": "invoice_number"}},
        {{"text": "PO-12345", "type": "purchase_order"}}
      ]
    }},
    "keyword_mapping": {{
      "primary_keywords": ["invoice", "payment", "total", "amount"],
      "secondary_keywords": ["services", "tax", "due", "net"]
    }}
  }}
}}

Instructions:
- Focus on entity names, types, and context only (no coordinates or confidence).
- Use at least 20 relevant structured entities.
- Remove all bbox, coordinate_ranges, and other UI-specific metadata.
- Optimize for embedding-based search (content-rich, unambiguous, varied vocabulary).
- Return ONLY valid JSON. Escape characters as needed.

Here's the extracted document text for processing:
{vision_data}

Return only the semantic_search_data JSON object."""

        print("🔄 Chunk 5: Semantic Search Data (Optimized)...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=12000, chunk_name="Semantic Search")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)

    def chunk_6_database_format(self, vision_data: str, doc_type: str) -> Dict[str, Any]:
        """Chunk 6: Database-Ready Format (Using Previous Chunks Data)"""
        
        def load_previous_chunks_data():
            """Load and combine data from all previous chunks"""
            try:
                combined_data = {}
                
                # Try to load chunk1 (classification)
                try:
                    with open("chunk1_classification.json", "r", encoding="utf-8") as f:
                        chunk1_data = json.load(f)
                        combined_data.update(chunk1_data)
                except:
                    pass
                
                # Try to load chunk2 (content)
                try:
                    with open("chunk2_content.json", "r", encoding="utf-8") as f:
                        chunk2_data = json.load(f)
                        combined_data.update(chunk2_data)
                except:
                    pass
                
                # Try to load chunk5 (semantic search)
                try:
                    with open("chunk5_search.json", "r", encoding="utf-8") as f:
                        chunk5_data = json.load(f)
                        combined_data.update(chunk5_data)
                except:
                    pass
                    
                return combined_data if combined_data else None
            except Exception as e:
                print(f"❌ Error loading previous chunks: {e}")
                return None

        def build_database_format_from_chunks(combined_data: Dict[str, Any]) -> Dict[str, Any]:
            """Build database format using actual chunk data structure"""
            metadata = {
                "id": f"doc_{int(time.time())}",
                "type": doc_type,
                "created_at": self.get_current_timestamp(),
                "processed_at": self.get_current_timestamp(),
                "status": "processed",
                "confidence_score": 0.94
            }

            # Extract fields from tab1_content
            extracted_fields = []
            tab1_content = combined_data.get("tab1_content", {})
            
            # Process all field categories from tab1_content
            for category_name, category_data in tab1_content.items():
                if isinstance(category_data, dict):
                    for field_name, field_info in category_data.items():
                        if isinstance(field_info, dict) and "value" in field_info:
                            extracted_fields.append({
                                "field_name": field_name,
                                "field_value": field_info.get("value", ""),
                                "field_type": self._infer_field_type(field_info.get("value", "")),
                                "confidence": field_info.get("confidence", 0.0),
                                "bbox": self._format_bbox(field_info.get("bbox", {})),
                                "category": category_name
                            })

            # Extract search terms from semantic_search_data
            search_index_data = []
            semantic_data = combined_data.get("semantic_search_data", {})
            
            if semantic_data:
                doc_id = metadata["id"]
                
                # Process structured entities
                entities = semantic_data.get("searchable_content", {}).get("structured_entities", [])
                for entity in entities:
                    search_index_data.append({
                        "term": entity.get("entity_text", ""),
                        "document_id": doc_id,
                        "entity_type": entity.get("entity_type", "unknown"),
                        "context": entity.get("context", ""),
                        "relevance": 0.9
                    })
                
                # Process search categories
                search_categories = semantic_data.get("search_categories", {})
                for category, items in search_categories.items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "text" in item:
                                search_index_data.append({
                                    "term": item["text"],
                                    "document_id": doc_id,
                                    "category": category,
                                    "type": item.get("type", "unknown"),
                                    "relevance": 0.8
                                })
                
                # Process primary keywords
                keywords = semantic_data.get("keyword_mapping", {})
                for keyword in keywords.get("primary_keywords", []):
                    search_index_data.append({
                        "term": keyword,
                        "document_id": doc_id,
                        "keyword_type": "primary",
                        "relevance": 0.7
                    })
                
                for keyword in keywords.get("secondary_keywords", []):
                    search_index_data.append({
                        "term": keyword,
                        "document_id": doc_id,
                        "keyword_type": "secondary",
                        "relevance": 0.6
                    })

            return {
                "database_ready_format": {
                    "document_metadata": metadata,
                    "extracted_fields": extracted_fields,
                    "search_index_data": search_index_data
                }
            }

        print("🔄 Chunk 6: Database Format Generation (Using Previous Chunks)...")
        
        # Try to build from previous chunks first
        combined_data = load_previous_chunks_data()
        
        if combined_data:
            try:
                print(f"✅ Found data from previous chunks, building database format...")
                result = build_database_format_from_chunks(combined_data)
                
                # Log statistics
                db_format = result.get("database_ready_format", {})
                field_count = len(db_format.get("extracted_fields", []))
                search_count = len(db_format.get("search_index_data", []))
                print(f"📊 Generated {field_count} fields and {search_count} search terms")
                
                return result
                
            except Exception as manual_err:
                print(f"⚠️ Manual parsing failed: {manual_err}. Falling back to LLM...")
        else:
            print("⚠️ No previous chunk data found. Using LLM fallback...")

        # Enhanced LLM fallback with more detailed prompt
        system_msg = "You are a database optimization specialist. Extract ALL relevant fields and search terms from the document data to create a comprehensive database-ready format."

        user_prompt = f"""Extract comprehensive database-ready format from this {doc_type}. 

IMPORTANT: Extract ALL fields, values, dates, names, amounts, and terms from the provided document data.

Return EXACTLY this JSON structure:

{{
  "database_ready_format": {{
    "document_metadata": {{
      "id": "doc_{int(time.time())}",
      "type": "{doc_type}",
      "created_at": "{self.get_current_timestamp()}",
      "processed_at": "{self.get_current_timestamp()}",
      "status": "processed",
      "confidence_score": 0.94
    }},
    "extracted_fields": [
      // Extract EVERY field from the document with proper data types
      {{"field_name": "performance_review_period", "field_value": "annually", "field_type": "string", "confidence": 0.98, "bbox": "54,72,635,56", "category": "fields_and_values"}},
      {{"field_name": "working_hours_per_week", "field_value": 40, "field_type": "integer", "confidence": 0.98, "bbox": "54,303,635,57", "category": "form_fields"}}
      // Include ALL other fields from the document
    ],
    "search_index_data": [
      // Extract ALL searchable terms, entity names, keywords
      {{"term": "performance review", "document_id": "doc_id", "entity_type": "process", "context": "Annual assessment", "relevance": 0.9}},
      {{"term": "training reimbursement", "document_id": "doc_id", "entity_type": "policy", "context": "Cost recovery policy", "relevance": 0.9}},
      {{"term": "40 hours per week", "document_id": "doc_id", "entity_type": "work_schedule", "context": "Working hours", "relevance": 0.8}}
      // Include ALL other searchable terms
    ]
  }}
}}

Instructions:
- Extract EVERY field, value, amount, date, and term from the document
- Use proper data types: string, integer, decimal, date, boolean
- Include ALL entities mentioned in the semantic search data
- Format bbox as comma-separated coordinates
- Generate comprehensive search index with ALL relevant terms
- Include confidence scores and categories where available
- Return ONLY valid JSON

Document data to process:
{vision_data[:8000]}  

Return the complete database_ready_format JSON with ALL extracted data."""

        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=15000, chunk_name="Database Format")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def _infer_field_type(self, value: str) -> str:
        """Infer field type from value"""
        if not value:
            return "string"
        
        value_str = str(value).strip()
        
        # Check for numeric values
        if value_str.replace(".", "").replace(",", "").replace("-", "").isdigit():
            return "decimal" if "." in value_str else "integer"
        
        # Check for dates (basic patterns)
        if any(pattern in value_str.lower() for pattern in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]):
            return "date"
        
        if any(pattern in value_str for pattern in ["-", "/"]) and any(char.isdigit() for char in value_str):
            return "date"
        
        # Check for boolean-like values
        if value_str.lower() in ["true", "false", "yes", "no"]:
            return "boolean"
            
        return "string"
    
    def _format_bbox(self, bbox_dict: Dict) -> str:
        """Format bbox dictionary to string"""
        if isinstance(bbox_dict, dict):
            return f"{bbox_dict.get('x', 0)},{bbox_dict.get('y', 0)},{bbox_dict.get('width', 0)},{bbox_dict.get('height', 0)}"
        return "0,0,0,0"
    
    def process_immediate_chunks(self, vision_data: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process chunks 1-4 for immediate frontend display."""
        
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        self.session_id = session_id
        print(f"\n🚀 Starting IMMEDIATE processing (Chunks 1-4) - Session: {session_id}")
        
        immediate_result = {}
        chunk_progress = {}
        
        try:
            # Chunk 1: Document Classification
            print("\n" + "="*60)
            chunk1_result = self.chunk_1_document_classification(vision_data)
            immediate_result.update(chunk1_result)
            chunk_progress['classification'] = True
            
            # Get document type for subsequent chunks
            doc_type = chunk1_result.get('document_classification', {}).get('specific_type', 'unknown')
            print(f"📋 Detected document type: {doc_type}")
            
            # Save with session ID
            self.save_progress_with_session(immediate_result, f"{session_id}_chunk1_classification.json")
            
            # Chunk 2: Structured Content
            print("\n" + "="*60)
            chunk2_result = self.chunk_2_structured_content(vision_data, doc_type)
            immediate_result.update(chunk2_result)
            chunk_progress['structured_content'] = True
            self.save_progress_with_session(immediate_result, f"{session_id}_chunk2_content.json")
            
            # Chunk 3: Summary and Insights
            print("\n" + "="*60)
            chunk3_result = self.chunk_3_summary_insights(vision_data, doc_type)
            immediate_result.update(chunk3_result)
            chunk_progress['summary_insights'] = True
            self.save_progress_with_session(immediate_result, f"{session_id}_chunk3_summary.json")
            
            # Chunk 4: Table Extraction
            print("\n" + "="*60)
            chunk4_result = self.chunk_4_table_extraction(vision_data)
            immediate_result.update(chunk4_result)
            chunk_progress['tables'] = True
            self.save_progress_with_session(immediate_result, f"{session_id}_chunk4_tables.json")
            
            print(f"\n✅ IMMEDIATE chunks (1-4) completed successfully!")
            print(f"📊 Immediate progress: {chunk_progress}")
            
            # Save the complete immediate result
            self.save_progress_with_session(immediate_result, f"{session_id}_immediate_complete.json")
            
            # Save to database if enabled
            if self.enable_db and self.db:
                try:
                    doc_id = self.db.save_immediate_results(session_id, {
                        "immediate_result": immediate_result,
                        "session_id": session_id
                    })
                    print(f"💾 Immediate results saved to database: {doc_id}")
                except Exception as e:
                    print(f"⚠️ Failed to save immediate results to database: {e}")
            
            # Save session metadata for background processing
            session_metadata = {
                "session_id": session_id,
                "doc_type": doc_type,
                "vision_data_length": len(vision_data),
                "immediate_completed_at": self.get_current_timestamp(),
                "chunks_completed": list(chunk_progress.keys()),
                "background_status": "pending"
            }
            self.save_progress_with_session(session_metadata, f"{session_id}_metadata.json")
            
            return {
                "session_id": session_id,
                "immediate_result": immediate_result,
                "background_status": "pending",
                "doc_type": doc_type
            }
            
        except Exception as e:
            print(f"\n❌ Error in immediate processing: {e}")
            print(f"📊 Completed chunks: {list(chunk_progress.keys())}")
            
            # Save partial progress
            if immediate_result:
                self.save_progress_with_session(immediate_result, f"{session_id}_immediate_partial.json")
                print("💾 Partial immediate results saved for debugging")
            
            raise

    def process_background_chunks(self, session_id: str, vision_data: str) -> Dict[str, Any]:
        """Process chunks 5-6 in background after immediate chunks are done."""
        
        print(f"\n🔄 Starting BACKGROUND processing (Chunks 5-6) - Session: {session_id}")
        
        background_result = {}
        chunk_progress = {}
        
        try:
            # Load session metadata and immediate results
            session_metadata = self.load_session_data(f"{session_id}_metadata.json")
            if not session_metadata:
                raise Exception(f"Session metadata not found for session: {session_id}")
            
            immediate_data = self.load_session_data(f"{session_id}_immediate_complete.json")
            if not immediate_data:
                raise Exception(f"Immediate results not found for session: {session_id}")
            
            doc_type = session_metadata.get('doc_type', 'unknown')
            print(f"📋 Processing background for document type: {doc_type}")
            
            # Update session status
            session_metadata['background_status'] = 'processing'
            session_metadata['background_started_at'] = self.get_current_timestamp()
            self.save_progress_with_session(session_metadata, f"{session_id}_metadata.json")
            
            # Chunk 5: Semantic Search
            print("\n" + "="*60)
            chunk5_result = self.chunk_5_semantic_search(vision_data, doc_type)
            background_result.update(chunk5_result)
            chunk_progress['semantic_search'] = True
            self.save_progress_with_session(background_result, f"{session_id}_chunk5_search.json")
            
            # Chunk 6: Database Format (now uses session-aware loading)
            print("\n" + "="*60)
            chunk6_result = self.chunk_6_database_format_session(session_id, vision_data, doc_type)
            background_result.update(chunk6_result)
            chunk_progress['database_format'] = True
            self.save_progress_with_session(background_result, f"{session_id}_chunk6_database.json")
            
            # Update session metadata
            session_metadata['background_status'] = 'completed'
            session_metadata['background_completed_at'] = self.get_current_timestamp()
            session_metadata['background_chunks'] = list(chunk_progress.keys())
            self.save_progress_with_session(session_metadata, f"{session_id}_metadata.json")
            
            print(f"\n✅ BACKGROUND chunks (5-6) completed successfully!")
            print(f"📊 Background progress: {chunk_progress}")
            
            # Save complete background result
            self.save_progress_with_session(background_result, f"{session_id}_background_complete.json")
            
            # Save to database if enabled
            if self.enable_db and self.db:
                try:
                    success = self.db.save_background_results(session_id, {
                        "background_result": background_result,
                        "session_id": session_id
                    })
                    if success:
                        print(f"💾 Background results saved to database")
                except Exception as e:
                    print(f"⚠️ Failed to save background results to database: {e}")
            
            # Create final combined result
            final_result = {**immediate_data, **background_result}
            self.save_progress_with_session(final_result, f"{session_id}_final_complete.json")
            
            return {
                "session_id": session_id,
                "background_result": background_result,
                "background_status": "completed",
                "combined_available": True
            }
            
        except Exception as e:
            print(f"\n❌ Error in background processing: {e}")
            print(f"📊 Completed background chunks: {list(chunk_progress.keys())}")
            
            # Update session status to failed
            try:
                session_metadata = self.load_session_data(f"{session_id}_metadata.json")
                if session_metadata:
                    session_metadata['background_status'] = 'failed'
                    session_metadata['background_error'] = str(e)
                    self.save_progress_with_session(session_metadata, f"{session_id}_metadata.json")
            except:
                pass
            
            # Save partial background progress
            if background_result:
                self.save_progress_with_session(background_result, f"{session_id}_background_partial.json")
                print("💾 Partial background results saved for debugging")
            
            raise

    def chunk_6_database_format_session(self, session_id: str, vision_data: str, doc_type: str) -> Dict[str, Any]:
        """Session-aware version of chunk 6 that loads data using session ID."""
        
        def load_previous_chunks_data_session():
            """Load and combine data from session-specific chunk files"""
            try:
                combined_data = {}
                
                # Try to load session-specific chunk files
                for chunk_name in ["chunk1_classification", "chunk2_content", "chunk5_search"]:
                    try:
                        chunk_data = self.load_session_data(f"{session_id}_{chunk_name}.json")
                        if chunk_data:
                            combined_data.update(chunk_data)
                    except Exception as e:
                        print(f"⚠️ Could not load {chunk_name} for session {session_id}: {e}")
                
                return combined_data if combined_data else None
            except Exception as e:
                print(f"❌ Error loading session chunks: {e}")
                return None

        def build_database_format_from_chunks(combined_data: Dict[str, Any]) -> Dict[str, Any]:
            """Build database format using actual chunk data structure"""
            metadata = {
                "id": f"doc_{session_id}_{int(time.time())}",
                "session_id": session_id,
                "type": doc_type,
                "created_at": self.get_current_timestamp(),
                "processed_at": self.get_current_timestamp(),
                "status": "processed",
                "confidence_score": 0.94
            }

            # Extract fields from tab1_content
            extracted_fields = []
            tab1_content = combined_data.get("tab1_content", {})
            
            # Process all field categories from tab1_content
            for category_name, category_data in tab1_content.items():
                if isinstance(category_data, dict):
                    for field_name, field_info in category_data.items():
                        if isinstance(field_info, dict) and "value" in field_info:
                            extracted_fields.append({
                                "field_name": field_name,
                                "field_value": field_info.get("value", ""),
                                "field_type": self._infer_field_type(field_info.get("value", "")),
                                "confidence": field_info.get("confidence", 0.0),
                                "bbox": self._format_bbox(field_info.get("bbox", {})),
                                "category": category_name
                            })

            # Extract search terms from semantic_search_data
            search_index_data = []
            semantic_data = combined_data.get("semantic_search_data", {})
            
            if semantic_data:
                doc_id = metadata["id"]
                
                # Process structured entities
                entities = semantic_data.get("searchable_content", {}).get("structured_entities", [])
                for entity in entities:
                    search_index_data.append({
                        "term": entity.get("entity_text", ""),
                        "document_id": doc_id,
                        "entity_type": entity.get("entity_type", "unknown"),
                        "context": entity.get("context", ""),
                        "relevance": 0.9
                    })
                
                # Process search categories
                search_categories = semantic_data.get("search_categories", {})
                for category, items in search_categories.items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and "text" in item:
                                search_index_data.append({
                                    "term": item["text"],
                                    "document_id": doc_id,
                                    "category": category,
                                    "type": item.get("type", "unknown"),
                                    "relevance": 0.8
                                })
                
                # Process primary keywords
                keywords = semantic_data.get("keyword_mapping", {})
                for keyword in keywords.get("primary_keywords", []):
                    search_index_data.append({
                        "term": keyword,
                        "document_id": doc_id,
                        "keyword_type": "primary",
                        "relevance": 0.7
                    })
                
                for keyword in keywords.get("secondary_keywords", []):
                    search_index_data.append({
                        "term": keyword,
                        "document_id": doc_id,
                        "keyword_type": "secondary",
                        "relevance": 0.6
                    })

            return {
                "database_ready_format": {
                    "document_metadata": metadata,
                    "extracted_fields": extracted_fields,
                    "search_index_data": search_index_data
                }
            }

        print(f"🔄 Chunk 6: Database Format Generation (Session: {session_id})...")
        
        # Try to build from previous chunks first
        combined_data = load_previous_chunks_data_session()
        
        if combined_data:
            try:
                print(f"✅ Found session data, building database format...")
                result = build_database_format_from_chunks(combined_data)
                
                # Log statistics
                db_format = result.get("database_ready_format", {})
                field_count = len(db_format.get("extracted_fields", []))
                search_count = len(db_format.get("search_index_data", []))
                print(f"📊 Generated {field_count} fields and {search_count} search terms")
                
                return result
                
            except Exception as manual_err:
                print(f"⚠️ Session-based parsing failed: {manual_err}. Falling back to LLM...")
        else:
            print("⚠️ No session chunk data found. Using LLM fallback...")

        # Enhanced LLM fallback (same as before but with session awareness)
        system_msg = "You are a database optimization specialist. Extract ALL relevant fields and search terms from the document data to create a comprehensive database-ready format."

        user_prompt = f"""Extract comprehensive database-ready format from this {doc_type} (Session: {session_id}). 

IMPORTANT: Extract ALL fields, values, dates, names, amounts, and terms from the provided document data.

Return EXACTLY this JSON structure:

{{
  "database_ready_format": {{
    "document_metadata": {{
      "id": "doc_{session_id}_{int(time.time())}",
      "session_id": "{session_id}",
      "type": "{doc_type}",
      "created_at": "{self.get_current_timestamp()}",
      "processed_at": "{self.get_current_timestamp()}",
      "status": "processed",
      "confidence_score": 0.94
    }},
    "extracted_fields": [
      // Extract EVERY field from the document with proper data types
      {{"field_name": "performance_review_period", "field_value": "annually", "field_type": "string", "confidence": 0.98, "bbox": "54,72,635,56", "category": "fields_and_values"}},
      {{"field_name": "working_hours_per_week", "field_value": 40, "field_type": "integer", "confidence": 0.98, "bbox": "54,303,635,57", "category": "form_fields"}}
      // Include ALL other fields from the document
    ],
    "search_index_data": [
      // Extract ALL searchable terms, entity names, keywords
      {{"term": "performance review", "document_id": "doc_{session_id}", "entity_type": "process", "context": "Annual assessment", "relevance": 0.9}},
      {{"term": "training reimbursement", "document_id": "doc_{session_id}", "entity_type": "policy", "context": "Cost recovery policy", "relevance": 0.9}}
      // Include ALL other searchable terms
    ]
  }}
}}

Instructions:
- Extract EVERY field, value, amount, date, and term from the document
- Use proper data types: string, integer, decimal, date, boolean
- Include ALL entities mentioned in the semantic search data
- Format bbox as comma-separated coordinates
- Generate comprehensive search index with ALL relevant terms
- Include confidence scores and categories where available
- Return ONLY valid JSON

Document data to process:
{vision_data[:8000]}  

Return the complete database_ready_format JSON with ALL extracted data."""

        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=15000, chunk_name="Database Format")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of both immediate and background processing for a session."""
        try:
            metadata = self.load_session_data(f"{session_id}_metadata.json")
            if not metadata:
                return {"status": "not_found", "session_id": session_id}
            
            return {
                "session_id": session_id,
                "doc_type": metadata.get("doc_type"),
                "immediate_status": "completed" if metadata.get("immediate_completed_at") else "unknown",
                "background_status": metadata.get("background_status", "pending"),
                "immediate_completed_at": metadata.get("immediate_completed_at"),
                "background_started_at": metadata.get("background_started_at"),
                "background_completed_at": metadata.get("background_completed_at"),
                "background_error": metadata.get("background_error"),
                "chunks_completed": metadata.get("chunks_completed", []),
                "background_chunks": metadata.get("background_chunks", [])
            }
            
        except Exception as e:
            return {"status": "error", "session_id": session_id, "error": str(e)}

    def get_session_results(self, session_id: str, result_type: str = "final") -> Optional[Dict[str, Any]]:
        """Get results for a session. result_type can be 'immediate', 'background', or 'final'."""
        try:
            if result_type == "immediate":
                return self.load_session_data(f"{session_id}_immediate_complete.json")
            elif result_type == "background":
                return self.load_session_data(f"{session_id}_background_complete.json")
            elif result_type == "final":
                return self.load_session_data(f"{session_id}_final_complete.json")
            else:
                return None
        except Exception as e:
            print(f"❌ Error loading {result_type} results for session {session_id}: {e}")
            return None

    def save_progress_with_session(self, data: Dict[str, Any], filename: str):
        """Save progress to file with session awareness."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Session progress saved: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save session progress: {e}")

    def load_session_data(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load session data from {filename}: {e}")
            return None
    
    def semantic_search(self, query: str, limit: int = 10, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Perform semantic search on stored documents."""
        if not self.enable_db or not self.db:
            print("⚠️ Database not enabled. Cannot perform semantic search.")
            return []
        
        return self.db.semantic_search(query, limit, document_id)
    
    def get_document_summary_from_db(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document summary from database."""
        if not self.enable_db or not self.db:
            print("⚠️ Database not enabled. Cannot get document summary.")
            return None
        
        return self.db.get_document_summary(document_id)
    
    def get_session_documents_from_db(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a session from database."""
        if not self.enable_db or not self.db:
            print("⚠️ Database not enabled. Cannot get session documents.")
            return []
        
        return self.db.get_session_documents(session_id)
    
    def save_progress(self, data: Dict[str, Any], filename: str):
        """Save progress to file for debugging."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Progress saved: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")

def process_document_from_source(client: PPQChunkedClient, document_path: str, document_type: str = "auto", session_id: Optional[str] = None, debug_mode: bool = False) -> Optional[Dict[str, Any]]:
    """Complete pipeline: Document → Enhanced Vision Extraction → Immediate Processing."""
    print(f"\n=== ENHANCED PIPELINE: Document to Immediate Processing ===")
    print(f"Document: {document_path}")
    print(f"Document type: {document_type}")
    print(f"Debug mode: {'enabled' if debug_mode else 'disabled'}")
    
    try:
        result = client.process_document_from_source(document_path, document_type, session_id, debug_mode)
        
        print("\n" + "="*60)
        print("📄 ENHANCED PIPELINE PROCESSING COMPLETE!")
        
        # Display results with enhanced validation
        immediate_data = result.get('immediate_result', {}).get('immediate_result', {})
        vision_validation = result.get('vision_validation', {})
        
        print(f"📊 Vision Extraction Results:")
        print(f"    Text blocks: {vision_validation.get('text_blocks_count', 0)}")
        print(f"    Document type: {vision_validation.get('document_type', 'unknown')}")
        print(f"    Confidence: {vision_validation.get('confidence', 0.0):.2f}")
        
        if 'document_classification' in immediate_data:
            doc_info = immediate_data['document_classification']
            print(f"📋 Processing Results:")
            print(f"    Document: {doc_info.get('specific_type', 'unknown')} (confidence: {doc_info.get('confidence', 0)})")
        
        session_id = result.get('session_id')
        print(f"🆔 Session ID: {session_id}")
        print(f"📁 Vision extraction saved: {result.get('vision_extraction_file')}")
        
        # Save pipeline result
        output_file = f"enhanced_pipeline_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Enhanced pipeline result saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ENHANCED PIPELINE PROCESSING FAILED: {str(e)}")
        logger.error("Enhanced pipeline processing failed: %s", str(e), exc_info=True)
        return None

def process_document_background_from_source(client: PPQChunkedClient, session_id: str) -> Optional[Dict[str, Any]]:
    """Background processing using saved vision data from pipeline processing."""
    print(f"\n=== PIPELINE BACKGROUND: Using Saved Vision Data ===")
    print(f"Session ID: {session_id}")
    
    try:
        result = client.process_document_background_from_source(session_id)
        
        print("\n" + "="*60)
        print("📄 PIPELINE BACKGROUND PROCESSING COMPLETE!")
        
        # Display key statistics
        background_data = result.get('background_result', {})
        
        if 'semantic_search_data' in background_data:
            search_data = background_data['semantic_search_data']
            if 'searchable_content' in search_data and 'structured_entities' in search_data['searchable_content']:
                entities_count = len(search_data['searchable_content']['structured_entities'])
                print(f"🔍 Searchable Entities: {entities_count}")
        
        if 'database_ready_format' in background_data:
            db_format = background_data['database_ready_format']
            field_count = len(db_format.get('extracted_fields', []))
            search_count = len(db_format.get('search_index_data', []))
            print(f"💾 Database Fields: {field_count}, Search Terms: {search_count}")
        
        print(f"🔄 Background Status: {result.get('background_status', 'unknown')}")
        print(f"📁 Combined Result Available: {result.get('combined_available', False)}")
        
        # Save background result
        output_file = f"pipeline_background_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Pipeline background result saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ PIPELINE BACKGROUND PROCESSING FAILED: {str(e)}")
        logger.error("Pipeline background processing failed: %s", str(e), exc_info=True)
        return None

def process_document_immediate(client: PPQChunkedClient, vision_data: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Process immediate chunks (1-4) for frontend display."""
    print("\n=== IMMEDIATE Document Extraction (Chunks 1-4) ===")
    print(f"Vision data length: {len(vision_data)} characters")
    
    try:
        result = client.process_immediate_chunks(vision_data, session_id)
        
        print("\n" + "="*60)
        print("📄 IMMEDIATE EXTRACTION COMPLETE!")
        
        # Validate immediate completeness
        immediate_sections = [
            'document_classification',
            'tab1_content', 
            'tab2_summary_insights',
            'tab3_tables'
        ]
        
        immediate_data = result.get('immediate_result', {})
        missing_sections = [section for section in immediate_sections if section not in immediate_data]
        
        if missing_sections:
            print(f"⚠️  Warning: Missing immediate sections: {missing_sections}")
        else:
            print("✅ ALL IMMEDIATE SECTIONS PRESENT!")
        
        # Display key statistics
        if 'document_classification' in immediate_data:
            doc_info = immediate_data['document_classification']
            print(f"📊 Document: {doc_info.get('specific_type', 'unknown')} (confidence: {doc_info.get('confidence', 0)})")
        
        if 'tab3_tables' in immediate_data:
            tables_count = len(immediate_data['tab3_tables'].get('identified_tables', []))
            print(f"📋 Tables Extracted: {tables_count}")
        
        session_id = result.get('session_id')
        print(f"🆔 Session ID: {session_id}")
        print(f"🔄 Background Status: {result.get('background_status', 'unknown')}")
        
        # Save immediate result with readable filename
        output_file = f"immediate_extraction_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Immediate extraction saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ IMMEDIATE EXTRACTION FAILED: {str(e)}")
        logger.error("Immediate processing failed: %s", str(e), exc_info=True)
        return None

def process_document_background(client: PPQChunkedClient, session_id: str, vision_data: str) -> Optional[Dict[str, Any]]:
    """Process background chunks (5-6) for semantic search and database preparation."""
    print(f"\n=== BACKGROUND Document Processing (Chunks 5-6) ===")
    print(f"Session ID: {session_id}")
    print(f"Vision data length: {len(vision_data)} characters")
    
    try:
        result = client.process_background_chunks(session_id, vision_data)
        
        print("\n" + "="*60)
        print("📄 BACKGROUND PROCESSING COMPLETE!")
        
        # Validate background completeness
        background_sections = [
            'semantic_search_data',
            'database_ready_format'
        ]
        
        background_data = result.get('background_result', {})
        missing_sections = [section for section in background_sections if section not in background_data]
        
        if missing_sections:
            print(f"⚠️  Warning: Missing background sections: {missing_sections}")
        else:
            print("✅ ALL BACKGROUND SECTIONS PRESENT!")
        
        # Display key statistics
        if 'semantic_search_data' in background_data:
            search_data = background_data['semantic_search_data']
            if 'searchable_content' in search_data and 'structured_entities' in search_data['searchable_content']:
                entities_count = len(search_data['searchable_content']['structured_entities'])
                print(f"🔍 Searchable Entities: {entities_count}")
        
        if 'database_ready_format' in background_data:
            db_format = background_data['database_ready_format']
            field_count = len(db_format.get('extracted_fields', []))
            search_count = len(db_format.get('search_index_data', []))
            print(f"💾 Database Fields: {field_count}, Search Terms: {search_count}")
        
        print(f"🔄 Background Status: {result.get('background_status', 'unknown')}")
        print(f"📁 Combined Result Available: {result.get('combined_available', False)}")
        
        # Save background result
        output_file = f"background_processing_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Background processing saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ BACKGROUND PROCESSING FAILED: {str(e)}")
        logger.error("Background processing failed: %s", str(e), exc_info=True)
        return None

# Keep the original function for backward compatibility
def process_document_with_validation(client: PPQChunkedClient, vision_data: str) -> Optional[Dict[str, Any]]:
    """Legacy function - processes all chunks in sequence (for backward compatibility)."""
    print("\n=== LEGACY: Complete Document Extraction (All Chunks) ===")
    print("⚠️  Consider using the new split approach: process_document_immediate + process_document_background")
    print(f"Vision data length: {len(vision_data)} characters")
    
    try:
        # Use immediate processing first
        immediate_result = process_document_immediate(client, vision_data)
        if not immediate_result:
            return None
            
        session_id = immediate_result.get('session_id')
        
        # Then process background
        background_result = process_document_background(client, session_id, vision_data)
        if not background_result:
            return immediate_result  # Return immediate results even if background fails
        
        # Get final combined result
        final_result = client.get_session_results(session_id, "final")
        
        print("\n" + "="*60)
        print("📄 COMPLETE EXTRACTION FINISHED!")
        
        # Save final complete result
        output_file = f"complete_extraction_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        print(f"💾 Complete extraction saved to: {output_file}")
        
        return final_result
        
    except Exception as e:
        print(f"\n❌ COMPLETE EXTRACTION FAILED: {str(e)}")
        logger.error("Complete processing failed: %s", str(e), exc_info=True)
        return None

def main():
    """Main function supporting both immediate and background processing modes."""
    parser = argparse.ArgumentParser(
        description="PPQ.ai document extraction with immediate and background processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Processing Modes:
  --mode immediate         Process chunks 1-4 with pre-extracted vision data (requires API key + --vision)
  --mode background        Process chunks 5-6 with pre-extracted vision data (requires API key + --session-id + --vision)  
  --mode complete          Process all chunks with pre-extracted vision data (requires API key + --vision)
  --mode pipeline          Complete pipeline: Document → Enhanced Vision → Immediate Processing (requires API key + --document)
  --mode pipeline-background  Background processing using saved vision data from pipeline mode (requires API key + --session-id)
  --mode status            Check status of a session (no API key needed)
  --mode search            Perform semantic search on stored documents (no API key needed)  
  --mode summary           Get document summary from database (no API key needed)

Enhanced Vision Features:
  • PDF page-by-page processing with automatic compression
  • Multi-page document support with combined results
  • Image compression for optimal API performance (max 2MB per page)
  • Automatic document type detection (PDF/image)
  • Robust error handling and fallback mechanisms
  • Preserves individual page data alongside combined results

Examples:
  # NEW: Enhanced pipeline from PDF (recommended - processes each page separately)
  python script.py --document contract.pdf --api-key your-ppq-key --mode pipeline
  
  # NEW: Process multi-page PDF with custom DPI
  python script.py --document large_document.pdf --api-key your-ppq-key --mode pipeline
  
  # NEW: Process scanned image with compression
  python script.py --document invoice_scan.jpg --api-key your-ppq-key --mode pipeline
  
  # Background processing after enhanced pipeline
  python script.py --api-key your-ppq-key --mode pipeline-background --session-id session_123
  
  # Traditional: Immediate processing with pre-extracted vision data
  python script.py --vision @vision.json --api-key your-ppq-key --mode immediate
  
  # Search processed documents (works with both enhanced and traditional processing)
  python script.py --mode search --query "training policy"
  
  # Auto-detect document type
  python script.py --document document.pdf --document-type auto --api-key your-ppq-key --mode pipeline
  
  # Force specific document type processing
  python script.py --document scan.jpg --document-type image --api-key your-ppq-key --mode pipeline

Dependencies:
  pip install requests pillow pymupdf
        """
    )
    
    parser.add_argument(
        "--vision",
        type=str,
        help="Vision extraction data file. Use @filename.json to load from file. Required for processing with pre-extracted vision data.",
    )
    parser.add_argument(
        "--document",
        type=str,
        help="Original document file (PDF, image) for complete pipeline with vision extraction. Alternative to --vision.",
    )
    parser.add_argument(
        "--document-type",
        type=str,
        choices=["auto", "pdf", "image"],
        default="auto",
        help="Type of document for vision extraction (default: auto-detect)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="PPQ.ai API key (required for processing modes: immediate, background, complete)",
        default=os.environ.get("PPQ_API_KEY")
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["immediate", "background", "complete", "status", "search", "summary", "pipeline", "pipeline-background"],
        default="complete",
        help="Processing mode (default: complete)"
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Session ID for background processing or status check"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Search query for semantic search mode"
    )
    parser.add_argument(
        "--document-id",
        type=str,
        help="Document ID for specific document operations"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="chunk_extraction.db",
        help="Path to SQLite database file (default: chunk_extraction.db)"
    )
    parser.add_argument(
        "--disable-db",
        action="store_true",
        help="Disable database integration"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout in seconds (default: 200)",
        default=200
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output and save debug files"
    )
    parser.add_argument(
        "--vision-debug",
        action="store_true", 
        help="Enable enhanced vision debugging (saves images and detailed logs)"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if API key is required for this mode
    api_required_modes = ["immediate", "background", "complete", "pipeline", "pipeline-background"]
    database_only_modes = ["status", "search", "summary"]
    
    if args.mode in api_required_modes and not args.api_key:
        print(f"❌ Error: --api-key is required for {args.mode} mode")
        print("   Set PPQ_API_KEY environment variable or use --api-key flag")
        return 1
    
    # Initialize client (only for modes that need it)
    client = None
    if args.mode in api_required_modes:
        try:
            client = PPQChunkedClient(
                api_key=args.api_key, 
                timeout=args.timeout,
                db_path=args.db_path,
                enable_db=not args.disable_db
            )
            db_status = "enabled" if not args.disable_db else "disabled"
            print(f"✅ PPQ.ai client initialized with split processing support (DB: {db_status})")
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            return 1
    elif args.mode in database_only_modes:
        # For database-only operations, create a minimal database connection
        try:
            if not args.disable_db:
                db = ChunkExtractionDB(args.db_path)
                print(f"✅ Database connection established: {args.db_path}")
            else:
                print("❌ Error: Database operations require database to be enabled")
                return 1
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return 1
    
    # Handle status mode
    if args.mode == "status":
        if not args.session_id:
            print("❌ Error: --session-id is required for status mode")
            return 1
        
        # Use file-based status check (no API needed)
        try:
            with open(f"{args.session_id}_metadata.json", 'r') as f:
                status = json.load(f)
            print("\n📊 SESSION STATUS:")
            print(json.dumps(status, indent=2))
        except FileNotFoundError:
            print(f"❌ Session {args.session_id} not found")
            return 1
        except Exception as e:
            print(f"❌ Error reading session status: {e}")
            return 1
        return 0
    
    # Handle search mode
    if args.mode == "search":
        if not args.query:
            print("❌ Error: --query is required for search mode")
            return 1
        
        print(f"\n🔍 SEMANTIC SEARCH: '{args.query}'")
        results = db.semantic_search(args.query, limit=20, document_id=args.document_id)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Term: '{result['term']}'")
                print(f"   Document: {result['document_id']} ({result['document_type']})")
                print(f"   Context: {result['context']}")
                print(f"   Relevance: {result['relevance']}")
                if result['category']:
                    print(f"   Category: {result['category']}")
        else:
            print("No results found.")
        return 0
    
    # Handle summary mode
    if args.mode == "summary":
        if not args.document_id:
            print("❌ Error: --document-id is required for summary mode")
            return 1
        
        print(f"\n📊 DOCUMENT SUMMARY: {args.document_id}")
        
        # Get document summary from database
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM document_metadata WHERE id = ?", (args.document_id,))
            doc_row = cursor.fetchone()
            
            if doc_row:
                doc_columns = [desc[0] for desc in cursor.description]
                doc_metadata = dict(zip(doc_columns, doc_row))
                
                cursor.execute("SELECT category, COUNT(*) FROM extracted_fields WHERE document_id = ? GROUP BY category", (args.document_id,))
                field_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                cursor.execute("SELECT COUNT(*) FROM semantic_index WHERE document_id = ?", (args.document_id,))
                semantic_count = cursor.fetchone()[0]
                
                summary = {
                    'document_metadata': doc_metadata,
                    'field_counts_by_category': field_counts,
                    'semantic_terms_count': semantic_count,
                    'total_fields': sum(field_counts.values())
                }
                
                print(json.dumps(summary, indent=2))
            else:
                print("Document not found.")
        except Exception as e:
            print(f"❌ Error getting document summary: {e}")
            return 1
        finally:
            conn.close()
        return 0
    
    # Handle modes that require vision data or document input
    vision_modes = ["immediate", "background", "complete"]
    pipeline_modes = ["pipeline"]
    
    if args.mode in vision_modes:
        if not args.vision:
            print(f"❌ Error: --vision is required for {args.mode} mode")
            print("   Use --vision @filename.json or provide vision extraction data")
            return 1
        
        # Load vision data
        try:
            vision_data = process_file_parameter(args.vision)
            print(f"✅ Vision data loaded ({len(vision_data)} characters)")
        except Exception as e:
            print(f"Error loading vision file: {e}")
            return 1
        
        # Validate vision data is JSON
        try:
            json.loads(vision_data)
            print("✅ Vision data is valid JSON")
        except json.JSONDecodeError:
            print("❌ Error: Vision data is not valid JSON")
            return 1
    
    elif args.mode in pipeline_modes:
        if not args.document:
            print(f"❌ Error: --document is required for {args.mode} mode")
            print("   Provide original document file (PDF, image) for vision extraction")
            return 1
        
        # Validate document file exists
        if not os.path.exists(args.document):
            print(f"❌ Error: Document file not found: {args.document}")
            return 1
        
        print(f"✅ Document file found: {args.document}")
    
    elif args.mode == "pipeline-background":
        if not args.session_id:
            print("❌ Error: --session-id is required for pipeline-background mode")
            return 1
    
    # Process based on mode
    if args.mode == "pipeline":
        print(f"\n🚀 Starting ENHANCED PIPELINE mode (Document → Vision → Processing)...")
        result = process_document_from_source(
            client, 
            args.document, 
            args.document_type, 
            args.session_id,
            debug_mode=(args.debug or args.vision_debug)
        )
        
        if result:
            session_id = result.get('session_id')
            vision_validation = result.get('vision_validation', {})
            
            print(f"\n🎉 ENHANCED PIPELINE PROCESSING COMPLETED!")
            print(f"🆔 Session ID: {session_id}")
            print(f"📄 Vision extraction saved: {result.get('vision_extraction_file')}")
            print(f"📊 Extracted {vision_validation.get('text_blocks_count', 0)} text blocks")
            print(f"📄 Use this session ID for background processing:")
            print(f"   python {sys.argv[0]} --api-key {args.api_key} --mode pipeline-background --session-id {session_id}")
            
            if args.vision_debug:
                print(f"🐛 Debug files saved in debug_images/ directory")
                
            return 0
        else:
            print("\n💥 ENHANCED PIPELINE PROCESSING FAILED!")
            return 1
            
    elif args.mode == "pipeline-background":
        print(f"\n🔄 Starting PIPELINE BACKGROUND mode...")
        print(f"🆔 Session ID: {args.session_id}")
        
        result = process_document_background_from_source(client, args.session_id)
        
        if result:
            print(f"\n🎉 PIPELINE BACKGROUND PROCESSING COMPLETED!")
            print(f"📁 Final combined result available")
            return 0
        else:
            print("\n💥 PIPELINE BACKGROUND PROCESSING FAILED!")
            return 1
            
    elif args.mode == "immediate":
        print(f"\n🚀 Starting IMMEDIATE processing mode...")
        result = process_document_immediate(client, vision_data, args.session_id)
        
        if result:
            session_id = result.get('session_id')
            print(f"\n🎉 IMMEDIATE PROCESSING COMPLETED!")
            print(f"🆔 Session ID: {session_id}")
            print(f"📄 Use this session ID for background processing:")
            print(f"   python {sys.argv[0]} --vision {args.vision} --api-key {args.api_key} --mode background --session-id {session_id}")
            return 0
        else:
            print("\n💥 IMMEDIATE PROCESSING FAILED!")
            return 1
            
    elif args.mode == "background":
        if not args.session_id:
            print("❌ Error: --session-id is required for background mode")
            return 1
        
        print(f"\n🔄 Starting BACKGROUND processing mode...")
        print(f"🆔 Session ID: {args.session_id}")
        
        result = process_document_background(client, args.session_id, vision_data)
        
        if result:
            print(f"\n🎉 BACKGROUND PROCESSING COMPLETED!")
            print(f"📁 Final combined result available")
            return 0
        else:
            print("\n💥 BACKGROUND PROCESSING FAILED!")
            return 1
            
    elif args.mode == "complete":
        print(f"\n📄 Starting COMPLETE processing mode (legacy)...")
        result = process_document_with_validation(client, vision_data)
        
        if result:
            print("\n🎉 COMPLETE PROCESSING FINISHED!")
            return 0
        else:
            print("\n💥 COMPLETE PROCESSING FAILED!")
            return 1
    
    return 1

if __name__ == "__main__":
    sys.exit(main())