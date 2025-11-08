#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/test_refactor.py
----------------------
Thorough, no-deps test refactoring tool that:
 - Scans /tests
 - Detects exact and near-duplicate tests (AST + token-normalized source)
 - Consolidates into a small canonical layout
 - Attempts conservative parametrize merges
 - Merges duplicate fixtures into tests/fixtures/conftest.py
 - Creates a backup zip and a machine-readable JSON report
 - Enforces CRLF for all written files (Windows-friendly)

Usage (dry run):
  python tools/test_refactor.py --verbose

Apply changes:
  python tools/test_refactor.py --apply --verbose

Only stdlib + pytest (at runtime when tests run). No new dependencies.
"""

import os, io, re, sys, json, ast, time, hashlib, zipfile, argparse, tokenize, textwrap
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Iterable, Any
from pathlib import Path
from difflib import SequenceMatcher

CRLF = "\r\n"

@dataclass(order=True)
class Span:
    start: int
    end: int

@dataclass
class TestFunction:
    file: Path
    name: str
    body_span: Span
    decorators: List[str]
    markers: List[str]
    is_fixture: bool
    source: str
    source_dedented: str
    src_norm: str
    ast_norm: str
    ast_hash: str
    src_hash: str
    num_asserts: int
    imports: List[str]
    classification: str = ""
    selected: bool = False
    cluster_id: Optional[int] = None

@dataclass
class Cluster:
    id: int
    members: List['TestFunction'] = field(default_factory=list)
    canonical: Optional['TestFunction'] = None
    similarity_basis: str = "ast"  # or 'src'
    merged: bool = False
    parametrized_code: Optional[str] = None
    reason: str = ""

@dataclass
class Report:
    timestamp: str
    root: str
    tests_dir: str
    backup_zip: Optional[str] = None
    threshold: float = 0.95
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    files_moved: List[Tuple[str, str]] = field(default_factory=list)
    functions_parametrized: List[Dict[str, Any]] = field(default_factory=list)
    fixtures_merged: List[Dict[str, Any]] = field(default_factory=list)
    clusters: List[Dict[str, Any]] = field(default_factory=list)
    lineage: Dict[str, Dict[str, Any]] = field(default_factory=dict)

# ----------------------------- Utilities ----------------------------------

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()

def _write_text_crlf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Normalize to CRLF unconditionally
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", CRLF)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def _zip_folder(src_dir: Path, dst_zip: Path) -> None:
    dst_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(src_dir.parent))

def _now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())

# ---------------------- Normalization & Hashing ----------------------------

def normalize_source_for_hash(source: str) -> str:
    """
    Tokenize to remove comments, normalize strings/numbers/whitespace.
    Keeps code structure but removes noise for duplicate detection.
    """
    out = []
    try:
        reader = io.StringIO(source).readline
        for toknum, tokval, *_ in tokenize.generate_tokens(reader):
            if toknum == tokenize.COMMENT:
                continue
            if toknum == tokenize.STRING:
                out.append('"STR"')
                continue
            if toknum == tokenize.NUMBER:
                out.append("0")
                continue
            if toknum in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                out.append("\n")
                continue
            # Normalize whitespace around operators/names
            if toknum == tokenize.NAME:
                # Keep pytest keywords and 'test_' names recognizable
                if tokval.startswith("test_") or tokval in {"pytest", "assert", "True", "False", "None"}:
                    out.append(tokval)
                else:
                    out.append("NAME")
                continue
            out.append(tokval)
    except tokenize.TokenError:
        # Fallback: crude normalization
        s = re.sub(r"#.*", "", source)  # strip comments
        s = re.sub(r'".*?"|\'.*?\'', '"STR"', s)  # strings
        s = re.sub(r"\b\d+(\.\d+)?\b", "0", s)     # numbers
        s = re.sub(r"\s+", " ", s)
        return s.strip()
    joined = "".join(out)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined

class ASTNormalizer(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.AST:
        # Keep pytest, True/False/None recognizable; else normalize
        if node.id in {"pytest", "True", "False", "None"} or node.id.startswith("test_"):
            return node
        return ast.copy_location(ast.Name(id="NAME", ctx=type(node.ctx)()), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        return ast.copy_location(ast.Attribute(value=node.value, attr="ATTR", ctx=node.ctx), node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        v = node.value
        if isinstance(v, (str, bytes)):
            return ast.copy_location(ast.Constant(value="STR"), node)
        if isinstance(v, (int, float, complex)):
            return ast.copy_location(ast.Constant(value=0), node)
        return node

def normalized_ast_dump(node: ast.AST) -> str:
    norm = ASTNormalizer().visit(ast.fix_missing_locations(node))
    return ast.dump(norm, include_attributes=False)

def count_asserts(node: ast.AST) -> int:
    class C(ast.NodeVisitor):
        def __init__(self):
            self.n = 0
        def visit_Assert(self, n): self.n += 1
    c = C()
    c.visit(node)
    return c.n

def extract_imports(tree: ast.AST) -> List[str]:
    imports = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.append(alias.name)
        elif isinstance(n, ast.ImportFrom):
            module = n.module or ""
            imports.append(module)
    return imports

def extract_markers(func: ast.FunctionDef) -> List[str]:
    marks = []
    for d in func.decorator_list:
        # pytest.mark.something
        if isinstance(d, ast.Attribute) and isinstance(d.value, ast.Attribute):
            chain = []
            base = d
            while isinstance(base, ast.Attribute):
                chain.append(base.attr)
                base = base.value
            if isinstance(base, ast.Name) and base.id == "pytest":
                mark = ".".join(reversed(chain + ["pytest"]))
                marks.append(mark)
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
            base = d.func
            chain = []
            while isinstance(base, ast.Attribute):
                chain.append(base.attr)
                base = base.value
            if isinstance(base, ast.Name) and base.id == "pytest":
                chain.append("pytest")
                mark = ".".join(reversed(chain))
                marks.append(mark)
        elif isinstance(d, ast.Name):
            marks.append(d.id)
    return sorted(set(marks))

def is_fixture(func: ast.FunctionDef) -> bool:
    for d in func.decorator_list:
        # @pytest.fixture or @fixture
        if isinstance(d, ast.Attribute) and d.attr == "fixture":
            return True
        if isinstance(d, ast.Name) and d.id == "fixture":
            return True
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "fixture":
            return True
    return False

def get_body_span(source: str, func: ast.FunctionDef) -> 'Span':
    lines = source.splitlines(keepends=True)
    start = func.lineno - 1
    end = (func.end_lineno or func.lineno)
    return Span(start, end)

def get_source_segment_by_span(source: str, span: 'Span') -> str:
    lines = source.splitlines(keepends=True)
    seg = "".join(lines[span.start:span.end])
    return seg

# ----------------------- Discovery & Collection ----------------------------

def discover_test_files(tests_dir: Path) -> List[Path]:
    files = []
    for p in tests_dir.rglob("*.py"):
        name = p.name.lower()
        if name.startswith("test_") or name.endswith("_test.py") or p.name == "conftest.py":
            files.append(p)
    return sorted(files)

def collect_test_items(py_file: Path) -> Tuple[List['TestFunction'], List['TestFunction']]:
    """
    Returns (fixtures, tests)
    """
    source = _read_text(py_file)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ([], [])

    imports = extract_imports(tree)
    fixtures: List[TestFunction] = []
    tests: List[TestFunction] = []

    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            name = n.name
            span = get_body_span(source, n)
            segment = get_source_segment_by_span(source, span)
            seg_dedented = textwrap.dedent(segment)
            src_norm = normalize_source_for_hash(seg_dedented)
            ast_norm = normalized_ast_dump(n)
            obj = TestFunction(
                file=py_file,
                name=name,
                body_span=span,
                decorators=[ast.get_source_segment(source, d) or "" for d in n.decorator_list],
                markers=extract_markers(n),
                is_fixture=is_fixture(n),
                source=segment,
                source_dedented=seg_dedented,
                src_norm=src_norm,
                ast_norm=ast_norm,
                ast_hash=_sha256(ast_norm),
                src_hash=_sha256(src_norm),
                num_asserts=count_asserts(n),
                imports=imports,
            )
            (fixtures if obj.is_fixture else tests).append(obj)
    return fixtures, tests

# ------------------------- Classification ----------------------------------

def classify(item: TestFunction) -> str:
    imps = " ".join(item.imports)
    src = item.source_dedented
    # Unit: core/utils
    if re.search(r"\bsrc\.core\b|\bcore\.", imps) or re.search(r"\butils?\b", src):
        return "unit_core_utils"
    # Unit: engine/orchestrator
    if re.search(r"\bsrc\.engine\b|\borchestr", imps):
        return "unit_engine_orchestrator"
    # Unit: services/clients
    if re.search(r"\bsrc\.services\b|\bclients?\b", imps):
        return "unit_services_clients"
    # Integration: CLI/API
    if re.search(r"\bFastAPI\b|\buvicorn\b|\bhttpx\b|\brequests\b", imps + " " + src) or re.search(r"\bcli\b|\btyper\b|\bclick\b", src, re.I):
        return "integration_cli_api"
    # E2E
    if re.search(r"\b(end[-_ ]?to[-_ ]?end|full[-_ ]?job|workflow)\b", src, re.I):
        return "e2e"
    # Regression
    if re.search(r"\b(regression|bug|issue|xfail)\b", " ".join(item.markers + [src]), re.I):
        return "regression"
    # Perf
    if re.search(r"\bperformance|benchmark|tim(e|ing)\b", src, re.I):
        return "perf"
    # Fallback
    return "unit_core_utils"

CANONICAL_DEST = {
    "unit_core_utils":       Path("tests/unit/test_core_and_utils.py"),
    "unit_engine_orchestrator": Path("tests/unit/test_engine_and_orchestrator.py"),
    "unit_services_clients": Path("tests/unit/test_services_and_clients.py"),
    "integration_cli_api":   Path("tests/integration/test_cli_and_api.py"),
    "e2e":                   Path("tests/e2e/test_full_job_happy_path.py"),
    "regression":            Path("tests/regression/test_regressions.py"),
    "perf":                  Path("tests/perf/test_performance_smoke.py"),
}

# ----------------------- Clustering & Dedupe -------------------------------

def cluster_duplicates(items: List[TestFunction], threshold: float = 0.95) -> List['Cluster']:
    clusters: List[Cluster] = []
    by_hash: Dict[str, Cluster] = {}
    cid = 0
    for it in items:
        if it.ast_hash in by_hash:
            cl = by_hash[it.ast_hash]
            it.cluster_id = cl.id
            cl.members.append(it)
        else:
            cl = Cluster(id=cid, members=[it], similarity_basis="ast")
            by_hash[it.ast_hash] = cl
            it.cluster_id = cid
            clusters.append(cl)
            cid += 1
    # Near-duplicates by normalized source within each classification
    class_map: Dict[str, List[TestFunction]] = {}
    for it in items:
        class_map.setdefault(it.classification, []).append(it)

    for cls, bucket in class_map.items():
        n = len(bucket)
        for i in range(n):
            for j in range(i+1, n):
                a, b = bucket[i], bucket[j]
                if a.ast_hash == b.ast_hash:
                    continue
                ratio = SequenceMatcher(None, a.src_norm, b.src_norm).ratio()
                if ratio >= threshold:
                    ca = next((c for c in clusters if c.id == a.cluster_id), None)
                    cb = next((c for c in clusters if c.id == b.cluster_id), None)
                    if ca is None or cb is None or ca.id == cb.id:
                        continue
                    if len(ca.members) < len(cb.members):
                        ca, cb = cb, ca
                    for m in cb.members:
                        m.cluster_id = ca.id
                        ca.members.append(m)
                    clusters = [c for c in clusters if c.id != cb.id]
    for c in clusters:
        c.canonical = sorted(c.members, key=lambda t: (-t.num_asserts, -len(t.source_dedented), t.name))[0]
    return clusters

# --------------------- Parametrization Attempt -----------------------------

def attempt_parametrize(cluster: 'Cluster') -> Optional[str]:
    """
    Very conservative: works only for tests that have a single top-level
    Assert or call where literals differ. Otherwise returns None.
    Generates a parametrized wrapper around the canonical function body.
    """
    if len(cluster.members) <= 1:
        return None
    bodies = []
    const_vectors = []
    for t in cluster.members:
        try:
            fn = ast.parse(t.source_dedented).body[0]
            if not isinstance(fn, ast.FunctionDef):
                return None
            bodies.append(fn)
            consts = []
            class K(ast.NodeVisitor):
                def visit_Constant(self, n):
                    if isinstance(n.value, (int, float, str)):
                        consts.append(n.value)
            K().visit(fn)
            const_vectors.append(consts)
        except Exception:
            return None
    shapes = [normalized_ast_dump(b) for b in bodies]
    if len(set(shapes)) != 1:
        return None
    if len(const_vectors) <= 1:
        return None
    max_len = max(len(v) for v in const_vectors)
    vecs = [v + [""] * (max_len - len(v)) for v in const_vectors]
    ids = [f"case{i}" for i in range(len(vecs))]
    template_src = textwrap.dedent(cluster.canonical.source_dedented)
    canon_consts = const_vectors[0]
    replaced = template_src
    used_positions = set()
    for idx, cval in enumerate(canon_consts):
        if isinstance(cval, str):
            lit = re.escape(repr(cval))
        else:
            lit = re.escape(str(cval))
        new = re.sub(lit, f"PARAM[{idx}]", replaced, count=1)
        if new != replaced:
            replaced = new
            used_positions.add(idx)
    if not used_positions:
        return None
    param_list = ",\n    ".join([repr(tuple(v)) for v in vecs])
    code = f"""
