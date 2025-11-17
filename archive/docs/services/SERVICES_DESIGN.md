# Services Module - Complete Design Documentation

## Overview

The services module provides production-ready integrations with external APIs and services, featuring:
- Multi-provider LLM with rate limiting and model mapping
- Full CRUD operations for GitHub Gists
- Google Trends data including trending searches
- Sentence transformer embeddings with dimension support
- Vector database with embedding storage
- Link validation with parallel execution and GET fallback

---

## 1. LLMService - Multi-Provider LLM with Rate Limiting and Model Mapping

### Core Features
- **Provider Fallback Chain**: Ollama → Gemini → OpenAI
- **Rate Limiting**: Per-provider token bucket (OLLAMA: 300/min, GEMINI: 60/min, OPENAI: 60/min)
- **Model Mapping**: Generic names ("fast", "smart", "code") map to provider-specific models
- **Caching**: Hash-based response caching with TTL
- **Thread-Safe**: Lock-protected operations

### Interface
```python
class LLMService:
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,  # Generic or provider-specific
        temperature: Optional[float] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str
    
    def check_health(self) -> Dict[str, bool]
```

---

## 2. GistService - Full CRUD for GitHub Gists

### Core Features
- **Create**: Upload new gists with content and description
- **Read**: Retrieve existing gists by ID
- **Update**: Modify gist content and description
- **Delete**: Remove gists
- **Error Handling**: 404 detection, timeout handling, token validation

### Interface
```python
class GistService:
    def create_gist(
        self,
        filename: str,
        content: str,
        description: str = "",
        public: bool = False
    ) -> Optional[str]  # Returns URL
    
    def get_gist(self, gist_id: str) -> Optional[Dict[str, Any]]
    
    def update_gist(
        self,
        gist_id: str,
        filename: str,
        content: str,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]
    
    def delete_gist(self, gist_id: str) -> bool
```

### Usage Example
```python
service = GistService(config)

# Create
url = service.create_gist("script.py", "print('hello')", "Example script")
gist_id = url.split('/')[-1]

# Read
gist = service.get_gist(gist_id)

# Update
updated = service.update_gist(gist_id, "script.py", "print('updated')", "New description")

# Delete
deleted = service.delete_gist(gist_id)
```

---

## 3. TrendsService - Google Trends with Trending Searches

### Core Features
- **Interest Over Time**: Historical trend data for keywords
- **Related Queries**: Top and rising related searches
- **Trending Searches**: Current trending searches by region

### Interface
```python
class TrendsService:
    def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = 'today 12-m'
    ) -> Optional[Any]  # Returns DataFrame
    
    def get_related_queries(self, keyword: str) -> Optional[Dict[str, Any]]
    
    def get_trending_searches(
        self,
        geo: str = 'united_states'
    ) -> Optional[Any]  # Returns DataFrame
```

### Supported Regions
- `united_states`, `united_kingdom`, `canada`, `australia`, `india`, etc.
- Region codes follow Google Trends naming conventions

### Usage Example
```python
service = TrendsService(config)

# Get trending searches
trends = service.get_trending_searches('united_states')
print(trends.head())  # Top trending searches

# Get interest over time
interest = service.get_interest_over_time(['python', 'javascript'])

# Get related queries
related = service.get_related_queries('machine learning')
```

---

## 4. EmbeddingService - Sentence Transformers with Dimension Support

### Core Features
- **Single Text Encoding**: Returns `List[float]` (single embedding)
- **Batch Encoding**: Returns `List[List[float]]` (multiple embeddings)
- **Dimension Query**: Get embedding vector dimension
- **Empty Input Handling**: Returns `[]` for empty strings/lists

### Interface
```python
class EmbeddingService:
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False
    ) -> Union[List[float], List[List[float]]]
    
    def get_dimension(self) -> int
```

### Usage Example
```python
service = EmbeddingService(config)

# Single text -> single embedding
embedding = service.encode("Hello world")  # Returns [0.1, 0.2, ..., 0.384]
assert len(embedding) == service.get_dimension()

# Multiple texts -> list of embeddings
embeddings = service.encode(["text1", "text2"])  # Returns [[...], [...]]
assert len(embeddings) == 2
assert len(embeddings[0]) == service.get_dimension()
```

---

## 5. DatabaseService - ChromaDB with Embedding Storage

### Core Features
- **Embedding Support**: Accepts pre-computed embeddings
- **Auto-Embedding**: ChromaDB generates embeddings if not provided
- **Metadata Filtering**: Query by metadata fields
- **Collection Management**: Create, query, delete collections

### Interface
```python
class DatabaseService:
    def add_documents(
        self,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,  # Pre-computed
        collection_name: Optional[str] = None
    )
    
    def query(
        self,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]
```

