"""Unit tests for src/utils/path_utils.py.

Tests path utilities including:
- Path traversal prevention
- URL-safe slug generation
- Safe directory creation
- Safe filename generation
"""

import pytest
from pathlib import Path
import tempfile
import os

from src.utils.path_utils import (
    safe_path,
    generate_slug,
    ensure_directory,
    get_safe_filename,
    is_safe_path,
    normalize_path
)


# ============================================================================
# Test safe_path
# ============================================================================

class TestSafePath:
    """Test safe_path function for path traversal prevention."""

    def test_safe_path_simple_file(self, tmp_path):
        """Test safe path with simple filename."""
        result = safe_path(tmp_path, "file.txt")
        assert result == tmp_path / "file.txt"

    def test_safe_path_subdirectory(self, tmp_path):
        """Test safe path with subdirectory."""
        result = safe_path(tmp_path, "subdir/file.txt")
        assert result == tmp_path / "subdir" / "file.txt"

    def test_safe_path_prevents_traversal(self, tmp_path):
        """Test path traversal is prevented."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            safe_path(tmp_path, "../etc/passwd")

    def test_safe_path_prevents_double_dot(self, tmp_path):
        """Test double-dot traversal is prevented."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            safe_path(tmp_path, "../../secret.txt")

    def test_safe_path_handles_current_dir(self, tmp_path):
        """Test handling of current directory reference."""
        result = safe_path(tmp_path, "./file.txt")
        assert result == tmp_path / "file.txt"

    def test_safe_path_with_string_inputs(self, tmp_path):
        """Test safe_path with string inputs."""
        result = safe_path(str(tmp_path), "file.txt")
        assert result == tmp_path / "file.txt"

    def test_safe_path_nested_subdirectories(self, tmp_path):
        """Test safe path with nested subdirectories."""
        result = safe_path(tmp_path, "a/b/c/file.txt")
        assert result == tmp_path / "a" / "b" / "c" / "file.txt"


# ============================================================================
# Test generate_slug
# ============================================================================

class TestGenerateSlug:
    """Test generate_slug function."""

    def test_generate_slug_simple(self):
        """Test simple slug generation."""
        assert generate_slug("Hello World") == "hello-world"

    def test_generate_slug_with_numbers(self):
        """Test slug with numbers."""
        assert generate_slug("Python 3.11") == "python-3-11"

    def test_generate_slug_removes_special_chars(self):
        """Test special characters are removed."""
        assert generate_slug("Hello, World! @#$") == "hello-world"

    def test_generate_slug_multiple_spaces(self):
        """Test multiple spaces become single hyphen."""
        assert generate_slug("Hello    World") == "hello-world"

    def test_generate_slug_leading_trailing_spaces(self):
        """Test leading/trailing spaces are removed."""
        assert generate_slug("  Hello World  ") == "hello-world"

    def test_generate_slug_consecutive_hyphens(self):
        """Test consecutive hyphens are collapsed."""
        assert generate_slug("Hello---World") == "hello-world"

    def test_generate_slug_max_length(self):
        """Test max_length parameter."""
        long_text = "This is a very long text that exceeds the maximum length"
        result = generate_slug(long_text, max_length=20)
        assert len(result) <= 20
        assert not result.endswith('-')

    def test_generate_slug_accented_characters(self):
        """Test accented characters are converted."""
        assert generate_slug("café") == "cafe"
        assert generate_slug("naïve") == "naive"
        assert generate_slug("Zürich") == "zurich"

    def test_generate_slug_empty_string(self):
        """Test empty string returns empty."""
        assert generate_slug("") == ""

    def test_generate_slug_only_special_chars(self):
        """Test string with only special characters."""
        assert generate_slug("@#$%^&*") == ""

    def test_generate_slug_german_characters(self):
        """Test German characters like ß."""
        assert generate_slug("Straße") == "strasse"

    def test_generate_slug_french_ligatures(self):
        """Test French ligatures like œ."""
        assert generate_slug("œuvre") == "oeuvre"

    def test_generate_slug_trim_at_word_boundary(self):
        """Test slug is trimmed at word boundary."""
        result = generate_slug("hello world amazing", max_length=12)
        # Should cut at word boundary, not mid-word
        assert result in ["hello-world", "hello"]


