
"""Mock/placeholder content detector for agents and aggregators."""

import re
from typing import Any, Dict, List, Tuple

# Common placeholder patterns that indicate mock outputs
_PLACEHOLDER_PATTERNS = [
    r"\blorem ipsum\b",
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bplaceholder\b",
    r"\bsample\b",
    r"\bdummy\b",
    r"\bmock\b",
    r"Your Optimized Title Here",
    r"\buntitled[-_\s]?topic\b",
    r"\btopic[_-]?output\b",
    r"\bwrite your .* here\b",
    r"\bcoming soon\b",
    r"\breplace this\b",
    r"\bauto[-\s]?generated\b",
    r"\btemplate\b.*\bfill\b",
    r"\bYour Title\b",
    r"\bBrand Name\b",
    r"\btag1\b|\btag2\b",
]

_PLACEHOLDER_RE = re.compile("|".join(f"(?:{p})" for p in _PLACEHOLDER_PATTERNS), re.IGNORECASE)

def _flatten_strings(obj: Any, acc: List[str]) -> None:
    if obj is None:
        return
    if isinstance(obj, str):
        acc.append(obj)
    elif isinstance(obj, (list, tuple, set)):
        for x in obj:
            _flatten_strings(x, acc)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            # keys can also be indicative
            if isinstance(k, str):
                acc.append(k)
            _flatten_strings(v, acc)

def is_mock_like(obj: Any) -> Tuple[bool, List[str]]:
    """Return (is_mock, hits) where hits are substrings that matched."""
    strings: List[str] = []
    _flatten_strings(obj, strings)
    hits = []
    for s in strings:
        m = _PLACEHOLDER_RE.search(s)
        if m:
            hits.append(m.group(0))
    return (len(hits) > 0, hits)

def annotate_status(output: Dict[str, Any]) -> Dict[str, Any]:
    """Return output enriched with 'status' and 'mock_hits' if detected."""
    is_mock, hits = is_mock_like(output)
    out = dict(output)
    if is_mock:
        out.setdefault("status", "mock")
        out["mock_hits"] = sorted(set(hits))
    else:
        out.setdefault("status", "ok")
    return out
