# Services Module

## Overview

Support services for vector storage, database management, and external integrations.

## Components

### `vectorstore.py`
Vector database integration for semantic search and content intelligence.

```python
class VectorStore:
    """ChromaDB vector store"""
    def add_documents(self, docs: List[Document])
    def search(self, query: str, k: int = 10) -> List[Document]
    def find_duplicates(self, threshold: float) -> List[Tuple]
```

### `datastore.py`
General data storage and retrieval.

```python
class DataStore:
    """Data persistence layer"""
    def save(self, key: str, value: Any)
    def load(self, key: str) -> Any
    def query(self, filter: Dict) -> List[Any]
```

### `google_trends.py`
Google Trends API integration for keyword research.

```python
class GoogleTrendsService:
    """Google Trends research"""
    def get_trends(self, keywords: List[str]) -> TrendsData
    def compare_keywords(self, keywords: List[str]) -> Comparison
```

### `github_service.py`
GitHub integration for Gist uploads.

```python
class GitHubService:
    """GitHub Gist management"""
    def create_gist(self, code: str, description: str) -> str
    def update_gist(self, gist_id: str, code: str)
```

### `database_service.py`
Database operations and migrations.

```python
class DatabaseService:
    """Database management"""
    def connect(self)
    def execute(self, query: str) -> Result
    def migrate(self)
```

## Usage

### Vector Store

```python
from src.services.vectorstore import VectorStore

store = VectorStore()

# Add documents
store.add_documents([
    {'id': 'doc1', 'content': 'Article...', 'metadata': {...}}
])

# Semantic search
results = store.search('Python tutorials', k=5)
```

### Google Trends

```python
from src.services.google_trends import GoogleTrendsService

trends = GoogleTrendsService()
data = trends.get_trends(['python', 'machine learning'])
```

### GitHub Gists

```python
from src.services.github_service import GitHubService

github = GitHubService(token='...')
gist_url = github.create_gist(
    code='print("Hello")',
    description='Example code'
)
```

## Configuration

Services are configured in `config/main.yaml`:

```yaml
services:
  vectorstore:
    provider: chromadb
    path: ./chroma_db
    
  github:
    token: ${GITHUB_TOKEN}
    
  google_trends:
    timeout: 30
```

## Dependencies

- `chromadb` - Vector database
- `sentence-transformers` - Embeddings
- `pytrends` - Google Trends
- `requests` - HTTP client
