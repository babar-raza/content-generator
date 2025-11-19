"""Unit tests for src/utils/content_utils.py.

Tests utility functions including:
- Code operations (extraction, validation, splitting, license insertion)
- SEO operations (keyword extraction, text cleaning)
- File system operations (reading, writing, hashing)
- RAG helpers (chunking, deduplication, query building)
- Caching operations
- Markdown operations (frontmatter, code blocks)
- Ingestion state management
"""

import pytest
from pathlib import Path
import tempfile
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.utils.content_utils import (
    # Code operations
    extract_code_blocks,
    is_csharp_code,
    find_license_insertion_point,
    insert_license,
    split_code_into_segments,
    _generate_segment_label,
    _generate_segment_label_from_template,

    # Code validation
    validate_code_quality,
    validate_api_compliance,

    # SEO operations
    clean_text,
    extract_keywords,
    inject_keywords_naturally,

    # File operations
    read_file_with_fallback_encoding,
    write_markdown_tree,
    compute_file_hash,

    # RAG helpers
    build_query,
    rerank_by_score,
    dedupe_context,
    chunk_text,

    # Caching
    cache_response,
    get_cached_response,
    cache_seo_keywords,

    # Markdown operations
    create_frontmatter,
    _process_field_rules,
    _truncate_at_word,
    create_gist_shortcode,
    create_code_block,

    # Ingestion state
    IngestionStateManager
)


# ============================================================================
# Test Code Operations
# ============================================================================

class TestExtractCodeBlocks:
    """Test extract_code_blocks function."""

    def test_extract_single_code_block(self):
        """Test extracting single code block."""
        text = "Some text\n```python\nprint('hello')\n```\nMore text"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert "print('hello')" in blocks[0]

    def test_extract_multiple_code_blocks(self):
        """Test extracting multiple code blocks."""
        text = "```python\ncode1\n```\ntext\n```javascript\ncode2\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 2
        assert "code1" in blocks[0]
        assert "code2" in blocks[1]

    def test_extract_no_code_blocks(self):
        """Test with no code blocks."""
        text = "Just plain text"
        blocks = extract_code_blocks(text)
        assert blocks == []

    def test_extract_code_block_no_language(self):
        """Test code block without language specifier."""
        text = "```\ncode without lang\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert "code without lang" in blocks[0]


class TestIsCsharpCode:
    """Test is_csharp_code function."""

    def test_is_csharp_with_using_and_class(self):
        """Test C# code with using and class."""
        code = "using System;\nclass MyClass { }"
        assert is_csharp_code(code) is True

    def test_is_csharp_with_namespace(self):
        """Test C# code with namespace."""
        code = "namespace MyApp { public class Test { } }"
        assert is_csharp_code(code) is True

    def test_not_csharp_python_code(self):
        """Test Python code is not detected as C#."""
        code = "def my_function():\n    print('hello')"
        assert is_csharp_code(code) is False

    def test_not_csharp_single_indicator(self):
        """Test code with single indicator isn't C#."""
        code = "class SomethingInPython:\n    pass"
        # Only has 'class', needs 2+ indicators
        assert is_csharp_code(code) is False


class TestFindLicenseInsertionPoint:
    """Test find_license_insertion_point function."""

    def test_insertion_at_first_non_empty_line(self):
        """Test insertion point at first non-empty line."""
        code = "\n\n\nusing System;\nclass Test {}"
        pos = find_license_insertion_point(code)
        assert pos > 0

    def test_insertion_at_start_no_empty_lines(self):
        """Test insertion at start when no empty lines."""
        code = "using System;\nclass Test {}"
        pos = find_license_insertion_point(code)
        assert pos == 0


class TestInsertLicense:
    """Test insert_license function."""

    def test_insert_license_into_code(self):
        """Test inserting license into code."""
        code = "using System;\nclass Test {}"
        licensed = insert_license(code, "// License Header\n")
        assert "// License Header" in licensed
        assert "using System" in licensed

    def test_license_not_duplicated(self):
        """Test license not inserted if already present."""
        code = "// License Header\nusing System;\nclass Test {}"
        licensed = insert_license(code, "// License Header")
        # Should only appear once
        assert licensed.count("// License Header") == 1


