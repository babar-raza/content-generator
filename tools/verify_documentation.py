#!/usr/bin/env python3
"""Verify that all referenced documentation exists."""

import re
from pathlib import Path
from typing import List, Tuple
import sys


def extract_doc_references(readme_path: Path) -> List[str]:
    """Extract documentation file references from README."""
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find markdown links: [text](docs/file.md)
    pattern = r'\[.+?\]\((docs/.+?\.md)\)'
    matches = re.findall(pattern, content)
    
    # Find direct references: docs/file.md
    pattern2 = r'(?:^|\s)(docs/[a-zA-Z0-9_/-]+\.md)'
    matches2 = re.findall(pattern2, content)
    
    return list(set(matches + matches2))


def verify_docs(doc_references: List[str], base_path: Path) -> Tuple[List[str], List[str]]:
    """Verify which docs exist and which are missing."""
    existing = []
    missing = []
    
    for doc_ref in doc_references:
        doc_path = base_path / doc_ref
        if doc_path.exists():
            existing.append(doc_ref)
        else:
            missing.append(doc_ref)
    
    return existing, missing


def create_missing_docs(missing: List[str], base_path: Path):
    """Create stub files for missing documentation."""
    for doc_ref in missing:
        doc_path = base_path / doc_ref
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create stub content
        title = doc_path.stem.replace('-', ' ').replace('_', ' ').title()
        stub_content = f"""# {title}

**Status:** 🚧 Documentation In Progress

## Overview

TODO: Add overview

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## Getting Started

TODO: Add getting started guide

## Usage

TODO: Add usage instructions

## Examples

TODO: Add examples

## API Reference

TODO: Add API reference

## Troubleshooting

TODO: Add troubleshooting guide

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
"""
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(stub_content)
        
        print(f"Created: {doc_ref}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify documentation')
    parser.add_argument('--create-missing', action='store_true',
                       help='Create stub files for missing docs')
    parser.add_argument('--base-path', default='.',
                       help='Base path for the project')
    
    args = parser.parse_args()
    
    base_path = Path(args.base_path)
    readme_path = base_path / 'README.md'
    
    if not readme_path.exists():
        print(f"Error: README.md not found at {readme_path}")
        sys.exit(1)
    
    # Extract references
    print("Extracting documentation references from README...")
    doc_refs = extract_doc_references(readme_path)
    print(f"Found {len(doc_refs)} documentation references\n")
    
    # Verify
    existing, missing = verify_docs(doc_refs, base_path)
    
    # Report
    print("Documentation Status:")
    print("=" * 60)
    
    for doc in sorted(existing):
        print(f"✓ {doc}")
    
    for doc in sorted(missing):
        print(f"✗ {doc} MISSING")
    
    print("=" * 60)
    print(f"\nSummary: {len(existing)}/{len(doc_refs)} docs found, {len(missing)} missing")
    
    # Create missing if requested
    if args.create_missing and missing:
        print("\nCreating missing documentation...")
        create_missing_docs(missing, base_path)
        print(f"\nCreated {len(missing)} stub files")
        print("Please fill in the TODO sections in each file")
    
    # Exit with error if docs missing and not creating them
    if missing and not args.create_missing:
        sys.exit(1)


if __name__ == '__main__':
    main()