# ============================================================================
# Test ensure_directory
# ============================================================================

class TestEnsureDirectory:
    """Test ensure_directory function."""

    def test_ensure_directory_creates_new(self, tmp_path):
        """Test creating new directory."""
        new_dir = tmp_path / "new_directory"
        result = ensure_directory(new_dir)
        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_nested(self, tmp_path):
        """Test creating nested directories."""
        nested = tmp_path / "a" / "b" / "c"
        result = ensure_directory(nested)
        assert result == nested
        assert nested.exists()
        assert nested.is_dir()

    def test_ensure_directory_already_exists(self, tmp_path):
        """Test with directory that already exists."""
        existing = tmp_path / "existing"
        existing.mkdir()
        result = ensure_directory(existing)
        assert result == existing
        assert existing.is_dir()

    def test_ensure_directory_string_path(self, tmp_path):
        """Test with string path."""
        new_dir = tmp_path / "string_dir"
        result = ensure_directory(str(new_dir))
        assert result == new_dir
        assert new_dir.exists()

    def test_ensure_directory_with_file_conflict(self, tmp_path):
        """Test error when path exists as file."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(OSError, match="not a directory"):
            ensure_directory(file_path)


# ============================================================================
# Test get_safe_filename
# ============================================================================

class TestGetSafeFilename:
    """Test get_safe_filename function."""

    def test_get_safe_filename_simple(self):
        """Test simple filename."""
        assert get_safe_filename("file.txt") == "file.txt"

    def test_get_safe_filename_removes_slashes(self):
        """Test path separators are removed."""
        assert get_safe_filename("path/to/file.txt") == "path-to-file.txt"

    def test_get_safe_filename_removes_colons(self):
        """Test colons are removed (Windows)."""
        assert get_safe_filename("file:name.txt") == "file-name.txt"

    def test_get_safe_filename_removes_asterisks(self):
        """Test wildcards are removed."""
        assert get_safe_filename("file*.txt") == "file.txt"

    def test_get_safe_filename_removes_question_marks(self):
        """Test question marks are removed."""
        assert get_safe_filename("file?.txt") == "file.txt"

    def test_get_safe_filename_removes_quotes(self):
        """Test quotes are removed."""
        assert get_safe_filename('file"name.txt') == "file-name.txt"

    def test_get_safe_filename_removes_pipes(self):
        """Test pipe characters are removed."""
        assert get_safe_filename("file|name.txt") == "file-name.txt"

    def test_get_safe_filename_removes_angle_brackets(self):
        """Test angle brackets are removed."""
        assert get_safe_filename("file<name>.txt") == "file-name.txt"

    def test_get_safe_filename_max_length(self):
        """Test max_length parameter."""
        long_name = "a" * 300 + ".txt"
        result = get_safe_filename(long_name, max_length=50)
        assert len(result) <= 50

    def test_get_safe_filename_preserves_extension(self):
        """Test file extension is preserved."""
        result = get_safe_filename("very-long-filename-that-exceeds-limit.txt", max_length=20)
        assert result.endswith(".txt")

    def test_get_safe_filename_empty_string(self):
        """Test empty string returns unnamed."""
        assert get_safe_filename("") == "unnamed"

    def test_get_safe_filename_only_extension(self):
        """Test filename with only extension."""
        result = get_safe_filename(".txt")
        assert result == "unnamed.txt"

    def test_get_safe_filename_multiple_extensions(self):
        """Test filename with multiple dots."""
        result = get_safe_filename("file.tar.gz")
        assert result == "file.tar.gz"

    def test_get_safe_filename_no_extension(self):
        """Test filename without extension."""
        result = get_safe_filename("filename")
        assert result == "filename"

    def test_get_safe_filename_consecutive_hyphens(self):
        """Test consecutive hyphens are collapsed."""
        result = get_safe_filename("file---name.txt")
        assert result == "file-name.txt"


# ============================================================================
# Test is_safe_path
# ============================================================================

class TestIsSafePath:
    """Test is_safe_path function."""

    def test_is_safe_path_simple_file(self):
        """Test simple relative path is safe."""
        assert is_safe_path("file.txt") is True

    def test_is_safe_path_subdirectory(self):
        """Test path in subdirectory is safe."""
        assert is_safe_path("subdir/file.txt") is True

    def test_is_safe_path_absolute_unsafe(self):
        """Test absolute path is not safe."""
        assert is_safe_path("/etc/passwd") is False

    def test_is_safe_path_traversal_unsafe(self):
        """Test path traversal is not safe."""
        assert is_safe_path("../etc/passwd") is False

    def test_is_safe_path_double_dot_unsafe(self):
        """Test double-dot traversal is not safe."""
        assert is_safe_path("../../secret") is False

    def test_is_safe_path_with_allowed_extensions(self):
        """Test extension checking."""
        assert is_safe_path("file.txt", ['.txt', '.json']) is True
        assert is_safe_path("file.exe", ['.txt', '.json']) is False

    def test_is_safe_path_extension_case_insensitive(self):
        """Test extension check is case-insensitive."""
        assert is_safe_path("file.TXT", ['.txt']) is True
        assert is_safe_path("file.Txt", ['.txt']) is True

    def test_is_safe_path_no_extension_filter(self):
        """Test with no extension filter (all allowed)."""
        assert is_safe_path("file.exe", None) is True

    def test_is_safe_path_current_dir_reference(self):
        """Test current directory reference."""
        assert is_safe_path("./file.txt") is True


# ============================================================================
# Test normalize_path
# ============================================================================

class TestNormalizePath:
    """Test normalize_path function."""

    def test_normalize_path_removes_dots(self):
        """Test removes . components."""
        result = normalize_path("./file.txt")
        assert result == Path("file.txt")

    def test_normalize_path_resolves_double_dots(self):
        """Test resolves .. components."""
        result = normalize_path("dir/../file.txt")
        assert result == Path("file.txt")

    def test_normalize_path_multiple_components(self):
        """Test complex path normalization."""
        result = normalize_path("./a/b/../c/./d.txt")
        assert result == Path("a/c/d.txt")

    def test_normalize_path_with_string(self):
        """Test with string input."""
        result = normalize_path("./data/../files/report.txt")
        assert result == Path("files/report.txt")

    def test_normalize_path_absolute(self):
        """Test with absolute path."""
        if os.name == 'nt':
            result = normalize_path("C:/data/../files/report.txt")
            assert result == Path("C:/files/report.txt")
        else:
            result = normalize_path("/data/../files/report.txt")
            assert result == Path("/files/report.txt")

    def test_normalize_path_already_normal(self):
        """Test path that's already normalized."""
        result = normalize_path("data/files/report.txt")
        assert result == Path("data/files/report.txt")


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_safe_file_upload_scenario(self, tmp_path):
        """Test realistic file upload security scenario."""
        upload_dir = tmp_path / "uploads"
        ensure_directory(upload_dir)

        # Simulate user-provided filename
        user_filename = "../../../etc/passwd"
        safe_filename = get_safe_filename(user_filename)

        # Create safe path
        safe_file_path = safe_path(upload_dir, safe_filename)

        # Verify it's within upload_dir
        assert safe_file_path.is_relative_to(upload_dir)

    def test_slug_and_directory_creation(self, tmp_path):
        """Test creating directory from slug."""
        title = "My Amazing Article! @2024"
        slug = generate_slug(title)

        article_dir = tmp_path / slug
        ensure_directory(article_dir)

        assert article_dir.exists()
        assert article_dir.is_dir()
        assert slug == "my-amazing-article-2024"

    def test_safe_path_validation_workflow(self):
        """Test safe path validation workflow."""
        test_paths = [
            ("file.txt", ['.txt'], True),
            ("../etc/passwd", ['.txt'], False),
            ("/absolute/path.txt", ['.txt'], False),
            ("subdir/file.json", ['.txt', '.json'], True),
            ("file.exe", ['.txt'], False),
        ]

        for path, extensions, expected in test_paths:
            result = is_safe_path(path, extensions)
            assert result == expected, f"Failed for {path}"
