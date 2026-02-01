#!/usr/bin/env python3
"""GitHub Gist API stub server for testing without secrets."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import sys


class GistStubHandler(BaseHTTPRequestHandler):
    """Mock GitHub Gist API handler."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path.startswith("/gists/"):
            # Return mock gist data
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            gist_data = {
                "id": "mock-gist-id-12345",
                "url": f"https://api.github.com{self.path}",
                "html_url": "https://gist.github.com/mockuser/mock-gist-id-12345",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "description": "Mock gist created by stub server",
                "public": True,
                "files": {
                    "mock_file.md": {
                        "filename": "mock_file.md",
                        "type": "text/markdown",
                        "size": 42,
                        "content": "# Mock Content\n\nThis is stub data."
                    }
                }
            }
            self.wfile.write(json.dumps(gist_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if self.path == "/gists":
            # Create gist
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            try:
                request_data = json.loads(body)
                gist_data = {
                    "id": "mock-created-gist-id",
                    "url": "https://api.github.com/gists/mock-created-gist-id",
                    "html_url": "https://gist.github.com/mockuser/mock-created-gist-id",
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "description": request_data.get("description", ""),
                    "public": request_data.get("public", True),
                    "files": request_data.get("files", {})
                }
                self.wfile.write(json.dumps(gist_data).encode())
            except Exception as e:
                error = {"error": str(e)}
                self.wfile.write(json.dumps(error).encode())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8201
    server = HTTPServer(('localhost', port), GistStubHandler)
    print(f"GitHub Gist stub server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  POST /gists - Create gist")
    print(f"  GET /gists/<id> - Get gist")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
