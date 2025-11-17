"""Trends Research Agent - Google Trends keyword research and analysis.

This agent performs comprehensive keyword research using Google Trends data,
analyzing search interest, related queries, and suggesting keyword variations.
"""

from typing import Optional, Dict, List, Any
import logging
import json
import time
from datetime import datetime, timedelta
import hashlib

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


class TrendsResearchAgent(SelfCorrectingAgent, Agent):
    """Agent for Google Trends keyword research and trend analysis.
    
    This agent performs keyword research using Google Trends API to:
    - Analyze search interest over time for given keywords
    - Find related queries and suggestions
    - Identify trending topics and seasonal patterns
    - Compare multiple keywords for relative popularity
    
    The agent includes rate limiting, caching, and error recovery mechanisms
    to ensure reliable operation with the Google Trends API.
    
    Example:
        >>> agent = TrendsResearchAgent(config, event_bus, trends_service)
        >>> event = AgentEvent(
        ...     event_type="execute_trends_research",
        ...     data={"keywords": ["python tutorial", "machine learning"]}
        ... )
        >>> result = agent.execute(event)
        >>> print(result.data["trends"])
    """
    
    # Cache TTL in seconds (1 hour)
    CACHE_TTL = 3600
    
    # Rate limiting delay between API calls (1.5 seconds)
    RATE_LIMIT_DELAY = 1.5
    
    def __init__(
        self, 
        config: Config, 
        event_bus: EventBus, 
        trends_service: TrendsService,
        llm_service: Optional[LLMService] = None
    ):
        """Initialize the Trends Research Agent.
        
        Args:
            config: Application configuration object
            event_bus: Event bus for agent communication
            trends_service: Service for accessing Google Trends data
            llm_service: Optional LLM service for enhanced analysis
        """
        self.trends_service = trends_service
        self.llm_service = llm_service
        
        # In-memory cache with TTL
        self._cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}
        
        # Last API call timestamp for rate limiting
        self._last_api_call = datetime.now()
        
        Agent.__init__(self, "TrendsResearchAgent", config, event_bus)
        logger.info("TrendsResearchAgent initialized with cache TTL=%ds", self.CACHE_TTL)
    
    def _create_contract(self) -> AgentContract:
        """Create agent contract defining capabilities and schemas.
        
        Returns:
            AgentContract with input/output schemas and capabilities
        """
        return AgentContract(
            agent_id="TrendsResearchAgent",
            capabilities=["trends_research", "keyword_analysis"],
            input_schema={
                "type": "object",
                "required": ["keywords"],
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keywords to research (max 5)"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe for trends analysis",
                        "default": "today 3-m"
                    },
                    "geo": {
                        "type": "string",
                        "description": "Geographic region for trends",
                        "default": "US"
                    }
                }
            },
            output_schema={
                "type": "object",
                "required": ["keywords", "trends", "suggestions"],
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Original keywords analyzed"
                    },
                    "trends": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Trend data for keywords"
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related keyword suggestions"
                    },
                    "related_queries": {
                        "type": "object",
                        "description": "Related queries by keyword"
                    },
                    "analysis": {
                        "type": "object",
                        "description": "Optional analysis metadata"
                    }
                }
            },
            publishes=["trends_research_complete", "trends_research_failed"]
        )
    
    def _subscribe_to_events(self):
        """Subscribe to relevant events on the event bus."""
        self.event_bus.subscribe("execute_trends_research", self.execute)
        self.event_bus.subscribe("execute_keyword_analysis", self.execute)
    
    def _compute_cache_key(self, keywords: List[str], timeframe: str, geo: str) -> str:
        """Compute cache key from request parameters.
        
        Args:
            keywords: List of keywords
            timeframe: Timeframe string
            geo: Geographic region
            
        Returns:
            SHA256 hash of parameters as cache key
        """
        cache_data = {
            "keywords": sorted(keywords),
            "timeframe": timeframe,
            "geo": geo
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
            logger.debug("Cache hit for trends research (age=%.1fs)", age)
            return data
        else:
            # Clean up expired entry
            del self._cache[cache_key]
            logger.debug("Cache expired for trends research (age=%.1fs)", age)
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Save data to cache with current timestamp.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self._cache[cache_key] = (data, datetime.now())
        logger.debug("Saved to cache: %s (total cached: %d)", cache_key[:12], len(self._cache))
    
    def _apply_rate_limit(self):
        """Apply rate limiting delay before API calls.
        
        Ensures minimum delay between consecutive API calls to avoid
        rate limiting by Google Trends API.
        """
        elapsed = (datetime.now() - self._last_api_call).total_seconds()
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
            time.sleep(sleep_time)
        self._last_api_call = datetime.now()
    
    def _fetch_interest_over_time(
        self, 
        keywords: List[str], 
        timeframe: str = "today 3-m"
    ) -> Optional[Dict[str, Any]]:
        """Fetch interest over time data from Google Trends.
        
        Args:
            keywords: List of keywords (max 5)
            timeframe: Timeframe string (e.g., "today 3-m", "today 12-m")
            
        Returns:
            Dictionary with trend data or None on error
        """
        try:
            self._apply_rate_limit()
            result = self.trends_service.get_interest_over_time(keywords, timeframe)
            
            if result is None:
                logger.warning("No trend data returned for keywords: %s", keywords)
                return None
            
            return result
            
        except Exception as e:
            logger.error("Error fetching interest over time: %s", e)
            return None
    
    def _fetch_related_queries(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Fetch related queries for a keyword.
        
        Args:
            keyword: Single keyword to analyze
            
        Returns:
            Dictionary with related queries or None on error
        """
        try:
            self._apply_rate_limit()
            result = self.trends_service.get_related_queries(keyword)
            
            if result is None:
                logger.debug("No related queries found for: %s", keyword)
                return None
            
            return result
            
        except Exception as e:
            logger.error("Error fetching related queries for '%s': %s", keyword, e)
            return None
    
    def _extract_suggestions(self, related_data: Dict[str, Any]) -> List[str]:
        """Extract keyword suggestions from related queries data.
        
        Args:
            related_data: Related queries data from Trends API
            
        Returns:
            List of suggested keywords
        """
        suggestions = []
        
        # Extract top queries
        if "top" in related_data:
            top_queries = related_data["top"]
            if isinstance(top_queries, dict) and "query" in top_queries:
                suggestions.extend(top_queries["query"].tolist()[:10])
        
        # Extract rising queries
        if "rising" in related_data:
            rising_queries = related_data["rising"]
            if isinstance(rising_queries, dict) and "query" in rising_queries:
                rising_list = rising_queries["query"].tolist()[:5]
                # Add only if not already in suggestions
                suggestions.extend([q for q in rising_list if q not in suggestions])
        
        return suggestions[:15]  # Limit to top 15 suggestions
    
    def _analyze_trends(
        self, 
        keywords: List[str],
        trend_data: Optional[Dict[str, Any]],
        related_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze trend data and generate insights.
        
        Args:
            keywords: List of keywords analyzed
            trend_data: Interest over time data
            related_data: Related queries for each keyword
            
        Returns:
            Analysis dictionary with insights
        """
        analysis = {
            "total_keywords": len(keywords),
            "has_trend_data": trend_data is not None,
            "keywords_with_related": len(related_data),
            "timestamp": datetime.now().isoformat()
        }
        
        # Analyze trend patterns if data available
        if trend_data and "data" in trend_data:
            data_points = trend_data["data"]
            if data_points:
                analysis["data_points"] = len(data_points)
                
                # Calculate average interest for each keyword
                avg_interest = {}
                for kw in keywords:
                    if kw in data_points[0]:
                        values = [point.get(kw, 0) for point in data_points]
                        avg_interest[kw] = sum(values) / len(values)
                
                analysis["average_interest"] = avg_interest
                
                # Identify most popular keyword
                if avg_interest:
                    top_keyword = max(avg_interest, key=avg_interest.get)
                    analysis["top_keyword"] = top_keyword
                    analysis["top_keyword_score"] = avg_interest[top_keyword]
        
        return analysis
    
    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        """Execute trends research for given keywords.
        
        This method performs comprehensive keyword research including:
        1. Fetching interest over time data
        2. Finding related queries and suggestions
        3. Analyzing trends and patterns
        4. Generating actionable insights
        
        Args:
            event: Agent event containing keywords in data["keywords"]
            
        Returns:
            AgentEvent with research results or None on error
            
        Example:
            >>> event = AgentEvent(
            ...     event_type="execute_trends_research",
            ...     data={
            ...         "keywords": ["python", "java", "javascript"],
            ...         "timeframe": "today 12-m"
            ...     }
            ... )
            >>> result = agent.execute(event)
        """
        try:
            # Extract parameters
            keywords = event.data.get("keywords", [])
            timeframe = event.data.get("timeframe", "today 3-m")
            geo = event.data.get("geo", "US")
            
            # Validate input
            if not keywords:
                raise ValueError("No keywords provided for trends research")
            
            # Limit to 5 keywords (Google Trends API limit)
            if len(keywords) > 5:
                logger.warning("Limiting keywords from %d to 5", len(keywords))
                keywords = keywords[:5]
            
            # Check cache
            cache_key = self._compute_cache_key(keywords, timeframe, geo)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result is not None:
                logger.info("Returning cached trends research for %d keywords", len(keywords))
                return AgentEvent(
                    event_type="trends_research_complete",
                    data=cached_result,
                    source_agent=self.agent_id,
                    correlation_id=event.correlation_id
                )
            
            # Fetch interest over time
            logger.info("Fetching trends for keywords: %s", keywords)
            trend_data = self._fetch_interest_over_time(keywords, timeframe)
            
            # Fetch related queries for each keyword
            related_data = {}
            suggestions = []
            
            for keyword in keywords:
                related = self._fetch_related_queries(keyword)
                if related:
                    related_data[keyword] = related
                    suggestions.extend(self._extract_suggestions(related))
            
            # Remove duplicates from suggestions
            suggestions = list(dict.fromkeys(suggestions))
            
            # Generate analysis
            analysis = self._analyze_trends(keywords, trend_data, related_data)
            
            # Build result
            result = {
                "keywords": keywords,
                "trends": trend_data.get("data", []) if trend_data else [],
                "suggestions": suggestions,
                "related_queries": related_data,
                "analysis": analysis,
                "timeframe": timeframe,
                "geo": geo
            }
            
            # Cache result
            self._save_to_cache(cache_key, result)
            
            logger.info(
                "Trends research complete: %d keywords, %d suggestions, %d related queries",
                len(keywords), len(suggestions), len(related_data)
            )
            
            return AgentEvent(
                event_type="trends_research_complete",
                data=result,
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )
            
        except Exception as e:
            logger.error("Trends research failed: %s", e, exc_info=True)
            return AgentEvent(
                event_type="trends_research_failed",
                data={"error": str(e), "keywords": event.data.get("keywords", [])},
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )


__all__ = ['TrendsResearchAgent']
# DOCGEN:LLM-FIRST@v4