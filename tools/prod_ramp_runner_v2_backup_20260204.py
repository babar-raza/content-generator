#!/usr/bin/env python3
"""Production Scale Ramp Runner - Execute jobs with strict quality gates.

Implements:
- Concurrent job execution (max 2)
- Quality gate v2 validation
- Stop conditions enforcement
- Comprehensive metrics tracking
"""

import json
import time
import csv
import re
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
import sys

# Import quality gate
sys.path.insert(0, str(Path(__file__).parent))
from quality_gate import evaluate_output

# Configure stdout for UTF-8
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# Configuration
BASE_URL = "http://localhost:8103"
MAX_CONCURRENCY = 2
JOB_TIMEOUT = 240
POLL_INTERVAL = 5

# Stop conditions
STOP_FAILURE_RATE = 0.02  # 2%
STOP_TIMEOUT_COUNT = 2
STOP_QUALITY_PASS_RATE = 0.98  # 98%
STOP_AVG_REFS = 3
STOP_REPEATED_ERROR_COUNT = 3


def slugify(text):
    """Convert text to filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text[:50]


def http_post_json(url, data):
    """POST JSON data to URL."""
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode('utf-8')}
    except Exception as e:
        return None, {"error": str(e)}


def http_get_json(url):
    """GET JSON from URL."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode('utf-8')}
    except Exception as e:
        return None, {"error": str(e)}


def execute_single_job(job_spec: Dict) -> Dict:
    """Execute a single job and wait for completion.

    Args:
        job_spec: {workflow_id, topic, output_path, job_index}

    Returns:
        Job result dict with metrics
    """
    workflow_id = job_spec['workflow_id']
    topic = job_spec['topic']
    output_path = job_spec['output_path']
    job_index = job_spec['job_index']

    print(f"[Job {job_index}] Starting: {topic[:50]}...")

    # Submit job
    job_payload = {
        "workflow_id": workflow_id,
        "topic": topic,
        "output_dir": output_path,
        "model": "phi4-mini:latest"
    }

    start_time = time.time()
    start_ts = datetime.now().isoformat()

    status_code, response_data = http_post_json(f"{BASE_URL}/api/jobs", job_payload)

    result = {
        "job_index": job_index,
        "job_id": None,
        "workflow_id": workflow_id,
        "topic": topic,
        "start_ts": start_ts,
        "end_ts": None,
        "duration_s": 0,
        "status": "unknown",
        "output_path": output_path,
        "output_bytes": 0,
        "error": None,
        "timeout": False,
        "quality_pass": False,
        "quality_metrics": {}
    }

    # Check submission
    if status_code not in [200, 201]:
        print(f"[Job {job_index}] ❌ Submission failed: {status_code}")
        result["status"] = "submission_failed"
        result["error"] = str(response_data.get('error', 'Unknown error'))
        result["end_ts"] = datetime.now().isoformat()
        result["duration_s"] = time.time() - start_time
        return result

    job_id = response_data.get('job_id')
    result["job_id"] = job_id
    print(f"[Job {job_index}] Submitted as {job_id}")

    # Poll for completion
    elapsed = 0
    final_status = "unknown"

    while elapsed < JOB_TIMEOUT:
        status_code, status_data = http_get_json(f"{BASE_URL}/api/jobs/{job_id}")

        if status_code == 200:
            final_status = status_data.get('status', 'unknown')

            if final_status in ['completed', 'failed', 'error']:
                break

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Check timeout
    if elapsed >= JOB_TIMEOUT and final_status not in ['completed', 'failed', 'error']:
        print(f"[Job {job_index}] ⏱️  TIMEOUT after {JOB_TIMEOUT}s")
        result["timeout"] = True
        result["status"] = "timeout"
    else:
        result["status"] = final_status
        print(f"[Job {job_index}] Status: {final_status}")

    result["end_ts"] = datetime.now().isoformat()
    result["duration_s"] = time.time() - start_time

    # Check output and run quality gate
    if final_status == 'completed':
        output_dir = Path(output_path)
        if output_dir.exists():
            md_files = list(output_dir.glob("*.md"))
            if md_files:
                # Use first markdown file
                primary_output = md_files[0]
                result["output_bytes"] = primary_output.stat().st_size

                # Run quality gate
                print(f"[Job {job_index}] Running quality gate...")
                try:
                    quality_result = evaluate_output(str(primary_output))
                    result["quality_pass"] = quality_result["pass"]
                    result["quality_metrics"] = quality_result["metrics"]

                    if quality_result["pass"]:
                        print(f"[Job {job_index}] ✅ Quality PASS")
                    else:
                        print(f"[Job {job_index}] ❌ Quality FAIL: {quality_result['failures']}")
                except Exception as e:
                    print(f"[Job {job_index}] ⚠️  Quality gate error: {e}")
                    result["error"] = f"quality_gate_error: {e}"

    return result


