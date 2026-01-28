"""Mock ChromaDB client for testing without real database operations.

Provides in-memory mock implementation of ChromaDB client and collection
for testing VectorStore and DatabaseService functionality.
"""

from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock
import numpy as np


class MockChromaCollection:
    """Mock ChromaDB collection for testing."""
    
    def __init__(self, name: str, metadata: Optional[Dict] = None):
        """Initialize mock collection.
        
        Args:
            name: Collection name
            metadata: Collection metadata
        """
        self.name = name
        self.metadata = metadata or {}
        self._documents: Dict[str, Dict[str, Any]] = {}
        
    def add(
        self,
        ids: List[str],
        embeddings: Optional[List[List[float]]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """Add documents to collection.

        Args:
            ids: Document IDs
            embeddings: Document embeddings (optional, will be auto-generated if None)
            documents: Document texts (optional)
            metadatas: Document metadata (optional)
        """
        # Auto-generate embeddings if not provided
        if embeddings is None and documents is not None:
            mock_encoder = MockSentenceTransformer()
            embeddings = mock_encoder.encode(documents).tolist()

        metadatas = metadatas or []
        documents = documents or [f"doc_{id}" for id in ids]
        embeddings = embeddings or [[0.0] * 384 for _ in ids]

        for i, doc_id in enumerate(ids):
            self._documents[doc_id] = {
                'id': doc_id,
                'embedding': embeddings[i],
                'document': documents[i],
                'metadata': metadatas[i] if i < len(metadatas) else {}
            }
    
    def query(
        self,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 5,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, List]:
        """Query for similar documents.
        
        Args:
            query_embeddings: Query embedding vectors (optional)
            query_texts: Query text strings (optional, will be auto-embedded)
            n_results: Number of results to return
            where: Optional metadata filter
            include: Fields to include in results
            
        Returns:
            Query results with ids, documents, metadatas, distances
        """
        # Handle query_texts by converting to embeddings
        if query_texts is not None and query_embeddings is None:
            mock_encoder = MockSentenceTransformer()
            query_embeddings = mock_encoder.encode(query_texts).tolist()
        
        # Ensure we have embeddings
        if query_embeddings is None:
            raise ValueError("Either query_embeddings or query_texts must be provided")
        
        include = include or ['documents', 'metadatas', 'distances']
        
        results = {
            'ids': [],
            'documents': [] if 'documents' in include else None,
            'metadatas': [] if 'metadatas' in include else None,
            'distances': [] if 'distances' in include else None,
            'embeddings': [] if 'embeddings' in include else None
        }
        
        for query_emb in query_embeddings:
            # Filter by metadata if provided
            filtered_docs = self._documents.items()
            if where:
                filtered_docs = [
                    (k, v) for k, v in filtered_docs
                    if all(v['metadata'].get(wk) == wv for wk, wv in where.items())
                ]
            
            # Calculate distances
            doc_distances = []
            for doc_id, doc_data in filtered_docs:
                doc_emb = doc_data['embedding']
                # Cosine distance
                distance = 1.0 - self._cosine_similarity(query_emb, doc_emb)
                doc_distances.append((doc_id, doc_data, distance))
            
            # Sort by distance and limit results
            doc_distances.sort(key=lambda x: x[2])
            doc_distances = doc_distances[:n_results]
            
            # Format results
            ids = [doc_id for doc_id, _, _ in doc_distances]
            docs = [doc_data['document'] for _, doc_data, _ in doc_distances] if 'documents' in include else None
            metas = [doc_data['metadata'] for _, doc_data, _ in doc_distances] if 'metadatas' in include else None
            dists = [dist for _, _, dist in doc_distances] if 'distances' in include else None
            embs = [doc_data['embedding'] for _, doc_data, _ in doc_distances] if 'embeddings' in include else None
            
            results['ids'].append(ids)
            if docs is not None:
                results['documents'].append(docs)
            if metas is not None:
                results['metadatas'].append(metas)
            if dists is not None:
                results['distances'].append(dists)
            if embs is not None:
                results['embeddings'].append(embs)
        
        return results
    
    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Dict[str, List]:
        """Get documents by ID or filter.

        Args:
            ids: Optional list of IDs to retrieve
            where: Optional metadata filter
            include: Fields to include in results
            limit: Optional limit on number of results
            offset: Optional offset for pagination

        Returns:
            Documents matching criteria
        """
        include = include or ['documents', 'metadatas', 'embeddings']

        # Get documents
        if ids:
            docs = [(doc_id, self._documents.get(doc_id)) for doc_id in ids if doc_id in self._documents]
        else:
            docs = list(self._documents.items())

        # Apply metadata filter
        if where:
            docs = [
                (k, v) for k, v in docs
                if v and all(v['metadata'].get(wk) == wv for wk, wv in where.items())
            ]

        # Apply offset and limit
        if offset > 0:
            docs = docs[offset:]
        if limit is not None:
            docs = docs[:limit]

        # Format results
        results = {
            'ids': [doc_id for doc_id, _ in docs],
            'documents': [doc_data['document'] for _, doc_data in docs if doc_data] if 'documents' in include else None,
            'metadatas': [doc_data['metadata'] for _, doc_data in docs if doc_data] if 'metadatas' in include else None,
            'embeddings': [doc_data['embedding'] for _, doc_data in docs if doc_data] if 'embeddings' in include else None
        }

        return results
    
    def delete(self, ids: List[str]):
        """Delete documents by ID.
        
        Args:
            ids: Document IDs to delete
        """
        for doc_id in ids:
            self._documents.pop(doc_id, None)
    
    def count(self) -> int:
        """Get document count.
        
        Returns:
            Number of documents in collection
        """
        return len(self._documents)
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (-1 to 1)
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


class MockChromaClient:
    """Mock ChromaDB client for testing."""
    
    def __init__(self, path: Optional[str] = None, settings: Any = None):
        """Initialize mock client.
        
        Args:
            path: Database path (ignored in mock)
            settings: ChromaDB settings (ignored in mock)
        """
        self.path = path
        self.settings = settings
        self._collections: Dict[str, MockChromaCollection] = {}
    
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict] = None
    ) -> MockChromaCollection:
        """Get or create a collection.
        
        Args:
            name: Collection name
            metadata: Collection metadata
            
        Returns:
            Mock collection
        """
        if name not in self._collections:
            self._collections[name] = MockChromaCollection(name, metadata)
        return self._collections[name]
    
    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict] = None
    ) -> MockChromaCollection:
        """Create a new collection.
        
        Args:
            name: Collection name
            metadata: Collection metadata
            
        Returns:
            Mock collection
            
        Raises:
            ValueError: If collection already exists
        """
        if name in self._collections:
            raise ValueError(f"Collection {name} already exists")
        
        self._collections[name] = MockChromaCollection(name, metadata)
        return self._collections[name]
    
    def get_collection(self, name: str) -> MockChromaCollection:
        """Get an existing collection.
        
        Args:
            name: Collection name
            
        Returns:
            Mock collection
            
        Raises:
            ValueError: If collection doesn't exist
        """
        if name not in self._collections:
            raise ValueError(f"Collection {name} does not exist")
        return self._collections[name]
    
    def delete_collection(self, name: str):
        """Delete a collection.
        
        Args:
            name: Collection name
        """
        self._collections.pop(name, None)
    
    def list_collections(self) -> List[MockChromaCollection]:
        """List all collections.
        
        Returns:
            List of mock collections
        """
        return list(self._collections.values())
    
    def reset(self):
        """Reset client by clearing all collections."""
        self._collections.clear()


