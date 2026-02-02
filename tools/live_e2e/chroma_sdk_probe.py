"""ChromaDB probe using chromadb Python SDK."""
import json
import sys
from pathlib import Path

try:
    import chromadb
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install --user chromadb", file=sys.stderr)
    sys.exit(1)


def probe_chroma_sdk(host="localhost", port=9100):
    """Probe ChromaDB using SDK.

    Args:
        host: ChromaDB host
        port: ChromaDB port

    Returns:
        dict: Collections info
    """
    results = {
        "mode": f"http://{host}:{port}",
        "collections": {},
        "total_vectors": 0,
        "status": "UNKNOWN",
        "error": None
    }

    try:
        client = chromadb.HttpClient(host=host, port=port)
        print(f"[OK] Connected to ChromaDB at {host}:{port}")

        # List collections
        collections = client.list_collections()
        print(f"\nFound {len(collections)} collection(s):")

        for coll in collections:
            name = coll.name
            count = coll.count()

            results["collections"][name] = {
                "count": count,
                "metadata": coll.metadata if hasattr(coll, 'metadata') else {}
            }
            results["total_vectors"] += count
            print(f"  - {name}: {count} vectors")

        results["status"] = "PASS" if results["total_vectors"] > 0 else "WARNING"

        if not collections:
            print("[WARNING] No collections found - may need to run ingestion", file=sys.stderr)
            results["status"] = "WARNING"

    except Exception as e:
        results["error"] = str(e)
        results["status"] = "FAIL"
        print(f"[FAIL] {results['error']}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Probe ChromaDB via SDK")
    parser.add_argument("--host", default="localhost", help="ChromaDB host")
    parser.add_argument("--port", type=int, default=9100, help="ChromaDB port")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--check-collection", help="Specific collection to check for")
    args = parser.parse_args()

    results = probe_chroma_sdk(args.host, args.port)

    # Check for specific collection if requested
    if args.check_collection:
        if args.check_collection in results["collections"]:
            coll_count = results["collections"][args.check_collection]["count"]
            print(f"\n[OK] Collection '{args.check_collection}' found with {coll_count} vectors")
            results["target_collection"] = args.check_collection
            results["target_count"] = coll_count
        else:
            print(f"\n[WARNING] Collection '{args.check_collection}' not found", file=sys.stderr)
            results["target_collection"] = args.check_collection
            results["target_count"] = 0

    # Write JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results written to {output_path}")

    # Write markdown summary
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# ChromaDB SDK Probe Results\n\n")
        f.write(f"**Status:** {results['status']}\n\n")
        f.write(f"**Mode:** {results['mode']}\n\n")
        f.write(f"**Total Vectors:** {results['total_vectors']}\n\n")

        if args.check_collection:
            f.write(f"**Target Collection:** {args.check_collection}\n\n")
            f.write(f"**Target Count:** {results.get('target_count', 0)}\n\n")

        f.write("## Collections\n\n")
        if results["collections"]:
            for name, info in results["collections"].items():
                f.write(f"- **{name}**: {info['count']} vectors\n")
        else:
            f.write("*No collections found*\n")

        if results["error"]:
            f.write(f"\n## Error\n\n```\n{results['error']}\n```\n")

    print(f"[OK] Markdown summary written to {md_path}")

    # Exit based on status
    if results["status"] == "FAIL":
        sys.exit(1)
    elif results["status"] == "WARNING" and args.check_collection:
        sys.exit(2)  # Collection not found
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
