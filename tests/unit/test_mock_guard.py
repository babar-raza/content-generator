"""Tests for mock_guard module."""

import pytest
from src.utils.mock_guard import is_mock_like, annotate_status, _flatten_strings


class TestFlattenStrings:
    """Tests for _flatten_strings helper function."""
    
    def test_flatten_string(self):
        """Test flattening a simple string."""
        acc = []
        _flatten_strings("hello", acc)
        assert acc == ["hello"]
    
    def test_flatten_list_of_strings(self):
        """Test flattening list of strings."""
        acc = []
        _flatten_strings(["one", "two", "three"], acc)
        assert acc == ["one", "two", "three"]
    
    def test_flatten_dict(self):
        """Test flattening dictionary."""
        acc = []
        _flatten_strings({"key1": "value1", "key2": "value2"}, acc)
        assert "key1" in acc
        assert "key2" in acc
        assert "value1" in acc
        assert "value2" in acc
    
    def test_flatten_nested_structure(self):
        """Test flattening nested structure."""
        acc = []
        obj = {
            "title": "Test",
            "items": ["item1", "item2"],
            "nested": {"sub": "value"}
        }
        _flatten_strings(obj, acc)
        
        assert "title" in acc
        assert "Test" in acc
        assert "item1" in acc
        assert "item2" in acc
        assert "sub" in acc
        assert "value" in acc
    
    def test_flatten_none(self):
        """Test flattening None."""
        acc = []
        _flatten_strings(None, acc)
        assert acc == []
    
    def test_flatten_tuple(self):
        """Test flattening tuple."""
        acc = []
        _flatten_strings(("a", "b", "c"), acc)
        assert acc == ["a", "b", "c"]
    
    def test_flatten_set(self):
        """Test flattening set."""
        acc = []
        _flatten_strings({"a", "b", "c"}, acc)
        assert len(acc) == 3
        assert all(x in acc for x in ["a", "b", "c"])
    
    def test_flatten_mixed_types(self):
        """Test flattening with mixed types."""
        acc = []
        obj = {
            "string": "text",
            "number": 123,
            "list": ["a", 456, "b"],
            "none": None
        }
        _flatten_strings(obj, acc)
        
        assert "string" in acc
        assert "text" in acc
        assert "a" in acc
        assert "b" in acc


class TestIsMockLike:
    """Tests for is_mock_like function."""
    
    def test_lorem_ipsum_detected(self):
        """Test detection of lorem ipsum."""
        is_mock, hits = is_mock_like("This is lorem ipsum text")
        assert is_mock is True
        assert any("lorem ipsum" in h.lower() for h in hits)
    
    def test_todo_detected(self):
        """Test detection of TODO."""
        is_mock, hits = is_mock_like("TODO: implement this")
        assert is_mock is True
        assert any("todo" in h.lower() for h in hits)
    
    def test_tbd_detected(self):
        """Test detection of TBD."""
        is_mock, hits = is_mock_like("This is TBD")
        assert is_mock is True
        assert any("tbd" in h.lower() for h in hits)
    
    def test_placeholder_detected(self):
        """Test detection of placeholder."""
        is_mock, hits = is_mock_like("This is a placeholder text")
        assert is_mock is True
        assert any("placeholder" in h.lower() for h in hits)
    
    def test_sample_detected(self):
        """Test detection of sample."""
        is_mock, hits = is_mock_like("Sample content here")
        assert is_mock is True
        assert any("sample" in h.lower() for h in hits)
    
    def test_dummy_detected(self):
        """Test detection of dummy."""
        is_mock, hits = is_mock_like("This is dummy data")
        assert is_mock is True
        assert any("dummy" in h.lower() for h in hits)
    
    def test_mock_detected(self):
        """Test detection of mock."""
        is_mock, hits = is_mock_like("Mock response")
        assert is_mock is True
        assert any("mock" in h.lower() for h in hits)
    
    def test_your_title_detected(self):
        """Test detection of Your Title."""
        is_mock, hits = is_mock_like("Your Title Here")
        assert is_mock is True
    
    def test_brand_name_detected(self):
        """Test detection of Brand Name."""
        is_mock, hits = is_mock_like("Brand Name placeholder")
        assert is_mock is True
    
    def test_coming_soon_detected(self):
        """Test detection of coming soon."""
        is_mock, hits = is_mock_like("Content coming soon")
        assert is_mock is True
    
    def test_replace_this_detected(self):
        """Test detection of replace this."""
        is_mock, hits = is_mock_like("Please replace this text")
        assert is_mock is True
    
    def test_auto_generated_detected(self):
        """Test detection of auto-generated."""
        is_mock, hits = is_mock_like("This is auto-generated content")
        assert is_mock is True
    
    def test_clean_text_not_mock(self):
        """Test that clean text is not detected as mock."""
        is_mock, hits = is_mock_like("This is real production content")
        assert is_mock is False
        assert hits == []
    
    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        test_cases = [
            "TODO",
            "todo",
            "ToDo",
            "tOdO"
        ]
        
        for text in test_cases:
            is_mock, hits = is_mock_like(text)
            assert is_mock is True
    
    def test_dict_input(self):
        """Test with dictionary input."""
        obj = {
            "title": "TODO: Add title",
            "content": "Real content"
        }
        
        is_mock, hits = is_mock_like(obj)
        assert is_mock is True
    
    def test_list_input(self):
        """Test with list input."""
        obj = ["Real text", "placeholder", "More text"]
        
        is_mock, hits = is_mock_like(obj)
        assert is_mock is True
    
    def test_nested_structure_detection(self):
        """Test detection in nested structures."""
        obj = {
            "data": {
                "items": ["item1", "TBD", "item3"]
            }
        }
        
        is_mock, hits = is_mock_like(obj)
        assert is_mock is True
    
    def test_multiple_matches(self):
        """Test with multiple placeholder patterns."""
        text = "TODO: This is a placeholder with lorem ipsum"
        
        is_mock, hits = is_mock_like(text)
        assert is_mock is True
        assert len(hits) >= 1  # Should find at least one pattern
    
    def test_empty_string(self):
        """Test with empty string."""
        is_mock, hits = is_mock_like("")
        assert is_mock is False
        assert hits == []
    
    def test_none_input(self):
        """Test with None input."""
        is_mock, hits = is_mock_like(None)
        assert is_mock is False
        assert hits == []


