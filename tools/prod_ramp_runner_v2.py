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
import io

# Configure stdout for UTF-8 on Windows (fixes Unicode encoding errors)
# Guard with __main__ check so importing for tests doesn't break pytest capture
if sys.platform == 'win32' and __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Import quality gate
sys.path.insert(0, str(Path(__file__).parent))
from quality_gate import evaluate_output

# Configuration
BASE_URL = "http://localhost:8103"
SERVER_ROOT = None  # Set via command line or environment
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


def deduplicate_topics(topics: List[Dict], required_count: int, all_topics: List[Dict]) -> List[Dict]:
    """Deduplicate topics by title (case-insensitive) and resample if needed.

    Args:
        topics: Initial topic batch
        required_count: Number of unique topics required
        all_topics: Full topic pool for resampling

    Returns:
        List of unique topics (length >= required_count if possible)
    """
    # Track seen titles (case-insensitive)
    seen_titles = set()
    unique_topics = []

    for topic in topics:
        title = topic['title_topic'].lower().strip()
        if title not in seen_titles:
            seen_titles.add(title)
            unique_topics.append(topic)

    removed_count = len(topics) - len(unique_topics)
    if removed_count > 0:
        print(f"🔍 Deduplication: Removed {removed_count} duplicate topics")

    # Resample if we don't have enough unique topics
    if len(unique_topics) < required_count:
        if not all_topics:
            raise ValueError(
                f"Insufficient unique topics: have {len(unique_topics)}, "
                f"need {required_count}, but no topic pool provided for resampling."
            )

        print(f"📊 Resampling to reach {required_count} unique topics...")
        initial_count = len(unique_topics)

        # Add more topics from pool that aren't already in our set
        for topic in all_topics:
            title = topic['title_topic'].lower().strip()
            if title not in seen_titles:
                seen_titles.add(title)
                unique_topics.append(topic)

                if len(unique_topics) >= required_count:
                    break

        added_count = len(unique_topics) - initial_count
        print(f"📊 Resampling added {added_count} topics ({initial_count} → {len(unique_topics)})")

        # Check if we reached the target after resampling
        if len(unique_topics) < required_count:
            raise ValueError(
                f"Topic pool exhausted: have {len(unique_topics)} unique topics, "
                f"need {required_count}. Pool size: {len(all_topics)}. "
                f"Cannot proceed - need to curate more diverse topics."
            )

    print(f"✅ Final topic count: {len(unique_topics)} unique topics")
    return unique_topics[:required_count]


def resolve_output_path(output_path_from_api):
    """Resolve output path to absolute filesystem path.

    Args:
        output_path_from_api: Path returned from API (may be relative or absolute)

    Returns:
        Absolute Path object, or None if path cannot be resolved

    Strategy:
        1. If already absolute and exists: use it
        2. If relative:
           a) Try: SERVER_ROOT / output_path
           b) Try: SERVER_ROOT / "outputs" / output_path
        3. Return first existing path, or None
    """
    if not SERVER_ROOT:
        # Fallback to relative resolution (not recommended)
        return Path(output_path_from_api)

    server_root = Path(SERVER_ROOT)
    path_obj = Path(output_path_from_api)

    # Case 1: Already absolute
    if path_obj.is_absolute():
        if path_obj.exists():
            return path_obj
        else:
            print(f"⚠️  Absolute path does not exist: {path_obj}")
            return None

    # Case 2: Relative path - try candidates
    candidates = [
        server_root / output_path_from_api,
        server_root / "outputs" / output_path_from_api
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # None exist - log candidates and return first candidate for debugging
    print(f"⚠️  Output path not found. Tried:")
    for c in candidates:
        print(f"   - {c}")

    return candidates[0]  # Return first candidate even if not exists


def http_post_json(url, data, retries=5, timeout=120):
    """POST JSON data to URL with retry logic.

    Args:
        url: Target URL
        data: Dictionary to send as JSON
        retries: Number of retry attempts for transient failures
        timeout: HTTP request timeout in seconds

    Returns:
        (status_code, response_dict, diagnostics)
        diagnostics includes full error details for logging
    """
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={'Content-Type': 'application/json'}
    )

    last_error_diag = {}

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode('utf-8')
                return response.status, json.loads(body), {}

        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode('utf-8')

            # Capture full diagnostics
            diag = {
                "status_code": status,
                "response_body": body[:500],  # First 500 chars
                "headers": dict(e.headers),
                "url": url,
                "attempt": attempt + 1
            }

            # Retry on transient errors with appropriate backoff
            if status in [429, 502, 503, 504] and attempt < retries - 1:
                if status == 429:
                    # Rate limit: use longer backoff (15-60s range for Gemini 15 RPM)
                    backoff = min(15 * (2 ** attempt), 120) + (time.time() % 3)
                else:
                    # Server errors: standard exponential backoff
                    backoff = (2 ** attempt) + (time.time() % 1)
                print(f"  ⏳ HTTP {status} on attempt {attempt+1}/{retries}, backoff {backoff:.1f}s")
                time.sleep(backoff)
                last_error_diag = diag
                continue

            return status, {"error": body}, diag

        except Exception as e:
            # Capture full exception details
            import traceback
            diag = {
                "exception_type": type(e).__name__,
                "exception_message": str(e),
                "traceback": traceback.format_exc(),
                "url": url,
                "attempt": attempt + 1
            }

            # Retry on connection errors
            if attempt < retries - 1 and isinstance(e, (urllib.error.URLError, ConnectionError, TimeoutError)):
                backoff = (2 ** attempt) + (time.time() % 1)
                print(f"  ⏳ {type(e).__name__} on attempt {attempt+1}/{retries}, backoff {backoff:.1f}s")
                time.sleep(backoff)
                last_error_diag = diag
                continue

            return None, {"error": str(e)}, diag

    # All retries exhausted
    return None, {"error": "All retries exhausted"}, last_error_diag


