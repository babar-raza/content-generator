"""Verify ChromaDB Collections and Counts

STOP-THE-LINE script: Connects to ChromaDB and verifies collections exist with data.
"""
import sys
import json
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)


def verify_chroma_counts(host: str = "localhost", port: int = 8000, db_path: str = "./chroma_db"):
    """Verify ChromaDB collections and counts.

    Args:
        host: ChromaDB host (for HTTP mode)
        port: ChromaDB port (for HTTP mode)
        db_path: Path to ChromaDB persistent storage (for file mode)

    Returns:
        dict: Collection counts and metadata
    """
    results = {
        "mode": "unknown",
        "collections": {},
        "total_vectors": 0,
        "status": "UNKNOWN",
        "error": None
    }

    # Try persistent client first (most common for local development)
    try:
        client = chromadb.PersistentClient(path=db_path)
        results["mode"] = f"persistent:{db_path}"
        print(f"[OK] Connected to ChromaDB persistent storage at {db_path}")
    except Exception as e1:
        # Fall back to HTTP client
        try:
            client = chromadb.HttpClient(host=host, port=port)
            # Try to list collections instead of heartbeat (which may not exist in all versions)
            client.list_collections()
            results["mode"] = f"http://{host}:{port}"
            print(f"[OK] Connected to ChromaDB HTTP server at {host}:{port}")
        except Exception as e2:
            results["error"] = f"Persistent: {str(e1)}, HTTP: {str(e2)}"
            results["status"] = "FAIL"
            print(f"[FAIL] STOP-THE-LINE: Cannot connect to ChromaDB", file=sys.stderr)
            print(f"  Persistent error: {e1}", file=sys.stderr)
            print(f"  HTTP error: {e2}", file=sys.stderr)
            return results

    # List collections
    try:
        collections = client.list_collections()
        print(f"\nFound {len(collections)} collection(s):")

        for collection in collections:
            name = collection.name
            count = collection.count()
            results["collections"][name] = {
                "count": count,
                "metadata": collection.metadata
            }
            results["total_vectors"] += count
            print(f"  - {name}: {count} vectors")

        # Check requirements
        blog_count = results["collections"].get("blog_knowledge", {}).get("count", 0)
        api_count = results["collections"].get("api_reference", {}).get("count", 0)

        if blog_count > 0 and api_count > 0:
            results["status"] = "PASS"
            print(f"\n[PASS] blog_knowledge={blog_count}, api_reference={api_count}")
        else:
            results["status"] = "FAIL"
            print(f"\n[FAIL] blog_knowledge={blog_count}, api_reference={api_count}")
            print("  Both collections must have count > 0", file=sys.stderr)

    except Exception as e:
        results["error"] = str(e)
        results["status"] = "FAIL"
        print(f"[FAIL] Error listing collections: {e}", file=sys.stderr)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Verify ChromaDB collections")
    parser.add_argument("--host", default="localhost", help="ChromaDB host")
    parser.add_argument("--port", type=int, default=8000, help="ChromaDB port")
    parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB persistent path")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()

    results = verify_chroma_counts(args.host, args.port, args.db_path)

    # Write JSON output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n[OK] Results written to {output_path}")

        # Also write markdown summary
        md_path = output_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# ChromaDB Collection Verification\n\n")
            f.write(f"**Status:** {results['status']}\n\n")
            f.write(f"**Mode:** {results['mode']}\n\n")
            f.write(f"**Total Vectors:** {results['total_vectors']}\n\n")
            f.write("## Collections\n\n")
            for name, info in results["collections"].items():
                f.write(f"- **{name}**: {info['count']} vectors\n")
            if results["error"]:
                f.write(f"\n## Error\n\n```\n{results['error']}\n```\n")
        print(f"[OK] Markdown summary written to {md_path}")

    # Exit with appropriate code
    sys.exit(0 if results["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
