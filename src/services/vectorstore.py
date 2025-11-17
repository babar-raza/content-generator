"""VectorStore implementation using ChromaDB for semantic search.

This module provides a wrapper around ChromaDB with embedding generation,
document storage, semantic search, and duplicate detection.
"""

import logging
import threading
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from src.core.config import Config

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for semantic search using ChromaDB and sentence-transformers.
    
    Provides document storage with embeddings, semantic search, duplicate detection,
    and collection management. Thread-safe for concurrent access.
    
    Attributes:
        config: Configuration object
        client: ChromaDB client
        embedding_model: SentenceTransformer model for generating embeddings
        collection: Active ChromaDB collection
    """
    
    def __init__(self, config: Config, collection_name: str = "default"):
        """Initialize VectorStore with ChromaDB and embedding model.
        
        Args:
            config: Configuration object with vectorstore settings
            collection_name: Name of the collection to use
            
        Raises:
            ImportError: If ChromaDB or sentence-transformers not available
        """
        self.config = config
        self._lock = threading.Lock()
        self._query_cache: Dict[str, Tuple[List[Dict[str, Any]], datetime]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Check dependencies
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available. VectorStore will operate in degraded mode.")
            self.client = None
            self.collection = None
        else:
            # Initialize ChromaDB client
            persist_dir = getattr(config, 'chroma_persist_directory', None)
            if persist_dir is None:
                # Use database.chroma_db_path if available
                if hasattr(config, 'database') and hasattr(config.database, 'chroma_db_path'):
                    persist_dir = config.database.chroma_db_path
                else:
                    persist_dir = './chroma_db'
            
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            
            try:
                self.client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                
                # Get or create collection
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                
                logger.info(f"ChromaDB initialized at {persist_dir}, collection: {collection_name}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize ChromaDB: {e}. Operating in degraded mode.")
                self.client = None
                self.collection = None
        
        # Initialize embedding model
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available. Embeddings will not be generated.")
            self.embedding_model = None
        else:
            try:
                # Get model name from config hierarchy
                model_name = 'sentence-transformers/all-MiniLM-L6-v2'  # Default
                if hasattr(config, 'database') and hasattr(config.database, 'embedding_model'):
                    model_name = config.database.embedding_model
                elif hasattr(config, 'embedding_model'):
                    model_name = config.embedding_model
                
                # Ensure model name has proper prefix
                if not model_name.startswith('sentence-transformers/'):
                    model_name = f'sentence-transformers/{model_name}'
                
                self.embedding_model = SentenceTransformer(model_name)
                logger.info(f"Embedding model loaded: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self.embedding_model = None
    
    def _generate_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for encoding (controls memory usage)
            
        Returns:
            List of embedding vectors
        """
        if not self.embedding_model:
            raise RuntimeError("Embedding model not available")
        
        if not texts:
            return []
        
        try:
            # Process in batches to control memory usage
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                embeddings = self.embedding_model.encode(
                    batch, 
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                all_embeddings.extend(embeddings.tolist())
                # Explicit cleanup of numpy array
                del embeddings
            
            return all_embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> None:
        """Add documents to the vector store with embeddings.
        
        Each document should have 'id' and 'content' keys. Optional 'metadata' key
        for additional document metadata.
        
        Args:
            documents: List of document dictionaries with 'id' and 'content'
            batch_size: Number of documents to process in each batch
            
        Raises:
            ValueError: If documents format is invalid
            RuntimeError: If ChromaDB not available
        """
        if not self.client or not self.collection:
            logger.warning("ChromaDB not available, cannot add documents")
            return
        
        if not documents:
            return
        
        # Validate documents
        for doc in documents:
            if 'id' not in doc or 'content' not in doc:
                raise ValueError("Each document must have 'id' and 'content' keys")
        
        with self._lock:
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Extract components
                ids = [doc['id'] for doc in batch]
                contents = [doc['content'] for doc in batch]
                metadatas = [doc.get('metadata', {}) for doc in batch]
                
                try:
                    # Generate embeddings
                    embeddings = self._generate_embeddings(contents)
                    
                    # Add to collection
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=contents,
                        metadatas=metadatas
                    )
                    
                    logger.debug(f"Added batch of {len(batch)} documents")
                    
                    # Explicit cleanup
                    del embeddings
                    del ids
                    del contents
                    del metadatas
                    
                except Exception as e:
                    logger.error(f"Failed to add document batch: {e}")
                    raise
        
        # Clear cache since collection changed
        self._query_cache.clear()
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using semantic search.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            filter: Optional metadata filter (e.g., {"source": "web"})
            use_cache: Whether to use query caching (default: True)
            
        Returns:
            List of result dictionaries with keys:
                - id: Document ID
                - content: Document content
                - metadata: Document metadata
                - score: Similarity score (lower is better for cosine distance)
        """
        if not self.client or not self.collection:
            logger.warning("ChromaDB not available, returning empty results")
            return []
        
        if not query:
            return []
        
        # Check cache if enabled
        if use_cache:
            cache_key = hashlib.md5(f"{query}:{k}:{filter}".encode()).hexdigest()
            
            if cache_key in self._query_cache:
                cached_results, cached_time = self._query_cache[cache_key]
                age = datetime.now() - cached_time
                
                if age < timedelta(seconds=self._cache_ttl):
                    logger.debug(f"Cache hit for query (age: {age.seconds}s)")
                    return cached_results
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search collection
            with self._lock:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    where=filter,
                    include=['documents', 'metadatas', 'distances']
                )
            
            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'score': results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            # Update cache if enabled
            if use_cache:
                self._query_cache[cache_key] = (formatted_results, datetime.now())
                
                # Cleanup old cache entries (keep only last 100)
                if len(self._query_cache) > 100:
                    # Remove oldest entries
                    sorted_cache = sorted(
                        self._query_cache.items(),
                        key=lambda x: x[1][1]
                    )
                    for old_key, _ in sorted_cache[:20]:
                        del self._query_cache[old_key]
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def find_duplicates(
        self,
        threshold: float = 0.95,
        batch_size: int = 100
    ) -> List[Tuple[str, str, float]]:
        """Find duplicate or near-duplicate documents based on similarity.
        
        Args:
            threshold: Similarity threshold (0-1, higher means more similar)
            batch_size: Number of documents to process at once
            
        Returns:
            List of tuples (doc_id_1, doc_id_2, similarity_score)
        """
        if not self.client or not self.collection:
            logger.warning("ChromaDB not available, cannot find duplicates")
            return []
        
        duplicates = []
        seen_pairs = set()  # Track pairs to avoid duplicates
        
        try:
            with self._lock:
                # Get total count first
                total_count = self.collection.count()
                
                if total_count == 0:
                    return []
                
                logger.debug(f"Finding duplicates in {total_count} documents")
                
                # Process in batches to avoid memory issues
                for offset in range(0, total_count, batch_size):
                    # Get batch of documents with embeddings
                    batch = self.collection.get(
                        limit=batch_size,
                        offset=offset,
                        include=['embeddings']
                    )
                    
                    if not batch['ids']:
                        continue
                    
                    batch_ids = batch['ids']
                    batch_embeddings = batch['embeddings']
                    
                    # Query for each document in batch
                    for i, (doc_id, embedding) in enumerate(zip(batch_ids, batch_embeddings)):
                        # Query with this document's embedding
                        results = self.collection.query(
                            query_embeddings=[embedding],
                            n_results=min(10, total_count),  # Limit similar results
                            include=['distances']
                        )
                        
                        if not results['ids'] or not results['ids'][0]:
                            continue
                        
                        # Check results against threshold
                        for j, result_id in enumerate(results['ids'][0]):
                            # Skip self-comparison
                            if result_id == doc_id:
                                continue
                            
                            # Convert distance to similarity (1 - distance for cosine)
                            distance = results['distances'][0][j]
                            similarity = 1.0 - distance
                            
                            # Check threshold
                            if similarity >= threshold:
                                # Create canonical pair (sorted) to avoid duplicates
                                pair = tuple(sorted([doc_id, result_id]))
                                
                                if pair not in seen_pairs:
                                    seen_pairs.add(pair)
                                    duplicates.append((doc_id, result_id, similarity))
                    
                    # Cleanup batch data
                    del batch
                    del batch_ids
                    del batch_embeddings
            
            logger.info(f"Found {len(duplicates)} duplicate pairs")
            return duplicates
            
        except Exception as e:
            logger.error(f"Duplicate detection failed: {e}")
            return []
    
    def collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the current collection.
        
        Returns:
            Dictionary with collection statistics:
                - count: Number of documents
                - name: Collection name
                - metadata: Collection metadata
        """
        if not self.client or not self.collection:
            return {
                'count': 0,
                'name': 'none',
                'metadata': {},
                'available': False
            }
        
        try:
            with self._lock:
                count = self.collection.count()
                metadata = self.collection.metadata
                name = self.collection.name
            
            return {
                'count': count,
                'name': name,
                'metadata': metadata,
                'available': True
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                'count': 0,
                'name': 'error',
                'metadata': {},
                'available': False
            }
    
    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents from the collection.
        
        Args:
            ids: List of document IDs to delete
        """
        if not self.client or not self.collection:
            logger.warning("ChromaDB not available, cannot delete documents")
            return
        
        if not ids:
            return
        
        try:
            with self._lock:
                self.collection.delete(ids=ids)
            
            # Clear cache since collection changed
            self._query_cache.clear()
            
            logger.debug(f"Deleted {len(ids)} documents")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise
    
    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        if not self.client or not self.collection:
            logger.warning("ChromaDB not available, cannot clear collection")
            return
        
        try:
            with self._lock:
                # Get all document IDs
                all_docs = self.collection.get()
                if all_docs['ids']:
                    self.collection.delete(ids=all_docs['ids'])
            
            # Clear query cache since collection changed
            self._query_cache.clear()
            
            logger.info("Collection cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise
    
    def clear_cache(self) -> None:
        """Clear the query cache.
        
        Useful when documents have been added/removed and cached results
        may be stale.
        """
        self._query_cache.clear()
        logger.debug("Query cache cleared")
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        if not self.client or not self.collection:
            return None
        
        try:
            with self._lock:
                result = self.collection.get(
                    ids=[doc_id],
                    include=['documents', 'metadatas', 'embeddings']
                )
            
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'content': result['documents'][0] if result['documents'] else '',
                    'metadata': result['metadatas'][0] if result['metadatas'] else {},
                    'embedding': result['embeddings'][0] if result['embeddings'] else []
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def list_collections(self) -> List[str]:
        """List all collections in the database.
        
        Returns:
            List of collection names
        """
        if not self.client:
            return []
        
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def create_collection(self, name: str) -> None:
        """Create a new collection.
        
        Args:
            name: Collection name
        """
        if not self.client:
            logger.warning("ChromaDB not available, cannot create collection")
            return
        
        try:
            self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created collection: {name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise
    
    def delete_collection(self, name: str) -> None:
        """Delete a collection.
        
        Args:
            name: Collection name
        """
        if not self.client:
            logger.warning("ChromaDB not available, cannot delete collection")
            return
        
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection: {name}")
            
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}")
            raise
    
    def switch_collection(self, name: str) -> None:
        """Switch to a different collection.
        
        Args:
            name: Collection name to switch to
        """
        if not self.client:
            logger.warning("ChromaDB not available, cannot switch collection")
            return
        
        try:
            with self._lock:
                self.collection = self.client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
            logger.info(f"Switched to collection: {name}")
            
        except Exception as e:
            logger.error(f"Failed to switch to collection {name}: {e}")
            raise
    
    def cleanup(self) -> None:
        """Cleanup resources and close connections.
        
        Call this when shutting down to properly release resources.
        """
        try:
            with self._lock:
                # Clear model reference to free memory
                if self.embedding_model is not None:
                    del self.embedding_model
                    self.embedding_model = None
                
                # ChromaDB client cleanup
                if self.client is not None:
                    # ChromaDB doesn't have explicit close, but we can clear references
                    self.collection = None
                    self.client = None
                
            logger.info("VectorStore cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        return False