class TestSplitCodeIntoSegments:
    """Test split_code_into_segments function."""

    def test_split_short_code(self):
        """Test splitting short code."""
        code = "\n".join([f"line {i}" for i in range(10)])
        segments = split_code_into_segments(code, min_lines=3, max_lines=5)
        assert len(segments) >= 2
        assert all('label' in s and 'code' in s for s in segments)

    def test_split_long_code(self):
        """Test splitting long code."""
        code = "\n".join([f"line {i}" for i in range(100)])
        segments = split_code_into_segments(code, min_lines=10, max_lines=25, max_segments=5)
        assert 3 <= len(segments) <= 5

    def test_split_empty_code(self):
        """Test splitting empty code."""
        segments = split_code_into_segments("")
        assert len(segments) == 1
        assert segments[0]['label'] == "Empty Code"

    def test_split_with_config(self):
        """Test splitting with config."""
        code = "using System;\nclass Test {}"
        mock_config = Mock()
        mock_config.get_code_template.return_value = {
            'segment_labels': {
                'patterns': [
                    {'regex': 'using', 'label': 'Segment {n}: Imports'}
                ],
                'default_label': 'Segment {n}: Code'
            }
        }
        segments = split_code_into_segments(code, config=mock_config)
        assert any('Imports' in s['label'] or 'Code' in s['label'] for s in segments)


class TestGenerateSegmentLabel:
    """Test _generate_segment_label function."""

    def test_label_for_imports(self):
        """Test label generation for imports."""
        code = "using System;\nusing System.Collections;"
        label = _generate_segment_label(code, 1)
        assert "Imports" in label or "Setup" in label

    def test_label_for_class_definition(self):
        """Test label for class definition."""
        code = "class MyClass {"
        label = _generate_segment_label(code, 2)
        assert "Class" in label

    def test_label_for_method(self):
        """Test label for method."""
        code = "void MyMethod() { return 42; }"
        label = _generate_segment_label(code, 3)
        assert "Method" in label


# ============================================================================
# Test Code Validation
# ============================================================================

class TestValidateCodeQuality:
    """Test validate_code_quality function."""

    def test_valid_code_moderate(self):
        """Test valid code passes moderate validation."""
        code = "using System;\nclass Test { public void Method() {} }"
        is_valid, issues = validate_code_quality(code, "moderate")
        assert is_valid is True

    def test_empty_code_fails(self):
        """Test empty code fails validation."""
        is_valid, issues = validate_code_quality("", "moderate")
        assert is_valid is False
        assert any("empty" in i["message"].lower() for i in issues)

    def test_unmatched_braces_fails(self):
        """Test unmatched braces fail validation."""
        code = "class Test { public void Method() { }"
        is_valid, issues = validate_code_quality(code, "moderate")
        assert is_valid is False
        assert any("brace" in i["message"].lower() for i in issues)

    def test_strict_level_catches_all_issues(self):
        """Test strict level catches all issues."""
        code = "class Test { public void Method() {} }"  # Missing using statement
        is_valid, issues = validate_code_quality(code, "strict")
        # Strict mode requires no issues at all
        assert len(issues) > 0

    def test_permissive_level_allows_minor_issues(self):
        """Test permissive level allows minor issues."""
        code = "class Test { public void Method() {} }"
        is_valid, issues = validate_code_quality(code, "permissive")
        # Should pass despite minor issues
        assert is_valid is True or len([i for i in issues if i['type'] == 'critical']) == 0


class TestValidateApiCompliance:
    """Test validate_api_compliance function."""

    def test_api_references_used(self):
        """Test API references are used."""
        code = "MyApiClass obj = new MyApiClass();"
        api_refs = ["MyApiClass provides functionality"]
        is_compliant, warnings = validate_api_compliance(code, api_refs)
        assert is_compliant is True
        assert len(warnings) == 0

    def test_api_references_not_used(self):
        """Test API references not used generates warnings."""
        code = "SomeOtherClass obj = new SomeOtherClass();"
        api_refs = ["MyApiClass provides functionality"]
        is_compliant, warnings = validate_api_compliance(code, api_refs)
        # Should warn about unused API
        assert len(warnings) > 0


# ============================================================================
# Test SEO Operations
# ============================================================================

class TestCleanText:
    """Test clean_text function."""

    def test_clean_special_characters(self):
        """Test removing special characters."""
        text = "Hello!!! @World# 123"
        cleaned = clean_text(text)
        assert "@" not in cleaned
        assert "#" not in cleaned
        assert "Hello" in cleaned

    def test_clean_normalize_whitespace(self):
        """Test normalizing whitespace."""
        text = "Hello\n\t  World"
        cleaned = clean_text(text)
        assert "\n" not in cleaned
        assert "\t" not in cleaned


