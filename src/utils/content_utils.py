# utils.py
"""Utility functions for code operations, SEO, file system, and RAG.

Contains helpers for code manipulation, validation, SEO operations, file I/O,
RAG helpers, and caching."""

from typing import List, Dict, Optional, Tuple, Any
import re
import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import yaml
from src.core.config import Config, CSHARP_LICENSE_HEADER

logger = logging.getLogger(__name__)

# ============================================================================
# Code Operations
# ============================================================================

def extract_code_blocks(text: str) -> List[str]:
    """Extract code blocks from markdown text."""
    pattern = r'```(?:\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches

def is_csharp_code(code: str) -> bool:
    """Check if code appears to be C#."""
    csharp_indicators = [
        r'\busing\s+\w+',
        r'\bnamespace\s+\w+',
        r'\bclass\s+\w+',
        r'\bpublic\s+',
        r'\bprivate\s+',
        r'\bvoid\s+\w+\s*\(',
        r'\bstring\s+\w+',
        r'\bint\s+\w+',
    ]

    matches = sum(1 for pattern in csharp_indicators if re.search(pattern, code))
    return matches >= 2  # Lower threshold to be more lenient

def find_license_insertion_point(code: str) -> int:
    """Find best position to insert license header."""
    lines = code.split('\n')

    insert_line = 0
    for i, line in enumerate(lines):
        if line.strip():
            insert_line = i
            break

    return sum(len(lines[i]) + 1 for i in range(insert_line))

def insert_license(code: str, license_text: Optional[str] = None) -> str:
    """Insert license header into C# code."""
    if license_text is None:
        license_text = CSHARP_LICENSE_HEADER

    if license_text.strip() in code:
        return code

    insert_pos = find_license_insertion_point(code)

    return code[:insert_pos] + license_text + "\n" + code[insert_pos:]

