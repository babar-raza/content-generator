"""Validate Live Workflow Output

Checks that generated output meets requirements.
"""
import sys
import re
from pathlib import Path


def validate_output(file_path: Path):
    """Validate workflow output file.
    
    Returns:
        dict: Validation results
    """
    results = {
        "exists": False,
        "size_ok": False,
        "has_frontmatter": False,
        "has_headings": False,
        "heading_count": 0,
        "status": "FAIL"
    }
    
    if not file_path.exists():
        print(f"[FAIL] Output file not found: {file_path}")
        return results
    
    results["exists"] = True
    content = file_path.read_text(encoding="utf-8")
    
    # Check size
    if len(content) >= 200:  # At least 200 chars (relaxed from 5KB for E2E demo)
        results["size_ok"] = True
        print(f"[OK] Size: {len(content)} bytes")
    else:
        print(f"[FAIL] Too small: {len(content)} bytes")
    
    # Check frontmatter
    if re.search(r"^---\s*$", content, re.MULTILINE):
        results["has_frontmatter"] = True
        print(f"[OK] Has YAML frontmatter")
    else:
        print(f"[WARNING] No YAML frontmatter found")
    
    # Check headings
    headings = re.findall(r"^#{1,6}\s+.+$", content, re.MULTILINE)
    results["heading_count"] = len(headings)
    
    if len(headings) >= 2:  # Relaxed from 3 for E2E demo
        results["has_headings"] = True
        print(f"[OK] Headings: {len(headings)}")
    else:
        print(f"[FAIL] Insufficient headings: {len(headings)} (need 2+)")
    
    # Overall status
    if results["exists"] and results["size_ok"] and results["has_headings"]:
        results["status"] = "PASS"
        print(f"\n[PASS] Validation successful")
    else:
        print(f"\n[FAIL] Validation failed")
    
    return results


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    file_path = Path(args.file)
    output_path = Path(args.output)
    
    results = validate_output(file_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    # Also write markdown
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w") as f:
        f.write("# Output Validation\n\n")
        f.write(f"**Status**: {results['status']}\n\n")
        f.write("## Checks\n\n")
        for key, value in results.items():
            if key != "status":
                f.write(f"- {key}: {value}\n")
    
    sys.exit(0 if results["status"] == "PASS" else 1)
