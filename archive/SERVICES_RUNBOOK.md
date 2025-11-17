# Services Module Runbook

## Quick Verification

### Test Imports
```bash
python -c "from src.services import LLMService, DatabaseService, EmbeddingService, GistService, LinkChecker, TrendsService; print('✓ All imports successful')"
```

### Run Import Test Script
```bash
python test_import.py
```

Expected output:
```
✓ All services imported successfully
  - LLMService: <class 'src.services.services.LLMService'>
  - DatabaseService: <class 'src.services.services.DatabaseService'>
  - EmbeddingService: <class 'src.services.services.EmbeddingService'>
  - GistService: <class 'src.services.services.GistService'>
  - LinkChecker: <class 'src.services.services.LinkChecker'>
  - TrendsService: <class 'src.services.services.TrendsService'>
```

## Running Tests

### Run All Service Tests
```bash
pytest tests/test_services_comprehensive.py -v
```

### Run Specific Test Classes
```bash
# Test only LLMService
pytest tests/test_services_comprehensive.py::TestLLMService -v

# Test only fallback chain
pytest tests/test_services_comprehensive.py::TestLLMService::test_generate_fallback_to_gemini -v

# Test health checks
pytest tests/test_services_comprehensive.py::TestLLMService::test_check_health -v
```

### Run with Coverage
```bash
pytest tests/test_services_comprehensive.py --cov=src.services --cov-report=html -v
```

## Service Usage Examples

### 1. LLMService - Multi-Provider with Fallback

```python
from src.core.config import Config
from src.services import LLMService

# Initialize with config
config = Config()
llm = LLMService(config)

# Basic generation (will try Ollama → Gemini → OpenAI)
response = llm.generate("Write a function to reverse a string")

# Force specific provider
response = llm.generate("Explain Python", provider="GEMINI")

# Check provider health
health = llm.check_health()
print(health)  # {'OLLAMA': True, 'GEMINI': True, 'OPENAI': False}

# JSON mode with schema
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"}
    }
}
response = llm.generate("Summarize this article", json_mode=True, json_schema=schema)
```

### 2. DatabaseService - ChromaDB Wrapper

```python
from src.services import DatabaseService

db = DatabaseService(config)

# Get or create collection
collection = db.get_or_create_collection("my_docs")

# Add documents
collection.add(
    documents=["Document 1 text", "Document 2 text"],
    ids=["doc1", "doc2"],
    metadatas=[{"source": "web"}, {"source": "pdf"}]
)

# Query
results = collection.query(
    query_texts=["search query"],
    n_results=5
)
```

### 3. EmbeddingService - Sentence Transformers

```python
from src.services import EmbeddingService

embedder = EmbeddingService(config)

# Single text
embedding = embedder.encode("This is a test sentence")
print(f"Embedding dimension: {len(embedding)}")

# Batch encoding
texts = ["Text 1", "Text 2", "Text 3"]
embeddings = embedder.encode(texts)
```

### 4. GistService - GitHub Gist API

```python
from src.services import GistService

gist = GistService(config)

# Create a new gist
result = gist.create_gist(
    filename="example.py",
    content="def hello():\n    print('Hello, World!')",
    description="Example Python function"
)
print(f"Gist URL: {result['html_url']}")

# Get existing gist
gist_data = gist.get_gist("abc123def456")
print(gist_data["files"])
```

### 5. TrendsService - Google Trends

```python
from src.services import TrendsService

trends = TrendsService(config)

# Get interest over time
keywords = ["python programming", "javascript"]
data = trends.get_interest_over_time(keywords)

# Get related queries
related = trends.get_related_queries("machine learning")
```

### 6. LinkChecker - HTTP Validation

```python
from src.services import LinkChecker

checker = LinkChecker(config)

# Check single link
is_valid = checker.check_link("https://example.com")
print(f"Link valid: {is_valid}")

# Batch check with retries
links = [
    "https://example.com",
    "https://example.com/page1",
    "https://example.com/page2"
]
results = checker.check_links(links, max_retries=3)
```

## Configuration Requirements

### Environment Variables

Create a `.env` file with:

```bash
# LLM Providers
OLLAMA_BASE_URL=http://localhost:11434
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here

# GitHub
GITHUB_TOKEN=your_github_token

# Paths
CACHE_DIR=./cache
CHROMA_PERSIST_DIR=./chroma_db

# Model Settings
LLM_PROVIDER=OLLAMA  # OLLAMA, GEMINI, or OPENAI
OLLAMA_TOPIC_MODEL=llama2
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Rate Limits
GEMINI_RPM_LIMIT=60
CACHE_TTL=3600
```

## Acceptance Criteria Verification

### ✅ All Services Implemented
- [x] LLMService with Ollama → Gemini → OpenAI fallback
- [x] DatabaseService (ChromaDB wrapper)
- [x] EmbeddingService (sentence-transformers)
- [x] GistService (GitHub Gist API)
- [x] TrendsService (Google Trends pytrends)
- [x] LinkChecker (HTTP validation)

### ✅ Imports Work
```bash
python -c "from src.services import LLMService, DatabaseService, EmbeddingService, GistService, LinkChecker, TrendsService"
# Should complete without errors
```

### ✅ LLMService.generate() with Fallback
```python
# Falls back through chain when providers fail
result = llm.generate("test")  # Tries Ollama first
```

### ✅ All Services Accept Config
```python
llm = LLMService(config)
db = DatabaseService(config)
embed = EmbeddingService(config)
gist = GistService(config)
trends = TrendsService(config)
checker = LinkChecker(config)
```

### ✅ Tests Pass
```bash
pytest tests/test_services_comprehensive.py -v
# All tests should be green
```

### ✅ No Network Calls in Tests
All external dependencies (requests, OpenAI client, Gemini client, etc.) are mocked.

## Troubleshooting

### Import Errors
If you get `ModuleNotFoundError`, ensure you're in the project root:
```bash
cd /home/claude
export PYTHONPATH=/home/claude:$PYTHONPATH
```

### Missing Dependencies
Install requirements:
```bash
pip install -r requirements.txt --break-system-packages
```

### Ollama Not Running
Start Ollama service:
```bash
# If using Docker
docker run -d -p 11434:11434 ollama/ollama

# If installed locally
ollama serve
```

### ChromaDB Permission Issues
Ensure write permissions:
```bash
mkdir -p ./chroma_db
chmod 755 ./chroma_db
```

## Architecture Notes

### Provider Priority
Default fallback order: `OLLAMA → GEMINI → OPENAI`

To change priority, set `LLM_PROVIDER` in config or use `provider` parameter:
```python
llm.generate("prompt", provider="GEMINI")  # Skip Ollama
```

### Retry Logic
Each provider attempts 3 times with exponential backoff:
- Attempt 1: immediate
- Attempt 2: wait 1s
- Attempt 3: wait 2s

Total timeout per provider: 30 seconds

### Caching
LLMService caches responses based on:
- Prompt text
- System prompt (if provided)
- JSON schema (if provided)
- JSON mode flag

Cache TTL: 3600 seconds (configurable via `CACHE_TTL`)

### Logging
All services use structlog for structured logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Self-Review Checklist

- [x] All 6 services implemented with no stubs
- [x] Fallback chain tested and working
- [x] Tests pass without network
- [x] Config-driven behavior (providers list)
- [x] Exception handling with clear messages
- [x] Type hints present on public methods
- [x] Logging structured and informative
- [x] Token usage tracking in LLMService
- [x] Provider health check implemented
- [x] Windows-friendly paths (Path objects)
- [x] Mock fixtures for all external APIs