### Usage Example with Embeddings
```python
# Generate embeddings separately
embedding_service = EmbeddingService(config)
texts = ["Document 1", "Document 2"]
embeddings = embedding_service.encode(texts)

# Store with pre-computed embeddings
db_service = DatabaseService(config)
db_service.add_documents(
    documents=texts,
    ids=["doc1", "doc2"],
    embeddings=embeddings,  # Provided embeddings
    metadatas=[{"source": "api"}, {"source": "web"}]
)

# Query uses stored embeddings
results = db_service.query(["search query"], n_results=5)
```

---

## 6. LinkChecker - Parallel Execution with GET Fallback

### Core Features
- **Parallel Execution**: ThreadPoolExecutor for batch checking
- **HEAD First**: Fast check with HEAD request
- **GET Fallback**: Automatically falls back to GET if HEAD fails or returns 405
- **Configurable Workers**: Control parallelism level
- **Sequential Mode**: Optional non-parallel checking

### Interface
```python
class LinkChecker:
    def check_url(
        self,
        url: str,
        method: str = 'HEAD'
    ) -> Tuple[bool, int, str]  # (is_valid, status_code, message)
    
    def check_urls(
        self,
        urls: List[str],
        parallel: bool = True,
        max_workers: Optional[int] = None
    ) -> Dict[str, Tuple[bool, int, str]]
```

### Behavior Details

#### HEAD to GET Fallback
1. Try HEAD request first (fast, no body download)
2. If HEAD returns 405 (Method Not Allowed), retry with GET
3. If HEAD raises exception, retry with GET
4. Return final result

#### Parallel Execution
- Uses `ThreadPoolExecutor` with configurable workers
- Default workers: 10 (configurable via `config.link_check_workers`)
- Processes URLs concurrently for speed
- Collects results as futures complete

### Usage Example
```python
service = LinkChecker(config)

# Single URL with automatic fallback
is_valid, status, msg = service.check_url("https://example.com")

# Batch parallel checking (default)
urls = ["https://site1.com", "https://site2.com", "https://site3.com"]
results = service.check_urls(urls, parallel=True, max_workers=5)

for url, (is_valid, status, msg) in results.items():
    print(f"{url}: {status} - {'✓' if is_valid else '✗'}")

# Sequential checking (for rate limiting)
results = service.check_urls(urls, parallel=False)
```

### Configuration
```python
config.link_check_timeout = 10  # Seconds per request
config.link_check_workers = 10  # Max parallel workers
```

---

## Cross-Service Integration

### Complete Workflow Example
```python
from src.core.config import Config
from src.services.services import (
    LLMService, EmbeddingService, DatabaseService,
    GistService, TrendsService, LinkChecker
)

config = Config()

# 1. Generate content with LLM
llm = LLMService(config)
content = llm.generate("Write about Python async", model="fast")

# 2. Create embeddings
embedder = EmbeddingService(config)
embedding = embedder.encode(content)
assert len(embedding) == embedder.get_dimension()

# 3. Store in vector database with embeddings
db = DatabaseService(config)
db.add_documents(
    documents=[content],
    ids=["article_1"],
    embeddings=[embedding],  # Pre-computed
    metadatas=[{"topic": "python"}]
)

# 4. Validate links in content
checker = LinkChecker(config)
links = extract_links(content)  # Your function
results = checker.check_urls(links, parallel=True)
valid_links = [url for url, (valid, _, _) in results.items() if valid]

# 5. Create GitHub Gist
gist = GistService(config)
gist_url = gist.create_gist("article.md", content, "Python Async Article")

# 6. Get trending topics
trends = TrendsService(config)
trending = trends.get_trending_searches('united_states')
related = trends.get_related_queries("python async")
```

---

## Configuration

### Required Config Attributes
```python
@dataclass
class Config:
    # LLM
    ollama_base_url: str = "http://localhost:11434"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_topic_model: str = "llama2"
    gemini_model: str = "models/gemini-1.5-flash"
    gemini_rpm_limit: int = 60
    openai_rpm_limit: int = 60
    ollama_rpm_limit: int = 300
    llm_temperature: float = 0.7
    
    # GitHub Gists
    github_gist_token: Optional[str] = None
    gist_upload_enabled: bool = False
    
    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    device: str = "cpu"
    
    # Database
    database.chroma_db_path: str = "./chroma_db"
    
    # Link Checker
    link_check_timeout: int = 10
    link_check_workers: int = 10
    
    # Caching
    cache_dir: str = "./cache"
    cache_ttl: int = 3600
```

---

## Error Handling

### Consistent Error Strategy
All services follow consistent patterns:

1. **Validation Errors**: Return `None` or `False` for invalid inputs (no exceptions)
2. **API Errors**: Log error, return `None`/`False`, propagate only for LLMService
3. **Timeouts**: Return `None`/`False` with timeout message
4. **404 Errors**: Detected and logged specifically for Gist operations
5. **Rate Limits**: Automatic throttling with fallback (LLMService)

### Example Error Handling
```python
# Gist operations return None on error
gist = service.get_gist("invalid_id")
if gist is None:
    print("Failed to retrieve gist")

# Link checker returns tuple with error info
is_valid, status, msg = checker.check_url("https://invalid")
if not is_valid:
    print(f"Check failed: {msg} (status: {status})")

# LLM raises RuntimeError only when all providers fail
try:
    result = llm.generate("prompt")
except RuntimeError as e:
    print(f"All providers failed: {e}")
```

