# Content Intelligence

## Vector Store (ChromaDB)
- Semantic search
- Content similarity
- Duplicate detection

## Embeddings
- Model: sentence-transformers/all-MiniLM-L6-v2
- Dimension: 384
- GPU acceleration supported

## Usage
```python
from src.services.vectorstore import VectorStore
from src.services.embeddings import EmbeddingService

# Create embeddings
embedder = EmbeddingService(config)
embedding = embedder.encode("content")

# Store in ChromaDB
vectorstore = VectorStore(config)
vectorstore.add_documents(...)
```

## Configuration
See [configuration.md](configuration.md) for vector store settings.
