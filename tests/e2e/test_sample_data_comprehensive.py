"""Comprehensive tests for all sample data in samples/ directory.

These tests verify that all sample data is valid and accessible for live testing.
They run in both mock and live modes to ensure data integrity.
"""

import pytest
from pathlib import Path
import yaml
import json


# ============================================================================
# Test Sample KB Files
# ============================================================================

class TestSampleKBFiles:
    """Test that all KB sample files are valid and readable."""

    def test_sample_kb_overview_exists(self, samples_path):
        """Test that sample KB overview file exists."""
        kb_file = samples_path / "fixtures" / "kb" / "sample-kb-overview.md"
        assert kb_file.exists()

        content = kb_file.read_text(encoding='utf-8')
        assert len(content) > 100
        assert "UCOP" in content or "Architecture" in content

    def test_sample_kb_architecture_exists(self, samples_path):
        """Test that KB architecture file exists."""
        kb_file = samples_path / "fixtures" / "kb" / "sample-kb-architecture.md"
        assert kb_file.exists()

        content = kb_file.read_text(encoding='utf-8')
        assert len(content) > 100
        assert "Agent Mesh" in content or "architecture" in content.lower()

    def test_all_kb_files_have_frontmatter(self, samples_path):
        """Test that all KB files have YAML frontmatter."""
        kb_dir = samples_path / "fixtures" / "kb"
        kb_files = list(kb_dir.glob("*.md"))

        assert len(kb_files) >= 2, "Should have at least 2 KB files"

        for kb_file in kb_files:
            content = kb_file.read_text(encoding='utf-8')
            assert content.startswith("---") or content.startswith("\ufeff---"), \
                f"{kb_file.name} should have YAML frontmatter"


# ============================================================================
# Test Sample Docs Files
# ============================================================================

class TestSampleDocsFiles:
    """Test that all docs sample files are valid."""

    def test_sample_api_reference_exists(self, samples_path):
        """Test that API reference file exists."""
        doc_file = samples_path / "fixtures" / "docs" / "sample-api-reference.md"
        assert doc_file.exists()

        content = doc_file.read_text(encoding='utf-8')
        assert "API" in content or "api" in content.lower()
        assert "POST" in content or "GET" in content

    def test_sample_api_workflows_exists(self, samples_path):
        """Test that workflows API docs exist."""
        doc_file = samples_path / "fixtures" / "docs" / "sample-api-workflows.md"
        assert doc_file.exists()

        content = doc_file.read_text(encoding='utf-8')
        assert "workflow" in content.lower()
        assert "GET" in content or "POST" in content

    def test_all_docs_files_are_markdown(self, samples_path):
        """Test that all docs files are markdown."""
        docs_dir = samples_path / "fixtures" / "docs"
        doc_files = list(docs_dir.glob("*.md"))

        assert len(doc_files) >= 2, "Should have at least 2 doc files"

        for doc_file in doc_files:
            assert doc_file.suffix == ".md"
            content = doc_file.read_text(encoding='utf-8')
            assert len(content) > 50


# ============================================================================
# Test Sample Tutorial Files
# ============================================================================

class TestSampleTutorialFiles:
    """Test that all tutorial sample files are valid."""

    def test_sample_tutorial_getting_started_exists(self, samples_path):
        """Test that getting started tutorial exists."""
        tutorial_file = samples_path / "fixtures" / "tutorials" / "sample-tutorial-getting-started.md"
        assert tutorial_file.exists()

        content = tutorial_file.read_text(encoding='utf-8')
        assert "tutorial" in content.lower() or "steps" in content.lower()

    def test_sample_tutorial_testing_exists(self, samples_path):
        """Test that testing tutorial exists."""
        tutorial_file = samples_path / "fixtures" / "tutorials" / "sample-tutorial-testing.md"
        assert tutorial_file.exists()

        content = tutorial_file.read_text(encoding='utf-8')
        assert "test" in content.lower()
        assert "mock" in content.lower() or "live" in content.lower()

    def test_all_tutorials_have_prerequisites(self, samples_path):
        """Test that tutorials have prerequisites section."""
        tutorials_dir = samples_path / "fixtures" / "tutorials"
        tutorial_files = list(tutorials_dir.glob("*.md"))

        assert len(tutorial_files) >= 2, "Should have at least 2 tutorial files"

        for tutorial_file in tutorial_files:
            content = tutorial_file.read_text(encoding='utf-8')
            # Check for common tutorial sections
            has_structure = any(keyword in content.lower() for keyword in [
                "prerequisite", "steps", "overview", "tutorial"
            ])
            assert has_structure, f"{tutorial_file.name} should have tutorial structure"


