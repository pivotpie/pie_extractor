"""Self-contained PPQ.ai document extraction with chunked processing and built-in prompts.

Usage:
    python ppq_chunked_self_contained.py --vision '@vision_extract.json' --api-key "your-key"
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
import mimetypes
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

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

    def get_session_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, document_type, confidence, status, 
                       immediate_completed_at, background_completed_at
                FROM document_metadata 
                WHERE session_id = ?
                ORDER BY created_at DESC
            """, (session_id,))
            
            results = cursor.fetchall()
            return [
                {
                    'document_id': row[0],
                    'document_type': row[1],
                    'confidence': row[2],
                    'status': row[3],
                    'immediate_completed_at': row[4],
                    'background_completed_at': row[5]
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"❌ Error getting session documents: {e}")
            return []
        finally:
            conn.close()

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
    
    def extract_vision_data(self, file_path: str) -> Optional[str]:
        """Extract vision data from document file (PDF, images, etc.)."""
        try:
            print(f"🔍 Starting vision extraction for: {file_path}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file info
            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            print(f"📄 File size: {file_size:,} bytes")
            print(f"📝 MIME type: {mime_type}")
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            # Prepare vision extraction request
            vision_url = f"{self.base_url}/chat/completions"
            
            vision_data = {
                "model": "gpt-4.1",  # or appropriate vision model
                "file_data": file_base64,
                "file_type": mime_type or "application/octet-stream",
                "file_name": os.path.basename(file_path),
                "extraction_options": {
                    "include_text_blocks": True,
                    "include_coordinates": True,
                    "include_confidence": True,
                    "ocr_language": "auto",
                    "extract_tables": True,
                    "extract_forms": True
                },
                "temperature": 0.0,
                "max_tokens": 32000
            }
            
            print("📡 Calling vision extraction API...")
            
            response = requests.post(
                vision_url, 
                json=vision_data, 
                headers=self.headers, 
                timeout=self.timeout * 2  # Vision extraction takes longer
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the vision data from response
            if "vision_data" in result:
                vision_json = result["vision_data"]
            elif "choices" in result and len(result["choices"]) > 0:
                # Handle standard OpenAI-like response
                vision_content = result["choices"][0]["message"]["content"]
                try:
                    # Try to parse as JSON if it's a JSON string
                    vision_json = json.loads(vision_content)
                except json.JSONDecodeError:
                    # If not JSON, wrap in a structure
                    vision_json = {
                        "document_type": "unknown",
                        "text_content": vision_content,
                        "text_blocks": [{"text": vision_content, "bbox": {"x": 0, "y": 0, "width": 100, "height": 100}}],
                        "extraction_metadata": {
                            "file_name": os.path.basename(file_path),
                            "file_size": file_size,
                            "mime_type": mime_type,
                            "extracted_at": datetime.now().isoformat()
                        }
                    }
            else:
                raise Exception("Unexpected vision API response format")
            
            # Convert to JSON string
            vision_json_str = json.dumps(vision_json, ensure_ascii=False)
            
            print(f"✅ Vision extraction complete ({len(vision_json_str)} characters)")
            
            # Save vision data for debugging/reuse
            vision_file = f"vision_extraction_{int(time.time())}.json"
            with open(vision_file, 'w', encoding='utf-8') as f:
                f.write(vision_json_str)
            print(f"💾 Vision data saved to: {vision_file}")
            
            return vision_json_str
            
        except requests.exceptions.Timeout:
            print("⏱️ Vision extraction timeout - try reducing file size or increasing timeout")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"🚫 Vision API error: {e}")
            if e.response.status_code == 413:
                print("   File too large - try reducing file size")
            elif e.response.status_code == 415:
                print("   Unsupported file type")
            raise
        except Exception as e:
            print(f"❌ Vision extraction failed: {e}")
            raise

    def process_document_from_file(self, file_path: str, session_id: Optional[str] = None, mode: str = "complete") -> Optional[Dict[str, Any]]:
        """Complete document processing pipeline from file to results."""
        try:
            # Step 1: Vision extraction
            print(f"\n{'='*60}")
            print("🎯 COMPLETE DOCUMENT PROCESSING PIPELINE")
            print(f"📄 Input file: {file_path}")
            print(f"🔄 Processing mode: {mode}")
            print(f"{'='*60}")
            
            vision_data = self.extract_vision_data(file_path)
            if not vision_data:
                print("❌ Vision extraction failed")
                return None
            
            # Step 2: Process based on mode
            if mode == "immediate":
                print(f"\n{'='*60}")
                print("⚡ IMMEDIATE PROCESSING (Chunks 1-4)")
                result = self.process_immediate_chunks(vision_data, session_id)
                
                if result:
                    result['vision_file'] = f"vision_extraction_{int(time.time())}.json"
                    result['source_file'] = file_path
                
                return result
                
            elif mode == "complete":
                print(f"\n{'='*60}")
                print("📄 COMPLETE PROCESSING (All Chunks)")
                
                # First do immediate processing
                immediate_result = self.process_immediate_chunks(vision_data, session_id)
                if not immediate_result:
                    return None
                
                session_id = immediate_result.get('session_id')
                
                # Then do background processing
                background_result = self.process_background_chunks(session_id, vision_data)
                
                # Combine results
                if background_result:
                    final_result = self.get_session_results(session_id, "final")
                    if final_result:
                        final_result['vision_file'] = f"vision_extraction_{int(time.time())}.json"
                        final_result['source_file'] = file_path
                    return final_result
                else:
                    # Return immediate results even if background failed
                    immediate_result['vision_file'] = f"vision_extraction_{int(time.time())}.json"
                    immediate_result['source_file'] = file_path
                    return immediate_result
            
            else:
                print(f"❌ Unsupported processing mode for file input: {mode}")
                return None
                
        except Exception as e:
            print(f"❌ Document processing pipeline failed: {e}")
            return None
    
    def background_process_from_vision_file(self, session_id: str, vision_file: str) -> Optional[Dict[str, Any]]:
        """Process background chunks using saved vision file."""
        try:
            # Load vision data from file
            with open(vision_file, 'r', encoding='utf-8') as f:
                vision_data = f.read()
            
            print(f"📂 Loaded vision data from: {vision_file}")
            
            # Process background chunks
            return self.process_background_chunks(session_id, vision_data)
            
        except Exception as e:
            print(f"❌ Background processing from vision file failed: {e}")
            return None
    
    def get_current_timestamp(self) -> str:
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

def process_document_from_file_immediate(client: PPQChunkedClient, file_path: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Process document from file - immediate mode (vision + chunks 1-4)."""
    print("\n=== COMPLETE PIPELINE: Document → Vision → Immediate Processing ===")
    print(f"Input file: {file_path}")
    
    try:
        result = client.process_document_from_file(file_path, session_id, "immediate")
        
        if result:
            print("\n" + "="*60)
            print("📄 PIPELINE COMPLETE (IMMEDIATE)!")
            
            # Display results similar to original function
            immediate_data = result.get('immediate_result', {})
            
            if 'document_classification' in immediate_data:
                doc_info = immediate_data['document_classification']
                print(f"📊 Document: {doc_info.get('specific_type', 'unknown')} (confidence: {doc_info.get('confidence', 0)})")
            
            if 'tab3_tables' in immediate_data:
                tables_count = len(immediate_data['tab3_tables'].get('identified_tables', []))
                print(f"📋 Tables Extracted: {tables_count}")
            
            session_id = result.get('session_id')
            source_file = result.get('source_file')
            vision_file = result.get('vision_file')
            
            print(f"🆔 Session ID: {session_id}")
            print(f"📄 Source File: {source_file}")
            print(f"🔍 Vision File: {vision_file}")
            
            # Save readable output
            output_file = f"immediate_extraction_{session_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 Results saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {str(e)}")
        logger.error("Document pipeline failed: %s", str(e), exc_info=True)
        return None

def process_document_from_file_complete(client: PPQChunkedClient, file_path: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Process document from file - complete mode (vision + all chunks)."""
    print("\n=== COMPLETE PIPELINE: Document → Vision → All Chunks → Database ===")
    print(f"Input file: {file_path}")
    
    try:
        result = client.process_document_from_file(file_path, session_id, "complete")
        
        if result:
            print("\n" + "="*60)
            print("📄 COMPLETE PIPELINE FINISHED!")
            
            # Display comprehensive results
            if 'document_classification' in result:
                doc_info = result['document_classification']
                print(f"📊 Document: {doc_info.get('specific_type', 'unknown')} (confidence: {doc_info.get('confidence', 0)})")
            
            if 'semantic_search_data' in result:
                search_data = result['semantic_search_data']
                if 'searchable_content' in search_data and 'structured_entities' in search_data['searchable_content']:
                    entities_count = len(search_data['searchable_content']['structured_entities'])
                    print(f"🔍 Searchable Entities: {entities_count}")
            
            if 'database_ready_format' in result:
                db_format = result['database_ready_format']
                field_count = len(db_format.get('extracted_fields', []))
                search_count = len(db_format.get('search_index_data', []))
                print(f"💾 Database Fields: {field_count}, Search Terms: {search_count}")
            
            source_file = result.get('source_file')
            vision_file = result.get('vision_file')
            
            print(f"📄 Source File: {source_file}")
            print(f"🔍 Vision File: {vision_file}")
            
            # Save readable output
            output_file = f"complete_extraction_{int(time.time())}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 Complete results saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ COMPLETE PIPELINE FAILED: {str(e)}")
        logger.error("Complete document pipeline failed: %s", str(e), exc_info=True)
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
  --mode immediate    Process chunks 1-4 for immediate frontend display (requires API key)
  --mode background   Process chunks 5-6 in background (requires API key + session-id)
  --mode complete     Process all chunks in sequence (requires API key)
  --mode vision-only  Extract vision data from document file only (requires API key)
  --mode status       Check status of a session (no API key needed)
  --mode search       Perform semantic search on stored documents (no API key needed)  
  --mode summary      Get document summary from database (no API key needed)

Input Options:
  --document FILE     Process raw document file (PDF, PNG, JPG, etc.) - includes vision extraction
  --vision @FILE.json Use pre-processed vision JSON file
  --vision-file FILE  Use saved vision extraction file (for background mode)

Examples:

  # COMPLETE PIPELINE: Document file → Vision extraction → All chunks → Database
  python script.py --document contract.pdf --api-key your-ppq-key --mode complete
  
  # TWO-PHASE PROCESSING: Document file → Immediate results (30-60s)
  python script.py --document contract.pdf --api-key your-ppq-key --mode immediate
  # Then background processing using the saved vision file:
  python script.py --vision-file vision_extraction_123.json --api-key your-ppq-key --mode background --session-id session_123
  
  # VISION EXTRACTION ONLY: Document → Vision JSON (no chunk processing)
  python script.py --document contract.pdf --api-key your-ppq-key --mode vision-only
  
  # TRADITIONAL: Pre-processed vision JSON → Chunks → Database
  python script.py --vision @vision.json --api-key your-ppq-key --mode complete
  
  # DATABASE OPERATIONS (no API key needed):
  python script.py --mode status --session-id session_123
  python script.py --mode search --query "training policy"
  python script.py --mode summary --document-id doc_session_123
  
  # SUPPORTED FILE TYPES:
  python script.py --document contract.pdf --api-key key --mode complete
  python script.py --document invoice.png --api-key key --mode immediate  
  python script.py --document receipt.jpg --api-key key --mode complete
        """
    )
    
    parser.add_argument(
        "--version",
        action="version", 
        version="PPQ.ai Document Processing Pipeline v2.0.0"
    )
    
    parser.add_argument(
        "--document",
        type=str,
        help="Document file path (PDF, PNG, JPG, etc.) for vision extraction + processing"
    )
    parser.add_argument(
        "--vision",
        type=str,
        help="Pre-processed vision JSON file. Use @filename.json to load from file. Alternative to --document."
    )
    parser.add_argument(
        "--vision-file", 
        type=str,
        help="Saved vision extraction file for background processing (alternative to --vision)"
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
        choices=["immediate", "background", "complete", "status", "search", "summary", "vision-only"],
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
        help="Enable debug output"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if API key is required for this mode
    api_required_modes = ["immediate", "background", "complete", "vision-only"]
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
    
    # Handle vision-only mode
    if args.mode == "vision-only":
        if not args.document:
            print("❌ Error: --document is required for vision-only mode")
            return 1
            
        try:
            print(f"\n🔍 VISION EXTRACTION ONLY")
            vision_data = client.extract_vision_data(args.document)
            
            if vision_data:
                print(f"\n✅ Vision extraction completed successfully!")
                print(f"📄 Vision data length: {len(vision_data)} characters")
                print(f"💾 Vision data saved to file for later use")
                return 0
            else:
                print(f"\n❌ Vision extraction failed!")
                return 1
                
        except Exception as e:
            print(f"\n❌ Vision extraction error: {e}")
            return 1
    
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
    
    # Handle modes that require input data
    if args.mode in ["immediate", "complete", "vision-only"]:
        # These modes need either --document or --vision
        if not args.document and not args.vision:
            print(f"❌ Error: {args.mode} mode requires either --document (raw file) or --vision (processed JSON)")
            return 1
        
        if args.document and args.vision:
            print("❌ Error: Cannot specify both --document and --vision. Choose one input method.")
            return 1
            
    elif args.mode == "background":
        # Background mode needs vision data and session-id
        if not args.session_id:
            print("❌ Error: --session-id is required for background mode")
            return 1
            
        if not args.vision and not args.vision_file:
            print("❌ Error: background mode requires either --vision or --vision-file")
            return 1
    
    # Process based on mode
    if args.mode == "immediate":
        print(f"\n🚀 Starting IMMEDIATE processing mode...")
        
        if args.document:
            # Process raw document file (includes vision extraction)
            result = client.process_document_from_file(args.document, args.session_id, "immediate")
        else:
            # Process pre-existing vision JSON
            vision_data = process_file_parameter(args.vision)
            print(f"✅ Vision data loaded ({len(vision_data)} characters)")
            json.loads(vision_data)  # Validate JSON
            print("✅ Vision data is valid JSON")
            
            result = process_document_immediate(client, vision_data, args.session_id)
        
        if result:
            session_id = result.get('session_id')
            print(f"\n🎉 IMMEDIATE PROCESSING COMPLETED!")
            print(f"🆔 Session ID: {session_id}")
            print(f"📄 Use this session ID for background processing:")
            
            if args.document:
                # For document files, background can use saved vision file
                vision_file = result.get('vision_file', 'vision_extraction_*.json')
                print(f"   python {sys.argv[0]} --vision-file {vision_file} --api-key {args.api_key} --mode background --session-id {session_id}")
            else:
                # For vision JSON files, use the same file
                print(f"   python {sys.argv[0]} --vision {args.vision} --api-key {args.api_key} --mode background --session-id {session_id}")
            return 0
        else:
            print("\n💥 IMMEDIATE PROCESSING FAILED!")
            return 1
            
    elif args.mode == "background":
        print(f"\n🔄 Starting BACKGROUND processing mode...")
        print(f"🆔 Session ID: {args.session_id}")
        
        if args.vision_file:
            # Use saved vision extraction file
            result = client.background_process_from_vision_file(args.session_id, args.vision_file)
        else:
            # Use vision JSON file
            vision_data = process_file_parameter(args.vision)
            print(f"✅ Vision data loaded ({len(vision_data)} characters)")
            json.loads(vision_data)  # Validate JSON
            print("✅ Vision data is valid JSON")
            
            result = process_document_background(client, args.session_id, vision_data)
        
        if result:
            print(f"\n🎉 BACKGROUND PROCESSING COMPLETED!")
            print(f"📁 Final combined result available")
            return 0
        else:
            print("\n💥 BACKGROUND PROCESSING FAILED!")
            return 1
            
    elif args.mode == "complete":
        print(f"\n📄 Starting COMPLETE processing mode...")
        
        if args.document:
            # Process raw document file (includes vision extraction + all chunks)
            result = client.process_document_from_file(args.document, args.session_id, "complete")
        else:
            # Process pre-existing vision JSON (legacy mode)
            vision_data = process_file_parameter(args.vision)
            print(f"✅ Vision data loaded ({len(vision_data)} characters)")
            json.loads(vision_data)  # Validate JSON
            print("✅ Vision data is valid JSON")
            
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