def verify_job_submitted(topic, timeout=30):
    """Check if a job for the given topic was actually created server-side.

    When an HTTP submission times out, the server may have received and
    processed the request. This function polls the jobs list to find it.

    Args:
        topic: The topic string that was submitted
        timeout: How long to keep polling (seconds)

    Returns:
        (job_id, status_data) if found, (None, None) otherwise
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            status_code, jobs_data = http_get_json(f"{BASE_URL}/api/jobs")
            if status_code == 200:
                jobs = jobs_data.get('jobs', [])
                for job in jobs:
                    if job.get('topic', '') == topic:
                        return job.get('job_id'), job
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)
    return None, None


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

    status_code, response_data, diagnostics = http_post_json(f"{BASE_URL}/api/jobs", job_payload)

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
        "quality_metrics": {},
        "api_output_path": None  # Track actual path returned by API
    }

    # Check submission
    if status_code not in [200, 201]:
        error_msg = str(response_data.get('error', 'Unknown error'))
        print(f"[Job {job_index}] ⚠️  Submission returned {status_code}")
        print(f"  URL: {BASE_URL}/api/jobs")
        print(f"  Payload: workflow={workflow_id}, topic={topic[:50]}")
        print(f"  Error: {error_msg[:200]}")

        if diagnostics:
            if "exception_type" in diagnostics:
                print(f"  Exception: {diagnostics['exception_type']}: {diagnostics['exception_message']}")

        # Before declaring failure, check if the job was actually created server-side
        # (submission may have succeeded but the HTTP response timed out)
        print(f"[Job {job_index}] 🔍 Verifying server-side job creation...")
        verified_job_id, verified_data = verify_job_submitted(topic, timeout=30)

        if verified_job_id:
            print(f"[Job {job_index}] ✅ Job found server-side as {verified_job_id} (timeout was client-side only)")
            job_id = verified_job_id
            result["job_id"] = job_id
            # Fall through to the polling loop below
        else:
            print(f"[Job {job_index}] ❌ Submission confirmed failed (not found server-side)")
            result["status"] = "submission_failed"
            result["error"] = error_msg
            result["end_ts"] = datetime.now().isoformat()
            result["duration_s"] = time.time() - start_time
            return result
    else:
        job_id = response_data.get('job_id')
        result["job_id"] = job_id

    print(f"[Job {job_index}] Submitted as {job_id}")

    # Poll for completion
    elapsed = 0
    final_status = "unknown"
    final_status_data = {}

    while elapsed < JOB_TIMEOUT:
        status_code, status_data = http_get_json(f"{BASE_URL}/api/jobs/{job_id}")

        if status_code == 200:
            final_status = status_data.get('status', 'unknown')
            final_status_data = status_data

            if final_status in ['completed', 'failed', 'error']:
                # Capture the output_path returned by the API
                if 'output_path' in status_data:
                    result["api_output_path"] = status_data['output_path']
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
        # CRITICAL FIX: Use exact API-returned output_path instead of globbing
        api_path = result.get("api_output_path")

        if api_path:
            # API returned a specific file path - use it directly
            primary_output = resolve_output_path(api_path)

            if primary_output and primary_output.exists():
                # Verify file is stable (size stops changing)
                prev_size = 0
                for check in range(3):
                    curr_size = primary_output.stat().st_size
                    if curr_size == prev_size and curr_size > 0:
                        break
                    prev_size = curr_size
                    time.sleep(0.5)

                result["output_bytes"] = primary_output.stat().st_size

                # Verify job_id in filename matches submitted job_id
                filename = primary_output.name
                if job_id and job_id not in filename:
                    print(f"[Job {job_index}] ⚠️  WARNING: job_id mismatch!")
                    print(f"  Submitted job_id: {job_id}")
                    print(f"  Output filename: {filename}")

                # Run quality gate
                print(f"[Job {job_index}] Running quality gate on: {primary_output}")
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
            else:
                print(f"[Job {job_index}] ❌ API-returned output path not found: {api_path}")
                result["error"] = f"output_file_not_found: {api_path}"
        else:
            # Fallback: API didn't return output_path - try directory glob (legacy)
            print(f"[Job {job_index}] ⚠️  No output_path in API response, using fallback glob")
            output_dir = resolve_output_path(output_path)

            if output_dir and output_dir.exists():
                # Find file with matching job_id
                md_files = list(output_dir.glob(f"{job_id}_*.md"))
                if not md_files:
                    # Fallback to any .md file
                    md_files = list(output_dir.glob("*.md"))

                if md_files:
                    primary_output = md_files[0]
                    result["output_bytes"] = primary_output.stat().st_size

                    print(f"[Job {job_index}] Running quality gate on: {primary_output}")
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
                else:
                    print(f"[Job {job_index}] ⚠️  No .md files found in {output_dir}")
                    result["error"] = "no_output_files_found"
            else:
                print(f"[Job {job_index}] ❌ Output directory not found: {output_path}")
                result["error"] = f"output_dir_not_found: {output_path}"

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

    # Preflight check: ensure output base directory exists
    if SERVER_ROOT:
        server_root = Path(SERVER_ROOT)
        output_base = server_root / "outputs" / f"prod_ramp_{ts}" / phase_name
        output_base.mkdir(parents=True, exist_ok=True)
        print(f"Output base created/verified: {output_base}")

    for i, topic_row in enumerate(topics):
        workflow_id = workflows[i % len(workflows)]
        topic = topic_row['title_topic']
        topic_slug = slugify(topic)

        # Build absolute output path for job submission
        if SERVER_ROOT:
            server_root = Path(SERVER_ROOT)
            output_path = str(server_root / "outputs" / f"prod_ramp_{ts}" / phase_name / topic_slug)
        else:
            # Fallback to relative (not recommended)
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
    import argparse

    parser = argparse.ArgumentParser(description='Production Ramp Runner with Path Fix')
    parser.add_argument('--phase', type=int, required=True, help='Phase size (e.g., 50)')
    parser.add_argument('--base_url', default='http://localhost:8103', help='API base URL')
    parser.add_argument('--server_root', required=True, help='Server repository root path')
    parser.add_argument('--concurrency', type=int, default=2, help='Max concurrent jobs')
    parser.add_argument('--topics_csv', default=None, help='Path to topics CSV file')
    args = parser.parse_args()

    # Set global configuration
    BASE_URL = args.base_url
    SERVER_ROOT = args.server_root
    MAX_CONCURRENCY = args.concurrency

    print(f"Production Ramp Runner")
    print(f"  Server Root: {SERVER_ROOT}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Phase: {args.phase}")
    print(f"  Concurrency: {MAX_CONCURRENCY}\n")

    # Load topics (requires external CSV)
    if not args.topics_csv:
        print("ERROR: --topics_csv required")
        sys.exit(1)

    all_topics = []
    with open(args.topics_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_topics.append(row)

    if len(all_topics) < args.phase:
        print(f"ERROR: Topics CSV has {len(all_topics)} rows, but phase requires {args.phase}")
        sys.exit(1)

    # Select initial batch and deduplicate
    initial_topics = all_topics[:args.phase * 2]  # Oversample for deduplication
    topics = deduplicate_topics(initial_topics, args.phase, all_topics)

    # Get workflows
    status_code, workflows_response = http_get_json(f"{BASE_URL}/api/workflows")
    if status_code != 200 or not workflows_response:
        print(f"ERROR: Failed to fetch workflows: {status_code}")
        sys.exit(1)

    workflows_data = workflows_response.get('workflows', [])
    if not workflows_data:
        print(f"ERROR: No workflows found in response")
        sys.exit(1)

    workflow_ids = [w['workflow_id'] for w in workflows_data]
    print(f"Available workflows: {workflow_ids}\n")

    # Prepare output directory
    from datetime import datetime, timedelta
    try:
        import pytz
        tz = pytz.timezone('Asia/Karachi')
        ts = datetime.now(tz).strftime('%Y%m%d-%H%M')
    except:
        # Fallback: UTC+5 for Asia/Karachi
        ts = (datetime.utcnow() + timedelta(hours=5)).strftime('%Y%m%d-%H%M')

    output_dir = Path(f"reports/prod_ramp_fix/{ts}/phase_{args.phase}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run phase
    job_results, phase_metrics, stop_triggered = run_phase(
        f"phase_{args.phase}",
        topics,
        workflow_ids,
        output_dir,
        ts
    )

    # Print final summary
    print(f"\n{'='*80}")
    print(f"PHASE {args.phase} COMPLETE")
    print(f"{'='*80}")
    print(f"Completed: {phase_metrics['completed']}/{phase_metrics['total_jobs']}")
    print(f"Failed: {phase_metrics['failed']}")
    print(f"Quality pass rate: {phase_metrics['quality_pass_rate']*100:.1f}%")
    print(f"Avg refs/output: {phase_metrics['avg_refs_per_output']:.2f}")

    if stop_triggered:
        print(f"\n🛑 STOP-THE-LINE: See HOLD.md for details")
        sys.exit(1)
    else:
        print(f"\n✅ Phase passed all thresholds")
        sys.exit(0)
