"""Content Intelligence Agent - Semantic relationship and topic analysis.

This agent analyzes content to extract semantic relationships, identify topics,
discover internal links, and build content knowledge graphs using embeddings
and vector similarity search.
"""

from typing import Optional, Dict, List, Any, Tuple
import logging
import json
import time
from datetime import datetime
import hashlib
import re
from collections import defaultdict

from ..base import (
    Agent, EventBus, AgentEvent, AgentContract, SelfCorrectingAgent,
    Config, LLMService, DatabaseService, EmbeddingService, GistService,
    LinkChecker, TrendsService, PROMPTS, SCHEMAS, CSHARP_LICENSE_HEADER,
    MarkdownDedup, read_file_with_fallback_encoding, chunk_text, 
    build_query, dedupe_context, insert_license, split_code_into_segments,
    validate_code_quality, validate_api_compliance, extract_keywords,
    inject_keywords_naturally, write_markdown_tree, create_frontmatter,
    create_gist_shortcode, create_code_block, extract_code_blocks,
    IngestionStateManager, build_section_prompt_enhancement,
    get_section_heading, is_section_enabled, logger
)


class ContentIntelligenceAgent(SelfCorrectingAgent, Agent):
    """Agent for semantic content analysis and relationship discovery.
    
    This agent performs deep content analysis to:
    - Extract semantic topics and themes
    - Find related content using vector similarity
    - Discover internal linking opportunities
    - Build content knowledge graphs
    - Identify content gaps and opportunities
    
    The agent uses embeddings and vector search to understand content
    relationships beyond simple keyword matching.
    
    Example:
        >>> agent = ContentIntelligenceAgent(
        ...     config, event_bus, 
        ...     embedding_service, database_service
        ... )
        >>> event = AgentEvent(
        ...     event_type="execute_content_intelligence",
        ...     data={"content": "Python tutorial on machine learning..."}
        ... )
        >>> result = agent.execute(event)
        >>> print(result.data["topics"])
    """
    
    # Cache TTL in seconds (1 hour)
    CACHE_TTL = 3600
    
    # Similarity threshold for related content
    SIMILARITY_THRESHOLD = 0.7
    
    # Maximum chunks to analyze per content
    MAX_CHUNKS = 20
    
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        embedding_service: EmbeddingService,
        database_service: DatabaseService,
        llm_service: Optional[LLMService] = None
    ):
        """Initialize the Content Intelligence Agent.
        
        Args:
            config: Application configuration object
            event_bus: Event bus for agent communication
            embedding_service: Service for generating embeddings
            database_service: Service for vector search
            llm_service: Optional LLM service for enhanced analysis
        """
        self.embedding_service = embedding_service
        self.database_service = database_service
        self.llm_service = llm_service
        
        # In-memory cache with TTL
        self._cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}
        
        Agent.__init__(self, "ContentIntelligenceAgent", config, event_bus)
        logger.info("ContentIntelligenceAgent initialized with similarity threshold=%.2f", 
                   self.SIMILARITY_THRESHOLD)
    
    def _create_contract(self) -> AgentContract:
        """Create agent contract defining capabilities and schemas.
        
        Returns:
            AgentContract with input/output schemas and capabilities
        """
        return AgentContract(
            agent_id="ContentIntelligenceAgent",
            capabilities=["content_analysis", "semantic_search", "topic_extraction"],
            input_schema={
                "type": "object",
                "required": ["content"],
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content text to analyze"
                    },
                    "max_related": {
                        "type": "integer",
                        "description": "Maximum related items to return",
                        "default": 10
                    },
                    "include_links": {
                        "type": "boolean",
                        "description": "Whether to extract internal links",
                        "default": True
                    },
                    "deep_analysis": {
                        "type": "boolean",
                        "description": "Perform deep topic analysis",
                        "default": False
                    }
                }
            },
            output_schema={
                "type": "object",
                "required": ["related", "topics", "links"],
                "properties": {
                    "related": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Related content items with similarity scores"
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Extracted topics and themes"
                    },
                    "links": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Internal linking opportunities"
                    },
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Extracted named entities"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key terms and phrases"
                    },
                    "analysis": {
                        "type": "object",
                        "description": "Analysis metadata"
                    }
                }
            },
            publishes=["content_intelligence_complete", "content_intelligence_failed"]
        )
    
    def _subscribe_to_events(self):
        """Subscribe to relevant events on the event bus."""
        self.event_bus.subscribe("execute_content_intelligence", self.execute)
        self.event_bus.subscribe("execute_content_analysis", self.execute)
        self.event_bus.subscribe("execute_semantic_search", self.execute)
    
    def _compute_cache_key(self, content: str, options: Dict[str, Any]) -> str:
        """Compute cache key from content and options.
        
        Args:
            content: Content text
            options: Analysis options
            
        Returns:
            SHA256 hash as cache key
        """
        # Use first 1000 chars of content for cache key
        content_sample = content[:1000]
        cache_data = {
            "content": content_sample,
            "options": options
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache if still valid.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached data if valid, None if expired or missing
        """
        if cache_key not in self._cache:
            return None
        
        data, timestamp = self._cache[cache_key]
        age = (datetime.now() - timestamp).total_seconds()
        
        if age < self.CACHE_TTL:
            logger.debug("Cache hit for content intelligence (age=%.1fs)", age)
            return data
        else:
            del self._cache[cache_key]
            logger.debug("Cache expired (age=%.1fs)", age)
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Save data to cache with current timestamp.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self._cache[cache_key] = (data, datetime.now())
        logger.debug("Saved to cache: %s", cache_key[:12])
    
    def _extract_topics_simple(self, content: str) -> List[str]:
        """Extract topics using simple keyword extraction.
        
        Args:
            content: Content text
            
        Returns:
            List of topic keywords
        """
        # Use existing extract_keywords utility
        keywords = extract_keywords(content, max_keywords=10)
        
        # Also extract common technical terms
        tech_patterns = [
            r'\b[A-Z][a-z]+(?:\.[A-Z][a-z]+)+\b',  # Namespaces (e.g., System.IO)
            r'\b[A-Z][a-z]+[A-Z][A-Za-z]+\b',  # CamelCase identifiers
            r'\b(?:API|SDK|HTTP|REST|JSON|XML|SQL|CSV)\b',  # Common acronyms
        ]
        
        tech_terms = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, content)
            tech_terms.extend(matches[:5])
        
        # Combine and deduplicate
        all_topics = list(dict.fromkeys(keywords + tech_terms))
        return all_topics[:15]
    
    def _extract_topics_llm(self, content: str) -> List[str]:
        """Extract topics using LLM for deeper analysis.
        
        Args:
            content: Content text
            
        Returns:
            List of topics identified by LLM
        """
        if not self.llm_service:
            logger.debug("LLM service not available for deep topic extraction")
            return []
        
        try:
            # Truncate content for LLM
            content_sample = content[:3000]
            
            prompt = f"""Analyze the following content and extract the main topics, themes, and concepts.
Return a JSON array of topic strings (max 10 topics).

Content:
{content_sample}

Respond with only a JSON array of strings, no other text."""

            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt="You are a content analysis expert. Extract topics concisely.",
                json_mode=True,
                model=self.config.ollama_topic_model
            )
            
            topics = json.loads(response)
            if isinstance(topics, list):
                return topics[:10]
            else:
                logger.warning("LLM returned non-list topics: %s", type(topics))
                return []
                
        except Exception as e:
            logger.warning("LLM topic extraction failed: %s", e)
            return []
    
    def _extract_entities(self, content: str) -> List[str]:
        """Extract named entities from content.
        
        Args:
            content: Content text
            
        Returns:
            List of named entities
        """
        entities = []
        
        # Extract capitalized phrases (potential entities)
        entity_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.findall(entity_pattern, content)
        
        # Filter out common words and keep unique entities
        common_words = {'The', 'This', 'That', 'These', 'Those', 'In', 'On', 'At'}
        entities = [m for m in matches if m not in common_words]
        entities = list(dict.fromkeys(entities))[:20]
        
        return entities
    
    def _find_related_content(
        self, 
        content: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Find related content using vector similarity search.
        
        Args:
            content: Content text
            max_results: Maximum number of related items to return
            
        Returns:
            List of related content with similarity scores
        """
        try:
            # Chunk content for embedding
            chunks = chunk_text(content, chunk_size=500)[:self.MAX_CHUNKS]
            
            if not chunks:
                return []
            
            # Generate embeddings for chunks
            embeddings = self.embedding_service.encode(chunks)
            
            # Use first chunk's embedding as primary query
            query_embedding = embeddings[0]
            
            # Search across all collections
            related_items = []
            collections = ["api", "blog", "docs", "kb", "tutorial"]
            
            for collection in collections:
                try:
                    results = self.database_service.query_by_embedding(
                        collection=collection,
                        query_embedding=query_embedding,
                        top_k=max_results // len(collections) + 2
                    )
                    
                    if results and "documents" in results:
                        docs = results["documents"][0] if results["documents"] else []
                        distances = results.get("distances", [[]])[0]
                        metadatas = results.get("metadatas", [[]])[0]
                        
                        for doc, dist, meta in zip(docs, distances, metadatas):
                            # Convert distance to similarity score
                            similarity = 1.0 - min(dist, 1.0)
                            
                            if similarity >= self.SIMILARITY_THRESHOLD:
                                related_items.append({
                                    "content": doc[:200],  # First 200 chars
                                    "similarity": round(similarity, 3),
                                    "collection": collection,
                                    "metadata": meta or {}
                                })
                
                except Exception as e:
                    logger.debug("Error querying collection %s: %s", collection, e)
                    continue
            
            # Sort by similarity and return top results
            related_items.sort(key=lambda x: x["similarity"], reverse=True)
            return related_items[:max_results]
            
        except Exception as e:
            logger.error("Error finding related content: %s", e)
            return []
    
    def _extract_internal_links(
        self, 
        content: str,
        related_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract and suggest internal linking opportunities.
        
        Args:
            content: Content text
            related_items: Related content items
            
        Returns:
            List of internal link suggestions
        """
        links = []
        
        # Extract existing links from content
        existing_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
        existing_targets = {target for _, target in existing_links}
        
        # Generate link suggestions from related items
        for item in related_items[:10]:
            metadata = item.get("metadata", {})
            
            # Skip if already linked
            if metadata.get("url") in existing_targets:
                continue
            
            # Suggest link based on similarity
            if item["similarity"] > 0.8:
                link_type = "highly_related"
            elif item["similarity"] > 0.75:
                link_type = "related"
            else:
                link_type = "somewhat_related"
            
            links.append({
                "type": link_type,
                "title": metadata.get("title", "Related Content"),
                "url": metadata.get("url", ""),
                "similarity": item["similarity"],
                "collection": item["collection"],
                "snippet": item["content"]
            })
        
        return links
    
    def _generate_analysis(
        self,
        content: str,
        topics: List[str],
        related_count: int,
        links_count: int
    ) -> Dict[str, Any]:
        """Generate analysis metadata.
        
        Args:
            content: Original content
            topics: Extracted topics
            related_count: Number of related items found
            links_count: Number of link opportunities
            
        Returns:
            Analysis metadata dictionary
        """
        return {
            "content_length": len(content),
            "word_count": len(content.split()),
            "topics_count": len(topics),
            "related_items_found": related_count,
            "link_opportunities": links_count,
            "timestamp": datetime.now().isoformat(),
            "has_sufficient_related": related_count >= 5,
            "link_density": links_count / max(len(content.split()), 1) * 1000  # Links per 1k words
        }
    
    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        """Execute content intelligence analysis.
        
        This method performs comprehensive content analysis including:
        1. Topic and entity extraction
        2. Semantic similarity search for related content
        3. Internal linking opportunity discovery
        4. Content relationship mapping
        
        Args:
            event: Agent event containing content in data["content"]
            
        Returns:
            AgentEvent with analysis results or None on error
            
        Example:
            >>> event = AgentEvent(
            ...     event_type="execute_content_intelligence",
            ...     data={
            ...         "content": "Tutorial on Python file I/O...",
            ...         "max_related": 15,
            ...         "deep_analysis": True
            ...     }
            ... )
            >>> result = agent.execute(event)
        """
        try:
            # Extract parameters
            content = event.data.get("content", "")
            max_related = event.data.get("max_related", 10)
            include_links = event.data.get("include_links", True)
            deep_analysis = event.data.get("deep_analysis", False)
            
            # Validate input
            if not content or len(content) < 50:
                raise ValueError("Content too short for analysis (minimum 50 characters)")
            
            # Check cache
            options = {
                "max_related": max_related,
                "include_links": include_links,
                "deep_analysis": deep_analysis
            }
            cache_key = self._compute_cache_key(content, options)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result is not None:
                logger.info("Returning cached content intelligence analysis")
                return AgentEvent(
                    event_type="content_intelligence_complete",
                    data=cached_result,
                    source_agent=self.agent_id,
                    correlation_id=event.correlation_id
                )
            
            logger.info("Analyzing content (%d chars, deep=%s)", len(content), deep_analysis)
            
            # Extract topics
            topics_simple = self._extract_topics_simple(content)
            topics_llm = self._extract_topics_llm(content) if deep_analysis else []
            topics = list(dict.fromkeys(topics_simple + topics_llm))[:15]
            
            # Extract entities
            entities = self._extract_entities(content)
            
            # Extract keywords
            keywords = extract_keywords(content, max_keywords=20)
            
            # Find related content
            related_items = self._find_related_content(content, max_related)
            
            # Extract internal links if requested
            links = []
            if include_links:
                links = self._extract_internal_links(content, related_items)
            
            # Generate analysis
            analysis = self._generate_analysis(
                content, topics, len(related_items), len(links)
            )
            
            # Build result
            result = {
                "related": related_items,
                "topics": topics,
                "links": links,
                "entities": entities,
                "keywords": keywords,
                "analysis": analysis
            }
            
            # Cache result
            self._save_to_cache(cache_key, result)
            
            logger.info(
                "Content intelligence complete: %d topics, %d related, %d links",
                len(topics), len(related_items), len(links)
            )
            
            return AgentEvent(
                event_type="content_intelligence_complete",
                data=result,
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )
            
        except Exception as e:
            logger.error("Content intelligence failed: %s", e, exc_info=True)
            return AgentEvent(
                event_type="content_intelligence_failed",
                data={"error": str(e)},
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )


__all__ = ['ContentIntelligenceAgent']
# DOCGEN:LLM-FIRST@v4