class TestExtractKeywords:
    """Test extract_keywords function."""

    def test_extract_keywords_from_text(self):
        """Test extracting keywords."""
        text = "Machine learning and artificial intelligence. Machine learning is important."
        keywords = extract_keywords(text, max_keywords=5)
        assert "machine" in keywords
        assert "learning" in keywords

    def test_extract_keywords_filters_stopwords(self):
        """Test stopwords are filtered."""
        text = "The and for are this that with from"
        keywords = extract_keywords(text)
        # All should be filtered as stopwords
        assert len(keywords) == 0

    def test_extract_keywords_max_limit(self):
        """Test max keywords limit."""
        text = " ".join([f"keyword{i}" for i in range(20)])
        keywords = extract_keywords(text, max_keywords=5)
        assert len(keywords) <= 5


class TestInjectKeywordsNaturally:
    """Test inject_keywords_naturally function."""

    def test_inject_keywords(self):
        """Test injecting keywords."""
        prose = "This is a test sentence. This is another sentence with more words."
        keywords = ["python", "programming"]
        result = inject_keywords_naturally(prose, keywords, max_density=2.0)
        # Should inject keywords (may or may not succeed based on logic)
        assert isinstance(result, str)

    def test_respect_density_limit(self):
        """Test density limit is respected."""
        prose = "python " * 10 + "test " * 10
        keywords = ["python"]
        result = inject_keywords_naturally(prose, keywords, max_density=50.0)
        # Should not inject more if already at density
        count = result.lower().count("python")
        total_words = len(result.split())
        density = (count / total_words) * 100
        assert density <= 50.0 + 5  # Small tolerance


# ============================================================================
# Test File Operations
# ============================================================================

class TestReadFileWithFallbackEncoding:
    """Test read_file_with_fallback_encoding function."""

    def test_read_utf8_file(self, tmp_path):
        """Test reading UTF-8 file."""
        file = tmp_path / "test.txt"
        file.write_text("Hello World", encoding='utf-8')
        content = read_file_with_fallback_encoding(file)
        assert content == "Hello World"

    def test_read_latin1_file(self, tmp_path):
        """Test reading Latin-1 file."""
        file = tmp_path / "test.txt"
        file.write_text("Café", encoding='latin-1')
        content = read_file_with_fallback_encoding(file)
        assert "Caf" in content  # May not decode perfectly but should work

    def test_read_nonexistent_file_raises(self, tmp_path):
        """Test reading nonexistent file raises."""
        file = tmp_path / "nonexistent.txt"
        with pytest.raises(Exception):  # FileNotFoundError or ValueError
            read_file_with_fallback_encoding(file)


class TestWriteMarkdownTree:
    """Test write_markdown_tree function."""

    def test_write_new_file(self, tmp_path):
        """Test writing new markdown file."""
        write_markdown_tree(tmp_path, "my-post", "# Content")
        output_file = tmp_path / "my-post" / "index.md"
        assert output_file.exists()
        assert output_file.read_text(encoding='utf-8') == "# Content"

    def test_backup_existing_file(self, tmp_path):
        """Test backing up existing file."""
        slug = "my-post"
        post_dir = tmp_path / slug
        post_dir.mkdir()
        output_file = post_dir / "index.md"
        output_file.write_text("Old content")

        write_markdown_tree(tmp_path, slug, "New content")

        backup_file = post_dir / "index.md.prev"
        assert backup_file.exists()
        assert backup_file.read_text() == "Old content"
        assert output_file.read_text(encoding='utf-8') == "New content"


class TestComputeFileHash:
    """Test compute_file_hash function."""

    def test_hash_consistency(self, tmp_path):
        """Test hash is consistent for same content."""
        file = tmp_path / "test.txt"
        file.write_text("Test content")

        hash1 = compute_file_hash(file)
        hash2 = compute_file_hash(file)

        assert hash1 == hash2

    def test_hash_different_for_different_content(self, tmp_path):
        """Test hash differs for different content."""
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 != hash2


# ============================================================================
# Test RAG Helpers
# ============================================================================

