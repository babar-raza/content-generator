#!/usr/bin/env python3
"""Parse pytest verbose output to extract failures."""
import json
import re
from pathlib import Path
from typing import Dict, List
import sys


def parse_pytest_output(input_file: Path) -> List[Dict]:
    """Parse pytest -vv output and extract failure information."""
    failures = []

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all FAILED lines
    failed_pattern = re.compile(
        r"FAILED (tests/[^\s]+) - (.+?)(?=\n(?:FAILED|PASSED|SKIPPED|={5,}|$))",
        re.DOTALL
    )

    for match in failed_pattern.finditer(content):
        nodeid = match.group(1)
        error_detail = match.group(2).strip()

        # Extract file:line if available
        file_line_match = re.search(r"(tests/[^:]+):(\d+)", error_detail)
        file_path = file_line_match.group(1) if file_line_match else nodeid.split("::")[0]
        line_num = file_line_match.group(2) if file_line_match else "?"

        # Extract assertion/exception headline
        headline = error_detail.split("\n")[0][:200]

        # Detect failure category
        category = categorize_failure(error_detail)

        failures.append({
            "nodeid": nodeid,
            "file": file_path,
            "line": line_num,
            "headline": headline,
            "category": category,
            "detail": error_detail[:500]  # Truncate for readability
        })

    return failures


def categorize_failure(error_detail: str) -> str:
    """Categorize failure based on error pattern."""
    error_lower = error_detail.lower()

    if "charmap" in error_lower or "codec can't encode" in error_lower or "unicodeencodeerror" in error_lower:
        return "UTF8_ENCODING"
    elif "config_hashes" in error_lower or "missing" in error_lower and "manifest" in error_lower:
        return "ARTIFACT_PERSISTENCE"
    elif "index.md" in error_lower or "output path" in error_lower:
        return "OUTPUT_PATH"
    elif "vectorstore" in error_lower and "none" in error_lower:
        return "VECTORSTORE_INIT"
    elif "database" in error_lower and "none" in error_lower:
        return "DATABASE_INIT"
    elif "embeddings" in error_lower and "none" in error_lower:
        return "EMBEDDINGS_INIT"
    elif "mcp" in error_lower and ("endpoint" in error_lower or "accessibility" in error_lower):
        return "MCP_ENDPOINT"
    elif "503" in error_detail or "service unavailable" in error_lower:
        return "SERVICE_UNAVAILABLE"
    elif "assert" in error_lower and "==" in error_detail:
        return "ASSERTION_MISMATCH"
    elif "typeerror" in error_lower:
        return "TYPE_ERROR"
    elif "attributeerror" in error_lower:
        return "ATTRIBUTE_ERROR"
    elif "keyerror" in error_lower:
        return "KEY_ERROR"
    else:
        return "OTHER"


def main():
    if len(sys.argv) != 3:
        print("Usage: parse_pytest_failures.py <input_file> <output_dir>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = parse_pytest_output(input_file)

    # Save JSON
    json_output = output_dir / "failures.json"
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(failures, f, indent=2)

    # Save Markdown
    md_output = output_dir / "failures.md"
    with open(md_output, "w", encoding="utf-8") as f:
        f.write(f"# Integration Test Failures\n\n")
        f.write(f"Total failures: {len(failures)}\n\n")

        for i, failure in enumerate(failures, 1):
            f.write(f"## {i}. {failure['nodeid']}\n\n")
            f.write(f"- **File:** {failure['file']}:{failure['line']}\n")
            f.write(f"- **Category:** {failure['category']}\n")
            f.write(f"- **Headline:** {failure['headline']}\n\n")
            f.write(f"```\n{failure['detail']}\n```\n\n")

    print(f"Parsed {len(failures)} failures")
    print(f"Saved to: {json_output} and {md_output}")


if __name__ == "__main__":
    main()
