#!/usr/bin/env python3
"""
Remove Legacy UI Files

This script removes all legacy dashboard and job detail UI files that are no longer
needed since the React UI has been deployed and covers the same functionality.

The React UI uses the MCP protocol endpoints which are now properly mounted.
"""

import os
import sys
from pathlib import Path

def remove_legacy_ui():
    """Remove all legacy UI files."""
    
    # Get project root
    script_dir = Path(__file__).parent
    
    # Files to remove
    legacy_files = [
        # Legacy HTML templates
        "src/web/templates/job_detail.html",
        "src/web/templates/job_detail_enhanced.html",
        "src/web/templates/dashboard.html",
        "src/web/templates/dashboard_integrated.html",
        "src/web/templates/test.html",
        
        # Legacy JavaScript
        "src/web/static/js/job_detail.js",
        "src/web/static/js/dashboard.js",
        
        # Legacy CSS (only used by removed templates)
        "src/web/static/css/styles.css",
        
        # Unused app files that serve legacy templates
        "src/web/app_integrated.py",
        "src/web/app_unified.py",
    ]
    
    removed = []
    not_found = []
    errors = []
    
    for file_path in legacy_files:
        full_path = script_dir / file_path
        
        if full_path.exists():
            try:
                if full_path.is_file():
                    full_path.unlink()
                    removed.append(file_path)
                    print(f"✓ Removed: {file_path}")
                else:
                    print(f"⚠ Skipped (not a file): {file_path}")
            except Exception as e:
                errors.append((file_path, str(e)))
                print(f"✗ Error removing {file_path}: {e}")
        else:
            not_found.append(file_path)
            print(f"○ Not found (already removed?): {file_path}")
    
    # Clean up empty directories
    empty_dirs = [
        "src/web/static/js",
        "src/web/static/css",
    ]
    
    for dir_path in empty_dirs:
        full_path = script_dir / dir_path
        if full_path.exists() and full_path.is_dir():
            try:
                if not any(full_path.iterdir()):
                    full_path.rmdir()
                    print(f"✓ Removed empty directory: {dir_path}")
            except Exception as e:
                print(f"⚠ Could not remove directory {dir_path}: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("LEGACY UI REMOVAL SUMMARY")
    print("=" * 60)
    print(f"Files removed: {len(removed)}")
    print(f"Files not found: {len(not_found)}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\nErrors encountered:")
        for file_path, error in errors:
            print(f"  - {file_path}: {error}")
        return 1
    
    print("\n✓ Legacy UI removal complete!")
    print("\nThe React UI at /src/web/static/dist/ is now the only UI.")
    print("It uses the MCP protocol endpoints at /mcp/*")
    print("\nNo legacy template routes exist in the main app.")
    
    return 0


if __name__ == "__main__":
    sys.exit(remove_legacy_ui())
