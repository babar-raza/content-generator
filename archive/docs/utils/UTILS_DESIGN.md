# Utils Module - Design Overview

## Architecture

### 1. PerformanceTracker (learning.py)

```python
class PerformanceTracker:
    """Thread-safe performance metrics tracking with sliding window.
    
    Uses collections.deque for O(1) append/pop operations.
    Tracks execution time, success rates, and failure patterns.
    """
    
    def __init__(self, window_size: int = 100):
        """Initialize tracker with sliding window.
        
        Args:
            window_size: Max number of measurements to keep
        """
        
    def record(self, duration: float, success: bool = True, metadata: dict = None):
        """Record a single measurement.
        
        Thread-safe operation using Lock.
        """
        
    def get_stats(self) -> dict:
        """Calculate statistics over the window.
        
        Returns:
            {
                'count': int,
                'avg_duration': float,
                'min_duration': float,
                'max_duration': float,
                'success_rate': float,
                'p50': float,  # median
                'p95': float,  # 95th percentile
                'p99': float   # 99th percentile
            }
        """
        
    def reset(self):
        """Clear all measurements."""
```

**Implementation Details:**
- Uses `collections.deque(maxlen=window_size)` for automatic eviction
- `threading.Lock` for thread safety
- Stores tuples: `(timestamp, duration, success, metadata)`
- Percentile calculation using sorted list

---

### 2. JSON Repair (json_repair.py)

```python
def repair_json(text: str) -> str:
    """Repair common JSON errors from LLM responses.
    
    Fixes:
    - Trailing commas: {"a": 1,} → {"a": 1}
    - Unquoted keys: {name: "value"} → {"name": "value"}
    - Single quotes: {'a': 1} → {"a": 1}
    - Missing closing brackets
    - Control characters
    
    Args:
        text: Potentially malformed JSON string
        
    Returns:
        Repaired JSON string
        
    Raises:
        ValueError: If JSON cannot be repaired
    """
```

**Repair Strategy:**
1. Extract JSON from markdown code blocks
2. Replace single quotes with double quotes (outside strings)
3. Remove trailing commas
4. Quote unquoted keys
5. Balance brackets
6. Validate with `json.loads()`

---

### 3. Path Utilities (path_utils.py)

```python
def safe_path(base_dir: Path, user_path: str) -> Path:
    """Prevent path traversal attacks.
    
    Ensures resolved path is within base_dir.
    
    Args:
        base_dir: Root directory
        user_path: User-provided path
        
    Returns:
        Safe resolved path
        
    Raises:
        ValueError: If path escapes base_dir
    """

def generate_slug(text: str, max_length: int = 50) -> str:
    """Generate URL-safe slug from text.
    
    - Lowercase
    - Replace spaces/special chars with hyphens
    - Remove consecutive hyphens
    - Trim to max_length
    
    Args:
        text: Input text
        max_length: Maximum slug length
        
    Returns:
        URL-safe slug
        
    Example:
        >>> generate_slug("Hello, World! 123")
        'hello-world-123'
    """

def ensure_directory(path: Path) -> Path:
    """Create directory if it doesn't exist.
    
    Thread-safe, handles race conditions.
    """
```

---

### 4. Retry Decorator (retry.py)

```python
def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Retry decorator with exponential backoff.
    
    Delay formula: min(initial_delay * (exponential_base ** attempt), max_delay)
    
    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Backoff multiplier
        exceptions: Tuple of exceptions to catch
        
    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def fetch_data():
            # Retries 3 times with 1s, 2s, 4s delays
            pass
    """
```

**Backoff Schedule Example:**
- Attempt 1: immediate
- Attempt 2: wait 1.0s
- Attempt 3: wait 2.0s
- Attempt 4: wait 4.0s (or max_delay if exceeded)

---

### 5. Validators (validators.py)

