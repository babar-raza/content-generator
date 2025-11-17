# tools/missing_docs_audit.py
from __future__ import annotations
import ast, os
from typing import List, Dict, Any, Tuple

REQ_FUNCTION_SECTIONS = {"Summary", "Args", "Returns"}  # Raises optional
REQ_CLASS_SECTIONS = {"Summary", "Responsibilities", "Construction", "Public API", "State and Invariants"}

def _has_marker(mod: ast.Module, exact_marker: str) -> bool:
    doc = ast.get_docstring(mod) or ""
    return exact_marker in doc

def _is_public(name: str) -> bool:
    return not name.startswith("_")

def _extract_section_names(text: str) -> set:
    if not text:
        return set()
    heads = set()
    for line in text.splitlines():
        s = line.strip().rstrip(":")
        # match our canonical headings (case-insensitive)
        if s.lower() in {
            "summary","args","returns","raises","preconditions","postconditions",
            "side effects","i/o schema","concurrency and performance","configuration",
            "external interactions","notes","responsibilities","construction",
            "public api","state and invariants","concurrency and i/o","error surface",
            "module overview","public api catalog","design notes"
        }:
            # normalize capitalization
            words = " ".join(w.capitalize() for w in s.split())
            heads.add(words)
    return heads

def _collect_symbols(tree: ast.AST, is_init: bool) -> List[Tuple[str, ast.AST | None]]:
    symbols = []

    def visit(node, prefix=""):
        if isinstance(node, ast.ClassDef) and _is_public(node.name):
            symbols.append((f"{prefix}{node.name}", node))
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and _is_public(item.name):
                    symbols.append((f"{prefix}{node.name}.{item.name}", item))
        elif isinstance(node, ast.FunctionDef) and _is_public(node.name):
            symbols.append((f"{prefix}{node.name}", node))

    for node in tree.body:
        visit(node)

    if is_init:
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    if _is_public(name):
                        symbols.append((name, None))  # None for re-export

    return symbols

def _parse(path: str) -> ast.Module | None:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        return ast.parse(code)
    except Exception:
        return None

def audit(paths: List[str], id_marker: str, size_limit_bytes: int) -> Dict[str, Any]:
    report = {"missing": []}
    for p in paths:
        try:
            if os.path.getsize(p) > size_limit_bytes:
                continue
        except OSError:
            continue

        mod = _parse(p)
        if mod is None:
            continue

        is_init = os.path.basename(p) == "__init__.py"
        symbols = _collect_symbols(mod, is_init)

        # Module-level marker check
        if not _has_marker(mod, id_marker):
            report["missing"].append({"file": p, "symbol": "module", "missing_sections": ["marker"]})

        for symbol_name, node in symbols:
            if node is None:  # re-export
                missing_secs = REQ_FUNCTION_SECTIONS
                report["missing"].append({"file": p, "symbol": symbol_name, "missing_sections": list(missing_secs)})
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                heads = _extract_section_names(doc)
                missing_secs = REQ_CLASS_SECTIONS - heads
                if missing_secs:
                    report["missing"].append({"file": p, "symbol": symbol_name, "missing_sections": list(missing_secs)})
            elif isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node) or ""
                heads = _extract_section_names(doc)
                missing_secs = REQ_FUNCTION_SECTIONS - heads
                if missing_secs:
                    report["missing"].append({"file": p, "symbol": symbol_name, "missing_sections": list(missing_secs)})

    return report
