#!/usr/bin/env python3
"""Competitor analysis API stub server."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys


class CompetitorStubHandler(BaseHTTPRequestHandler):
    """Mock competitor analysis API."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        """Handle GET requests."""
        if "/competitors" in self.path or "/analysis" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            competitor_data = {
                "competitors": [
                    {
                        "name": "MockCompetitor A",
                        "market_share": 25.5,
                        "strengths": ["Fast processing", "Good documentation"],
                        "weaknesses": ["Limited formats", "High cost"]
                    },
                    {
                        "name": "MockCompetitor B",
                        "market_share": 18.2,
                        "strengths": ["Wide format support", "Cloud integration"],
                        "weaknesses": ["Slower", "Complex API"]
                    }
                ],
                "market_analysis": {
                    "total_market_size": "$500M",
                    "growth_rate": "12% YoY"
                }
            }
            self.wfile.write(json.dumps(competitor_data).encode())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8203
    server = HTTPServer(('localhost', port), CompetitorStubHandler)
    print(f"Competitor stub server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  GET /competitors - Get competitor data")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
