"""Lightweight ChromaDB HTTP probe using standard library only."""
import json
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def probe_chroma_http(host="localhost", port=9100):
    """Probe ChromaDB via HTTP v2 API.

    Args:
        host: ChromaDB host
        port: ChromaDB port

    Returns:
        dict: Collections info
    """
    base_url = f"http://{host}:{port}/api/v2"
    results = {
        "mode": f"http://{host}:{port}",
        "collections": {},
        "total_vectors": 0,
        "status": "UNKNOWN",
        "error": None
    }

    # Check heartbeat
    try:
        with urlopen(f"{base_url}/heartbeat", timeout=5) as response:
            heartbeat = json.loads(response.read().decode())
            print(f"[OK] ChromaDB heartbeat: {heartbeat}")
    except (URLError, HTTPError) as e:
        results["error"] = f"Heartbeat failed: {e}"
        results["status"] = "FAIL"
        print(f"[FAIL] {results['error']}", file=sys.stderr)
        return results

    # List collections
    try:
        with urlopen(f"{base_url}/collections", timeout=10) as response:
            collections_data = json.loads(response.read().decode())

        print(f"\nFound {len(collections_data)} collection(s):")

        for coll in collections_data:
            name = coll.get("name", "unknown")
            coll_id = coll.get("id", "unknown")

            # Get collection count
            try:
                with urlopen(f"{base_url}/collections/{coll_id}/count", timeout=10) as count_resp:
                    count = int(count_resp.read().decode())
            except Exception as e:
                print(f"  Warning: Could not get count for {name}: {e}", file=sys.stderr)
                count = -1

            results["collections"][name] = {
                "count": count,
                "id": coll_id,
                "metadata": coll.get("metadata", {})
            }

            if count >= 0:
                results["total_vectors"] += count
                print(f"  - {name}: {count} vectors (id: {coll_id})")
            else:
                print(f"  - {name}: count unknown (id: {coll_id})")

        results["status"] = "PASS" if results["total_vectors"] > 0 else "FAIL"

    except (URLError, HTTPError) as e:
        results["error"] = f"List collections failed: {e}"
        results["status"] = "FAIL"
        print(f"[FAIL] {results['error']}", file=sys.stderr)

    return results


def main():
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Probe ChromaDB via HTTP")
    parser.add_argument("--host", default="localhost", help="ChromaDB host")
    parser.add_argument("--port", type=int, default=9100, help="ChromaDB port")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    results = probe_chroma_http(args.host, args.port)

    # Write JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results written to {output_path}")

    # Write markdown summary
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# ChromaDB HTTP Probe Results\n\n")
        f.write(f"**Status:** {results['status']}\n\n")
        f.write(f"**Mode:** {results['mode']}\n\n")
        f.write(f"**Total Vectors:** {results['total_vectors']}\n\n")
        f.write("## Collections\n\n")
        if results["collections"]:
            for name, info in results["collections"].items():
                f.write(f"- **{name}**: {info['count']} vectors\n")
        else:
            f.write("*No collections found*\n")
        if results["error"]:
            f.write(f"\n## Error\n\n```\n{results['error']}\n```\n")
    print(f"[OK] Markdown summary written to {md_path}")

    sys.exit(0 if results["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
