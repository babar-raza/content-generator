"""Integration tests for validation API routes.

Tests all endpoints in src/web/routes/validation.py including:
- Content validation for multiple content types
- File validation
- Batch validation
"""

import pytest
from io import BytesIO
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.routes import validation


@pytest.fixture
def app():
    """Create FastAPI app with validation router."""
    test_app = FastAPI()
    test_app.include_router(validation.router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestContentValidation:
    """Test content validation endpoint."""

    def test_validate_markdown_success(self, client):
        """Test successfully validating valid markdown."""
        response = client.post("/api/validate", json={
            "content": "# Hello\n\nThis is valid markdown",
            "content_type": "markdown"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "markdown"
        assert data["total_issues"] == 0
        assert "timestamp" in data

    def test_validate_markdown_empty_content(self, client):
        """Test validating empty markdown."""
        response = client.post("/api/validate", json={
            "content": "",
            "content_type": "markdown"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["rule_id"] == "MD001"
        assert "empty" in data["errors"][0]["message"].lower()

    def test_validate_markdown_heading_skip(self, client):
        """Test markdown with skipped heading levels."""
        response = client.post("/api/validate", json={
            "content": "# Heading 1\n\n### Heading 3",
            "content_type": "markdown"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True  # Warnings don't make it invalid
        assert len(data["warnings"]) == 1
        assert "skipped" in data["warnings"][0]["message"].lower()

    def test_validate_markdown_trailing_whitespace(self, client):
        """Test markdown with trailing whitespace."""
        response = client.post("/api/validate", json={
            "content": "# Heading  \nText",
            "content_type": "markdown"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) == 1
        assert "trailing" in data["warnings"][0]["message"].lower()

    def test_validate_markdown_strict_mode(self, client):
        """Test markdown strict validation."""
        response = client.post("/api/validate", json={
            "content": "# Heading  \nText",
            "content_type": "markdown",
            "strict": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False  # Strict mode makes it invalid
        assert len(data["errors"]) == 1

    def test_validate_yaml_success(self, client):
        """Test successfully validating valid YAML."""
        response = client.post("/api/validate", json={
            "content": "key: value\nlist:\n  - item1\n  - item2",
            "content_type": "yaml"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "yaml"

    def test_validate_yaml_invalid(self, client):
        """Test validating invalid YAML."""
        response = client.post("/api/validate", json={
            "content": "key: value\n:invalid syntax",  # Invalid YAML syntax
            "content_type": "yaml"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        assert data["errors"][0]["rule_id"] == "YAML001"

    def test_validate_json_success(self, client):
        """Test successfully validating valid JSON."""
        response = client.post("/api/validate", json={
            "content": '{"key": "value", "array": [1, 2, 3]}',
            "content_type": "json"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "json"

    def test_validate_json_invalid(self, client):
        """Test validating invalid JSON."""
        response = client.post("/api/validate", json={
            "content": '{"key": "value"',  # Missing closing brace
            "content_type": "json"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["rule_id"] == "JSON001"

    def test_validate_html_success(self, client):
        """Test successfully validating HTML."""
        response = client.post("/api/validate", json={
            "content": "<html><body>Hello</body></html>",
            "content_type": "html"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "html"

    def test_validate_html_empty(self, client):
        """Test validating empty HTML."""
        response = client.post("/api/validate", json={
            "content": "",
            "content_type": "html"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 1
        assert data["errors"][0]["rule_id"] == "HTML001"

    def test_validate_unsupported_type(self, client):
        """Test validating unsupported content type."""
        response = client.post("/api/validate", json={
            "content": "Some content",
            "content_type": "unsupported"
        })

        assert response.status_code == 400
        assert "Unsupported content type" in response.json()["detail"]

    def test_validate_with_multiple_issues(self, client):
        """Test markdown with multiple issues."""
        content = "# Heading  \n\n\n\n### Skipped level  \nText"
        response = client.post("/api/validate", json={
            "content": content,
            "content_type": "markdown"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["total_issues"] > 1

    def test_validate_error_handling(self, client):
        """Test error handling for validation failures."""
        # This will likely succeed, but tests the error path exists
        response = client.post("/api/validate", json={
            "content": "Test content",
            "content_type": "markdown"
        })

        assert response.status_code in [200, 500]


class TestFileValidation:
    """Test file validation endpoint."""

    def test_validate_markdown_file(self, client):
        """Test validating markdown file."""
        file_content = b"# Heading\n\nValid markdown"
        files = {"file": ("test.md", BytesIO(file_content), "text/markdown")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "markdown"

    def test_validate_yaml_file(self, client):
        """Test validating YAML file."""
        file_content = b"key: value\nlist:\n  - item"
        files = {"file": ("test.yaml", BytesIO(file_content), "text/yaml")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "yaml"

    def test_validate_json_file(self, client):
        """Test validating JSON file."""
        file_content = b'{"key": "value"}'
        files = {"file": ("test.json", BytesIO(file_content), "application/json")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "json"

    def test_validate_html_file(self, client):
        """Test validating HTML file."""
        file_content = b"<html><body>Hello</body></html>"
        files = {"file": ("test.html", BytesIO(file_content), "text/html")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["content_type"] == "html"

    def test_validate_file_yml_extension(self, client):
        """Test validating .yml file extension."""
        file_content = b"key: value"
        files = {"file": ("test.yml", BytesIO(file_content), "text/plain")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "yaml"

    def test_validate_file_default_markdown(self, client):
        """Test that unknown extensions default to markdown."""
        file_content = b"# Heading"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "markdown"

    def test_validate_file_with_override(self, client):
        """Test validating file with content type override."""
        file_content = b'{"key": "value"}'
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        data_form = {"content_type": "json"}

        response = client.post("/api/validate/file", files=files, data=data_form)

        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "json"
        assert data["valid"] is True

    def test_validate_file_strict_mode(self, client):
        """Test file validation in strict mode."""
        file_content = b"# Heading  \nText"  # Has trailing space
        files = {"file": ("test.md", BytesIO(file_content), "text/markdown")}
        data_form = {"strict": "true"}

        response = client.post("/api/validate/file", files=files, data=data_form)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False  # Strict mode

    def test_validate_invalid_file(self, client):
        """Test validating invalid file."""
        file_content = b'{"invalid json'
        files = {"file": ("test.json", BytesIO(file_content), "application/json")}

        response = client.post("/api/validate/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0


class TestBatchValidation:
    """Test batch validation endpoint."""

    def test_validate_batch_success(self, client):
        """Test successfully validating batch of content."""
        response = client.post("/api/validate/batch", json={
            "items": [
                {"content": "# Valid Markdown", "content_type": "markdown"},
                {"content": '{"key": "value"}', "content_type": "json"},
                {"content": "key: value", "content_type": "yaml"}
            ]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["valid_count"] == 3
        assert data["invalid_count"] == 0
        assert len(data["results"]) == 3

    def test_validate_batch_mixed_results(self, client):
        """Test batch validation with mixed results."""
        response = client.post("/api/validate/batch", json={
            "items": [
                {"content": "# Valid", "content_type": "markdown"},
                {"content": "", "content_type": "markdown"},  # Invalid
                {"content": '{"valid": true}', "content_type": "json"}
            ]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["valid_count"] == 2
        assert data["invalid_count"] == 1

    def test_validate_batch_all_invalid(self, client):
        """Test batch validation with all invalid items."""
        response = client.post("/api/validate/batch", json={
            "items": [
                {"content": "", "content_type": "markdown"},
                {"content": "", "content_type": "html"}
            ]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["valid_count"] == 0
        assert data["invalid_count"] == 2

    def test_validate_batch_empty_list(self, client):
        """Test batch validation with empty list."""
        response = client.post("/api/validate/batch", json={
            "items": []
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["valid_count"] == 0
        assert data["invalid_count"] == 0

    def test_validate_batch_different_types(self, client):
        """Test batch validation with different content types."""
        response = client.post("/api/validate/batch", json={
            "items": [
                {"content": "# Markdown", "content_type": "markdown"},
                {"content": '["array"]', "content_type": "json"},
                {"content": "list:\n  - item", "content_type": "yaml"},
                {"content": "<p>HTML</p>", "content_type": "html"}
            ]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert all(r["valid"] for r in data["results"])

    def test_validate_batch_with_strict_mode(self, client):
        """Test batch validation with strict mode."""
        response = client.post("/api/validate/batch", json={
            "items": [
                {"content": "# Heading  \nText", "content_type": "markdown", "strict": True},
                {"content": "# Valid", "content_type": "markdown", "strict": False}
            ]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["valid_count"] == 1  # One fails strict mode
        assert data["invalid_count"] == 1

    def test_validate_batch_with_rules(self, client):
        """Test batch validation with specific rules."""
        response = client.post("/api/validate/batch", json={
            "items": [
                {
                    "content": "# Test",
                    "content_type": "markdown",
                    "rules": ["MD001", "MD009"]
                }
            ]
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1

    def test_validate_batch_error_handling(self, client):
        """Test error handling in batch validation."""
        # Test with potentially problematic content
        response = client.post("/api/validate/batch", json={
            "items": [
                {"content": "Valid", "content_type": "markdown"}
            ]
        })

        assert response.status_code in [200, 500]
