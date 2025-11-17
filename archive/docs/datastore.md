# Datastore

## Overview

UCOP uses ChromaDB for vector storage and semantic search capabilities.

## Vector Store

### Configuration

```yaml
vectorstore:
  provider: "chromadb"
  path: "./chroma_db"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
```

### Embedding Generation

```python
from src.services.vectorstore import VectorStore

store = VectorStore()

# Embed and store content
store.add_documents([
    {"id": "doc1", "content": "Article content...", "metadata": {...}},
    {"id": "doc2", "content": "Another article...", "metadata": {...}}
])
```

### Semantic Search

```python
# Search for similar content
results = store.search(
    query="Python tutorials",
    k=10,  # Top 10 results
    filter={"category": "programming"}
)
```

## Content Intelligence

### Semantic Linking

Automatically identify related content:

```python
from src.agents.research.content_intelligence import ContentIntelligenceAgent

agent = ContentIntelligenceAgent()
related = agent.find_related_content(
    content="Article about Python decorators",
    limit=5
)
```

### Duplicate Detection

Detect near-duplicate content:

```python
duplicates = store.find_duplicates(
    threshold=0.95  # 95% similarity
)
```

## Performance

### Indexing

- Batch indexing for large datasets
- Incremental updates for new content
- Automatic reindexing on schema changes

### Query Optimization

- Cached embeddings
- Approximate nearest neighbor (ANN) search
- Filter pushdown for metadata queries

## Maintenance

```bash
# Rebuild index
python tools/maintain.py vectorstore rebuild

# Optimize storage
python tools/maintain.py vectorstore optimize

# Backup data
python tools/maintain.py vectorstore backup --output backup.tar.gz
```