def run_phase(
    phase_name: str,
    topics: List[Dict],
    workflows: List[str],
    output_dir: Path,
    ts: str
) -> Tuple[List[Dict], Dict, bool]:
    """Execute a phase of jobs with concurrency control.

    Args:
        phase_name: e.g., "phase_50"
        topics: List of topic dicts from CSV
        workflows: List of workflow IDs to use
        output_dir: Phase output directory
        ts: Timestamp

    Returns:
        (job_results, phase_metrics, stop_triggered)
    """
    print(f"\n{'='*80}")
    print(f"PHASE: {phase_name.upper()}")
    print(f"Jobs: {len(topics)}")
    print(f"{'='*80}\n")

    # Prepare job specs
    job_specs = []
    for i, topic_row in enumerate(topics):
        workflow_id = workflows[i % len(workflows)]
        topic = topic_row['title_topic']
        topic_slug = slugify(topic)
        output_path = f"outputs/prod_ramp_{ts}/{phase_name}/{topic_slug}"

        job_specs.append({
            "job_index": i + 1,
            "workflow_id": workflow_id,
            "topic": topic,
            "output_path": output_path
        })

    # Execute with concurrency
    job_results = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        futures = {executor.submit(execute_single_job, spec): spec for spec in job_specs}

        for future in as_completed(futures):
            try:
                result = future.result()
                job_results.append(result)
            except Exception as e:
                spec = futures[future]
                print(f"[Job {spec['job_index']}] ❌ Exception: {e}")
                job_results.append({
                    "job_index": spec['job_index'],
                    "error": str(e),
                    "status": "exception"
                })

    # Sort by job index
    job_results = sorted(job_results, key=lambda x: x.get('job_index', 0))

    # Write jobs.jsonl
    jobs_jsonl = output_dir / "jobs.jsonl"
    with open(jobs_jsonl, 'w', encoding='utf-8') as f:
        for job in job_results:
            f.write(json.dumps(job) + '\n')

    # Compute phase metrics
    total_jobs = len(job_results)
    completed_jobs = [j for j in job_results if j.get('status') == 'completed']
    failed_jobs = [j for j in job_results if j.get('status') not in ['completed', 'unknown']]
    timeout_jobs = [j for j in job_results if j.get('timeout', False)]

    failure_rate = len(failed_jobs) / total_jobs if total_jobs > 0 else 0
    completion_rate = len(completed_jobs) / total_jobs if total_jobs > 0 else 0

    # Quality metrics
    quality_passed = [j for j in completed_jobs if j.get('quality_pass', False)]
    quality_pass_rate = len(quality_passed) / len(completed_jobs) if completed_jobs else 0

    # Avg references
    ref_counts = [j.get('quality_metrics', {}).get('reference_count', 0) for j in completed_jobs]
    avg_refs = sum(ref_counts) / len(ref_counts) if ref_counts else 0

    # Duration stats
    durations = [j.get('duration_s', 0) for j in job_results if j.get('duration_s', 0) > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0
    p95_duration = sorted(durations)[int(len(durations) * 0.95)] if durations else 0

    # Error signatures
    error_sigs = {}
    for job in job_results:
        error = job.get('error')
        if error:
            sig = str(error)[:100]
            error_sigs[sig] = error_sigs.get(sig, 0) + 1

    repeated_errors = [sig for sig, count in error_sigs.items() if count >= STOP_REPEATED_ERROR_COUNT]

    phase_metrics = {
        "phase": phase_name,
        "total_jobs": total_jobs,
        "completed": len(completed_jobs),
        "failed": len(failed_jobs),
        "timeouts": len(timeout_jobs),
        "completion_rate": completion_rate,
        "failure_rate": failure_rate,
        "quality_passed": len(quality_passed),
        "quality_pass_rate": quality_pass_rate,
        "avg_refs_per_output": avg_refs,
        "avg_duration_s": avg_duration,
        "p95_duration_s": p95_duration,
        "error_signatures": error_sigs,
        "repeated_errors": repeated_errors
    }

    # Write quality.json
    quality_json = output_dir / "quality.json"
    with open(quality_json, 'w', encoding='utf-8') as f:
        json.dump({
            "phase": phase_name,
            "quality_passed": len(quality_passed),
            "quality_failed": len(completed_jobs) - len(quality_passed),
            "quality_pass_rate": quality_pass_rate,
            "avg_refs": avg_refs,
            "details": [
                {
                    "job_index": j.get('job_index'),
                    "job_id": j.get('job_id'),
                    "topic": j.get('topic'),
                    "quality_pass": j.get('quality_pass'),
                    "quality_metrics": j.get('quality_metrics')
                }
                for j in completed_jobs
            ]
        }, f, indent=2)

    # Write summary.md
    summary_md = output_dir / "summary.md"
    with open(summary_md, 'w', encoding='utf-8') as f:
        f.write(f"# {phase_name.upper()} Summary\n\n")
        f.write(f"## Execution Metrics\n\n")
        f.write(f"- Total jobs: {total_jobs}\n")
        f.write(f"- Completed: {len(completed_jobs)} ({completion_rate*100:.1f}%)\n")
        f.write(f"- Failed: {len(failed_jobs)} ({failure_rate*100:.1f}%)\n")
        f.write(f"- Timeouts: {len(timeout_jobs)}\n")
        f.write(f"- Avg duration: {avg_duration:.1f}s\n")
        f.write(f"- P95 duration: {p95_duration:.1f}s\n\n")

        f.write(f"## Quality Metrics\n\n")
        f.write(f"- Quality passed: {len(quality_passed)} / {len(completed_jobs)}\n")
        f.write(f"- Quality pass rate: {quality_pass_rate*100:.1f}%\n")
        f.write(f"- Avg refs/output: {avg_refs:.2f}\n\n")

        if error_sigs:
            f.write(f"## Error Signatures\n\n")
            for sig, count in sorted(error_sigs.items(), key=lambda x: x[1], reverse=True)[:5]:
                f.write(f"- [{count}x] {sig}\n")
            f.write("\n")

        if repeated_errors:
            f.write(f"## ⚠️  Repeated Errors (≥3 occurrences)\n\n")
            for sig in repeated_errors:
                f.write(f"- {sig}\n")
            f.write("\n")

    # Check stop conditions
    stop_triggered = False
    stop_reasons = []

    if failure_rate >= STOP_FAILURE_RATE:
        stop_reasons.append(f"Failure rate {failure_rate*100:.1f}% >= {STOP_FAILURE_RATE*100:.1f}%")
        stop_triggered = True

    if len(timeout_jobs) >= STOP_TIMEOUT_COUNT:
        stop_reasons.append(f"Timeout count {len(timeout_jobs)} >= {STOP_TIMEOUT_COUNT}")
        stop_triggered = True

    if quality_pass_rate < STOP_QUALITY_PASS_RATE:
        stop_reasons.append(f"Quality pass rate {quality_pass_rate*100:.1f}% < {STOP_QUALITY_PASS_RATE*100:.1f}%")
        stop_triggered = True

    if avg_refs < STOP_AVG_REFS:
        stop_reasons.append(f"Avg refs {avg_refs:.2f} < {STOP_AVG_REFS}")
        stop_triggered = True

    if repeated_errors:
        stop_reasons.append(f"Repeated error signatures: {len(repeated_errors)}")
        stop_triggered = True

    if stop_triggered:
        print(f"\n{'='*80}")
        print(f"🛑 STOP-THE-LINE TRIGGERED")
        print(f"{'='*80}")
        for reason in stop_reasons:
            print(f"  - {reason}")
        print(f"{'='*80}\n")

        # Write HOLD.md
        hold_file = output_dir / "HOLD.md"
        with open(hold_file, 'w', encoding='utf-8') as f:
            f.write(f"# HOLD - Stop Condition Triggered\n\n")
            f.write(f"Phase: {phase_name}\n\n")
            f.write(f"## Stop Reasons\n\n")
            for reason in stop_reasons:
                f.write(f"- {reason}\n")

    print(f"\nPhase {phase_name} complete:")
    print(f"  Completion: {completion_rate*100:.1f}%")
    print(f"  Failure: {failure_rate*100:.1f}%")
    print(f"  Quality pass: {quality_pass_rate*100:.1f}%")
    print(f"  Avg refs: {avg_refs:.2f}")

    return job_results, phase_metrics, stop_triggered


if __name__ == '__main__':
    print("This is a library module. Use it from the main ramp script.")
