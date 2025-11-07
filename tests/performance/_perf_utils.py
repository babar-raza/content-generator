import os, json, time, statistics
from pathlib import Path

PERF_RESULTS_PATH = os.environ.get("PERF_RESULTS_PATH", "reports/perf_results.json")
PERF_ITERS = int(os.environ.get("PERF_ITERS", "10"))
PERF_WARMUP = int(os.environ.get("PERF_WARMUP", "3"))
PERF_TIMEOUT = float(os.environ.get("PERF_TIMEOUT", "5.0"))

def _ensure_file():
    p = Path(PERF_RESULTS_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("[]", encoding="utf-8")
    return p

def record_result(suite, case, timings):
    p = _ensure_file()
    try:
        data = json.loads(p.read_text(encoding="utf-8") or "[]")
    except Exception:
        data = []
    timings = [t for t in timings if isinstance(t, (int,float)) and t >= 0]
    if not timings:
        timings = [0.0]
    def pctl(vals, q):
        if len(vals) < 2:
            return max(vals)
        idx = max(0, min(len(vals)-1, int(round(q*(len(vals)-1)))))
        return sorted(vals)[idx]
    out = {
        "suite": suite,
        "case": case,
        "iters": len(timings),
        "min": min(timings),
        "max": max(timings),
        "mean": sum(timings)/len(timings),
        "median": pctl(timings, 0.5),
        "p90": pctl(timings, 0.90),
        "p95": pctl(timings, 0.95),
        "stdev": (statistics.pstdev(timings) if len(timings) > 1 else 0.0),
    }
    data.append(out)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out

def time_call(fn, *, iters=None, warmup=None):
    iters = PERF_ITERS if iters is None else iters
    warmup = PERF_WARMUP if warmup is None else warmup
    for _ in range(max(0, int(warmup))):
        try: fn()
        except Exception: return []
    timings = []
    for _ in range(max(1, int(iters))):
        t0 = time.perf_counter()
        fn()
        timings.append(time.perf_counter() - t0)
    return timings
