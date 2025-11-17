# Services Module - Minimal Design

## 1. LLMService - Multi-Provider LLM with Fallback Chain

### Core Interface
```python
class LLMService:
    def __init__(self, config: Config) -> None:
        """Initialize with provider priority and rate limiting."""
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        json_schema: Optional[Dict] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: int = 60,
        task_context: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> str:
        """Generate text with automatic fallback chain: Ollama → Gemini → OpenAI.
        
        - Tries providers in priority order
        - 3 retries per provider with exponential backoff
        - 30 second timeout per provider
        - Response caching with TTL
        - Structured logging for each attempt
        """
        
    def check_health(self) -> Dict[str, bool]:
        """Check health status of all configured providers.
        
        Returns:
            {'OLLAMA': bool, 'GEMINI': bool, 'OPENAI': bool}
        """
```

### Implementation Details
- **Provider Selection**: Config.llm_provider sets primary, fallback to others
- **Caching**: Hash-based cache with configurable TTL
- **Rate Limiting**: Gemini-specific rate limiter (requests per minute)
- **Model Mapping**: Automatic model translation across providers
- **Smart Routing**: Optional Ollama model router for task-specific models

### Dependencies
- `requests` - HTTP calls to Ollama
- `google.generativeai` - Gemini API
- `openai` - OpenAI API

---

## 2. DatabaseService - ChromaDB Vector Store Wrapper

### Core Interface
```python
class DatabaseService:
    def __init__(self, config: Config) -> None:
        """Initialize ChromaDB client with persistence."""
        
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict] = None
    ) -> Collection:
        """Get existing or create new ChromaDB collection."""
        
    def add_documents(
        self,
        collection: Collection,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict]] = None,
        embeddings: Optional[List[List[float]]] = None
    ) -> None:
        """Add documents to collection with optional embeddings."""
        
    def query(
        self,
        collection: Collection,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """Query collection for similar documents."""
```

### Implementation Details
- **Persistence**: PersistentClient with configurable directory
- **Collections**: Namespace-based organization
- **Embeddings**: Automatic embedding via EmbeddingService if not provided
- **Metadata**: Rich filtering via ChromaDB's where clause

### Dependencies
- `chromadb` - Vector database

---

## 3. EmbeddingService - Sentence Transformers Integration

### Core Interface
```python
class EmbeddingService:
    def __init__(self, config: Config) -> None:
        """Initialize sentence-transformers model."""
        
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False
    ) -> Union[List[float], List[List[float]]]:
        """Convert text(s) to embedding vector(s).
        
        Returns:
            Single embedding for str input, list of embeddings for list input
        """
        
    def get_dimension(self) -> int:
        """Get embedding vector dimension."""
```

### Implementation Details
- **Model**: Default 'all-MiniLM-L6-v2' (384 dimensions)
- **Batch Processing**: Efficient batch encoding
- **Device Support**: Auto-detect GPU/CPU
- **Normalization**: Optional L2 normalization

### Dependencies
- `sentence-transformers` - Embedding models

---

## 4. GistService - GitHub Gist API Integration

### Core Interface
```python
class GistService:
    def __init__(self, config: Config) -> None:
        """Initialize with GitHub token."""
        
    def create_gist(
        self,
        filename: str,
        content: str,
        description: str = "",
        public: bool = True
    ) -> Dict:
        """Create a new GitHub Gist.
        
        Returns:
            {'id': str, 'url': str, 'html_url': str, 'files': dict}
        """
        
    def get_gist(self, gist_id: str) -> Dict:
        """Fetch existing Gist by ID."""
        
    def update_gist(
        self,
        gist_id: str,
        filename: str,
        content: str
    ) -> Dict:
        """Update existing Gist."""
        
    def delete_gist(self, gist_id: str) -> bool:
        """Delete Gist."""
```

### Implementation Details
- **Authentication**: Bearer token from config
- **File Management**: Single or multiple files per Gist
- **Public/Private**: Configurable visibility
- **Error Handling**: Retry on 5xx errors

### Dependencies
- `requests` - GitHub API calls

---

## 5. TrendsService - Google Trends via pytrends