```python
def validate_config(config: dict, required_fields: list, schema: dict = None) -> None:
    """Validate configuration dictionary.
    
    Args:
        config: Configuration dictionary
        required_fields: List of required field names
        schema: Optional type schema {field: type}
        
    Raises:
        ValueError: If validation fails
        
    Example:
        schema = {'api_key': str, 'timeout': int}
        validate_config(config, ['api_key'], schema)
    """

def validate_input(
    value: any,
    expected_type: type = None,
    min_value: any = None,
    max_value: any = None,
    allowed_values: list = None,
    pattern: str = None
) -> None:
    """Validate input against constraints.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        min_value: Minimum value (for numbers/lengths)
        max_value: Maximum value
        allowed_values: Whitelist of allowed values
        pattern: Regex pattern (for strings)
        
    Raises:
        TypeError: If type mismatch
        ValueError: If value out of range
    """

def validate_url(url: str, schemes: list = None) -> bool:
    """Validate URL format.
    
    Args:
        url: URL to validate
        schemes: Allowed schemes (default: ['http', 'https'])
        
    Returns:
        True if valid, False otherwise
    """
```

---

## Module Structure

```
src/utils/
├── __init__.py          # Export all utilities
├── learning.py          # PerformanceTracker
├── json_repair.py       # JSON repair utilities
├── path_utils.py        # Path operations
├── retry.py             # Retry decorators
└── validators.py        # Input validation

tests/unit/
└── test_utils.py        # Comprehensive tests
```

---

## Cross-Module Integration

### Typical Usage Flow

```python
from src.utils import (
    PerformanceTracker,
    repair_json,
    safe_path,
    generate_slug,
    retry_with_backoff,
    validate_config
)

# 1. Track performance
tracker = PerformanceTracker(window_size=100)

@retry_with_backoff(max_attempts=3)
def process_with_llm(prompt):
    start = time.time()
    try:
        response = llm.generate(prompt)  # May return malformed JSON
        repaired = repair_json(response)
        duration = time.time() - start
        tracker.record(duration, success=True)
        return repaired
    except Exception as e:
        duration = time.time() - start
        tracker.record(duration, success=False)
        raise

# 2. Safe file operations
base = Path("/data")
user_path = "outputs/report.txt"
safe_file = safe_path(base, user_path)

# 3. Generate slug for filename
title = "My Report: 2024 Analysis"
filename = f"{generate_slug(title)}.json"

# 4. Validate configuration
config = {'api_key': 'xxx', 'timeout': 30}
validate_config(config, ['api_key'], {'api_key': str, 'timeout': int})

# 5. Get performance metrics
stats = tracker.get_stats()
print(f"Average: {stats['avg_duration']:.2f}s, Success: {stats['success_rate']:.1%}")
```

---

## Design Principles

### 1. Thread Safety
- `PerformanceTracker` uses `threading.Lock`
- `ensure_directory` handles race conditions
- All utilities are stateless (except PerformanceTracker)

### 2. Error Handling
- Clear exception messages
- Type validation at boundaries
- Fail fast with informative errors

### 3. Performance
- O(1) operations for PerformanceTracker (deque)
- Lazy evaluation where possible
- Minimal allocations

### 4. Testability
- Pure functions (no side effects except I/O)
- Dependency injection where needed
- Clear success/failure paths

### 5. Documentation
- Docstrings with examples
- Type hints for IDE support
- Usage patterns documented

---

## Testing Strategy

### Unit Tests Coverage

1. **PerformanceTracker**
   - Basic recording
   - Statistics calculation
   - Thread safety (concurrent access)
   - Window size enforcement
   - Edge cases (empty, single item)

2. **JSON Repair**
   - Trailing commas (objects, arrays)
   - Unquoted keys
   - Single quotes
   - Nested structures
   - Edge cases (empty, invalid)

3. **Path Utils**
   - Path traversal prevention
   - Slug generation (special chars, unicode)
   - Directory creation (exists, permissions)

4. **Retry Decorator**
   - Successful retry
   - Max attempts exhausted
   - Backoff timing
   - Exception filtering

5. **Validators**
   - Config validation (missing, wrong type)
   - Input validation (range, pattern)
   - URL validation (schemes, formats)

---

## Dependencies

**All Standard Library:**
- `collections.deque` - Sliding window
- `threading.Lock` - Thread safety
- `pathlib.Path` - Path operations
- `re` - Regex for slug/validation
- `json` - JSON parsing
- `time` - Delays and timing
- `functools` - Decorator wrapping
- `logging` - Retry logging
- `urllib.parse` - URL validation

**No External Dependencies Required**