def create_mock_client(**kwargs) -> MockChromaClient:
    """Factory function to create mock ChromaDB client.
    
    Args:
        **kwargs: Arguments for MockChromaClient
        
    Returns:
        Mock ChromaDB client
    """
    return MockChromaClient(**kwargs)


class MockSentenceTransformer:
    """Mock SentenceTransformer model for testing."""

    def __init__(self, model_name=None, device=None, **kwargs):
        """Initialize mock model.

        Args:
            model_name: Model name (ignored in mock)
            device: Device for computation (ignored in mock)
            **kwargs: Additional arguments (ignored in mock)
        """
        self.model_name = model_name
        self.device = device or 'cpu'
    
    def encode(self, texts, show_progress_bar=False, **kwargs):
        """Mock encode that returns consistent embeddings.
        
        Args:
            texts: Text or list of texts to encode
            show_progress_bar: Whether to show progress (ignored)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # Return consistent random embeddings based on text hash
        embeddings = []
        for text in texts:
            # Use hash to generate consistent embeddings
            np.random.seed(hash(text) % (2**32))
            emb = np.random.randn(384).astype(np.float32)
            # Normalize
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)
        
        return np.array(embeddings)


def create_mock_embedding_model(model_name=None):
    """Factory function to create mock SentenceTransformer model.
    
    Args:
        model_name: Model name (optional)
        
    Returns:
        Mock SentenceTransformer instance
    """
    return MockSentenceTransformer(model_name)