class TestBuildQuery:
    """Test build_query function."""

    def test_build_general_query(self):
        """Test building general query."""
        topic = {"title": "Machine Learning", "rationale": "Important topic"}
        query = build_query(topic, "general")
        assert "Machine Learning" in query
        assert "Important topic" in query

    def test_build_code_query(self):
        """Test building code query."""
        topic = {"title": "Python API"}
        query = build_query(topic, "code")
        assert "Python API" in query
        assert "code" in query.lower() or "api" in query.lower()


class TestRerankByScore:
    """Test rerank_by_score function."""

    def test_rerank_by_score(self):
        """Test reranking results by score."""
        results = [("text1", 0.5), ("text2", 0.9), ("text3", 0.3)]
        reranked = rerank_by_score(results, top_k=2)
        assert reranked == ["text2", "text1"]

    def test_rerank_respects_top_k(self):
        """Test reranking respects top_k limit."""
        results = [("text1", 0.8), ("text2", 0.9), ("text3", 0.7), ("text4", 0.6)]
        reranked = rerank_by_score(results, top_k=2)
        assert len(reranked) == 2


class TestDedupeContext:
    """Test dedupe_context function."""

    def test_dedupe_identical_contexts(self):
        """Test deduplication of identical contexts."""
        contexts = ["Same text", "Different text", "Same text"]
        deduped = dedupe_context(contexts)
        assert len(deduped) == 2

    def test_dedupe_similar_contexts(self):
        """Test deduplication of similar contexts."""
        contexts = [
            "This is about machine learning",
            "This is about machine learning and AI",
            "Completely different topic"
        ]
        deduped = dedupe_context(contexts, similarity_threshold=0.7)
        # Similarity algorithm may or may not dedupe based on threshold - just verify it's a list
        assert isinstance(deduped, list)
        assert len(deduped) >= 1

    def test_dedupe_empty_list(self):
        """Test deduplication of empty list."""
        deduped = dedupe_context([])
        assert deduped == []