# ============================================================================
# Test Sample Blog Files
# ============================================================================

class TestSampleBlogFiles:
    """Test that blog sample files are valid."""

    def test_sample_blog_ai_trends_exists(self, samples_path):
        """Test that AI trends blog post exists."""
        blog_file = samples_path / "fixtures" / "blog" / "sample-blog-ai-trends.md"
        assert blog_file.exists()

        content = blog_file.read_text(encoding='utf-8')
        assert len(content) > 500, "Blog post should have substantial content"
        assert "AI" in content or "agent" in content.lower()

    def test_blog_files_have_metadata(self, samples_path):
        """Test that blog files have frontmatter metadata."""
        blog_dir = samples_path / "fixtures" / "blog"
        if not blog_dir.exists():
            pytest.skip("Blog directory not found")

        blog_files = list(blog_dir.glob("*.md"))
        assert len(blog_files) >= 1, "Should have at least 1 blog file"

        for blog_file in blog_files:
            content = blog_file.read_text(encoding='utf-8')
            assert content.startswith("---") or content.startswith("\ufeff---"), \
                f"{blog_file.name} should have frontmatter"


# ============================================================================
# Test Workflow Config Files
# ============================================================================

class TestWorkflowConfigFiles:
    """Test that workflow configuration files are valid YAML."""

    def test_sample_workflow_exists(self, sample_workflow_config):
        """Test that sample workflow config exists."""
        assert sample_workflow_config.exists()

    def test_sample_workflow_is_valid_yaml(self, sample_workflow_config):
        """Test that sample workflow is valid YAML."""
        with open(sample_workflow_config, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert 'workflow' in data
        assert 'steps' in data['workflow']

    def test_blog_generation_workflow_exists(self, samples_path):
        """Test that blog generation workflow exists."""
        workflow_file = samples_path / "config" / "workflows" / "blog_generation_workflow.yaml"
        assert workflow_file.exists()

        with open(workflow_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert 'workflow' in data
        assert data['workflow']['name'] == 'blog_post_generation'
        assert len(data['workflow']['steps']) > 5

    def test_simple_research_workflow_exists(self, samples_path):
        """Test that simple research workflow exists."""
        workflow_file = samples_path / "config" / "workflows" / "simple_research_workflow.yaml"
        assert workflow_file.exists()

        with open(workflow_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert 'workflow' in data
        assert data['workflow']['name'] == 'simple_research'

    def test_all_workflows_have_required_fields(self, samples_path):
        """Test that all workflow files have required fields."""
        workflows_dir = samples_path / "config" / "workflows"
        workflow_files = list(workflows_dir.glob("*.yaml"))

        assert len(workflow_files) >= 3, "Should have at least 3 workflow files"

        required_fields = ['name', 'steps']

        for workflow_file in workflow_files:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            assert 'workflow' in data, f"{workflow_file.name} should have 'workflow' key"

            for field in required_fields:
                assert field in data['workflow'], \
                    f"{workflow_file.name} should have '{field}' field"


# ============================================================================
# Test External API Response Files
# ============================================================================

class TestExternalAPIResponseFiles:
    """Test that external API response samples are valid JSON."""

    def test_github_issues_sample_exists(self, samples_path):
        """Test that GitHub issues sample exists."""
        api_file = samples_path / "external" / "api_responses" / "github_issues_sample.json"
        assert api_file.exists()

        with open(api_file, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            data = json.load(f)

        assert data is not None
        assert isinstance(data, (dict, list))

    def test_search_api_sample_exists(self, samples_path):
        """Test that search API sample exists."""
        api_file = samples_path / "external" / "api_responses" / "search_api_sample.json"
        assert api_file.exists()

        with open(api_file, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            data = json.load(f)

        assert data is not None

    def test_all_api_responses_are_valid_json(self, samples_path):
        """Test that all API response files are valid JSON."""
        api_dir = samples_path / "external" / "api_responses"
        json_files = list(api_dir.glob("*.json"))

        assert len(json_files) >= 2, "Should have at least 2 API response files"

        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8-sig') as f:  # Handle BOM
                data = json.load(f)

            assert data is not None, f"{json_file.name} should contain valid JSON"


# ============================================================================
# Test Sample Manifests
# ============================================================================

class TestSampleManifests:
    """Test that sample manifest files are valid."""

    def test_job_success_manifest_exists(self, samples_path):
        """Test that job success manifest exists."""
        manifest_file = samples_path / "manifests" / "job_success_manifest.json"
        assert manifest_file.exists()

        with open(manifest_file, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            data = json.load(f)

        assert 'job_id' in data or 'workflow' in data

    def test_job_failure_manifest_exists(self, samples_path):
        """Test that job failure manifest exists."""
        manifest_file = samples_path / "manifests" / "job_failure_manifest.json"
        assert manifest_file.exists()

        with open(manifest_file, 'r', encoding='utf-8-sig') as f:  # Handle BOM
            data = json.load(f)

        assert data is not None


# ============================================================================
# Test Sample Templates
# ============================================================================

class TestSampleTemplates:
    """Test that sample templates are valid."""

    def test_blog_template_exists(self, samples_path):
        """Test that blog template exists."""
        template_file = samples_path / "templates" / "blog" / "sample_blog_template.md"
        assert template_file.exists()

        content = template_file.read_text(encoding='utf-8')
        assert len(content) > 50

    def test_howto_template_exists(self, samples_path):
        """Test that how-to template exists."""
        template_file = samples_path / "templates" / "howto" / "sample_howto_template.md"
        assert template_file.exists()

        content = template_file.read_text(encoding='utf-8')
        assert len(content) > 50


# ============================================================================
# Integration Tests
# ============================================================================

class TestSampleDataIntegration:
    """Test that sample data integrates correctly."""

    def test_all_sample_data_accessible(self, samples_path):
        """Test that all sample data directories exist and are accessible."""
        required_dirs = [
            "fixtures/kb",
            "fixtures/docs",
            "fixtures/tutorials",
            "fixtures/blog",
            "config/workflows",
            "external/api_responses",
            "manifests",
            "templates"
        ]

        for dir_path in required_dirs:
            full_path = samples_path / dir_path
            assert full_path.exists(), f"Required directory not found: {dir_path}"
            assert full_path.is_dir(), f"Should be a directory: {dir_path}"

    def test_sample_data_count(self, samples_path):
        """Test that we have sufficient sample data files."""
        all_files = list(samples_path.rglob("*"))
        data_files = [f for f in all_files if f.is_file()]

        # Should have at least 15 sample files (not counting logs)
        assert len(data_files) >= 15, \
            f"Should have at least 15 sample files, found {len(data_files)}"

    def test_no_empty_sample_files(self, samples_path):
        """Test that no sample files are empty."""
        all_files = list(samples_path.rglob("*.md")) + \
                    list(samples_path.rglob("*.yaml")) + \
                    list(samples_path.rglob("*.json"))

        for file_path in all_files:
            if file_path.is_file():
                content = file_path.read_text(encoding='utf-8')
                assert len(content) > 10, f"{file_path.name} should not be empty"
