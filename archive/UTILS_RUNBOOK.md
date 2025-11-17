# Utils Module - Runbook

## Quick Verification

### Test Imports
```bash
python -c "from src.utils import PerformanceTracker; pt = PerformanceTracker(); print('OK')"
```

Expected output: `OK`

### Run All Tests
```bash
pytest tests/unit/test_utils.py -v
```

## Module Overview

The utils module provides 5 categories of utilities:

1. **Performance Tracking** - Sliding window metrics
2. **JSON Repair** - Fix malformed LLM responses
3. **Path Utilities** - Safe file operations
4. **Retry Decorators** - Exponential backoff
5. **Validators** - Input validation

All utilities use **only Python standard library** - no external dependencies.

## Usage Examples

### 1. PerformanceTracker - Sliding Window Metrics

```python
from src.utils import PerformanceTracker

# Create tracker with 100-item window
tracker = PerformanceTracker(window_size=100)

# Record operations
tracker.record(duration=1.5, success=True, metadata={'model': 'llama2'})
tracker.record(duration=2.3, success=False, metadata={'error': 'timeout'})

# Get statistics
stats = tracker.get_stats()
print(f"Average: {stats['avg_duration']:.2f}s")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"P95: {stats['p95']:.2f}s")

# Get recent failures
failures = tracker.get_recent_failures(limit=5)
for timestamp, duration, metadata in failures:
    print(f"Failed: {metadata.get('error')}")

# Reset tracker
tracker.reset()
```

**Thread Safety:** All operations are thread-safe using `threading.Lock`.

**Performance:** O(1) append/pop using `collections.deque`.

### 2. JSON Repair - Fix Malformed JSON

```python
from src.utils import repair_json, JSONRepair

# Fix trailing commas
text = '{"key": "value",}'
repaired = repair_json(text)  # Returns: '{"key": "value"}'

# Fix unquoted keys
text = '{name: "John", age: 30}'
result = JSONRepair.repair(text)  # Returns: {"name": "John", "age": 30}

# Fix single quotes
text = "{'key': 'value'}"
result = JSONRepair.repair(text)  # Returns: {"key": "value"}

# Handle nested structures
text = '{"outer": {"inner": "value",}, "list": [1, 2,]}'
result = JSONRepair.repair(text)
```

**Supported Fixes:**
- Trailing commas (objects and arrays)
- Unquoted keys
- Single quotes → double quotes
- Missing closing brackets
- Control characters

### 3. Path Utilities - Safe File Operations

```python
from src.utils import (
    safe_path,
    generate_slug,
    ensure_directory,
    get_safe_filename,
    is_safe_path
)

# Prevent path traversal attacks
base = Path("/data")
safe = safe_path(base, "files/report.txt")  # OK
# safe_path(base, "../etc/passwd")  # Raises ValueError

# Generate URL-safe slugs
slug = generate_slug("Hello, World! 123")  # Returns: "hello-world-123"
slug = generate_slug("Über cool café")  # Returns: "uber-cool-cafe"
slug = generate_slug("Long title...", max_length=20)  # Truncates

# Create directories safely (thread-safe)
path = ensure_directory("/tmp/my_app/data")

# Clean filenames
safe_name = get_safe_filename("file:name?.txt")  # Returns: "file-name.txt"

# Check path safety
if is_safe_path("data/file.txt", allowed_extensions=['.txt', '.json']):
    process_file(path)
```

### 4. Retry Decorators - Exponential Backoff