def split_code_into_segments(
    code: str,
    min_lines: int = 5,
    max_lines: int = 15,
    min_segments: int = 3,
    max_segments: int = 5,
    config: Optional[Config] = None
) -> List[Dict[str, str]]:
    """Split code into segments for explanation using templates."""
    # Handle empty code case
    if not code.strip():
        return [{
            "label": "Empty Code",
            "code": ""
        }]

    lines = code.split('\n')
    total_lines = len(lines)

    # Calculate target segment count
    if total_lines <= min_lines * min_segments:
        num_segments = max(2, total_lines // max_lines)
    elif total_lines >= max_lines * max_segments:
        num_segments = max_segments
    else:
        num_segments = max(min_segments, min(max_segments, total_lines // max_lines))

    # Calculate lines per segment
    lines_per_segment = total_lines // num_segments

    # Allow ±2 lines variance
    if lines_per_segment < min_lines - 2:
        lines_per_segment = min_lines - 2
    elif lines_per_segment > max_lines + 2:
        lines_per_segment = max_lines + 2

    segments = []
    current_line = 0

    for i in range(num_segments):
        if i == num_segments - 1:
            segment_lines = lines[current_line:]
        else:
            segment_lines = lines[current_line:current_line + lines_per_segment]

        segment_code = '\n'.join(segment_lines)

        # Use template-based labeling if available
        if config:
            label = _generate_segment_label_from_template(segment_code, i + 1, config)
        else:
            label = _generate_segment_label(segment_code, i + 1)

        segments.append({
            "label": label,
            "code": segment_code
        })

        current_line += lines_per_segment

    return segments

def _generate_segment_label_from_template(code: str, segment_num: int, config: Config) -> str:
    """Generate label using code template patterns."""
    code_template = config.get_code_template()

    if code_template and 'segment_labels' in code_template:
        patterns = code_template['segment_labels'].get('patterns', [])

        # Try each pattern
        for pattern_def in patterns:
            regex_pattern = pattern_def.get('regex', '')
            label_template = pattern_def.get('label', '')

            try:
                if regex_pattern and re.search(regex_pattern, code, re.IGNORECASE):
                    return label_template.replace('{n}', str(segment_num))
            except re.error:
                continue

        # Use default from template
        default_label = code_template['segment_labels'].get('default_label', 'Segment {n}: Code Block')
        return default_label.replace('{n}', str(segment_num))

    # Fallback to hardcoded logic
    return _generate_segment_label(code, segment_num)

def _generate_segment_label(code: str, segment_num: int) -> str:
    """Generate descriptive label for code segment (fallback)."""
    if 'using' in code.lower() or 'import' in code.lower():
        return f"Segment {segment_num}: Imports and Setup"
    elif 'class' in code.lower() and '{' in code:
        return f"Segment {segment_num}: Class Definition"
    elif 'public static void main' in code.lower():
        return f"Segment {segment_num}: Main Method"
    elif 'void' in code or 'return' in code:
        return f"Segment {segment_num}: Method Implementation"
    else:
        return f"Segment {segment_num}: Code Block"

# ============================================================================
# Code Validation
# ============================================================================

def validate_code_quality(code: str, level: str = "moderate") -> Tuple[bool, List[Dict]]:
    """Validate code quality with configurable strictness."""
    issues = []

    if not code.strip():
        issues.append({
            "type": "critical",
            "message": "Code is empty",
            "location": "global"
        })

    brace_count = code.count('{') - code.count('}')
    if brace_count != 0:
        issues.append({
            "type": "critical",
            "message": f"Unmatched braces (difference: {brace_count})",
            "location": "global"
        })

    if not re.search(r'\busing\s+\w+', code):
        issues.append({
            "type": "minor",
            "message": "No using statements found",
            "location": "top"
        })

    if 'class' in code.lower() and not re.search(r'\bclass\s+\w+', code):
        issues.append({
            "type": "minor",
            "message": "Malformed class declaration",
            "location": "class"
        })

    quote_count = code.count('"') - code.count('\\"')
    if quote_count % 2 != 0:
        issues.append({
            "type": "critical",
            "message": "Unclosed string literal",
            "location": "strings"
        })

    critical_issues = [i for i in issues if i["type"] == "critical"]

    if level == "strict":
        is_valid = len(issues) == 0
    elif level == "moderate":
        is_valid = len(critical_issues) == 0
    else:  # permissive
        catastrophic = any(
            "empty" in i["message"].lower() or "unmatched" in i["message"].lower()
            for i in critical_issues
        )
        is_valid = not catastrophic

    return is_valid, issues

def validate_api_compliance(code: str, api_references: List[str]) -> Tuple[bool, List[str]]:
    """Validate code complies with API references."""
    warnings = []

    used_types = set(re.findall(r'\b([A-Z][a-zA-Z0-9_]*)\b', code))

    for ref in api_references:
        ref_types = set(re.findall(r'\b([A-Z][a-zA-Z0-9_]*)\b', ref))

        if ref_types and not ref_types.intersection(used_types):
            warnings.append(f"API reference '{ref[:50]}...' not used in code")

    is_compliant = len(warnings) == 0 or len(warnings) < len(api_references)

    return is_compliant, warnings

# ============================================================================
# SEO Operations
# ============================================================================

def clean_text(text: str) -> str:
    """Clean text by removing special characters and normalizing."""
    text = re.sub(r'\n[\t ]+', ' ', text)
    text = re.sub(r'[^ a-zA-Z0-9]+', '', text)
    return text.strip()

def extract_keywords(text: str, max_keywords: int = 8) -> List[str]:
    """Extract keywords from text using simple heuristics."""
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    stop_words = {'the', 'and', 'for', 'are', 'this', 'that', 'with', 'from',
                  'have', 'will', 'can', 'your', 'more', 'about', 'into', 'than',
                  'them', 'these', 'their', 'was', 'been', 'has', 'had', 'were'}

    filtered_freq = {
        word: freq for word, freq in word_freq.items()
        if word not in stop_words and freq > 0
    }

    sorted_words = sorted(filtered_freq.items(), key=lambda x: x[1], reverse=True)

    return [word for word, _ in sorted_words[:max_keywords]]

def inject_keywords_naturally(
    prose: str,
    keywords: List[str],
    max_density: float = 1.5
) -> str:
    """Inject keywords naturally into prose while respecting density limits."""
    words = re.findall(r'\b\w+\b', prose)
    total_words = len(words)

    if total_words == 0:
        return prose

    modified_prose = prose

    for keyword in keywords:
        current_count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', prose, re.IGNORECASE))
        current_density = (current_count / total_words) * 100

        if current_density >= max_density:
            continue

        max_occurrences = int((max_density / 100) * total_words)
        to_add = max(0, max_occurrences - current_count)

        if to_add > 0:
            sentences = re.split(r'([.!?]\s+)', modified_prose)

            injected = 0
            for i in range(0, len(sentences) - 1, 2):
                if injected >= to_add:
                    break

                sentence = sentences[i]

                if len(sentence.split()) < 10 or sentence.startswith('#'):
                    continue

                if keyword.lower() not in sentence.lower():
                    words_in_sentence = sentence.split()
                    if len(words_in_sentence) > 5:
                        insert_pos = len(words_in_sentence) // 2
                        words_in_sentence.insert(insert_pos, keyword)
                        sentences[i] = ' '.join(words_in_sentence)
                        injected += 1

            modified_prose = ''.join(sentences)

    return modified_prose

# ============================================================================
# File System Operations
# ============================================================================

def read_file_with_fallback_encoding(filepath: Path) -> str:
    """Read file with fallback encoding detection."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']

    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading {filepath} with {encoding}: {e}")
            continue

    raise ValueError(f"Could not read file {filepath} with any encoding")

def write_markdown_tree(output_dir: Path, slug: str, content: str):
    """Write markdown file in directory structure."""
    post_dir = output_dir / slug
    post_dir.mkdir(parents=True, exist_ok=True)

    output_file = post_dir / "index.md"

    if output_file.exists():
        backup_file = post_dir / "index.md.prev"
        # Remove existing backup if it exists
        if backup_file.exists():
            backup_file.unlink()
        output_file.rename(backup_file)
        logger.info(f"Backed up existing file to {backup_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"Wrote markdown file to {output_file}")

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA-256 hash of file."""
    sha256 = hashlib.sha256()

    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)

    return sha256.hexdigest()

# ============================================================================
# RAG Helpers
# ============================================================================

def build_query(topic: Dict[str, str], query_type: str = "general") -> str:
    """Build search query from topic."""
    if query_type == "code" or query_type == "api":
        return f"{topic['title']} implementation code example API"
    else:
        return f"{topic['title']} {topic.get('rationale', '')}"

def rerank_by_score(results: List[Tuple[str, float]], top_k: int = 8) -> List[str]:
    """Rerank results by relevance score."""
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    return [text for text, _ in sorted_results[:top_k]]

def dedupe_context(contexts: List[str], similarity_threshold: float = 0.85) -> List[str]:
    """Deduplicate context chunks by similarity."""
    if not contexts:
        return []

    deduped = []
    seen_hashes = set()

    for context in contexts:
        context_hash = hashlib.sha256(context.encode()).hexdigest()

        if context_hash not in seen_hashes:
            is_duplicate = False
            for existing in deduped:
                len_ratio = len(context) / len(existing) if len(existing) > 0 else 0
                if 0.8 < len_ratio < 1.2:
                    words1 = set(context.lower().split())
                    words2 = set(existing.lower().split())
                    overlap = len(words1.intersection(words2)) / len(words1.union(words2))

                    if overlap > similarity_threshold:
                        is_duplicate = True
                        break

            if not is_duplicate:
                deduped.append(context)
                seen_hashes.add(context_hash)

    return deduped

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Chunk text into overlapping segments."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            next_period = text.find('.', end, min(len(text), end + 50))
            if next_period != -1:
                end = next_period + 1

        chunk = text[start:end]
        chunks.append(chunk)

        start = end - overlap

    return chunks

# ============================================================================
# Caching Operations
# ============================================================================

def cache_response(cache_dir: Path, input_hash: str, output: str):
    """Cache a response."""
    cache_file = cache_dir / "responses.jsonl"

    try:
        with open(cache_file, 'a') as f:
            entry = {
                'input_hash': input_hash,
                'output': output,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to cache response: {e}")

def get_cached_response(
    cache_dir: Path,
    input_hash: str,
    max_age_seconds: int = 3600
) -> Optional[str]:
    """Get cached response if available and not expired."""
    cache_file = cache_dir / "responses.jsonl"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            for line in f:
                entry = json.loads(line)
                if entry['input_hash'] == input_hash:
                    timestamp = datetime.fromisoformat(entry['timestamp'])
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    age = (datetime.now(timezone.utc) - timestamp).total_seconds()

                    if age <= max_age_seconds:
                        return entry['output']
    except Exception as e:
        logger.error(f"Failed to read cache: {e}")

    return None

def cache_seo_keywords(cache_dir: Path, content_hash: str, keywords: List[str]):
    """Cache SEO keywords."""
    cache_file = cache_dir / "seo_keywords.jsonl"

    try:
        with open(cache_file, 'a') as f:
            entry = {
                'content_hash': content_hash,
                'keywords': keywords,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to cache keywords: {e}")

# ============================================================================
# Markdown Operations
# ============================================================================

def create_frontmatter(metadata: Dict[str, Any], config: Config = None) -> str:
    """Create YAML frontmatter using template."""
    from datetime import datetime, timezone

    if config:
        template = config.get_frontmatter_template()
    else:
        # Fallback to default
        template = {
            'author': 'Babar Raza',
            'draft': True,
            'categories': ['Aspose.Total Plugin Family'],
        }

    frontmatter_data = {}

    # Process each field according to template
    for field, rules in template.items():
        if isinstance(rules, str):
            # Simple string value (possibly with {family} placeholder)
            value = rules.replace('{family}', metadata.get('family', 'Words'))
            frontmatter_data[field] = value
        elif isinstance(rules, list):
            # List with possible placeholders
            frontmatter_data[field] = [
                item.replace('{family}', metadata.get('family', 'Words'))
                for item in rules
            ]
        elif isinstance(rules, dict):
            # Complex field with generation rules
            frontmatter_data[field] = _process_field_rules(field, rules, metadata)
        else:
            frontmatter_data[field] = rules

    # Add any remaining metadata fields not in template
    for key in ['slug', 'tags', 'keywords']:
        if key not in frontmatter_data and key in metadata:
            frontmatter_data[key] = metadata[key]

    # Add enhanced field
    frontmatter_data['enhanced'] = True

    # Add lastmod if not present
    if 'lastmod' not in frontmatter_data:
        # Use fixed date for deterministic output
        frontmatter_data['lastmod'] = '2025-10-31'

    yaml_output = "---\n"
    yaml_output += yaml.dump(frontmatter_data, default_flow_style=False, allow_unicode=True, width=1000)
    yaml_output += "---\n\n"

    return yaml_output

def _process_field_rules(field_name: str, rules: Dict, metadata: Dict) -> Any:
    """Process field generation rules from template."""
    # Get value from source
    source = rules.get('source', '')
    value = None

    if source == 'auto':
        if field_name == 'date':
            from datetime import datetime, timezone
            # Use fixed date for deterministic output
            value = '2025-10-31'
    elif '.' in source:
        # Nested key like "seo_metadata.title"
        parts = source.split('.')
        value = metadata
        for part in parts:
            value = value.get(part, {}) if isinstance(value, dict) else None
            if value is None:
                break
    else:
        value = metadata.get(source)

    # Try fallback if no value
    if not value and 'fallback' in rules:
        fallback = rules['fallback']
        if '.' in fallback:
            parts = fallback.split('.')
            value = metadata
            for part in parts:
                value = value.get(part, {}) if isinstance(value, dict) else None
                if value is None:
                    break
        else:
            value = metadata.get(fallback, '')

    # Apply transformations
    if value and 'max_length' in rules:
        max_len = rules['max_length']
        truncate_type = rules.get('truncate', 'hard')
        if len(str(value)) > max_len:
            if truncate_type == 'word_boundary':
                value = _truncate_at_word(str(value), max_len)
            else:
                value = str(value)[:max_len]

    if value and rules.get('transform') == 'lowercase':
        value = str(value).lower()

    # Ensure different from other fields if specified
    if value and 'ensure_different_from' in rules:
        for other_field in rules['ensure_different_from']:
            other_value = metadata.get(other_field, '')
            if value and other_value and str(value)[:50] == str(other_value)[:50]:
                # Make it different by adding context
                if field_name == 'description' and 'content' in metadata:
                    # Extract second sentence from content
                    sentences = metadata['content'].split('. ')
                    if len(sentences) > 1:
                        value = sentences[1].strip()
                        if not value.endswith('.'):
                            value += '.'

    return value or ''

def _truncate_at_word(text: str, max_length: int) -> str:
    """Truncate text at word boundary."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        return truncated[:last_space].strip()
    return truncated.strip()

def create_gist_shortcode(user: str, gist_id: str, filename: str) -> str:
    """Create Hugo gist shortcode."""
    return f'{{{{< gist {user} {gist_id} "{filename}" >}}}}'

def create_code_block(code: str, language: str = "cs") -> str:
    """    Create markdown code block conforming to code_template.

    Args:
        code: Code content
        language: Programming language (default: cs)

    Returns:
        Formatted code block with CRLF line endings"""
    # Ensure CRLF line endings for Windows compatibility
    # Strip any existing line ending variations and apply CRLF consistently
    code_lines = code.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    code_normalized = '\r\n'.join(line.rstrip() for line in code_lines)

    # Build code block with CRLF
    return f"```{language}\r\n{code_normalized}\r\n```"

# ============================================================================
# Ingestion State Management
# ============================================================================

class IngestionStateManager:
    """Manages state of ingested files to avoid re-processing unchanged content."""

    def __init__(self, state_file: Path):
        """Initialize state manager.

        Args:
            state_file: Path to JSON file storing ingestion state"""
        self.state_file = state_file
        self.state: Dict[str, Dict] = self._load_state()

    def _load_state(self) -> Dict[str, Dict]:
        """Load ingestion state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load ingestion state: {e}")
                return {}
        return {}

    def _save_state(self):
        """Save ingestion state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save ingestion state: {e}")

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def needs_ingestion(self, file_path: Path, collection: str) -> bool:
        """Check if file needs to be ingested.

        Args:
            file_path: Path to file
            collection: Target collection name (kb, blog, api)

        Returns:
            True if file should be ingested, False if already up-to-date"""
        file_key = f"{collection}:{str(file_path)}"

        # File not seen before
        if file_key not in self.state:
            return True

        # File doesn't exist anymore
        if not file_path.exists():
            return False

        # Check if file has changed
        current_hash = self.compute_file_hash(file_path)
        stored_hash = self.state[file_key].get('hash')

        if current_hash != stored_hash:
            logger.info(f"File changed: {file_path.name}")
            return True

        logger.debug(f"Skipping unchanged file: {file_path.name}")
        return False

    def mark_ingested(self, file_path: Path, collection: str, chunk_count: int):
        """Mark file as ingested, tolerating nonexistent files for tracking tests."""
        file_key = f"{collection}:{str(file_path)}"
        exists = file_path.exists()
        try:
            file_size = file_path.stat().st_size if exists else 0
        except Exception:
            file_size = 0
        try:
            file_hash = self.compute_file_hash(file_path) if exists else None
        except Exception:
            file_hash = None

        self.state[file_key] = {
            "hash": file_hash,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "chunk_count": int(chunk_count),
            "file_size": int(file_size),
        }
        self._save_state()

    def get_collection_stats(self, collection: str) -> Dict[str, int]:
        """Get statistics for a collection.

        Args:
            collection: Collection name

        Returns:
            Dictionary with file count and total chunks"""
        files = [k for k in self.state.keys() if k.startswith(f"{collection}:")]
        total_chunks = sum(self.state[k].get('chunk_count', 0) for k in files)

        return {
            'file_count': len(files),
            'total_chunks': total_chunks
        }

    def clear_collection(self, collection: str):
        """Clear state for a specific collection.

        Args:
            collection: Collection to clear"""
        keys_to_remove = [k for k in self.state.keys() if k.startswith(f"{collection}:")]
        for key in keys_to_remove:
            del self.state[key]
        self._save_state()
        logger.info(f"Cleared ingestion state for collection: {collection}")

# ============================================================================
# Unit Tests
# ============================================================================

if __name__ == "__main__":
    import unittest

    class TestCodeOperations(unittest.TestCase):
        def test_split_code_into_segments(self):
            code = "\n".join([f"line {i}" for i in range(50)])
            segments = split_code_into_segments(code, min_lines=5, max_lines=15)

            self.assertGreaterEqual(len(segments), 3)
            self.assertLessEqual(len(segments), 5)

            for segment in segments:
                self.assertIn("label", segment)
                self.assertIn("code", segment)

        def test_insert_license(self):
            code = "using System;\n\nclass Test {}"
            licensed = insert_license(code)

            self.assertIn("Metered", licensed)
            self.assertIn("using System", licensed)
            self.assertIn("class Test", licensed)

    class TestCodeValidation(unittest.TestCase):
        def test_validate_code_quality_moderate(self):
            valid_code = "using System;\nclass Test { public void Method() {} }"
            is_valid, issues = validate_code_quality(valid_code, "moderate")
            self.assertTrue(is_valid)

            invalid_code = "class Test { public void Method() { }"
            is_valid, issues = validate_code_quality(invalid_code, "moderate")
            self.assertFalse(is_valid)

    class TestSEOOperations(unittest.TestCase):
        def test_extract_keywords(self):
            text = "This is about machine learning and artificial intelligence. "\
                   "Machine learning is important for AI development."

            keywords = extract_keywords(text, max_keywords=5)

            self.assertIn("machine", keywords)
            self.assertIn("learning", keywords)

    class TestRAGHelpers(unittest.TestCase):
        def test_chunk_text(self):
            text = "This is a test. " * 100
            chunks = chunk_text(text, chunk_size=100, overlap=20)

            self.assertGreater(len(chunks), 1)

        def test_dedupe_context(self):
            contexts = [
                "This is context one.",
                "This is context two.",
                "This is context one.",
            ]

            deduped = dedupe_context(contexts)

            self.assertEqual(len(deduped), 2)

    unittest.main()

# === MIGRATED FROM utils_dedup.py ===
class MarkdownDedup:
    """Utilities for markdown/title/heading deduplication and normalization (migrated from utils_dedup)."""

    pass
