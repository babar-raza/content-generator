# Troubleshooting Guide

Common issues and solutions for UCOP.

## Quick Diagnostics

```bash
# Check system health
python tools/validate_system.py

# Test LLM connectivity
python tools/validate.py

# View logs
tail -f logs/ucop.log

# Check running jobs
python ucop_cli.py job list --status running
```

## Installation Issues

### Python Version Too Old

**Symptom**: `SyntaxError` or `ModuleNotFoundError`

**Solution**:
```bash
# Check version
python --version

# Install Python 3.10+
# Ubuntu
sudo apt install python3.10

# Mac
brew install python@3.10

# Windows
# Download from python.org
```

### Dependencies Installation Fails

**Symptom**: `pip install` errors

**Solution**:
```bash
# Upgrade pip
pip install --upgrade pip

# Install build tools
# Ubuntu
sudo apt install python3-dev build-essential

# Mac
xcode-select --install

# Try again
pip install -r requirements.txt -v
```

### Virtual Environment Issues

**Symptom**: Cannot activate venv

**Solution**:
```bash
# Remove and recreate
rm -rf venv
python -m venv venv

# Activate
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

## LLM Connection Issues

### Ollama Not Responding

**Symptom**: `ConnectionError: Cannot connect to Ollama`

**Solution**:
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start Ollama
# Mac: Open Ollama app
# Linux: systemctl start ollama
# Windows: Start from Start menu

# Verify model is pulled
ollama list
ollama pull qwen2.5:14b
```

### Gemini API Errors

**Symptom**: `401 Unauthorized` or `429 Rate Limit`

**Solution**:
```bash
# Check API key
echo $GEMINI_API_KEY

# Verify key is valid
python -c "from google import generativeai; generativeai.configure(api_key='YOUR_KEY'); print(list(generativeai.list_models()))"

# Rate limit: Reduce RPM in config
# config/main.yaml
llm:
  rate_limiting:
    gemini:
      requests_per_minute: 30  # Reduce from 60
```

### OpenAI API Errors

**Symptom**: `RateLimitError` or `AuthenticationError`

**Solution**:
```bash
# Check API key
echo $OPENAI_API_KEY

# Check quota
# Visit: https://platform.openai.com/usage

# Reduce rate
# config/main.yaml
llm:
  rate_limiting:
    openai:
      requests_per_minute: 50
```

## Runtime Errors

### Job Stuck or Hanging

**Symptom**: Job shows "running" for hours

**Solution**:
```bash
# Check job details
python ucop_cli.py job get <job_id> --logs

# Check which agent is stuck
python ucop_cli.py viz flows --job <job_id>

# Pause and inspect
python ucop_cli.py job pause <job_id>

# Check agent timeout in config
# config/agents.yaml
agents:
  stuck_agent:
    resources:
      max_runtime_s: 300  # Increase if needed
```

### Agent Timeout

**Symptom**: `AgentTimeoutError: Agent exceeded max runtime`

**Solution**:
```bash
# Increase timeout for specific agent
# config/agents.yaml
agents:
  code_generation_agent:
    resources:
      max_runtime_s: 600  # Increase from 300

# Or globally
# config/main.yaml
timeouts:
  agent_default: 600
```

### Out of Memory

**Symptom**: `MemoryError` or process killed

**Solution**:
```bash
# Check memory usage
free -h

# Reduce parallel agents
# config/main.yaml
workflows:
  max_parallel_agents: 2  # Reduce from 5

# Reduce context window
# .env
OLLAMA_NUM_CTX=2048  # Reduce from 4096
```

### Checkpoint Corruption

**Symptom**: Cannot restore from checkpoint

**Solution**:
```bash
# List checkpoints
python ucop_cli.py checkpoint list --job <job_id>

# Try earlier checkpoint
python ucop_cli.py checkpoint restore --job <job_id> --checkpoint <earlier_id>

# If all fail, restart job
python ucop_cli.py generate --input <original_input>
```

## Web UI Issues

### UI Not Loading

**Symptom**: Blank page or 404

**Solution**:
```bash
# Check server is running
curl http://localhost:8000/health

# Rebuild UI
cd src/web/static
npm run build

# Check static files
ls -la src/web/static/dist/

# Restart server
pkill -f start_web.py
python start_web.py
```

### WebSocket Connection Failed

**Symptom**: Real-time updates not working

**Solution**:
```bash
# Check WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Host: localhost:8000" \
  -H "Origin: http://localhost:8000" \
  http://localhost:8000/ws

# Check firewall/proxy allows WebSocket
# Nginx example:
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### 404 on API Endpoints

**Symptom**: API calls return 404

**Solution**:
```bash
# Check if MCP web adapter is mounted
grep -n "src.mcp.web_adapter" src/web/app.py

# If not, this is known issue (see design-history.md)
# Fix: Mount correct router
# src/web/app.py
from src.mcp.web_adapter import router as mcp_router
app.include_router(mcp_router, prefix="/mcp")
```

## Performance Issues

### Slow Generation

**Symptom**: Takes >10 minutes per blog post

**Diagnosis**:
```bash
# Check bottlenecks
python ucop_cli.py viz bottlenecks --threshold 60