```python
from src.utils import retry_with_backoff, retry_on_condition, RetryContext
import requests

# Basic retry with backoff
@retry_with_backoff(max_attempts=3, initial_delay=1.0)
def fetch_data(url):
    """Retries on any exception with delays: 1s, 2s, 4s"""
    return requests.get(url)

# Retry specific exceptions only
@retry_with_backoff(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=10.0,
    exceptions=(ConnectionError, TimeoutError)
)
def connect_database():
    """Only retries on connection/timeout errors"""
    return db.connect()

# Retry based on return value
@retry_on_condition(
    lambda x: x is not None,
    max_attempts=3,
    initial_delay=1.0
)
def get_cache_value():
    """Retries until non-None value returned"""
    return cache.get('key')

# Custom callback on retry
def on_retry_callback(attempt, exception, delay):
    print(f"Retry {attempt}: {exception}, waiting {delay}s")

@retry_with_backoff(max_attempts=3, on_retry=on_retry_callback)
def risky_operation():
    pass

# Manual retry control with context manager
with RetryContext(max_attempts=3, initial_delay=1.0) as retry:
    while retry.should_retry():
        try:
            result = risky_operation()
            retry.success()
            break
        except Exception as e:
            retry.failure(e)
```

**Backoff Formula:** `min(initial_delay * (exponential_base ** attempt), max_delay)`

**Example Schedule:**
- `initial_delay=1.0, exponential_base=2.0`:
  - Attempt 1: immediate
  - Attempt 2: wait 1.0s
  - Attempt 3: wait 2.0s
  - Attempt 4: wait 4.0s

### 5. Validators - Input Validation

```python
from src.utils import (
    validate_config,
    validate_input,
    validate_url,
    validate_email,
    validate_port,
    validate_ipv4
)

# Validate configuration dictionaries
config = {'api_key': 'abc123', 'timeout': 30}
validate_config(
    config,
    required_fields=['api_key'],
    schema={'api_key': str, 'timeout': int}
)

# Comprehensive input validation
validate_input(
    value=42,
    param_name="age",
    expected_type=int,
    min_value=0,
    max_value=150
)

validate_input(
    value="test@example.com",
    param_name="email",
    expected_type=str,
    pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

validate_input(
    value="password123",
    param_name="password",
    expected_type=str,
    min_length=8,
    not_empty=True
)

# URL validation
if validate_url("https://example.com"):
    fetch_data(url)

if validate_url("http://api.example.com:8080/path", schemes=['http', 'https']):
    call_api(url)

# Email validation
if validate_email("user@example.com"):
    send_email(address)

# Port validation
if validate_port(8080):
    start_server(port)

if validate_port(443, allow_privileged=True):
    bind_socket(port)

# IPv4 validation
if validate_ipv4("192.168.1.1"):
    connect_to_host(ip)
```

## Combined Example: Complete Workflow

```python
from src.utils import (
    PerformanceTracker,
    retry_with_backoff,
    repair_json,
    safe_path,
    generate_slug,
    validate_config,
)
from pathlib import Path
import time

# 1. Validate configuration
config = {
    'base_dir': '/data',
    'api_key': 'secret',
    'max_retries': 3
}
validate_config(config, ['base_dir', 'api_key'], 
                {'base_dir': str, 'api_key': str, 'max_retries': int})

# 2. Setup performance tracking
tracker = PerformanceTracker(window_size=100)

# 3. Process with retry and tracking
@retry_with_backoff(max_attempts=config['max_retries'])
def process_document(title, content):
    start = time.time()
    try:
        # Generate safe filename
        slug = generate_slug(title)
        filename = f"{slug}.json"
        
        # Get safe path
        base = Path(config['base_dir'])
        file_path = safe_path(base, f"outputs/{filename}")
        
        # Repair JSON if needed
        clean_content = repair_json(content)
        
        # Save file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(clean_content)
        
        # Record success
        duration = time.time() - start
        tracker.record(duration, success=True, metadata={'file': filename})
        
        return file_path
        
    except Exception as e:
        duration = time.time() - start
        tracker.record(duration, success=False, metadata={'error': str(e)})
        raise

# 4. Use it
try:
    path = process_document("My Report: 2024", '{"data": "value",}')
    print(f"Saved to: {path}")
except Exception as e:
    print(f"Failed: {e}")

# 5. Check performance
stats = tracker.get_stats()
print(f"Processed {stats['count']} documents")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Average time: {stats['avg_duration']:.2f}s")
```

## Testing