class TestAnnotateStatus:
    """Tests for annotate_status function."""
    
    def test_annotate_mock_content(self):
        """Test annotating mock content."""
        output = {"text": "TODO: implement this"}
        
        result = annotate_status(output)
        
        assert result["status"] == "mock"
        assert "mock_hits" in result
        assert len(result["mock_hits"]) > 0
    
    def test_annotate_clean_content(self):
        """Test annotating clean content."""
        output = {"text": "Real production content"}
        
        result = annotate_status(output)
        
        assert result["status"] == "ok"
        assert "mock_hits" not in result
    
    def test_preserves_original_data(self):
        """Test that original data is preserved."""
        output = {
            "title": "My Title",
            "content": "Real content",
            "metadata": {"author": "John"}
        }
        
        result = annotate_status(output)
        
        assert result["title"] == "My Title"
        assert result["content"] == "Real content"
        assert result["metadata"] == {"author": "John"}
    
    def test_does_not_overwrite_status(self):
        """Test that existing status is not overwritten."""
        output = {
            "text": "Real content",
            "status": "custom_status"
        }
        
        result = annotate_status(output)
        
        assert result["status"] == "custom_status"
    
    def test_mock_hits_sorted_and_unique(self):
        """Test that mock hits are sorted and unique."""
        output = {
            "text": "TODO TODO TBD TBD placeholder"
        }
        
        result = annotate_status(output)
        
        assert result["status"] == "mock"
        hits = result["mock_hits"]
        # Should be sorted
        assert hits == sorted(hits)
        # Should be unique
        assert len(hits) == len(set(hits))
    
    def test_returns_new_dict(self):
        """Test that function returns new dict, not modifying original."""
        output = {"text": "content"}
        
        result = annotate_status(output)
        
        assert result is not output
        assert "status" in result
        assert "status" not in output
    
    def test_empty_dict(self):
        """Test with empty dictionary."""
        output = {}
        
        result = annotate_status(output)
        
        assert result["status"] == "ok"
    
    def test_complex_nested_structure(self):
        """Test with complex nested structure."""
        output = {
            "sections": [
                {"title": "Real Title", "content": "Real content"},
                {"title": "TODO", "content": "placeholder"}
            ]
        }
        
        result = annotate_status(output)
        
        assert result["status"] == "mock"
        assert "mock_hits" in result
    
    def test_multiple_mock_patterns(self):
        """Test detection of multiple mock patterns."""
        output = {
            "title": "TODO",
            "description": "placeholder text",
            "content": "lorem ipsum"
        }
        
        result = annotate_status(output)
        
        assert result["status"] == "mock"
        assert len(result["mock_hits"]) >= 3
