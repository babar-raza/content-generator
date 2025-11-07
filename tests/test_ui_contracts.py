"""Test UI contract requirements - that required elements exist."""
import pytest
from pathlib import Path


def test_dashboard_has_template_dropdown():
    """Test that dashboard.html contains template dropdown."""
    dashboard_path = Path("src/web/templates/dashboard.html")
    assert dashboard_path.exists(), "dashboard.html not found"
    
    content = dashboard_path.read_text()
    
    # Check for template dropdown
    assert 'id="job-template"' in content, "Template dropdown missing"
    assert '<select id="job-template"' in content, "Template select element missing"
    assert 'blog_default' in content, "Blog default template option missing"
    assert 'code_' in content, "Code template options missing"
    assert 'kb_' in content, "KB template options missing"
    assert 'docs_' in content, "Docs template options missing"


def test_dashboard_has_context_pickers():
    """Test that dashboard.html contains all context pickers."""
    dashboard_path = Path("src/web/templates/dashboard.html")
    content = dashboard_path.read_text()
    
    # Check for all context pickers
    assert 'id="job-kb-path"' in content, "KB path picker missing"
    assert 'id="job-docs-path"' in content, "Docs path picker missing"
    assert 'id="job-blog-path"' in content, "Blog path picker missing"
    assert 'id="job-api-path"' in content, "API path picker missing"
    assert 'id="job-tutorial-path"' in content, "Tutorial path picker missing"
    
    # Check for browse buttons
    assert 'onclick="browsePath' in content, "Browse buttons missing"
    assert content.count('Browse') >= 5, "Not enough browse buttons (should be at least 5)"


def test_dashboard_has_auto_topic_checkbox():
    """Test that dashboard.html contains auto-topic checkbox."""
    dashboard_path = Path("src/web/templates/dashboard.html")
    content = dashboard_path.read_text()
    
    assert 'id="job-auto-topic"' in content, "Auto-topic checkbox missing"
    assert 'type="checkbox"' in content, "Checkbox type missing"
    assert 'Auto-derive topic' in content or 'auto-topic' in content.lower(), "Auto-topic label missing"


def test_job_detail_has_log_modal_functions():
    """Test that job_detail.js contains log modal functions."""
    js_path = Path("src/web/static/js/job_detail.js")
    assert js_path.exists(), "job_detail.js not found"
    
    content = js_path.read_text()
    
    # Check for modal functions
    assert 'showLogModal' in content, "showLogModal function missing"
    assert 'closeLogModal' in content, "closeLogModal function missing"
    assert 'downloadJSON' in content, "downloadJSON function missing"
    assert '/api/agents/' in content, "Agent API call missing"


def test_log_modal_shows_json_io():
    """Test that log modal displays JSON input/output."""
    js_path = Path("src/web/static/js/job_detail.js")
    content = js_path.read_text()
    
    # Check for JSON display elements
    assert 'json-output' in content or 'JSON.stringify' in content, "JSON output display missing"
    assert 'Input' in content and 'Output' in content, "Input/Output sections missing"
    assert 'Download' in content or 'download' in content.lower(), "Download functionality missing"


def test_dashboard_js_sends_all_fields():
    """Test that dashboard.js sends all required fields."""
    js_path = Path("src/web/static/js/dashboard.js")
    assert js_path.exists(), "dashboard.js not found"
    
    content = js_path.read_text()
    
    # Check that form submission includes all fields
    assert 'template_name' in content, "template_name not sent"
    assert 'auto_topic' in content, "auto_topic not sent"
    assert 'docs_path' in content, "docs_path not sent"
    assert 'blog_path' in content, "blog_path not sent"
    assert 'api_path' in content, "api_path not sent"
    assert 'tutorial_path' in content, "tutorial_path not sent"


def test_web_app_has_agent_logs_endpoint():
    """Test that app_unified.py has agent logs endpoint."""
    app_path = Path("src/web/app_unified.py")
    assert app_path.exists(), "app_unified.py not found"
    
    content = app_path.read_text()
    
    # Check for agent logs endpoint
    assert '/api/agents/' in content, "Agent logs endpoint missing"
    assert 'redact_secrets' in content, "Secret redaction missing"


def test_template_files_have_metadata():
    """Test that template files have proper metadata structure."""
    blog_templates = Path("templates/new_blog_templates.yaml")
    code_templates = Path("templates/new_code_templates.yaml")
    kb_templates = Path("templates/kb_templates.yaml")
    docs_templates = Path("templates/docs_templates.yaml")
    
    assert blog_templates.exists(), "Blog templates not found"
    assert code_templates.exists(), "Code templates not found"
    assert kb_templates.exists(), "KB templates not found"
    assert docs_templates.exists(), "Docs templates not found"
    
    blog_content = blog_templates.read_text()
    code_content = code_templates.read_text()
    kb_content = kb_templates.read_text()
    docs_content = docs_templates.read_text()
    
    # Check for metadata structure
    for content, name in [(blog_content, "blog"), (code_content, "code"), 
                          (kb_content, "kb"), (docs_content, "docs")]:
        assert 'id:' in content, f"{name} templates missing id"
        assert 'type:' in content, f"{name} templates missing type"
        assert 'version:' in content, f"{name} templates missing version"
        assert 'schema:' in content, f"{name} templates missing schema"


def test_pipeline_order_matches_config():
    """Test that pipeline view would match config order (placeholder test)."""
    # This would require checking the job detail page rendering
    # For now, just verify config file exists
    config_path = Path("config/agents.yaml")
    assert config_path.exists(), "agents.yaml config not found"
    
    content = config_path.read_text()
    assert 'pipeline:' in content or 'agents:' in content, "Pipeline definition missing from config"
