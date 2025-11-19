"""Tests for citation_tracker module."""

import pytest
from src.utils.citation_tracker import Citation, CitationTracker


class TestCitation:
    """Tests for Citation dataclass."""
    
    def test_citation_creation(self):
        """Test creating a Citation."""
        citation = Citation(
            doc_path="/path/to/doc.md",
            section="Introduction",
            line_number=10,
            excerpt="This is an excerpt...",
            relevance_score=0.95
        )
        
        assert citation.doc_path == "/path/to/doc.md"
        assert citation.section == "Introduction"
        assert citation.line_number == 10
        assert citation.excerpt == "This is an excerpt..."
        assert citation.relevance_score == 0.95
    
    def test_citation_attributes(self):
        """Test Citation has all required attributes."""
        citation = Citation("path", "section", 1, "excerpt", 0.9)
        
        assert hasattr(citation, 'doc_path')
        assert hasattr(citation, 'section')
        assert hasattr(citation, 'line_number')
        assert hasattr(citation, 'excerpt')
        assert hasattr(citation, 'relevance_score')


class TestCitationTracker:
    """Tests for CitationTracker class."""
    
    def test_initialization(self):
        """Test tracker initialization."""
        tracker = CitationTracker()
        assert tracker.citations == []
    
    def test_add_citation_basic(self):
        """Test adding a basic citation."""
        tracker = CitationTracker()
        tracker.add_citation(
            doc_path="/docs/test.md",
            chunk_text="Sample text content",
            score=0.8,
            line_start=5
        )
        
        assert len(tracker.citations) == 1
        assert tracker.citations[0].doc_path == "/docs/test.md"
        assert tracker.citations[0].line_number == 5
        assert tracker.citations[0].relevance_score == 0.8
    
    def test_add_citation_with_heading(self):
        """Test adding citation extracts section from heading."""
        tracker = CitationTracker()
        chunk_text = "# Installation\nThis is how to install..."
        
        tracker.add_citation("/docs/guide.md", chunk_text, 0.9)
        
        assert tracker.citations[0].section == "Installation"
    
    def test_add_citation_long_text(self):
        """Test that long text is truncated in excerpt."""
        tracker = CitationTracker()
        long_text = "a" * 150
        
        tracker.add_citation("/docs/long.md", long_text, 0.7)
        
        assert len(tracker.citations[0].excerpt) == 103  # 100 + "..."
        assert tracker.citations[0].excerpt.endswith("...")
    
    def test_add_citation_short_text(self):
        """Test that short text is not truncated."""
        tracker = CitationTracker()
        short_text = "Short text"
        
        tracker.add_citation("/docs/short.md", short_text, 0.7)
        
        assert tracker.citations[0].excerpt == short_text
        assert not tracker.citations[0].excerpt.endswith("...")
    
    def test_extract_section_with_heading(self):
        """Test extracting section from markdown heading."""
        tracker = CitationTracker()
        text = "# Main Title\nContent here"
        
        section = tracker._extract_section(text)
        assert section == "Main Title"
    
    def test_extract_section_with_multiple_hashes(self):
        """Test extracting section from heading with multiple #."""
        tracker = CitationTracker()
        text = "## Subsection\nContent"
        
        section = tracker._extract_section(text)
        assert section == "Subsection"
    
    def test_extract_section_no_heading(self):
        """Test extracting section when no heading present."""
        tracker = CitationTracker()
        text = "Just plain text without heading"
        
        section = tracker._extract_section(text)
        assert section == "main"
    
    def test_extract_section_heading_with_whitespace(self):
        """Test extracting section removes whitespace."""
        tracker = CitationTracker()
        text = "###   Spaced Out   \nContent"
        
        section = tracker._extract_section(text)
        assert section == "Spaced Out"
    
    def test_get_citations(self):
        """Test getting all citations."""
        tracker = CitationTracker()
        tracker.add_citation("/doc1.md", "Text 1", 0.9)
        tracker.add_citation("/doc2.md", "Text 2", 0.8)
        
        citations = tracker.get_citations()
        
        assert len(citations) == 2
        assert citations[0].doc_path == "/doc1.md"
        assert citations[1].doc_path == "/doc2.md"
    
    def test_get_citations_returns_copy(self):
        """Test that get_citations returns a copy."""
        tracker = CitationTracker()
        tracker.add_citation("/doc1.md", "Text", 0.9)
        
        citations1 = tracker.get_citations()
        citations2 = tracker.get_citations()
        
        # They should be equal but not the same object
        assert citations1 == citations2
        assert citations1 is not citations2
    
    def test_format_sources_empty(self):
        """Test formatting sources when no citations."""
        tracker = CitationTracker()
        result = tracker.format_sources()
        assert result == ""
    
    def test_format_sources_single_citation(self):
        """Test formatting sources with single citation."""
        tracker = CitationTracker()
        tracker.add_citation(
            "/docs/test.md",
            "# Introduction\nThis is a test",
            0.95,
            line_start=1
        )
        
        result = tracker.format_sources()
        
        assert "## Sources" in result
        assert "/docs/test.md" in result
        assert "Score: 0.95" in result
        assert "line 1" in result
    
    def test_format_sources_sorts_by_relevance(self):
        """Test that sources are sorted by relevance score."""
        tracker = CitationTracker()
        tracker.add_citation("/doc1.md", "Text 1", 0.6)
        tracker.add_citation("/doc2.md", "Text 2", 0.9)
        tracker.add_citation("/doc3.md", "Text 3", 0.7)
        
        result = tracker.format_sources()
        
        # doc2 (0.9) should appear first
        lines = result.split('\n')
        assert any("/doc2.md" in line and line.startswith("1.") for line in lines)
    
    def test_format_sources_removes_duplicates(self):
        """Test that duplicate documents are removed."""
        tracker = CitationTracker()
        tracker.add_citation("/doc.md", "# Section A\nText", 0.9)
        tracker.add_citation("/doc.md", "# Section A\nMore text", 0.8)
        
        result = tracker.format_sources()
        
        # Should only have one entry
        numbered_lines = [line for line in result.split('\n') if line.strip().startswith('1.') or line.strip().startswith('2.')]
        assert len(numbered_lines) == 1
    
    def test_format_sources_with_sections(self):
        """Test formatting includes section anchors."""
        tracker = CitationTracker()
        tracker.add_citation(
            "/doc.md",
            "# Getting Started\nContent",
            0.9
        )
        
        result = tracker.format_sources()
        
        assert "#getting-started" in result
    
    def test_format_sources_main_section_no_anchor(self):
        """Test that main section doesn't get anchor."""
        tracker = CitationTracker()
        tracker.add_citation(
            "/doc.md",
            "Plain text without heading",
            0.9
        )
        
        result = tracker.format_sources()
        
        # Should have doc path but no # anchor
        lines = [line for line in result.split('\n') if '/doc.md' in line]
        assert len(lines) > 0
        assert "(/doc.md)" in result
    
    def test_get_summary_empty(self):
        """Test getting summary with no citations."""
        tracker = CitationTracker()
        summary = tracker.get_summary()
        
        assert summary['total_citations'] == 0
        assert summary['unique_documents'] == 0
        assert summary['average_relevance'] == 0
    
    def test_get_summary_single_citation(self):
        """Test getting summary with single citation."""
        tracker = CitationTracker()
        tracker.add_citation("/doc.md", "Text", 0.8)
        
        summary = tracker.get_summary()
        
        assert summary['total_citations'] == 1
        assert summary['unique_documents'] == 1
        assert summary['average_relevance'] == 0.8
    
    def test_get_summary_multiple_citations(self):
        """Test getting summary with multiple citations."""
        tracker = CitationTracker()
        tracker.add_citation("/doc1.md", "Text 1", 0.9)
        tracker.add_citation("/doc2.md", "Text 2", 0.7)
        tracker.add_citation("/doc1.md", "Text 3", 0.8)
        
        summary = tracker.get_summary()
        
        assert summary['total_citations'] == 3
        assert summary['unique_documents'] == 2
        assert summary['average_relevance'] == pytest.approx((0.9 + 0.7 + 0.8) / 3)
    
    def test_multiple_add_citation_calls(self):
        """Test adding multiple citations sequentially."""
        tracker = CitationTracker()
        
        for i in range(5):
            tracker.add_citation(
                f"/doc{i}.md",
                f"Content {i}",
                0.5 + i * 0.1
            )
        
        assert len(tracker.citations) == 5
        assert tracker.citations[0].doc_path == "/doc0.md"
        assert tracker.citations[4].doc_path == "/doc4.md"
    
    def test_citation_default_line_start(self):
        """Test that line_start defaults to 0."""
        tracker = CitationTracker()
        tracker.add_citation("/doc.md", "Text", 0.8)
        
        assert tracker.citations[0].line_number == 0
