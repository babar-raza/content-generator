# tools/repo_scan.py
import ast, os, re, hashlib, json
from collections import defaultdict

ROOT = os.environ.get("PROJECT_ROOT", "/mnt/data/project")

def py_files():
    for d, _, files in os.walk(ROOT):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(d, f)

def normalize(code):
    code = re.sub(r"#.*", "", code)
    code = re.sub(r'"""[\\s\\S]*?"""', "", code)
    code = re.sub(r"'''[\\s\\S]*?'''", "", code)
    code = re.sub(r"\\s+", " ", code).strip()
    return code

def shingles(s, k=20):
    return {hashlib.md5(s[i:i+k].encode()).hexdigest() for i in range(0, max(0, len(s)-k+1), k)}

import_graph = defaultdict(set)
entities = []  # {file, type, name, start, end, sig_hash, shingles}

for path in py_files():
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for n in node.names:
                    import_graph[path].add(n.name.split(".")[0])
            else:
                if node.module:
                    import_graph[path].add(node.module.split(".")[0])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start)
            body = "\\n".join(src.splitlines()[start-1:end])
            body_norm = normalize(body)
            sh = shingles(body_norm, 30)
            sig = f"{type(node).__name__}:{node.name}:{len(body_norm)}"
            sig_hash = hashlib.md5(sig.encode()).hexdigest()
            entities.append({
                "file": path, "type": type(node).__name__, "name": node.name,
                "start": start, "end": end, "sig_hash": sig_hash, "shingles": list(sh)
            })

# duplicate detection by Jaccard
dups = []
for i in range(len(entities)):
    si = set(entities[i]["shingles"])
    for j in range(i+1, len(entities)):
        sj = set(entities[j]["shingles"])
        if not si or not sj: continue
        jacc = len(si & sj) / len(si | sj)
        if jacc >= 0.6 and entities[i]["name"] != entities[j]["name"]:
            dups.append({
                "a": entities[i], "b": entities[j], "similarity": round(jacc, 2)
            })

report = {
    "import_graph": {k: sorted(list(v)) for k, v in import_graph.items()},
    "duplicates": dups
}
os.makedirs("/mnt/data/reports", exist_ok=True)
with open("/mnt/data/reports/wiring_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("Wrote /mnt/data/reports/wiring_report.json")
