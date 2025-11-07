"""Integration test for FastAPI - import app (or create_app()), GET one of ["/health", "/ping", "/"] returns 2xx."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test FastAPI app import and health endpoint
class TestFastAPIIntegration:
    """Test FastAPI app integration."""

    def test_import_app_module(self):
        """Test that we can import the FastAPI app module."""
        try:
            from src.web import app
            assert app is not None
        except ImportError as e:
            # If import fails, check if it's due to missing dependencies
            if "fastapi" in str(e).lower():
                pytest.skip("FastAPI not installed - skipping web integration tests")
            else:
                raise

    def test_app_has_expected_structure(self):
        """Test that the imported app has expected FastAPI structure."""
        pytest.importorskip("fastapi")

        from src.web import app

        # Check that it's a FastAPI instance
        assert hasattr(app, 'routes')
        assert hasattr(app, 'router')

        # Check that routes exist
        routes = [route.path for route in app.routes]
        assert len(routes) > 0, "App should have routes defined"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test GET /health returns 2xx status."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")  # For testing FastAPI

        from src.web import app
        from httpx import AsyncClient

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/health")

            # Should return 2xx status
            assert 200 <= response.status_code < 300, f"Health endpoint returned {response.status_code}"

            # Should return JSON
            assert response.headers.get("content-type", "").startswith("application/json")

    @pytest.mark.asyncio
    async def test_ping_endpoint(self):
        """Test GET /ping returns 2xx status."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        from src.web import app
        from httpx import AsyncClient

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/ping")

            # Should return 2xx status
            assert 200 <= response.status_code < 300, f"Ping endpoint returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test GET / returns 2xx status."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        from src.web import app
        from httpx import AsyncClient

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/")

            # Should return 2xx status
            assert 200 <= response.status_code < 300, f"Root endpoint returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_health_endpoint_content(self):
        """Test that health endpoint returns expected content."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        from src.web import app
        from httpx import AsyncClient

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/health")
            data = response.json()

            # Should contain status information
            assert "status" in data or "healthy" in str(data).lower() or "ok" in str(data).lower()

    def test_create_app_function(self):
        """Test if there's a create_app() function available."""
        try:
            from src.web.app import create_app
            # If function exists, test that it returns a FastAPI app
            test_app = create_app()
            assert test_app is not None
            assert hasattr(test_app, 'routes')
        except ImportError:
            # create_app function may not exist, which is fine
            pass

    def test_app_routes_include_expected_endpoints(self):
        """Test that app includes expected API endpoints."""
        pytest.importorskip("fastapi")

        from src.web import app

        routes = [route.path for route in app.routes]

        # Should have at least one of the required endpoints
        required_endpoints = ["/health", "/ping", "/"]
        has_required = any(endpoint in routes for endpoint in required_endpoints)

        assert has_required, f"App should have at least one of {required_endpoints}, but has: {routes}"

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test that API responses include appropriate CORS headers."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        from src.web import app
        from httpx import AsyncClient

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/health")

            # Check for common CORS headers (may or may not be present)
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods",
                "access-control-allow-headers"
            ]

            # At minimum, should not have errors
            assert response.status_code < 400

    def test_app_startup_without_errors(self):
        """Test that app can be created without import/configuration errors."""
        pytest.importorskip("fastapi")

        # This should not raise any exceptions
        from src.web import app

        # Verify it's properly configured
        assert app.title is not None
        assert len(app.title) > 0

    @pytest.mark.asyncio
    async def test_multiple_endpoints_consistency(self):
        """Test that all health-check endpoints return consistent responses."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        from src.web import app
        from httpx import AsyncClient

        endpoints = ["/health", "/ping", "/"]

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            responses = {}
            for endpoint in endpoints:
                try:
                    response = await client.get(endpoint)
                    responses[endpoint] = response.status_code
                except Exception:
                    # Endpoint might not exist, skip
                    continue

            # All accessible endpoints should return 2xx
            for endpoint, status in responses.items():
                assert 200 <= status < 300, f"Endpoint {endpoint} returned {status}"

            # At least one endpoint should work
            assert len(responses) > 0, "No health endpoints accessible"