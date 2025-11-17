<<<<<<< Updated upstream
=======
"""At a glance
- Purpose: Provides unified interfaces to external services (LLM providers, vector database, embeddings, GitHub, trends, link validation).
- Key inputs: Config object with service-specific settings.
- Key outputs: Service instances with consistent APIs for LLM calls, database operations, embeddings, gist uploads, trend analysis, link checking.
- External deps: Various external APIs (Ollama, Gemini, OpenAI, ChromaDB, sentence-transformers, GitHub API, Google Trends, requests).
- Collaborators: Used by agents and orchestration modules requiring external service integration; provides fallback chains for reliability.
- Lifecycle: Services instantiated during system initialization; maintain connections/caches throughout operation.

Deeper dive
- Core concepts: Service abstraction layer with consistent interfaces; fallback chains for LLM providers; configuration-driven service selection.
- Important invariants: All services accept Config object; structured logging throughout; graceful degradation on service failures.
- Error surface: Service-specific failures (API limits, network issues, auth failures) handled with logging and fallbacks.
- Performance notes: Connection pooling, caching, rate limiting; async support where available.
- Security notes: API keys from config; HTTPS for external calls; no sensitive data logging.
"""

from src.services.services import (
    LLMService,
    DatabaseService,
    EmbeddingService,
    GistService,
    LinkChecker,
    TrendsService,
)

__all__ = [
    "LLMService",
    "DatabaseService", 
    "EmbeddingService",
    "GistService",
    "LinkChecker",
    "TrendsService",
]
# DOCGEN:LLM-FIRST@v4
>>>>>>> Stashed changes
