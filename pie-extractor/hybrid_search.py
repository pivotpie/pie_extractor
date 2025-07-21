"""
Hybrid Semantic Search System for RAG.
Combines TF-IDF fast filtering with LLM semantic scoring for optimal performance.
"""

import sqlite3
import json
import time
import logging
import pickle
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import re

# Scientific computing imports
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not installed. Install with: pip install scikit-learn")

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with scoring information."""
    doc_id: str
    content: str
    title: str
    metadata: Dict[str, Any]
    tfidf_score: float
    llm_score: float
    hybrid_score: float
    rank: int


@dataclass
class SearchConfig:
    """Configuration for hybrid search."""
    tfidf_candidates: int = 5  # Number of TF-IDF candidates to pass to LLM
    final_results: int = 3     # Final number of results to return
    tfidf_weight: float = 0.3  # Weight for TF-IDF score in hybrid
    llm_weight: float = 0.7    # Weight for LLM score in hybrid
    ngram_range: Tuple[int, int] = (1, 2)  # N-gram range for TF-IDF
    max_features: int = 10000  # Maximum TF-IDF features
    min_df: int = 1           # Minimum document frequency
    max_df: float = 0.95      # Maximum document frequency
    cache_tfidf: bool = True  # Cache TF-IDF vectorizer
    cache_ttl: int = 3600     # Cache TTL in seconds


class DocumentStore:
    """SQLite-based document storage for hybrid search."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for document storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    query_hash TEXT PRIMARY KEY,
                    results TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON documents(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON documents(title)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON search_cache(expires_at)")
            
            conn.commit()
    
    def add_document(self, doc_id: str, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add or update a document in the store."""
        metadata = metadata or {}
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if document exists and content has changed
            cursor = conn.execute("""
                SELECT content_hash FROM documents WHERE doc_id = ?
            """, (doc_id,))
            
            existing = cursor.fetchone()
            if existing and existing[0] == content_hash:
                return False  # No update needed
            
            # Insert or update document
            conn.execute("""
                INSERT OR REPLACE INTO documents 
                (doc_id, title, content, metadata, content_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (doc_id, title, content, json.dumps(metadata), content_hash))
            
            conn.commit()
            return True
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from the store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT doc_id, title, content, metadata FROM documents
                ORDER BY updated_at DESC
            """)
            
            documents = []
            for row in cursor.fetchall():
                doc = {
                    "doc_id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3])
                }
                documents.append(doc)
            
            return documents
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT doc_id, title, content, metadata FROM documents
                WHERE doc_id = ?
            """, (doc_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "doc_id": row[0],
                "title": row[1],
                "content": row[2],
                "metadata": json.loads(row[3])
            }
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get document store statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT AVG(LENGTH(content)), MAX(LENGTH(content)), MIN(LENGTH(content))
                FROM documents
            """)
            content_stats = cursor.fetchone()
            
            return {
                "document_count": doc_count,
                "avg_content_length": content_stats[0] or 0,
                "max_content_length": content_stats[1] or 0,
                "min_content_length": content_stats[2] or 0
            }


class TFIDFProcessor:
    """TF-IDF processing for fast document filtering."""
    
    def __init__(self, config: SearchConfig):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for TF-IDF processing")
        
        self.config = config
        self.vectorizer = None
        self.tfidf_matrix = None
        self.documents = []
        self.cache_path = Path("tfidf_cache.pkl")
        self.last_build_time = 0
    
    def build_index(self, documents: List[Dict[str, Any]], force_rebuild: bool = False):
        """Build TF-IDF index from documents."""
        # Check if we can use cached version
        if (not force_rebuild and 
            self.config.cache_tfidf and 
            self.cache_path.exists() and 
            self._is_cache_valid()):
            self._load_cache()
            return
        
        logger.info(f"Building TF-IDF index for {len(documents)} documents...")
        start_time = time.time()
        
        # Store documents
        self.documents = documents
        
        # Prepare text corpus
        corpus = []
        for doc in documents:
            # Combine title and content for better matching
            text = f"{doc['title']} {doc['content']}"
            corpus.append(self._preprocess_text(text))
        
        # Build TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.config.ngram_range,
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            max_df=self.config.max_df,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )
        
        # Fit and transform corpus
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.last_build_time = time.time()
        
        # Cache if enabled
        if self.config.cache_tfidf:
            self._save_cache()
        
        build_time = time.time() - start_time
        logger.info(f"TF-IDF index built in {build_time:.2f} seconds")
        logger.info(f"Vocabulary size: {len(self.vectorizer.vocabulary_)}")
        logger.info(f"Matrix shape: {self.tfidf_matrix.shape}")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for TF-IDF."""
        # Basic text cleaning
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text)      # Normalize whitespace
        return text.strip()
    
    def search(self, query: str, top_k: int = None) -> List[Tuple[int, float]]:
        """Search using TF-IDF and return top candidates with scores."""
        if self.vectorizer is None or self.tfidf_matrix is None:
            raise ValueError("TF-IDF index not built. Call build_index() first.")
        
        top_k = top_k or self.config.tfidf_candidates
        
        # Transform query
        query_processed = self._preprocess_text(query)
        query_vector = self.vectorizer.transform([query_processed])
        
        # Compute similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Get top candidates
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Only include non-zero similarities
                results.append((int(idx), float(similarities[idx])))
        
        return results
    
    def _is_cache_valid(self) -> bool:
        """Check if cached TF-IDF is still valid."""
        if not self.cache_path.exists():
            return False
        
        cache_time = self.cache_path.stat().st_mtime
        current_time = time.time()
        
        return (current_time - cache_time) < self.config.cache_ttl
    
    def _save_cache(self):
        """Save TF-IDF components to cache."""
        try:
            cache_data = {
                'vectorizer': self.vectorizer,
                'tfidf_matrix': self.tfidf_matrix,
                'documents': self.documents,
                'last_build_time': self.last_build_time
            }
            
            with open(self.cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"TF-IDF cache saved to {self.cache_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save TF-IDF cache: {e}")
    
    def _load_cache(self):
        """Load TF-IDF components from cache."""
        try:
            with open(self.cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.vectorizer = cache_data['vectorizer']
            self.tfidf_matrix = cache_data['tfidf_matrix']
            self.documents = cache_data['documents']
            self.last_build_time = cache_data['last_build_time']
            
            logger.info(f"TF-IDF cache loaded from {self.cache_path}")
            
        except Exception as e:
            logger.warning(f"Failed to load TF-IDF cache: {e}")


class LLMScorer:
    """LLM-based semantic scoring for search results."""
    
    def __init__(self, llm_function: Callable[[str], str]):
        """
        Initialize LLM scorer.
        
        Args:
            llm_function: Function that takes a prompt and returns LLM response
        """
        self.llm_function = llm_function
    
    def score_relevance(self, query: str, documents: List[Dict[str, Any]]) -> List[float]:
        """Score document relevance using LLM."""
        if not documents:
            return []
        
        # Prepare prompt for batch scoring
        prompt = self._build_scoring_prompt(query, documents)
        
        try:
            # Get LLM response
            response = self.llm_function(prompt)
            
            # Parse scores from response
            scores = self._parse_scores(response, len(documents))
            
            return scores
            
        except Exception as e:
            logger.warning(f"LLM scoring failed: {e}")
            # Return neutral scores as fallback
            return [0.5] * len(documents)
    
    def _build_scoring_prompt(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """Build prompt for LLM-based relevance scoring."""
        prompt = f"""You are an expert document relevance scorer. Rate how relevant each document is to the given query on a scale of 0-10.

Query: "{query}"

For each document below, provide a relevance score (0-10) where:
- 0-2: Not relevant at all
- 3-4: Slightly relevant
- 5-6: Moderately relevant  
- 7-8: Highly relevant
- 9-10: Extremely relevant

Consider semantic meaning, context, and how well the document answers the query.

Documents to score:
"""
        
        for i, doc in enumerate(documents):
            prompt += f"\nDocument {i+1}:\nTitle: {doc['title']}\nContent: {doc['content'][:500]}...\n"
        
        prompt += f"""
Please respond with ONLY the scores in this exact format:
Document 1: [score]
Document 2: [score]
Document 3: [score]
...

Example response:
Document 1: 8.5
Document 2: 3.2
Document 3: 9.1
"""
        
        return prompt
    
    def _parse_scores(self, response: str, expected_count: int) -> List[float]:
        """Parse LLM response to extract relevance scores."""
        scores = []
        
        # Look for pattern "Document X: score"
        pattern = r'Document\s+\d+:\s*([\d.]+)'
        matches = re.findall(pattern, response, re.IGNORECASE)
        
        for match in matches:
            try:
                score = float(match)
                # Normalize to 0-1 range
                normalized_score = max(0.0, min(1.0, score / 10.0))
                scores.append(normalized_score)
            except ValueError:
                scores.append(0.5)  # Default neutral score
        
        # Ensure we have the right number of scores
        while len(scores) < expected_count:
            scores.append(0.5)
        
        return scores[:expected_count]


class HybridSemanticSearch:
    """
    Main hybrid search system combining TF-IDF and LLM scoring.
    
    Features:
    - Two-stage retrieval architecture
    - Fast TF-IDF filtering followed by LLM semantic scoring
    - Configurable parameters and weights
    - Document caching and storage
    - Performance optimization
    """
    
    def __init__(self, db_path: str, llm_function: Callable[[str], str], config: SearchConfig = None):
        """
        Initialize hybrid search system.
        
        Args:
            db_path: Path to SQLite database for document storage
            llm_function: Function for LLM-based scoring
            config: Search configuration
        """
        self.config = config or SearchConfig()
        self.document_store = DocumentStore(db_path)
        self.tfidf_processor = TFIDFProcessor(self.config) if SKLEARN_AVAILABLE else None
        self.llm_scorer = LLMScorer(llm_function)
        self.index_built = False
        
        logger.info("HybridSemanticSearch initialized")
    
    def add_document(self, doc_id: str, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a document to the search index."""
        added = self.document_store.add_document(doc_id, title, content, metadata)
        
        if added:
            # Mark index as needing rebuild
            self.index_built = False
            logger.info(f"Added document: {doc_id}")
        
        return added
    
    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        """Add multiple documents in batch."""
        added_count = 0
        
        for doc in documents:
            if self.add_document(
                doc_id=doc.get("doc_id"),
                title=doc.get("title", ""),
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {})
            ):
                added_count += 1
        
        logger.info(f"Added {added_count} documents in batch")
        return added_count
    
    def build_index(self, force_rebuild: bool = False):
        """Build search index from stored documents."""
        if not SKLEARN_AVAILABLE:
            logger.warning("TF-IDF indexing disabled (scikit-learn not available)")
            self.index_built = True
            return
        
        documents = self.document_store.get_all_documents()
        
        if not documents:
            logger.warning("No documents found to index")
            return
        
        self.tfidf_processor.build_index(documents, force_rebuild)
        self.index_built = True
        
        logger.info(f"Search index built for {len(documents)} documents")
    
    def search(self, 
               query: str, 
               tfidf_candidates: int = None, 
               final_results: int = None) -> List[SearchResult]:
        """
        Perform hybrid search combining TF-IDF and LLM scoring.
        
        Args:
            query: Search query
            tfidf_candidates: Number of TF-IDF candidates (overrides config)
            final_results: Number of final results (overrides config)
            
        Returns:
            List of SearchResult objects ranked by hybrid score
        """
        start_time = time.time()
        
        # Use provided parameters or fall back to config
        tfidf_k = tfidf_candidates or self.config.tfidf_candidates
        final_k = final_results or self.config.final_results
        
        # Ensure index is built
        if not self.index_built:
            self.build_index()
        
        # Stage 1: TF-IDF fast filtering
        if SKLEARN_AVAILABLE and self.tfidf_processor:
            logger.info(f"Stage 1: TF-IDF filtering (top {tfidf_k} candidates)")
            tfidf_results = self.tfidf_processor.search(query, tfidf_k)
            
            if not tfidf_results:
                logger.info("No TF-IDF matches found")
                return []
            
            # Get candidate documents
            candidate_docs = []
            tfidf_scores = []
            
            for doc_idx, tfidf_score in tfidf_results:
                doc = self.tfidf_processor.documents[doc_idx]
                candidate_docs.append(doc)
                tfidf_scores.append(tfidf_score)
        else:
            # Fallback: use all documents if TF-IDF not available
            logger.info("TF-IDF not available, using all documents")
            candidate_docs = self.document_store.get_all_documents()
            tfidf_scores = [0.5] * len(candidate_docs)
        
        # Stage 2: LLM semantic scoring
        logger.info(f"Stage 2: LLM semantic scoring ({len(candidate_docs)} candidates)")
        llm_scores = self.llm_scorer.score_relevance(query, candidate_docs)
        
        # Combine scores using hybrid weighting
        results = []
        for i, doc in enumerate(candidate_docs):
            tfidf_score = tfidf_scores[i] if i < len(tfidf_scores) else 0.0
            llm_score = llm_scores[i] if i < len(llm_scores) else 0.0
            
            # Calculate hybrid score
            hybrid_score = (
                self.config.tfidf_weight * tfidf_score + 
                self.config.llm_weight * llm_score
            )
            
            result = SearchResult(
                doc_id=doc["doc_id"],
                content=doc["content"],
                title=doc["title"],
                metadata=doc["metadata"],
                tfidf_score=tfidf_score,
                llm_score=llm_score,
                hybrid_score=hybrid_score,
                rank=0  # Will be set after sorting
            )
            results.append(result)
        
        # Sort by hybrid score and assign ranks
        results.sort(key=lambda x: x.hybrid_score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        
        # Return top final_k results
        final_results = results[:final_k]
        
        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time:.3f} seconds")
        logger.info(f"Returned {len(final_results)} results")
        
        return final_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search system statistics."""
        doc_stats = self.document_store.get_stats()
        
        stats = {
            "documents": doc_stats,
            "index_built": self.index_built,
            "config": asdict(self.config),
            "tfidf_available": SKLEARN_AVAILABLE
        }
        
        if SKLEARN_AVAILABLE and self.tfidf_processor and self.index_built:
            stats["tfidf"] = {
                "vocabulary_size": len(self.tfidf_processor.vectorizer.vocabulary_) if self.tfidf_processor.vectorizer else 0,
                "matrix_shape": self.tfidf_processor.tfidf_matrix.shape if self.tfidf_processor.tfidf_matrix is not None else None,
                "last_build_time": self.tfidf_processor.last_build_time
            }
        
        return stats


# Example LLM function for testing
def example_llm_function(prompt: str) -> str:
    """Example LLM function for testing (returns mock scores)."""
    import random
    
    # Count documents in prompt
    doc_count = prompt.count("Document ")
    
    # Generate mock scores
    response = ""
    for i in range(1, doc_count + 1):
        score = random.uniform(3.0, 9.0)
        response += f"Document {i}: {score:.1f}\n"
    
    return response


# Usage example and testing
if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("🔍 Hybrid Semantic Search Test")
        print("=" * 40)
        
        # Check dependencies
        if not SKLEARN_AVAILABLE:
            print("❌ scikit-learn not available. Install with: pip install scikit-learn")
            sys.exit(1)
        
        # Create search system
        search = HybridSemanticSearch("test_search.db", example_llm_function)
        
        # Add sample documents
        sample_docs = [
            {
                "doc_id": "doc1",
                "title": "Python Programming Guide",
                "content": "Python is a high-level programming language known for its simplicity and readability. It's widely used in web development, data science, and AI.",
                "metadata": {"category": "programming", "language": "python"}
            },
            {
                "doc_id": "doc2", 
                "title": "Machine Learning Basics",
                "content": "Machine learning is a subset of AI that enables computers to learn from data without explicit programming. Common algorithms include linear regression and neural networks.",
                "metadata": {"category": "ai", "difficulty": "beginner"}
            },
            {
                "doc_id": "doc3",
                "title": "Database Design Principles", 
                "content": "Database design involves organizing data efficiently. Key principles include normalization, indexing, and maintaining referential integrity.",
                "metadata": {"category": "database", "topic": "design"}
            }
        ]
        
        print(f"Adding {len(sample_docs)} sample documents...")
        added_count = search.add_documents_batch(sample_docs)
        print(f"Added {added_count} documents")
        
        # Build index
        print("Building search index...")
        search.build_index()
        
        # Test search
        test_queries = [
            "Python programming language",
            "machine learning algorithms", 
            "database normalization"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = search.search(query, tfidf_candidates=3, final_results=2)
            
            for result in results:
                print(f"  📄 {result.title}")
                print(f"     TF-IDF: {result.tfidf_score:.3f}, LLM: {result.llm_score:.3f}, Hybrid: {result.hybrid_score:.3f}")
                print(f"     Content: {result.content[:100]}...")
        
        # Get statistics
        stats = search.get_stats()
        print(f"\n📊 Search Statistics:")
        print(f"Documents: {stats['documents']['document_count']}")
        print(f"Index built: {stats['index_built']}")
        print(f"TF-IDF available: {stats['tfidf_available']}")
        
        if "tfidf" in stats:
            print(f"Vocabulary size: {stats['tfidf']['vocabulary_size']}")
        
        print("\n✅ Hybrid search test completed successfully")
        
    except Exception as e:
        print(f"❌ Hybrid search test failed: {e}")
        sys.exit(1)