import pytest

@pytest.mark.parametrize("PARAM", [
    {param_list}
], ids={ids!r})
{replaced}
"""
    code = re.sub(r"def\s+test_([a-zA-Z0-9_]+)\s*\(\s*\)", r"def test_\1(PARAM)", code)
    return code.strip("\n")

# ---------------------- Fixture Consolidation ------------------------------

def consolidate_fixtures(fixtures: List[TestFunction]) -> Tuple[str, List[Dict[str, Any]]]:
    seen = {}
    merged = []
    parts = ["from __future__ import annotations", "", "# Shared fixtures consolidated by tool", ""]
    for fx in sorted(fixtures, key=lambda f: (str(f.file), f.name)):
        if fx.ast_hash in seen:
            merged.append({"name": fx.name, "from": str(fx.file), "kept": seen[fx.ast_hash]})
            continue
        seen[fx.ast_hash] = f"{fx.name} ({fx.file})"
        parts.append(fx.source_dedented.rstrip())
        parts.append("")
    content = CRLF.join(parts) + CRLF
    return content, merged

# ------------------------ Writing Canonical Files --------------------------

HEADER = "from __future__ import annotations"

def assemble_file_header(title: str) -> str:
    return CRLF.join([
        HEADER,
        "",
        f"# {title}",
        "# This file was generated by tools/test_refactor.py",
        ""
    ]) + CRLF

def classify_and_bucket(tests: List[TestFunction]) -> Dict[str, List[TestFunction]]:
    buckets: Dict[str, List[TestFunction]] = {}
    for t in tests:
        t.classification = classify(t)
        buckets.setdefault(t.classification, []).append(t)
    return buckets

def build_canonical_files(buckets: Dict[str, List[TestFunction]], threshold: float, rpt: Report) -> Dict[Path, str]:
    outputs: Dict[Path, str] = {}
    for cls, items in buckets.items():
        dest = CANONICAL_DEST.get(cls)
        if not dest:
            continue
        clusters = cluster_duplicates(items, threshold=threshold)
        file_parts = [assemble_file_header(dest.name.replace(".py", "").replace("_", " ").title())]
        for cl in sorted(clusters, key=lambda c: (c.canonical.name if c.canonical else "", c.id)):
            para = attempt_parametrize(cl)
            if para:
                cl.merged = True
                cl.parametrized_code = para
                rpt.functions_parametrized.append({
                    "cluster_id": cl.id,
                    "canonical": f"{cl.canonical.file}::{cl.canonical.name}",
                    "members": [f"{m.file}::{m.name}" for m in cl.members],
                    "dest": str(dest),
                })
                file_parts.append(para)
                file_parts.append("")
                for m in cl.members:
                    rpt.lineage[f"{m.file}::{m.name}"] = {"final": f"{dest}::parametrized[{cl.id}]",
                                                         "canonical": f"{cl.canonical.file}::{cl.canonical.name}"}
            else:
                if cl.canonical:
                    file_parts.append(cl.canonical.source_dedented.rstrip())
                    file_parts.append("")
                    for m in cl.members:
                        rpt.lineage[f"{m.file}::{m.name}"] = {"final": f"{dest}::{cl.canonical.name}",
                                                             "canonical": f"{cl.canonical.file}::{cl.canonical.name}",
                                                             "merged": m.name != cl.canonical.name}
        outputs[dest] = CRLF.join(file_parts)
        rpt.clusters.append({
            "dest": str(dest),
            "count": sum(len(c.members) for c in clusters),
            "clusters": [{
                "id": c.id,
                "canonical": f"{c.canonical.file}::{c.canonical.name}" if c.canonical else None,
                "members": [f"{m.file}::{m.name}" for m in c.members],
                "parametrized": bool(c.parametrized_code),
            } for c in clusters]
        })
    return outputs

# ----------------------------- Orchestrator --------------------------------

def run(root: Path, tests_dir: Path, apply: bool, threshold: float, verbose: bool) -> Report:
    rpt = Report(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        root=str(root),
        tests_dir=str(tests_dir),
        threshold=threshold,
    )
    if not tests_dir.exists():
        print(f"[!] Tests directory not found: {tests_dir}", file=sys.stderr)
        return rpt

    backup_zip = Path("reports") / f"test-dedupe-backup-{_now_stamp()}.zip"
    try:
        _zip_folder(tests_dir, backup_zip)
        rpt.backup_zip = str(backup_zip)
        if verbose:
            print(f"[i] Backup created: {backup_zip}")
    except Exception as e:
        print(f"[!] Backup failed: {e}", file=sys.stderr)

    all_files = discover_test_files(tests_dir)
    all_fixtures: List[TestFunction] = []
    all_tests: List[TestFunction] = []
    for f in all_files:
        fixtures, tests = collect_test_items(f)
        all_fixtures.extend(fixtures)
        all_tests.extend(tests)

    fixtures_content, merged = consolidate_fixtures(all_fixtures)
    rpt.fixtures_merged = merged

    buckets = classify_and_bucket(all_tests)
    outputs = build_canonical_files(buckets, threshold=threshold, rpt=rpt)

    if apply:
        conftest_path = Path("tests/fixtures/conftest.py")
        _write_text_crlf(conftest_path, fixtures_content)
        rpt.files_created.append(str(conftest_path))

        for dest, content in outputs.items():
            _write_text_crlf(dest, content)
            rpt.files_created.append(str(dest))

        preserved = {str(Path(p)) for p in rpt.files_created} | {str(Path("tests/conftest.py")), str(conftest_path)}
        for old in all_files:
            s = str(old)
            if s not in preserved and "fixtures" not in s:
                try:
                    os.remove(old)
                    rpt.files_deleted.append(s)
                except Exception:
                    pass

    Path("reports").mkdir(parents=True, exist_ok=True)
    report_path = Path("reports/test-dedupe-report.json")
    _write_text_crlf(report_path, json.dumps(rpt.__dict__, indent=2))
    if verbose:
        print(f"[i] Report written to {report_path}")

    return rpt

def parse_args(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description="Deduplicate and consolidate pytest tests under /tests")
    p.add_argument("--root", default=".", help="Project root (default: .)")
    p.add_argument("--tests-dir", default="tests", help="Tests directory (default: tests)")
    p.add_argument("--apply", action="store_true", help="Apply changes (write canonical files and remove old tests)")
    p.add_argument("--threshold", type=float, default=0.95, help="Near-duplicate threshold (default: 0.95)")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    return p.parse_args(argv)

def main():
    args = parse_args()
    root = Path(args.root).resolve()
    tests_dir = (root / args.tests_dir).resolve()
    os.chdir(root)
    rpt = run(root, tests_dir, apply=args.apply, threshold=args.threshold, verbose=args.verbose)
    print(json.dumps({
        "backup_zip": rpt.backup_zip,
        "files_created": rpt.files_created,
        "files_deleted": rpt.files_deleted,
        "functions_parametrized": len(rpt.functions_parametrized),
        "fixtures_merged": len(rpt.fixtures_merged),
        "report": "reports/test-dedupe-report.json",
    }, indent=2))

if __name__ == "__main__":
    main()
