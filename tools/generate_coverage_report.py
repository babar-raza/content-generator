#!/usr/bin/env python3
"""Generate test coverage report and check minimum threshold."""

import subprocess
import sys
import re
from pathlib import Path
import xml.etree.ElementTree as ET


def run_coverage(output_dir: Path = Path('htmlcov')):
    """Run pytest with coverage."""
    cmd = [
        'pytest',
        '--cov=src',
        '--cov-report=html',
        '--cov-report=xml',
        '--cov-report=term',
        '-v'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def parse_coverage_xml(xml_path: Path = Path('coverage.xml')) -> dict:
    """Parse coverage XML to get module-level coverage."""
    if not xml_path.exists():
        return {}
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    coverage_data = {}
    
    for package in root.findall('.//package'):
        for cls in package.findall('.//class'):
            filename = cls.get('filename')
            line_rate = float(cls.get('line-rate', 0))
            coverage_pct = line_rate * 100
            
            coverage_data[filename] = coverage_pct
    
    return coverage_data


def get_overall_coverage(xml_path: Path = Path('coverage.xml')) -> float:
    """Get overall coverage percentage."""
    if not xml_path.exists():
        return 0.0
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    line_rate = float(root.get('line-rate', 0))
    return line_rate * 100


def generate_badge(coverage_pct: float, output_path: Path = Path('coverage-badge.svg')):
    """Generate SVG coverage badge."""
    if coverage_pct >= 80:
        color = 'brightgreen'
    elif coverage_pct >= 70:
        color = 'green'
    elif coverage_pct >= 60:
        color = 'yellowgreen'
    elif coverage_pct >= 50:
        color = 'yellow'
    else:
        color = 'red'
    
    badge_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="100" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h61v20H0z"/>
    <path fill="{color}" d="M61 0h39v20H61z"/>
    <path fill="url(#b)" d="M0 0h100v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="30.5" y="15" fill="#010101" fill-opacity=".3">coverage</text>
    <text x="30.5" y="14">coverage</text>
    <text x="79.5" y="15" fill="#010101" fill-opacity=".3">{coverage_pct:.0f}%</text>
    <text x="79.5" y="14">{coverage_pct:.0f}%</text>
  </g>
</svg>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(badge_svg)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate coverage report')
    parser.add_argument('--min-coverage', type=float, default=70,
                       help='Minimum coverage percentage required')
    parser.add_argument('--generate-badge', action='store_true',
                       help='Generate coverage badge SVG')
    
    args = parser.parse_args()
    
    print("Running tests with coverage...")
    result = run_coverage()
    
    if result.returncode != 0:
        print("\nTests failed!")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    
    # Get coverage
    overall_coverage = get_overall_coverage()
    coverage_data = parse_coverage_xml()
    
    print(f"\nOverall Coverage: {overall_coverage:.1f}%")
    
    if overall_coverage >= args.min_coverage:
        print(f"✓ Meets minimum requirement ({args.min_coverage}%)")
    else:
        print(f"✗ Below minimum requirement ({args.min_coverage}%)")
    
    # Show modules below threshold
    below_threshold = {
        module: cov for module, cov in coverage_data.items()
        if cov < args.min_coverage
    }
    
    if below_threshold:
        print(f"\nModules below {args.min_coverage}% coverage:")
        for module, cov in sorted(below_threshold.items(), key=lambda x: x[1]):
            print(f"  - {module}: {cov:.1f}%")
    
    # Generate badge if requested
    if args.generate_badge:
        generate_badge(overall_coverage)
        print("\nGenerated coverage badge: coverage-badge.svg")
    
    print(f"\nDetailed HTML report: htmlcov/index.html")
    
    # Exit with error if below threshold
    if overall_coverage < args.min_coverage:
        sys.exit(1)


if __name__ == '__main__':
    main()