### Run All Tests
```bash
pytest tests/unit/test_utils.py -v
```

### Run Specific Test Classes
```bash
# Test only PerformanceTracker
pytest tests/unit/test_utils.py::TestPerformanceTracker -v

# Test only JSON repair
pytest tests/unit/test_utils.py::TestJSONRepair -v

# Test only validators
pytest tests/unit/test_utils.py::TestValidators -v
```

### Run with Coverage
```bash
pytest tests/unit/test_utils.py --cov=src.utils --cov-report=html -v
```

## Troubleshooting

### Import Errors

If you get import errors:
```bash
export PYTHONPATH=/home/claude:$PYTHONPATH
python -c "from src.utils import PerformanceTracker; print('OK')"
```

### PerformanceTracker Dependencies

The existing `learning.py` has dependencies on `src.core`. If you encounter import issues:

```python
# The __init__.py handles this gracefully:
try:
    from src.utils.learning import PerformanceTracker
except ImportError:
    # Fallback or warning
    pass
```

### Thread Safety

All PerformanceTracker operations are thread-safe:
```python
import threading

tracker = PerformanceTracker()

def worker():
    for i in range(100):
        tracker.record(0.1, success=True)

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# Safe: all 1000 measurements recorded
assert len(tracker) == 1000
```

## Performance Characteristics

### PerformanceTracker
- **Record:** O(1) - using deque with maxlen
- **Get stats:** O(n) where n = window_size
- **Thread safety:** Lock-based, minimal contention
- **Memory:** O(window_size)

### JSON Repair
- **Time:** O(n) where n = string length
- **Space:** O(n) for repaired string
- **Max attempts:** 3 by default

### Path Operations
- **safe_path:** O(1) path operations
- **generate_slug:** O(n) string operations
- **ensure_directory:** O(depth) directory creation

### Retry Decorators
- **Overhead:** Minimal (function wrapping)
- **Backoff:** Exponential with cap
- **Memory:** O(1) per retry

## Best Practices

### 1. Performance Tracking
```python
# Good: Appropriate window size for your use case
tracker = PerformanceTracker(window_size=1000)  # Last 1000 operations

# Good: Include metadata for debugging
tracker.record(1.5, success=False, metadata={'error': 'timeout', 'model': 'llama2'})

# Good: Check stats periodically
if stats['failure_rate'] > 0.1:  # More than 10% failures
    alert_team()
```

### 2. JSON Repair
```python
# Good: Always handle repair failures
try:
    clean = repair_json(llm_response)
except ValueError as e:
    logger.error(f"Could not repair JSON: {e}")
    # Fallback logic
```

### 3. Path Operations
```python
# Good: Always use safe_path for user input
user_file = request.params.get('file')
safe_file = safe_path(base_dir, user_file)

# Good: Validate paths before use
if is_safe_path(user_file, allowed_extensions=['.txt', '.json']):
    process(user_file)
```

### 4. Retry Logic
```python
# Good: Retry only specific exceptions
@retry_with_backoff(exceptions=(ConnectionError, TimeoutError))
def network_call():
    pass

# Good: Set reasonable limits
@retry_with_backoff(max_attempts=3, max_delay=30.0)
def expensive_operation():
    pass
```

### 5. Validation
```python
# Good: Validate at system boundaries
def api_endpoint(data):
    validate_config(data, required_fields=['api_key'])
    # Process validated data
    
# Good: Provide clear param names in errors
validate_input(user_age, param_name="user_age", expected_type=int, min_value=0)
```

## Dependencies

**None!** All utilities use only Python standard library:
- `collections.deque`
- `threading.Lock`
- `pathlib.Path`
- `re`
- `json`
- `time`
- `functools`
- `logging`
- `urllib.parse`

## Self-Review Checklist

- [x] All utilities implemented and tested
- [x] PerformanceTracker thread-safe
- [x] JSON repair handles edge cases
- [x] Tests cover error paths
- [x] Type hints on all functions
- [x] Docstrings with examples
- [x] No external dependencies
- [x] All tests pass
