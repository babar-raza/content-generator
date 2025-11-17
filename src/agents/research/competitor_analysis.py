"""Competitor Analysis Agent - Top-ranking content analysis for SEO.

This agent analyzes top-ranking content for target keywords to identify
common topics, content gaps, and optimization opportunities for better
search engine rankings.
"""

from typing import Optional, Dict, List, Any, Set
import logging
import json
import time
from datetime import datetime
import hashlib
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse

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


class CompetitorAnalysisAgent(SelfCorrectingAgent, Agent):
    """Agent for analyzing top-ranking competitor content.
    
    This agent performs competitive content analysis to:
    - Identify top-ranking content for target keywords
    - Extract common topics and themes from competitors
    - Discover content gaps and opportunities
    - Analyze content structure and optimization
    - Generate actionable SEO recommendations
    
    The agent simulates search result analysis and provides insights
    for creating better-optimized content.
    
    Example:
        >>> agent = CompetitorAnalysisAgent(
        ...     config, event_bus,
        ...     database_service, trends_service
        ... )
        >>> event = AgentEvent(
        ...     event_type="execute_competitor_analysis",
        ...     data={"keyword": "python file handling tutorial"}
        ... )
        >>> result = agent.execute(event)
        >>> print(result.data["gaps"])
    """
    
    # Cache TTL in seconds (2 hours for competitor data)
    CACHE_TTL = 7200
    
    # Number of top results to analyze
    TOP_RESULTS_COUNT = 10
    
    # Rate limit delay for external calls (2 seconds)
    RATE_LIMIT_DELAY = 2.0
    
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        database_service: DatabaseService,
        trends_service: Optional[TrendsService] = None,
        llm_service: Optional[LLMService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """Initialize the Competitor Analysis Agent.
        
        Args:
            config: Application configuration object
            event_bus: Event bus for agent communication
            database_service: Service for vector search
            trends_service: Optional service for trends data
            llm_service: Optional LLM service for analysis
            embedding_service: Optional service for embeddings
        """
        self.database_service = database_service
        self.trends_service = trends_service
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        
        # In-memory cache with TTL
        self._cache: Dict[str, tuple[Dict[str, Any], datetime]] = {}
        
        # Last API call timestamp for rate limiting
        self._last_call = datetime.now()
        
        Agent.__init__(self, "CompetitorAnalysisAgent", config, event_bus)
        logger.info("CompetitorAnalysisAgent initialized with top_results=%d", 
                   self.TOP_RESULTS_COUNT)
    
    def _create_contract(self) -> AgentContract:
        """Create agent contract defining capabilities and schemas.
        
        Returns:
            AgentContract with input/output schemas and capabilities
        """
        return AgentContract(
            agent_id="CompetitorAnalysisAgent",
            capabilities=["competitor_analysis", "content_gap_analysis", "seo_research"],
            input_schema={
                "type": "object",
                "required": ["keyword"],
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Target keyword to analyze"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top results to analyze",
                        "default": 10
                    },
                    "include_trends": {
                        "type": "boolean",
                        "description": "Include Google Trends data",
                        "default": True
                    },
                    "deep_analysis": {
                        "type": "boolean",
                        "description": "Perform deep content analysis",
                        "default": False
                    }
                }
            },
            output_schema={
                "type": "object",
                "required": ["top_results", "common_topics", "gaps"],
                "properties": {
                    "top_results": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Top-ranking content analysis"
                    },
                    "common_topics": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Common topics across top results"
                    },
                    "gaps": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Content gaps and opportunities"
                    },
                    "keywords": {
                        "type": "object",
                        "description": "Keyword analysis and suggestions"
                    },
                    "structure": {
                        "type": "object",
                        "description": "Common content structure patterns"
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Actionable recommendations"
                    },
                    "analysis": {
                        "type": "object",
                        "description": "Analysis metadata"
                    }
                }
            },
            publishes=["competitor_analysis_complete", "competitor_analysis_failed"]
        )
    
    def _subscribe_to_events(self):
        """Subscribe to relevant events on the event bus."""
        self.event_bus.subscribe("execute_competitor_analysis", self.execute)
        self.event_bus.subscribe("execute_content_gap_analysis", self.execute)
    
    def _compute_cache_key(self, keyword: str, options: Dict[str, Any]) -> str:
        """Compute cache key from keyword and options.
        
        Args:
            keyword: Target keyword
            options: Analysis options
            
        Returns:
            SHA256 hash as cache key
        """
        cache_data = {
            "keyword": keyword.lower().strip(),
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
            logger.debug("Cache hit for competitor analysis (age=%.1fs)", age)
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
    
    def _apply_rate_limit(self):
        """Apply rate limiting delay before external calls."""
        elapsed = (datetime.now() - self._last_call).total_seconds()
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
            time.sleep(sleep_time)
        self._last_call = datetime.now()
    
    def _simulate_search_results(
        self,
        keyword: str,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Simulate search results using internal content database.
        
        Since we don't make actual web searches, we simulate top results
        by querying our internal content database for relevant matches.
        
        Args:
            keyword: Search keyword
            top_n: Number of results to return
            
        Returns:
            List of simulated search results
        """
        results = []
        
        # Query multiple collections to simulate diverse search results
        collections = ["blog", "tutorial", "docs", "kb", "api"]
        
        for collection in collections:
            try:
                self._apply_rate_limit()
                
                query_result = self.database_service.query(
                    collection=collection,
                    query=keyword,
                    top_k=top_n // len(collections) + 2
                )
                
                if query_result and "documents" in query_result:
                    docs = query_result["documents"][0] if query_result["documents"] else []
                    metadatas = query_result.get("metadatas", [[]])[0]
                    distances = query_result.get("distances", [[]])[0]
                    
                    for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances)):
                        # Convert distance to relevance score
                        relevance = 1.0 - min(dist, 1.0)
                        
                        results.append({
                            "rank": len(results) + 1,
                            "title": meta.get("title", f"Article {i+1}"),
                            "url": meta.get("url", f"/content/{collection}/{i}"),
                            "snippet": doc[:300],  # First 300 chars
                            "content": doc,
                            "collection": collection,
                            "relevance": round(relevance, 3),
                            "metadata": meta or {}
                        })
            
            except Exception as e:
                logger.debug("Error querying collection %s: %s", collection, e)
                continue
        
        # Sort by relevance and return top N
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:top_n]
    
    def _extract_topics_from_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract common topics from top results.
        
        Args:
            results: List of search results
            
        Returns:
            List of topics with frequency counts
        """
        all_keywords = []
        topic_sources = defaultdict(list)
        
        for result in results:
            content = result.get("content", "")
            
            # Extract keywords from each result
            keywords = extract_keywords(content, max_keywords=15)
            
            for kw in keywords:
                all_keywords.append(kw)
                topic_sources[kw].append(result["rank"])
        
        # Count keyword frequencies
        keyword_counts = Counter(all_keywords)
        
        # Build topic list with metadata
        topics = []
        for keyword, count in keyword_counts.most_common(20):
            topics.append({
                "topic": keyword,
                "frequency": count,
                "coverage": round(count / len(results), 2),  # % of results covering this
                "appears_in_ranks": sorted(topic_sources[keyword][:5])
            })
        
        return topics
    
    def _analyze_content_structure(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze common content structure patterns.
        
        Args:
            results: List of search results
            
        Returns:
            Dictionary with structure analysis
        """
        structure_data = {
            "average_length": 0,
            "common_sections": [],
            "code_examples_count": 0,
            "lists_count": 0,
            "headings_pattern": {}
        }
        
        total_length = 0
        section_counter = Counter()
        code_count = 0
        list_count = 0
        
        for result in results:
            content = result.get("content", "")
            total_length += len(content)
            
            # Extract headings (markdown style)
            headings = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
            section_counter.update(headings)
            
            # Count code blocks
            code_blocks = re.findall(r'```[\s\S]*?```', content)
            code_count += len(code_blocks)
            
            # Count lists
            list_items = re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE)
            list_count += len(list_items)
        
        if results:
            structure_data["average_length"] = total_length // len(results)
            structure_data["common_sections"] = [
                {"heading": h, "frequency": c} 
                for h, c in section_counter.most_common(10)
            ]
            structure_data["code_examples_count"] = code_count // len(results)
            structure_data["lists_count"] = list_count // len(results)
        
        return structure_data
    
    def _identify_content_gaps(
        self,
        keyword: str,
        results: List[Dict[str, Any]],
        common_topics: List[Dict[str, Any]],
        trends_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Identify content gaps and opportunities.
        
        Args:
            keyword: Target keyword
            results: Top search results
            common_topics: Common topics found
            trends_data: Optional trends data
            
        Returns:
            List of content gap opportunities
        """
        gaps = []
        
        # Gap 1: Topics with low coverage
        low_coverage_topics = [
            t for t in common_topics 
            if t["coverage"] < 0.3 and t["frequency"] >= 2
        ]
        
        if low_coverage_topics:
            gaps.append({
                "type": "low_coverage_topics",
                "priority": "high",
                "description": "Topics mentioned by some top results but not widely covered",
                "topics": [t["topic"] for t in low_coverage_topics[:5]],
                "opportunity": "Cover these topics to be more comprehensive"
            })
        
        # Gap 2: Missing code examples
        has_code = sum(1 for r in results if "```" in r.get("content", ""))
        if has_code < len(results) * 0.5:
            gaps.append({
                "type": "code_examples",
                "priority": "medium",
                "description": "Only %d/%d top results include code examples" % (has_code, len(results)),
                "opportunity": "Add practical code examples to stand out"
            })
        
        # Gap 3: Trending related keywords not covered
        if trends_data and "suggestions" in trends_data:
            suggestions = trends_data["suggestions"]
            covered_keywords = {t["topic"].lower() for t in common_topics}
            
            uncovered_trending = [
                s for s in suggestions[:10]
                if s.lower() not in covered_keywords
            ]
            
            if uncovered_trending:
                gaps.append({
                    "type": "trending_keywords",
                    "priority": "high",
                    "description": "Trending keywords not covered by top results",
                    "keywords": uncovered_trending[:5],
                    "opportunity": "Target these trending keywords for competitive advantage"
                })
        
        # Gap 4: Content depth
        avg_length = sum(len(r.get("content", "")) for r in results) // max(len(results), 1)
        if avg_length < 2000:
            gaps.append({
                "type": "content_depth",
                "priority": "medium",
                "description": "Top results have average length of %d chars" % avg_length,
                "opportunity": "Create more comprehensive, in-depth content (3000+ words)"
            })
        
        # Gap 5: Multimedia content
        has_images = sum(1 for r in results if re.search(r'!\[.*?\]\(.*?\)', r.get("content", "")))
        if has_images < len(results) * 0.3:
            gaps.append({
                "type": "multimedia",
                "priority": "low",
                "description": "Few top results include images or diagrams",
                "opportunity": "Add visual content, diagrams, and screenshots"
            })
        
        return gaps
    
    def _generate_recommendations(
        self,
        keyword: str,
        gaps: List[Dict[str, Any]],
        common_topics: List[Dict[str, Any]],
        structure: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable SEO recommendations.
        
        Args:
            keyword: Target keyword
            gaps: Identified content gaps
            common_topics: Common topics
            structure: Structure analysis
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Prioritize high-priority gaps
        high_priority_gaps = [g for g in gaps if g.get("priority") == "high"]
        
        for gap in high_priority_gaps:
            recommendations.append(
                f"{gap['type'].replace('_', ' ').title()}: {gap.get('opportunity', 'Optimize')}"
            )
        
        # Topic coverage recommendations
        top_topics = [t["topic"] for t in common_topics[:5]]
        if top_topics:
            recommendations.append(
                f"Must cover these core topics: {', '.join(top_topics)}"
            )
        
        # Structure recommendations
        if structure.get("code_examples_count", 0) > 0:
            recommendations.append(
                f"Include at least {structure['code_examples_count']} code examples"
            )
        
        # Length recommendation
        avg_len = structure.get("average_length", 0)
        if avg_len > 0:
            target_len = int(avg_len * 1.3)  # 30% more than average
            recommendations.append(
                f"Target content length: {target_len}+ characters ({target_len//4}+ words)"
            )
        
        # Common sections to include
        common_sections = structure.get("common_sections", [])
        if common_sections:
            top_sections = [s["heading"] for s in common_sections[:3]]
            recommendations.append(
                f"Include these common sections: {', '.join(top_sections)}"
            )
        
        return recommendations
    
    def _generate_analysis(
        self,
        keyword: str,
        results_count: int,
        topics_count: int,
        gaps_count: int
    ) -> Dict[str, Any]:
        """Generate analysis metadata.
        
        Args:
            keyword: Target keyword
            results_count: Number of results analyzed
            topics_count: Number of topics found
            gaps_count: Number of gaps identified
            
        Returns:
            Analysis metadata dictionary
        """
        return {
            "keyword": keyword,
            "results_analyzed": results_count,
            "topics_identified": topics_count,
            "gaps_found": gaps_count,
            "timestamp": datetime.now().isoformat(),
            "competitive_difficulty": "high" if topics_count > 15 else "medium",
            "opportunity_score": min(gaps_count * 20, 100)  # 0-100 score
        }
    
    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        """Execute competitor analysis for target keyword.
        
        This method performs comprehensive competitor analysis including:
        1. Identifying top-ranking content (simulated)
        2. Extracting common topics and themes
        3. Analyzing content structure patterns
        4. Identifying content gaps and opportunities
        5. Generating actionable recommendations
        
        Args:
            event: Agent event containing keyword in data["keyword"]
            
        Returns:
            AgentEvent with analysis results or None on error
            
        Example:
            >>> event = AgentEvent(
            ...     event_type="execute_competitor_analysis",
            ...     data={
            ...         "keyword": "python asyncio tutorial",
            ...         "top_n": 15,
            ...         "include_trends": True
            ...     }
            ... )
            >>> result = agent.execute(event)
        """
        try:
            # Extract parameters
            keyword = event.data.get("keyword", "")
            top_n = event.data.get("top_n", self.TOP_RESULTS_COUNT)
            include_trends = event.data.get("include_trends", True)
            deep_analysis = event.data.get("deep_analysis", False)
            
            # Validate input
            if not keyword or len(keyword) < 2:
                raise ValueError("Invalid keyword for competitor analysis")
            
            # Check cache
            options = {
                "top_n": top_n,
                "include_trends": include_trends,
                "deep_analysis": deep_analysis
            }
            cache_key = self._compute_cache_key(keyword, options)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result is not None:
                logger.info("Returning cached competitor analysis for '%s'", keyword)
                return AgentEvent(
                    event_type="competitor_analysis_complete",
                    data=cached_result,
                    source_agent=self.agent_id,
                    correlation_id=event.correlation_id
                )
            
            logger.info("Analyzing competitors for keyword: '%s' (top_n=%d)", keyword, top_n)
            
            # Simulate search results (using internal database)
            top_results = self._simulate_search_results(keyword, top_n)
            
            if not top_results:
                logger.warning("No results found for keyword: %s", keyword)
                # Return empty but valid result
                empty_result = {
                    "top_results": [],
                    "common_topics": [],
                    "gaps": [],
                    "keywords": {"target": keyword, "related": []},
                    "structure": {},
                    "recommendations": ["No competitor data available - research keyword validity"],
                    "analysis": self._generate_analysis(keyword, 0, 0, 0)
                }
                return AgentEvent(
                    event_type="competitor_analysis_complete",
                    data=empty_result,
                    source_agent=self.agent_id,
                    correlation_id=event.correlation_id
                )
            
            # Extract common topics
            common_topics = self._extract_topics_from_results(top_results)
            
            # Analyze content structure
            structure = self._analyze_content_structure(top_results)
            
            # Get trends data if requested
            trends_data = None
            if include_trends and self.trends_service:
                try:
                    from .trends_research import TrendsResearchAgent
                    trends_event = AgentEvent(
                        event_type="execute_trends_research",
                        data={"keywords": [keyword]},
                        correlation_id=event.correlation_id
                    )
                    trends_result = TrendsResearchAgent(
                        self.config, self.event_bus, self.trends_service
                    ).execute(trends_event)
                    if trends_result:
                        trends_data = trends_result.data
                except Exception as e:
                    logger.debug("Failed to fetch trends data: %s", e)
            
            # Identify content gaps
            gaps = self._identify_content_gaps(keyword, top_results, common_topics, trends_data)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                keyword, gaps, common_topics, structure
            )
            
            # Generate analysis
            analysis = self._generate_analysis(
                keyword, len(top_results), len(common_topics), len(gaps)
            )
            
            # Build result
            result = {
                "top_results": [
                    {
                        "rank": r["rank"],
                        "title": r["title"],
                        "url": r["url"],
                        "snippet": r["snippet"],
                        "relevance": r["relevance"],
                        "collection": r["collection"]
                    }
                    for r in top_results
                ],
                "common_topics": common_topics,
                "gaps": gaps,
                "keywords": {
                    "target": keyword,
                    "related": [t["topic"] for t in common_topics[:10]],
                    "trending": trends_data.get("suggestions", [])[:5] if trends_data else []
                },
                "structure": structure,
                "recommendations": recommendations,
                "analysis": analysis
            }
            
            # Cache result
            self._save_to_cache(cache_key, result)
            
            logger.info(
                "Competitor analysis complete: %d results, %d topics, %d gaps, %d recommendations",
                len(top_results), len(common_topics), len(gaps), len(recommendations)
            )
            
            return AgentEvent(
                event_type="competitor_analysis_complete",
                data=result,
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )
            
        except Exception as e:
            logger.error("Competitor analysis failed: %s", e, exc_info=True)
            return AgentEvent(
                event_type="competitor_analysis_failed",
                data={"error": str(e), "keyword": event.data.get("keyword", "")},
                source_agent=self.agent_id,
                correlation_id=event.correlation_id
            )


__all__ = ['CompetitorAnalysisAgent']
# DOCGEN:LLM-FIRST@v4