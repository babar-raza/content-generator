"""Tests for uploaded files support in input resolver."""

import pytest
from pathlib import Path
import tempfile
from src.engine.input_resolver import InputResolver, ContextSet


class TestUploadedFilesResolver:
    """Test uploaded files resolution."""
    
    def test_empty_uploads_dict(self):
        """Test empty uploads dict fails."""
        resolver = InputResolver()
        
        with pytest.raises(Exception):
            resolver.resolve({})
    
    def test_uploaded_files_single_category(self):
        """Test uploaded files from single category."""
        resolver = InputResolver()
        
        # Create temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_file = Path(tmpdir) / "test.md"
            kb_file.write_text("# Test KB\nContent here")
            
            uploads = {
                'kb': [str(kb_file)],
                'docs': [],
                'blog': []
            }
            
            result = resolver.resolve(uploads)
            
            assert result.primary_content
            assert "[KB]" in result.primary_content
            assert "Test KB" in result.primary_content
            assert result.metadata['input_mode'] == 'uploaded_files'
            assert result.metadata['file_count'] == 1
            assert 'kb' in result.metadata['categories']
    
    def test_uploaded_files_multiple_categories(self):
        """Test uploaded files from multiple categories."""
        resolver = InputResolver()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_file = Path(tmpdir) / "kb.md"
            kb_file.write_text("# KB Content")
            
            docs_file = Path(tmpdir) / "docs.md"
            docs_file.write_text("# Docs Content")
            
            blog_file = Path(tmpdir) / "blog.md"
            blog_file.write_text("# Blog Content")
            
            uploads = {
                'kb': [str(kb_file)],
                'docs': [str(docs_file)],
                'blog': [str(blog_file)],
                'api': [],
                'tutorial': []
            }
            
            result = resolver.resolve(uploads)
            
            assert "[KB]" in result.primary_content
            assert "[DOCS]" in result.primary_content
            assert "[BLOG]" in result.primary_content
            assert result.metadata['file_count'] == 3
            assert len(result.metadata['categories']) == 3
    
    def test_uploaded_files_multiple_files_per_category(self):
        """Test multiple files in one category."""
        resolver = InputResolver()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            kb1 = Path(tmpdir) / "kb1.md"
            kb1.write_text("# KB 1")
            
            kb2 = Path(tmpdir) / "kb2.md"
            kb2.write_text("# KB 2")
            
            uploads = {
                'kb': [str(kb1), str(kb2)],
                'docs': []
            }
            
            result = resolver.resolve(uploads)
            
            assert result.metadata['file_count'] == 2
            assert "KB 1" in result.primary_content
            assert "KB 2" in result.primary_content
    
    def test_uploaded_files_nonexistent_file_skipped(self):
        """Test nonexistent files are skipped gracefully."""
        resolver = InputResolver()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            good_file = Path(tmpdir) / "good.md"
            good_file.write_text("# Good")
            
            uploads = {
                'kb': [str(good_file), "/nonexistent/path.md"],
                'docs': []
            }
            
            result = resolver.resolve(uploads)
            
            assert result.metadata['file_count'] == 1
            assert "Good" in result.primary_content