### Core Interface
```python
class TrendsService:
    def __init__(self, config: Config) -> None:
        """Initialize pytrends client."""
        
    def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = 'today 12-m',
        geo: str = ''
    ) -> pd.DataFrame:
        """Get interest over time for keywords.
        
        Returns DataFrame with date index and keyword columns.
        """
        
    def get_related_queries(
        self,
        keyword: str
    ) -> Dict[str, pd.DataFrame]:
        """Get related search queries (top and rising)."""
        
    def get_trending_searches(
        self,
        geo: str = 'united_states'
    ) -> pd.DataFrame:
        """Get current trending searches."""
```

### Implementation Details
- **Rate Limiting**: Built-in delays between requests
- **Timeframes**: Support for various periods (1h, 1d, 7d, 12m, 5y)
- **Geolocation**: Country/region filtering
- **Categories**: Optional category filtering

### Dependencies
- `pytrends` - Google Trends API wrapper

---

## 6. LinkChecker - HTTP Link Validation

### Core Interface
```python
class LinkChecker:
    def __init__(self, config: Config) -> None:
        """Initialize with timeout and retry settings."""
        
    def check_link(
        self,
        url: str,
        method: str = 'HEAD',
        timeout: int = 10,
        max_retries: int = 3
    ) -> bool:
        """Check if URL is accessible.
        
        Returns:
            True if status code is 2xx or 3xx, False otherwise
        """
        
    def check_links(
        self,
        urls: List[str],
        parallel: bool = True,
        max_workers: int = 10
    ) -> Dict[str, bool]:
        """Batch check multiple URLs.
        
        Returns:
            {url: is_valid} for each URL
        """
        
    def get_status_code(self, url: str) -> Optional[int]:
        """Get HTTP status code for URL."""
```

### Implementation Details
- **Methods**: HEAD (fast) or GET (fallback)
- **Retries**: Exponential backoff on timeouts/5xx
- **Parallel**: ThreadPoolExecutor for batch checking
- **User-Agent**: Custom UA to avoid bot blocking
- **Redirects**: Follow redirects, validate final destination

### Dependencies
- `requests` - HTTP client

---

## Cross-Service Integration

### Typical Workflow
```python
# 1. Generate content with LLM
llm = LLMService(config)
content = llm.generate("Write about Python async")

# 2. Create embeddings
embedder = EmbeddingService(config)
embedding = embedder.encode(content)

# 3. Store in vector DB
db = DatabaseService(config)
collection = db.get_or_create_collection("articles")
db.add_documents(
    collection,
    documents=[content],
    ids=["article_1"],
    embeddings=[embedding]
)

# 4. Validate links in content
checker = LinkChecker(config)
links = extract_links(content)  # Your extraction logic
link_status = checker.check_links(links)

# 5. Create GitHub Gist for code samples
gist = GistService(config)
code_sample = extract_code(content)  # Your extraction logic
gist_result = gist.create_gist("example.py", code_sample)

# 6. Research trending topics
trends = TrendsService(config)
related = trends.get_related_queries("Python async")
```

### Configuration Dependencies

All services require a `Config` object with these attributes:

```python
@dataclass
class Config:
    # LLM
    llm_provider: str = "OLLAMA"
    ollama_base_url: str = "http://localhost:11434"
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    gemini_rpm_limit: int = 60
    
    # Database
    chroma_persist_directory: str = "./chroma_db"
    
    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # GitHub
    github_token: Optional[str] = None
    
    # Caching
    cache_dir: str = "./cache"
    cache_ttl: int = 3600
    
    # General
    deterministic: bool = False
    global_seed: int = 42
```

### Error Handling Strategy

All services use consistent error handling:

1. **Validation Errors**: Raise `ValueError` for invalid inputs
2. **Connection Errors**: Log warning, raise `ConnectionError`
3. **Auth Errors**: Raise `ValueError` for missing/invalid credentials
4. **Rate Limits**: Auto-retry with backoff
5. **Timeouts**: Configurable per-service timeouts

### Logging Convention

All services use structured logging:

```python
import logging
logger = logging.getLogger(__name__)

# Info: Successful operations
logger.info("✓ Generated response from Ollama", extra={'provider': 'OLLAMA', 'tokens': 150})

# Warning: Recoverable failures
logger.warning("Ollama failed, trying Gemini", extra={'error': str(e)})

# Error: Unrecoverable failures
logger.error("All providers failed", extra={'providers_tried': ['OLLAMA', 'GEMINI', 'OPENAI']})
```
