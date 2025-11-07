#!/usr/bin/env python3
import json, sys
from pathlib import Path

def main(path_json="reports/perf_results.json", path_md="reports/perf_summary.md"):
    p = Path(path_json)
    if not p.exists():
        print("No perf_results.json found.", file=sys.stderr)
        return 1
    data = json.loads(p.read_text(encoding="utf-8"))
    by_suite = {}
    for rec in data:
        by_suite.setdefault(rec["suite"], []).append(rec)
    lines = ["# Performance Summary", ""]
    for suite, rows in by_suite.items():
        lines.append(f"## {suite}")
        lines.append("")
        lines.append("| case | iters | mean (s) | p95 (s) | max (s) | stdev |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for r in rows:
            lines.append(f"| {r['case']} | {r['iters']} | {r['mean']:.4f} | {r['p95']:.4f} | {r['max']:.4f} | {r['stdev']:.4f} |")
        lines.append("")
    Path(path_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path_md}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