# Profile workflow
python profile_system.py --workflow blog_generation
```

**Solutions**:
1. **Use faster model**:
```yaml
# config/main.yaml
llm:
  models:
    ollama: "phi4:14b"  # Faster than qwen2.5:14b
```

2. **Enable caching**:
```yaml
# config/main.yaml
caching:
  enabled: true
  ttl: 3600
```

3. **Increase parallelism**:
```yaml
workflows:
  max_parallel_agents: 10
```

### High Memory Usage

**Symptom**: System slows down, swap usage high

**Solutions**:
```yaml
# 1. Reduce context window
# .env
OLLAMA_NUM_CTX=2048

# 2. Limit parallel agents
# config/main.yaml
workflows:
  max_parallel_agents: 3

# 3. Use smaller model
llm:
  models:
    ollama: "phi4:14b"  # Uses less memory
```

### High CPU Usage

**Symptom**: CPU at 100% constantly

**Solutions**:
```bash
# 1. Check if model is using CPU instead of GPU
python -c "import torch; print(torch.cuda.is_available())"

# 2. Limit workers
# config/main.yaml
workers:
  max_workers: 2

# 3. Use cloud LLM instead of local
# .env
# Comment out OLLAMA_HOST
GEMINI_API_KEY=your_key
```

## Configuration Issues

### Invalid Configuration

**Symptom**: `ConfigurationError` on startup

**Solution**:
```bash
# Validate config
python tools/validate.py

# Check YAML syntax
python -m yaml config/main.yaml

# Reset to defaults
cp config/main.yaml config/main.yaml.backup
git checkout config/main.yaml
```

### Environment Variables Not Loading

**Symptom**: Uses default values instead of .env

**Solution**:
```bash
# Check .env file exists
ls -la .env

# Load manually
export $(cat .env | xargs)

# Verify loaded
echo $GEMINI_API_KEY

# Alternative: Use python-dotenv
pip install python-dotenv
```

### Hot Reload Not Working

**Symptom**: Config changes not applied

**Solution**:
```bash
# Check if enabled
grep ENABLE_HOT_RELOAD .env

# Enable
export ENABLE_HOT_RELOAD=true

# Restart if disabled
pkill -f start_web.py
python start_web.py
```

## Content Quality Issues

### Poor Quality Output

**Symptom**: Generated content is low quality

**Solutions**:
1. **Improve source material**:
```bash
# Ensure KB articles have:
# - Clear structure
# - Code examples
# - Proper formatting
```

2. **Adjust temperature**:
```yaml
# config/main.yaml
llm:
  temperature: 0.5  # Lower for more focused output
```

3. **Use better model**:
```yaml
llm:
  providers:
    - gemini  # Generally better quality than local
```

### Inconsistent Tone

**Symptom**: Content tone varies across sections

**Solution**:
```json
# config/tone.json
{
  "default_tone": "professional",
  "enforce_consistency": true,
  "tone_check_agents": [
    "introduction_writer_agent",
    "section_writer_agent",
    "conclusion_writer_agent"
  ]
}
```

### Missing Code Examples

**Symptom**: Blog posts lack code samples

**Solution**:
```bash
# Check API ingestion
python ucop_cli.py ingest api ./api_docs/

# Verify API context available
python ucop_cli.py agent invoke api_search_agent \
  --input '{"query": "image processing"}'

# Enable code generation
# config/main.yaml
workflows:
  default:
    steps:
      - code_generation  # Ensure included
      - code_validation
```

## Testing Issues

### Tests Failing

**Symptom**: `pytest` fails with import errors

**Solution**:
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run with verbose
pytest -v -s

# Run specific test
pytest tests/unit/test_agents.py::test_outline_agent
```

### Mock Services Not Working

**Symptom**: Tests try to call real APIs

**Solution**:
```python
# Use mock LLM in tests
# conftest.py
@pytest.fixture
def mock_llm():
    with patch('src.services.llm_service.LLMService') as mock:
        mock.return_value.generate.return_value = "Mock response"
        yield mock
```

## Logging & Debugging

### Insufficient Logging

**Solution**:
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Or in .env
LOG_LEVEL=DEBUG

# View logs
tail -f logs/ucop.log

# Filter logs
grep "ERROR" logs/ucop.log
```

### Debug Specific Agent

```bash
# Enable agent-level logging
python ucop_cli.py agent invoke code_generation_agent \
  --input '...' \
  --log-level DEBUG

# Or set in config
# config/agents.yaml
agents:
  code_generation_agent:
    debug: true
    log_level: DEBUG
```

## Getting Help

If issue persists:

1. **Check logs**: `logs/ucop.log`
2. **Run diagnostics**: `python tools/validate_system.py`
3. **Check GitHub issues**: Search for similar problems
4. **Ask for help**: Provide:
   - Error message
   - Log excerpt
   - Config (redact API keys)
   - Steps to reproduce

## Common Error Codes

- **E001**: Configuration error
- **E002**: LLM connection error  
- **E003**: Agent timeout
- **E004**: Checkpoint error
- **E005**: Validation error
- **E006**: Storage error
- **E007**: Network error

See logs for detailed error messages.
