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
from typing import Dict, List, Optional, Any
from datetime import datetime

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

class PPQChunkedClient:
    """PPQ.ai client with chunked processing and self-contained prompts."""
    
    def __init__(self, api_key: str, timeout: int = 200):
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
        """Chunk 5: Semantic Search Data Generation"""
        
        system_msg = "You are a search optimization expert. Generate comprehensive searchable content with precise location mapping."
        
        user_prompt = f"""Generate searchable content for this {doc_type}. Return EXACTLY this JSON structure:

{{
  "semantic_search_data": {{
    "searchable_content": {{
      "full_text_index": "Complete concatenated searchable text from entire document",
      "structured_entities": [
        {{
          "entity_text": "Company Name",
          "entity_type": "organization",
          "context": "Vendor information",
          "bbox": {{"x": 240, "y": 120, "width": 400, "height": 60}},
          "confidence": 0.98,
          "related_terms": ["Company", "Corp", "LLC"]
        }},
        {{
          "entity_text": "$1,500.00",
          "entity_type": "currency",
          "context": "Total amount",
          "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}},
          "confidence": 0.95,
          "related_terms": ["total", "amount", "1500", "fifteen hundred"]
        }}
      ]
    }},
    "search_categories": {{
      "contact_information": {{
        "items": [
          {{"text": "email@example.com", "type": "email", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}},
          {{"text": "(555) 123-4567", "type": "phone", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}}
        ]
      }},
      "financial_data": {{
        "items": [
          {{"text": "$1,500.00", "type": "total_amount", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}},
          {{"text": "$150.00", "type": "tax_amount", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}}
        ]
      }},
      "dates_and_deadlines": {{
        "items": [
          {{"text": "2025-01-15", "type": "document_date", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}},
          {{"text": "2025-02-15", "type": "due_date", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}}
        ]
      }},
      "identifiers_and_references": {{
        "items": [
          {{"text": "INV-2025-001", "type": "invoice_number", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}},
          {{"text": "PO-12345", "type": "purchase_order", "bbox": {{"x": 0, "y": 0, "width": 0, "height": 0}}}}
        ]
      }}
    }},
    "keyword_mapping": {{
      "primary_keywords": ["invoice", "payment", "total", "amount"],
      "secondary_keywords": ["services", "tax", "due", "net"],
      "location_keywords": ["header", "footer", "line_items", "totals"],
      "coordinate_ranges": {{
        "header_region": {{"x_range": [0, 2480], "y_range": [0, 400]}},
        "body_region": {{"x_range": [0, 2480], "y_range": [400, 1400]}},
        "footer_region": {{"x_range": [0, 2480], "y_range": [1400, 3508]}}
      }}
    }}
  }}
}}

Instructions:
- Extract ALL searchable text and entities (minimum 20 entities)
- Use ACTUAL coordinates from vision data
- Create comprehensive search categories
- Generate related terms for better search matching
- Map keywords to document regions
- Return ONLY valid JSON. Escape all line breaks and special characters properly using JSON syntax. Do NOT include unescaped newlines or tabs inside string values.

Vision Data for search indexing:
{vision_data}

Return ONLY the complete semantic_search_data JSON structure."""

        print("🔄 Chunk 5: Semantic Search Data...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=20000, chunk_name="Semantic Search")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def chunk_6_database_format(self, vision_data: str, doc_type: str) -> Dict[str, Any]:
        """Chunk 6: Database-Ready Format"""
        
        system_msg = "You are a database optimization specialist. Generate database-ready format for efficient storage and querying."
        
        user_prompt = f"""Generate database-optimized format for this {doc_type}. Return EXACTLY this JSON structure:

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
      {{"field_name": "document_number", "field_value": "INV-001", "field_type": "string", "confidence": 0.95, "bbox": "240,120,400,60"}},
      {{"field_name": "total_amount", "field_value": 1500.00, "field_type": "decimal", "confidence": 0.98, "bbox": "2000,1500,480,120"}},
      {{"field_name": "document_date", "field_value": "2025-01-15", "field_type": "date", "confidence": 0.95, "bbox": "1600,460,700,200"}}
    ],
    "search_index_data": [
      {{"term": "invoice", "document_id": "doc_id", "positions": [{{"x": 900, "y": 320, "w": 600, "h": 70}}], "relevance": 0.9}},
      {{"term": "total", "document_id": "doc_id", "positions": [{{"x": 2000, "y": 1500, "w": 480, "h": 120}}], "relevance": 0.8}},
      {{"term": "company", "document_id": "doc_id", "positions": [{{"x": 240, "y": 120, "w": 400, "h": 60}}], "relevance": 0.7}}
    ]
  }}
}}

Instructions:
- Create optimized field extraction for database storage
- Generate searchable index terms with positions
- Use proper data types (string, decimal, date, integer)
- Include relevance scoring for search terms
- Serialize coordinates as comma-separated strings
- Return ONLY valid JSON. Escape all line breaks and special characters properly using JSON syntax. Do NOT include unescaped newlines or tabs inside string values.

Vision Data for database optimization:
{vision_data}

Return ONLY the complete database_ready_format JSON structure."""

        print("🔄 Chunk 6: Database Format Generation...")
        response = self.make_api_request_with_retry(system_msg, user_prompt, max_tokens=12000, chunk_name="Database Format")
        clean_json = self.extract_json_from_response(response)
        return json.loads(clean_json)
    
    def process_document_in_chunks(self, vision_data: str) -> Dict[str, Any]:
        """Process document using chunked approach with self-contained prompts."""
        
        complete_result = {}
        chunk_progress = {}
        
        try:
            # Chunk 1: Document Classification
            print("\n" + "="*60)
            chunk1_result = self.chunk_1_document_classification(vision_data)
            complete_result.update(chunk1_result)
            chunk_progress['classification'] = True
            
            # Get document type for subsequent chunks
            doc_type = chunk1_result.get('document_classification', {}).get('specific_type', 'unknown')
            print(f"📋 Detected document type: {doc_type}")
            
            # Save progress
            self.save_progress(complete_result, "chunk1_classification.json")
            
            # Chunk 2: Structured Content
            print("\n" + "="*60)
            chunk2_result = self.chunk_2_structured_content(vision_data, doc_type)
            complete_result.update(chunk2_result)
            chunk_progress['structured_content'] = True
            self.save_progress(complete_result, "chunk2_content.json")
            
            # Chunk 3: Summary and Insights
            print("\n" + "="*60)
            chunk3_result = self.chunk_3_summary_insights(vision_data, doc_type)
            complete_result.update(chunk3_result)
            chunk_progress['summary_insights'] = True
            self.save_progress(complete_result, "chunk3_summary.json")
            
            # Chunk 4: Table Extraction
            print("\n" + "="*60)
            chunk4_result = self.chunk_4_table_extraction(vision_data)
            complete_result.update(chunk4_result)
            chunk_progress['tables'] = True
            self.save_progress(complete_result, "chunk4_tables.json")
            
            # Chunk 5: Semantic Search
            print("\n" + "="*60)
            chunk5_result = self.chunk_5_semantic_search(vision_data, doc_type)
            complete_result.update(chunk5_result)
            chunk_progress['semantic_search'] = True
            self.save_progress(complete_result, "chunk5_search.json")
            
            # Chunk 6: Database Format
            print("\n" + "="*60)
            chunk6_result = self.chunk_6_database_format(vision_data, doc_type)
            complete_result.update(chunk6_result)
            chunk_progress['database_format'] = True
            self.save_progress(complete_result, "chunk6_database.json")
            
            print(f"\n✅ All chunks completed successfully!")
            print(f"📊 Chunk progress: {chunk_progress}")
            
            return complete_result
            
        except Exception as e:
            print(f"\n❌ Error in chunked processing: {e}")
            print(f"📊 Completed chunks: {list(chunk_progress.keys())}")
            
            # Save partial progress
            if complete_result:
                self.save_progress(complete_result, "partial_extraction.json")
                print("💾 Partial results saved for debugging")
            
            raise
    
    def save_progress(self, data: Dict[str, Any], filename: str):
        """Save progress to file for debugging."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Progress saved: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")

def process_document_with_validation(client: PPQChunkedClient, vision_data: str) -> Optional[Dict[str, Any]]:
    """Process document extraction with full validation and error handling."""
    print("\n=== Chunked Document Extraction with Self-Contained Prompts ===")
    print(f"Vision data length: {len(vision_data)} characters")
    
    try:
        result = client.process_document_in_chunks(vision_data)
        
        print("\n" + "="*60)
        print("📄 EXTRACTION COMPLETE!")
        
        # Validate completeness
        required_sections = [
            'document_classification',
            'tab1_content', 
            'tab2_summary_insights',
            'tab3_tables',
            'semantic_search_data',
            'database_ready_format'
        ]
        
        missing_sections = [section for section in required_sections if section not in result]
        
        if missing_sections:
            print(f"⚠️  Warning: Missing sections: {missing_sections}")
        else:
            print("✅ ALL REQUIRED SECTIONS PRESENT!")
        
        # Display key statistics
        if 'document_classification' in result:
            doc_info = result['document_classification']
            print(f"📊 Document: {doc_info.get('specific_type', 'unknown')} (confidence: {doc_info.get('confidence', 0)})")
        
        if 'semantic_search_data' in result:
            search_data = result['semantic_search_data']
            if 'searchable_content' in search_data and 'structured_entities' in search_data['searchable_content']:
                entities_count = len(search_data['searchable_content']['structured_entities'])
                print(f"🔍 Searchable Entities: {entities_count}")
        
        if 'tab3_tables' in result:
            tables_count = len(result['tab3_tables'].get('identified_tables', []))
            print(f"📋 Tables Extracted: {tables_count}")
        
        # Save final complete result
        output_file = "complete_chunked_extraction.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Complete extraction saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ EXTRACTION FAILED: {str(e)}")
        logger.error("Chunked processing failed: %s", str(e), exc_info=True)
        return None

def main():
    """Main function for chunked document extraction."""
    parser = argparse.ArgumentParser(
        description="Chunked PPQ.ai document extraction with self-contained prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--vision",
        type=str,
        help="Vision extraction data file. Use @filename.json to load from file",
        required=True
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="PPQ.ai API key",
        default=os.environ.get("PPQ_API_KEY"),
        required=True
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
    
    # Load vision data only (no prompt file needed!)
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
    
    # Initialize client with retry logic
    try:
        client = PPQChunkedClient(api_key=args.api_key, timeout=args.timeout)
        print("✅ PPQ.ai client initialized with chunked processing and retry logic")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return 1
    
    # Process the document in chunks
    result = process_document_with_validation(client, vision_data)
    
    if result:
        print("\n🎉 CHUNKED DOCUMENT EXTRACTION COMPLETED SUCCESSFULLY!")
        return 0
    else:
        print("\n💥 CHUNKED DOCUMENT EXTRACTION FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())