---

## Performance Characteristics

### LLMService
- **Cache Hit**: ~0.1ms (hash lookup)
- **Rate Limit Check**: ~0.1ms (under lock)
- **Provider Call**: 100ms - 10s (network dependent)

### GistService
- **Create/Update/Delete**: 200ms - 2s (GitHub API)
- **Get**: 100ms - 1s (GitHub API)

### TrendsService
- **All Methods**: 1s - 5s (Google Trends API)
- **Rate Limiting**: Built into pytrends library

### EmbeddingService
- **Single Text**: 10-50ms (model dependent)
- **Batch (32)**: 100-500ms (model dependent)
- **get_dimension**: <1ms

### DatabaseService
- **Add**: 10-100ms per document
- **Query**: 10-100ms (vector similarity)
- **Collection Operations**: <10ms

### LinkChecker
- **Single HEAD**: 100ms - 2s (network + server)
- **Single GET**: 200ms - 5s (includes body download)
- **Parallel (10 URLs)**: Similar to single URL time (parallelized)
- **Sequential**: Linear scaling with URL count

---

## Testing Strategy

All services have comprehensive test coverage:

### Unit Tests
- Input validation (empty strings, None values)
- Success cases with mocked external calls
- Error cases (404, timeouts, exceptions)
- Edge cases (empty lists, special characters)

### Integration Tests
- Multi-service workflows
- Embedding → Database integration
- Parallel link checking with mixed results
- Complete CRUD workflows

### Test Guidelines
- Zero network calls (all mocked)
- Deterministic results (seeded randoms)
- Windows-compatible paths
- Fast execution (<1s per test)

---

## Dependencies

### Required Packages
- `requests` - HTTP client for APIs
- `sentence-transformers` - Text embeddings (optional)
- `chromadb` - Vector database (optional)
- `pytrends` - Google Trends API (optional)

### Standard Library
- `threading` - Lock protection, ThreadPoolExecutor
- `collections.deque` - Rate limiting token bucket
- `concurrent.futures` - Parallel execution
- `hashlib` - Cache key generation
- `json` - Data serialization
- `time` - Rate limiting, backoff

---

## Best Practices

### When to Use Each Service

**LLMService**: Content generation, summarization, classification
**GistService**: Code snippet sharing, configuration backup, log storage
**TrendsService**: Market research, content planning, keyword discovery
**EmbeddingService**: Semantic search, document clustering, similarity
**DatabaseService**: Long-term storage, retrieval of embeddings
**LinkChecker**: Content validation, broken link detection, health checks

### Performance Tips

1. **Batch Operations**: Use `check_urls(parallel=True)` for multiple URLs
2. **Pre-Compute Embeddings**: Generate once, store in database
3. **Cache Aggressively**: LLM responses have high cache hit rates
4. **Parallel Where Possible**: LinkChecker with `max_workers` tuned to load
5. **Rate Limit Awareness**: Monitor provider limits, adjust config values

### Error Recovery

```python
# Gist with retry logic
def create_gist_with_retry(service, filename, content, max_attempts=3):
    for attempt in range(max_attempts):
        result = service.create_gist(filename, content)
        if result:
            return result
        time.sleep(2 ** attempt)  # Exponential backoff
    return None

# Link checking with timeout handling
def check_with_timeout(checker, urls, timeout=30):
    import signal
    
    def handler(signum, frame):
        raise TimeoutError("Check timeout")
    
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    
    try:
        return checker.check_urls(urls, parallel=True)
    finally:
        signal.alarm(0)
```

---

## Migration Guide

### From Previous Version

If updating from an earlier version, note these changes:

1. **GistService**: Now has full CRUD (get, update, delete added)
2. **TrendsService**: Added `get_trending_searches()` method
3. **EmbeddingService**: `encode()` now handles single text (returns List[float])
4. **DatabaseService**: `add_documents()` now accepts `embeddings` parameter
5. **LinkChecker**: `check_urls()` now parallel by default with GET fallback

### Code Updates Needed

```python
# OLD: GistService only had create
url = gist_service.create_gist("file.py", "content")
# NEW: Can now read, update, delete
gist = gist_service.get_gist(gist_id)
updated = gist_service.update_gist(gist_id, "file.py", "new content")
deleted = gist_service.delete_gist(gist_id)

# OLD: EmbeddingService always returned List[List[float]]
embeddings = embedder.encode("text")  # [[...]]
embedding = embeddings[0]
# NEW: Returns List[float] for single text
embedding = embedder.encode("text")  # [...]

# OLD: LinkChecker was sequential
results = checker.check_urls(urls)
# NEW: Parallel by default
results = checker.check_urls(urls)  # Automatic parallelism
results = checker.check_urls(urls, parallel=False)  # Opt-in sequential
```
