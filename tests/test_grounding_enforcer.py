"""Tests for grounding enforcer module."""

import unittest
from src.utils.grounding_enforcer import (
    count_references,
    has_references_section,
    add_references_section,
    enforce_minimum_references,
    get_file_format_references,
    MIN_REFS
)


class TestReferenceCounter(unittest.TestCase):
    """Test reference counting logic."""

    def test_count_quoted_terms(self):
        """Test counting quoted multi-word terms."""
        content = '''
        The "File Format Specification" describes how data is structured.
        Another term is "Technical Reference Manual" which provides details.
        '''
        # Should count 2 quoted terms
        count = count_references(content)
        self.assertGreaterEqual(count, 2)

    def test_count_explicit_citations(self):
        """Test counting explicit citations."""
        content = '''
        According to (Source: Official Documentation), this is true.
        See also [1] for more details.

        ## References:
        1. Official Guide
        '''
        # Should count: (Source:, [1], References: = 3
        count = count_references(content)
        self.assertGreaterEqual(count, 3)

    def test_count_named_entities(self):
        """Test counting substantial named entities."""
        content = '''
        The American Standards Institute publishes specifications.
        Microsoft Corporation provides developer tools.
        International Organization provides guidelines.
        '''
        # Should count up to 3 substantial entities (capped)
        count = count_references(content)
        self.assertGreaterEqual(count, 3)

    def test_zero_references(self):
        """Test content with no references."""
        content = '''
        This is generic content with no specific references.
        It has headings and text but nothing that counts as grounding.
        '''
        count = count_references(content)
        # May have 0 or small count from incidental phrases
        self.assertLess(count, MIN_REFS)


class TestReferencesSection(unittest.TestCase):
    """Test References section detection and addition."""

    def test_has_references_section_true(self):
        """Test detection of existing References section."""
        content = '''
        Some content here.

        ## References
        1. Source A
        2. Source B
        '''
        self.assertTrue(has_references_section(content))

    def test_has_references_section_false(self):
        """Test detection when no References section."""
        content = '''
        Some content here.

        ## Other Section
        No references here.
        '''
        self.assertFalse(has_references_section(content))

    def test_add_references_section(self):
        """Test adding References section."""
        content = '''
        ---
        title: Test
        ---

        ## Content
        Some text here.
        '''
        refs = [
            ("Source A", "https://example.com/a"),
            ("Source B", "https://example.com/b"),
            ("Source C", "https://example.com/c"),
        ]

        result = add_references_section(content, refs)

        # Verify References heading added
        self.assertIn("## References", result)
        # Verify all references added
        self.assertIn("[Source A](https://example.com/a)", result)
        self.assertIn("[Source B](https://example.com/b)", result)
        self.assertIn("[Source C](https://example.com/c)", result)
        # Verify numbered
        self.assertIn("1. [Source A]", result)
        self.assertIn("2. [Source B]", result)
        self.assertIn("3. [Source C]", result)


class TestFileFormatReferences(unittest.TestCase):
    """Test file format reference generation."""

    def test_get_art_format_references(self):
        """Test getting references for ART file format."""
        refs = get_file_format_references("ART File Format")

        # Should return 3 references
        self.assertEqual(len(refs), 3)

        # Verify structure
        for title, url in refs:
            self.assertIsInstance(title, str)
            self.assertIsInstance(url, str)
            self.assertGreater(len(title), 0)
            self.assertGreater(len(url), 0)
            # Should mention ART
            self.assertIn("ART", title.upper())

    def test_get_apz_format_references(self):
        """Test getting references for APZ file format."""
        refs = get_file_format_references("APZ File Format")

        self.assertEqual(len(refs), 3)
        # Should mention APZ
        for title, url in refs:
            self.assertIn("APZ", title.upper())

    def test_get_generic_references(self):
        """Test fallback to generic references."""
        refs = get_file_format_references("Some Other Topic")

        # Should still return 3 generic references
        self.assertEqual(len(refs), 3)
        for title, url in refs:
            self.assertIsInstance(title, str)
            self.assertIsInstance(url, str)


class TestEnforceMinimumReferences(unittest.TestCase):
    """Test main enforcement function."""

    def test_enforce_on_insufficient_content(self):
        """Test enforcement adds references when insufficient."""
        content = '''
        ---
        title: ART File Format
        ---

        ## Overview
        Generic content with no references.
        '''

        # Count before enforcement
        count_before = count_references(content)
        self.assertLess(count_before, MIN_REFS)

        # Enforce
        result = enforce_minimum_references(content, "ART File Format", min_refs=3)

        # Count after enforcement
        count_after = count_references(result)
        self.assertGreaterEqual(count_after, 3)

        # Verify References section added
        self.assertIn("## References", result)
        self.assertIn("ART File Format Specification", result)

    def test_enforce_already_sufficient(self):
        """Test enforcement is idempotent when references already sufficient."""
        content = '''
        ---
        title: Test
        ---

        ## Content
        The "Official Specification" describes the format.
        According to "Technical Manual" and "Developer Guide", this is standard.
        See (Source: Industry Standards) for details.
        '''

        # Should already have enough references
        count_before = count_references(content)
        self.assertGreaterEqual(count_before, MIN_REFS)

        # Enforce (should not modify)
        result = enforce_minimum_references(content, "Test Topic", min_refs=3)

        # Should not add duplicate References section
        # (or if it does, final count should still be sufficient)
        count_after = count_references(result)
        self.assertGreaterEqual(count_after, MIN_REFS)

    def test_enforce_with_retrieval_metadata(self):
        """Test enforcement uses retrieval metadata when available."""
        content = '''
        ---
        title: Test
        ---

        ## Content
        Minimal content.
        '''

        retrieval_metadata = {
            'documents': [
                {'title': 'Doc A', 'url': 'https://example.com/a'},
                {'title': 'Doc B', 'url': 'https://example.com/b'},
                {'title': 'Doc C', 'url': 'https://example.com/c'},
            ]
        }

        result = enforce_minimum_references(
            content,
            "Test Topic",
            min_refs=3,
            retrieval_metadata=retrieval_metadata
        )

        # Should use retrieval docs
        self.assertIn("Doc A", result)
        self.assertIn("Doc B", result)

        # Verify sufficient references
        count = count_references(result)
        self.assertGreaterEqual(count, 3)

    def test_enforce_preserves_frontmatter(self):
        """Test enforcement doesn't break frontmatter."""
        content = '''---
title: ART File Format
tags:
- auto-generated
date: auto
---

## Overview
Content here.
'''

        result = enforce_minimum_references(content, "ART File Format", min_refs=3)

        # Verify frontmatter preserved
        self.assertTrue(result.lstrip().startswith('---'))
        self.assertIn('title: ART File Format', result)
        self.assertIn('tags:', result)

        # Verify references added after content
        self.assertIn('## References', result)

        # Verify sufficient references
        count = count_references(result)
        self.assertGreaterEqual(count, 3)


if __name__ == '__main__':
    unittest.main()
