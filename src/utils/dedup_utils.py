#!/usr/bin/env python3
"""
Heading Deduplication Utility for P2
Removes duplicate headings from generated markdown content
"""

import re
from typing import List, Tuple, Set
import logging

logger = logging.getLogger(__name__)

def deduplicate_headings(markdown_content: str) -> Tuple[str, List[dict]]:
    """
    Remove duplicate consecutive headings from markdown content.
    
    Args:
        markdown_content: The markdown content to process
        
    Returns:
        Tuple of (deduplicated_content, list_of_removed_duplicates)
    """
    lines = markdown_content.split('\n')
    result_lines = []
    removed_duplicates = []
    
    # Track seen headings in a sliding window
    previous_heading = None
    previous_heading_line = None
    
    for i, line in enumerate(lines, 1):
        # Check if this is a heading
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        
        if heading_match:
            level = heading_match.group(1)
            text = heading_match.group(2).strip()
            normalized = text.lower().strip(':.,;!?')
            current_heading = (level, normalized)
            
            # Check if this is a duplicate of the previous heading
            if current_heading == previous_heading:
                # This is a duplicate - skip it
                removed_duplicates.append({
                    'line': i,
                    'heading': line.strip(),
                    'level': level,
                    'text': text,
                    'previous_line': previous_heading_line
                })
                logger.info(f"Removed duplicate heading at line {i}: {line.strip()}")
                continue
            else:
                # New heading - track it
                previous_heading = current_heading
                previous_heading_line = i
        
        result_lines.append(line)
    
    deduplicated_content = '\n'.join(result_lines)
    return deduplicated_content, removed_duplicates

def remove_heading_from_content(content: str, heading_text: str) -> str:
    """
    Remove a specific heading line from content if it appears at the start.
    
    This is useful when generated content includes its own heading that
    conflicts with the template-provided heading.
    """
    lines = content.split('\n')
    
    if not lines:
        return content
    
    # Check first non-empty line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        # Check if it matches the heading to remove
        heading_match = re.match(r'^#{1,6}\s+(.+)$', stripped)
        if heading_match:
            extracted_text = heading_match.group(1).strip()
            normalized_extracted = extracted_text.lower().strip(':.,;!?')
            normalized_target = heading_text.lower().strip(':.,;!?')
            
            if normalized_extracted == normalized_target:
                # Remove this line
                lines.pop(i)
                # Also remove following empty line if present
                if i < len(lines) and not lines[i].strip():
                    lines.pop(i)
                return '\n'.join(lines)
        
        # If we hit non-heading content, stop
        break
    
    return content
# DOCGEN:LLM-FIRST@v4