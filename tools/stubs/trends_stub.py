#!/usr/bin/env python3
"""Google Trends API stub server for testing without network."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import random


class TrendsStubHandler(BaseHTTPRequestHandler):
    """Mock Trends API handler."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        """Handle GET requests."""
        if "/trends" in self.path or "/search" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Return mock trends data
            trends_data = {
                "trending_searches": [
                    {"query": "API documentation", "volume": random.randint(1000, 50000)},
                    {"query": "file conversion", "volume": random.randint(1000, 50000)},
                    {"query": "PDF generation", "volume": random.randint(1000, 50000)},
                    {"query": "data visualization", "volume": random.randint(1000, 50000)}
                ],
                "related_queries": [
                    "document processing",
                    "image manipulation",
                    "text extraction"
                ],
                "timestamp": "2026-01-31T09:30:00Z"
            }
            self.wfile.write(json.dumps(trends_data).encode())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8202
    server = HTTPServer(('localhost', port), TrendsStubHandler)
    print(f"Trends stub server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  GET /trends - Get trending searches")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