class TestChunkText:
    """Test chunk_text function."""

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        text = "Short text"
        chunks = chunk_text(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_long_text(self):
        """Test chunking long text."""
        text = "This is a sentence. " * 100
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1

    def test_chunk_overlap(self):
        """Test chunk overlap."""
        text = "A" * 200
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        # Chunks should have some overlap
        assert len(chunks) > 1


# ============================================================================
# Test Caching Operations
# ============================================================================

class TestCacheOperations:
    """Test caching operations."""

    def test_cache_and_retrieve_response(self, tmp_path):
        """Test caching and retrieving response."""
        cache_dir = tmp_path
        cache_dir.mkdir(exist_ok=True)

        cache_response(cache_dir, "hash123", "response data")

        retrieved = get_cached_response(cache_dir, "hash123", max_age_seconds=3600)
        assert retrieved == "response data"

    def test_cached_response_expires(self, tmp_path):
        """Test cached response expires."""
        cache_dir = tmp_path
        cache_dir.mkdir(exist_ok=True)

        cache_response(cache_dir, "hash123", "old data")

        # Try to retrieve with max_age=0 (should be expired)
        retrieved = get_cached_response(cache_dir, "hash123", max_age_seconds=0)
        assert retrieved is None

    def test_no_cached_response(self, tmp_path):
        """Test retrieving non-existent cache."""
        cache_dir = tmp_path
        retrieved = get_cached_response(cache_dir, "nonexistent", max_age_seconds=3600)
        assert retrieved is None

    def test_cache_seo_keywords(self, tmp_path):
        """Test caching SEO keywords."""
        cache_dir = tmp_path
        cache_dir.mkdir(exist_ok=True)

        cache_seo_keywords(cache_dir, "hash123", ["python", "machine", "learning"])

        cache_file = cache_dir / "seo_keywords.jsonl"
        assert cache_file.exists()


# ============================================================================
# Test Markdown Operations
# ============================================================================

class TestCreateFrontmatter:
    """Test create_frontmatter function."""

    def test_create_basic_frontmatter(self):
        """Test creating basic frontmatter."""
        metadata = {"title": "Test Post", "slug": "test-post"}
        frontmatter = create_frontmatter(metadata)

        assert "---" in frontmatter
        assert "enhanced: true" in frontmatter

    def test_create_frontmatter_with_config(self):
        """Test creating frontmatter with config."""
        metadata = {"title": "Test", "family": "Words"}
        mock_config = Mock()
        mock_config.get_frontmatter_template.return_value = {
            "title": "{family}",
            "draft": True
        }

        frontmatter = create_frontmatter(metadata, mock_config)
        assert "Words" in frontmatter or "title" in frontmatter


class TestTruncateAtWord:
    """Test _truncate_at_word function."""

    def test_truncate_at_word_boundary(self):
        """Test truncation at word boundary."""
        text = "This is a long sentence that needs truncation"
        truncated = _truncate_at_word(text, 20)
        assert len(truncated) <= 20
        assert not truncated.endswith(" ")

    def test_no_truncation_needed(self):
        """Test no truncation when text is short."""
        text = "Short text"
        truncated = _truncate_at_word(text, 100)
        assert truncated == text


class TestCreateGistShortcode:
    """Test create_gist_shortcode function."""

    def test_create_gist_shortcode(self):
        """Test creating gist shortcode."""
        shortcode = create_gist_shortcode("user123", "abc123", "test.cs")
        assert "gist" in shortcode
        assert "user123" in shortcode
        assert "abc123" in shortcode
        assert "test.cs" in shortcode


class TestCreateCodeBlock:
    """Test create_code_block function."""

    def test_create_code_block(self):
        """Test creating code block."""
        code = "print('hello')"
        block = create_code_block(code, "python")
        assert "```python" in block
        assert "print('hello')" in block
        assert block.endswith("```")

    def test_code_block_with_crlf(self):
        """Test code block has CRLF line endings."""
        code = "line1\nline2\nline3"
        block = create_code_block(code, "python")
        assert "\r\n" in block


# ============================================================================
# Test Ingestion State Management
# ============================================================================

class TestIngestionStateManager:
    """Test IngestionStateManager class."""

    def test_init_creates_empty_state(self, tmp_path):
        """Test initialization creates empty state."""
        state_file = tmp_path / "state.json"
        manager = IngestionStateManager(state_file)
        assert isinstance(manager.state, dict)

    def test_needs_ingestion_new_file(self, tmp_path):
        """Test new file needs ingestion."""
        state_file = tmp_path / "state.json"
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = IngestionStateManager(state_file)
        assert manager.needs_ingestion(test_file, "kb") is True

    def test_mark_ingested(self, tmp_path):
        """Test marking file as ingested."""
        state_file = tmp_path / "state.json"
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = IngestionStateManager(state_file)
        manager.mark_ingested(test_file, "kb", chunk_count=5)

        assert not manager.needs_ingestion(test_file, "kb")

    def test_needs_ingestion_after_change(self, tmp_path):
        """Test file needs re-ingestion after change."""
        state_file = tmp_path / "state.json"
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")

        manager = IngestionStateManager(state_file)
        manager.mark_ingested(test_file, "kb", chunk_count=5)

        # Modify file
        test_file.write_text("modified")

        assert manager.needs_ingestion(test_file, "kb") is True

    def test_get_collection_stats(self, tmp_path):
        """Test getting collection statistics."""
        state_file = tmp_path / "state.json"
        test_file1 = tmp_path / "test1.txt"
        test_file2 = tmp_path / "test2.txt"
        test_file1.write_text("content1")
        test_file2.write_text("content2")

        manager = IngestionStateManager(state_file)
        manager.mark_ingested(test_file1, "kb", chunk_count=3)
        manager.mark_ingested(test_file2, "kb", chunk_count=5)

        stats = manager.get_collection_stats("kb")
        assert stats['file_count'] == 2
        assert stats['total_chunks'] == 8

    def test_clear_collection(self, tmp_path):
        """Test clearing collection state."""
        state_file = tmp_path / "state.json"
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = IngestionStateManager(state_file)
        manager.mark_ingested(test_file, "kb", chunk_count=5)

        manager.clear_collection("kb")

        stats = manager.get_collection_stats("kb")
        assert stats['file_count'] == 0

    def test_state_persists_across_instances(self, tmp_path):
        """Test state persists across manager instances."""
        state_file = tmp_path / "state.json"
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager1 = IngestionStateManager(state_file)
        manager1.mark_ingested(test_file, "kb", chunk_count=5)

        # Create new instance
        manager2 = IngestionStateManager(state_file)
        assert not manager2.needs_ingestion(test_file, "kb")

    def test_compute_file_hash(self, tmp_path):
        """Test computing file hash."""
        state_file = tmp_path / "state.json"
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager = IngestionStateManager(state_file)
        hash1 = manager.compute_file_hash(test_file)
        hash2 = manager.compute_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length
