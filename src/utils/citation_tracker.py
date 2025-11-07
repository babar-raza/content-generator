"""Citation tracker for knowledge base sources."""

from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Single citation reference."""
    doc_path: str
    section: str
    line_number: int
    excerpt: str
    relevance_score: float


class CitationTracker:
    """Tracks citations from knowledge base."""
    
    def __init__(self):
        self.citations: List[Citation] = []
        logger.debug("CitationTracker initialized")
    
    def add_citation(self,
                    doc_path: str,
                    chunk_text: str,
                    score: float,
                    line_start: int = 0):
        """Record a citation."""
        
        # Extract section heading
        section = self._extract_section(chunk_text)
        
        # Get excerpt (first 100 chars)
        excerpt = chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
        
        self.citations.append(Citation(
            doc_path=doc_path,
            section=section,
            line_number=line_start,
            excerpt=excerpt,
            relevance_score=score
        ))
        
        logger.debug(f"Citation added: {doc_path}#{section}")
    
    def _extract_section(self, text: str) -> str:
        """Extract section heading from text."""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Found a heading
                return line.lstrip('#').strip()
        
        return "main"
    
    def get_citations(self) -> List[Citation]:
        """Get all citations."""
        return self.citations.copy()
    
    def format_sources(self) -> str:
        """Format citations as markdown."""
        if not self.citations:
            return ""
        
        # Sort by relevance
        sorted_citations = sorted(
            self.citations,
            key=lambda c: c.relevance_score,
            reverse=True
        )
        
        output = ["## Sources\n"]
        
        seen_docs = set()
        citation_num = 1
        
        for cite in sorted_citations:
            # Avoid duplicate docs
            doc_key = f"{cite.doc_path}#{cite.section}"
            if doc_key in seen_docs:
                continue
            
            seen_docs.add(doc_key)
            
            # Create anchor link
            anchor = f"#{cite.section.lower().replace(' ', '-')}" if cite.section != "main" else ""
            
            output.append(
                f"{citation_num}. [{cite.doc_path}]({cite.doc_path}{anchor}) "
                f"(line {cite.line_number}) - Score: {cite.relevance_score:.2f}\n   "
                f"*{cite.excerpt}*"
            )
            
            citation_num += 1
        
        return "\n".join(output)
    
    def get_summary(self) -> dict:
        """Get citation summary."""
        unique_docs = len(set(c.doc_path for c in self.citations))
        avg_score = sum(c.relevance_score for c in self.citations) / len(self.citations) if self.citations else 0
        
        return {
            "total_citations": len(self.citations),
            "unique_documents": unique_docs,
            "average_relevance": avg_score
        }
