# Utils Module

## Overview

Utility functions and helper classes used throughout the system.

## Components

### `content_utils.py`
Content processing utilities.

```python
def extract_keywords(text: str) -> List[str]
def count_words(text: str) -> int
def sanitize_html(html: str) -> str
```

### `json_repair.py`
Repairs malformed JSON from LLM responses.

```python
def repair_json(json_str: str) -> Dict
def validate_json(json_str: str) -> bool
```

### `tone_utils.py`
Manages content tone and style.

```python
class ToneManager:
    """Tone management"""
    def apply_tone(self, content: str, tone: str) -> str
    def detect_tone(self, content: str) -> str
```

### `model_helper.py`
LLM provider utilities and helpers.

```python
def get_available_models() -> List[str]
def select_model(task: str) -> str
def estimate_tokens(text: str) -> int
```

### `ollama_detector.py`
Detects and validates Ollama installation.

```python
def is_ollama_available() -> bool
def get_ollama_models() -> List[str]
def test_ollama_connection() -> bool
```

### `resilience.py`
Retry logic and error recovery.

```python
@retry(max_attempts=3, backoff='exponential')
def resilient_call(func: Callable) -> Any
```

### `citation_tracker.py`
Tracks sources and citations.

```python
class CitationTracker:
    """Track content sources"""
    def add_citation(self, source: str, content: str)
    def generate_bibliography(self) -> List[str]
```

### `workflow_utils.py`
Workflow helper functions.

```python
def validate_workflow(workflow: Dict) -> ValidationResult
def resolve_dependencies(steps: List[Step]) -> List[Step]
```

### `dedup_utils.py`
Deduplication utilities.

```python
def find_duplicates(items: List[Any], threshold: float) -> List[Tuple]
def merge_duplicates(items: List[Any]) -> List[Any]
```

### `duplication_detector.py`
Advanced duplicate detection.

```python
class DuplicationDetector:
    """Detect duplicate content"""
    def detect(self, content: str) -> List[Match]
```

### `learning.py`
Self-learning and improvement utilities.

```python
class LearningManager:
    """Track and learn from executions"""
    def record_execution(self, metrics: Dict)
    def suggest_improvements(self) -> List[str]
```

### `mock_guard.py`
Prevents mock/stub code in production.

```python
def ensure_no_mocks(code: str) -> ValidationResult
def validate_production_ready(module: str) -> bool
```

### `simple_monitor.py`
Simple performance monitoring.

```python
class SimpleMonitor:
    """Basic monitoring"""
    def track(self, metric: str, value: float)
    def report(self) -> Dict
```

## Usage

```python
from src.utils.json_repair import repair_json
from src.utils.resilience import retry

# Repair malformed JSON
fixed = repair_json('{"key": "value"')

# Resilient function call
@retry(max_attempts=3)
def unstable_api_call():
    # API call that might fail
    pass
```

## Dependencies

- `structlog` - Logging
- `tenacity` - Retry logic (if used)
- Standard library modules
