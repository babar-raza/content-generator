#!/usr/bin/env python3
"""Link validation stub - validates against local Aspose sample files."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
from pathlib import Path
import re


class LinkValidationStubHandler(BaseHTTPRequestHandler):
    """Mock link validation against local files."""

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if self.path == "/validate":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            try:
                request_data = json.loads(body)
                links = request_data.get("links", [])

                results = []
                for link in links:
                    # Mock validation - just check if it looks like a valid URL/path
                    is_valid = bool(re.match(r'https?://', link) or Path(link).exists())
                    results.append({
                        "link": link,
                        "valid": is_valid,
                        "status_code": 200 if is_valid else 404,
                        "checked_at": "2026-01-31T09:30:00Z"
                    })

                response = {
                    "total_links": len(links),
                    "valid_count": sum(1 for r in results if r["valid"]),
                    "invalid_count": sum(1 for r in results if not r["valid"]),
                    "results": results
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                error = {"error": str(e)}
                self.wfile.write(json.dumps(error).encode())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8204
    server = HTTPServer(('localhost', port), LinkValidationStubHandler)
    print(f"Link validation stub server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  POST /validate - Validate links")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
