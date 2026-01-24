"""
Live Vector Store Smoke Tests - Wave 2 Prep

These tests interact with real vector databases. They are:
- Guarded by TEST_MODE=live
- Guarded by database connectivity
- Safe (use temporary collections, clean up after)
- Minimal data (5 documents max)

Run with: pytest -m live tests/live/test_live_vector_store_smoke.py
"""

import os
import pytest
from .conftest import skip_if_not_live, skip_if_no_env


@pytest.mark.live
class TestChromaDBLive:
    """Test ChromaDB vector store (if running)."""

    @skip_if_not_live()
    def test_chromadb_connection(self):
        """Test ChromaDB connection."""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb package not installed")

        chroma_host = os.getenv('CHROMA_HOST', 'localhost')
        chroma_port = int(os.getenv('CHROMA_PORT', '8000'))

        try:
            # Try HTTP client first
            client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            client.heartbeat()
            print(f"[OK] ChromaDB reachable at {chroma_host}:{chroma_port}")

        except Exception as e:
            # Fallback to persistent client (local mode)
            try:
                client = chromadb.PersistentClient(path="./chroma_db")
                client.heartbeat()
                print("[OK] ChromaDB connected in persistent mode")
            except Exception as e2:
                pytest.skip(f"ChromaDB not reachable: {e}, {e2}")

    @skip_if_not_live()
    def test_chromadb_crud_operations(self):
        """Test ChromaDB CRUD operations with minimal data."""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb package not installed")

        chroma_host = os.getenv('CHROMA_HOST', 'localhost')
        chroma_port = int(os.getenv('CHROMA_PORT', '8000'))

        # Connect to ChromaDB
        try:
            client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            client.heartbeat()
        except:
            try:
                client = chromadb.PersistentClient(path="./chroma_db")
            except Exception as e:
                pytest.skip(f"ChromaDB not available: {e}")

        collection_name = "test_wave2_smoke"

        try:
            # Clean up any existing test collection
            try:
                client.delete_collection(name=collection_name)
            except:
                pass

            # Create collection
            collection = client.create_collection(name=collection_name)

            # Insert 5 test documents
            documents = [
                "The sky is blue",
                "Grass is green",
                "Water is clear",
                "Fire is hot",
                "Ice is cold"
            ]

            ids = [f"doc_{i}" for i in range(len(documents))]

            collection.add(
                documents=documents,
                ids=ids,
                metadatas=[{"source": "test"} for _ in documents]
            )

            # Query for similar documents
            results = collection.query(
                query_texts=["What color is the sky?"],
                n_results=2
            )

            # Assertions
            assert results is not None
            assert 'documents' in results
            assert len(results['documents'][0]) == 2
            # Should find "The sky is blue" as most relevant
            assert "blue" in results['documents'][0][0].lower() or "sky" in results['documents'][0][0].lower()

            print(f"[OK] ChromaDB CRUD operations successful")
            print(f"     Query returned: {results['documents'][0][0]}")

        finally:
            # Clean up
            try:
                client.delete_collection(name=collection_name)
                print(f"[OK] Test collection '{collection_name}' deleted")
            except Exception as e:
                print(f"[WARN] Failed to delete test collection: {e}")


@pytest.mark.live
class TestQdrantLive:
    """Test Qdrant vector store (if running)."""

    @skip_if_not_live()
    @skip_if_no_env('QDRANT_URL', 'QDRANT_URL not set')
    def test_qdrant_connection(self):
        """Test Qdrant connection."""
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            pytest.skip("qdrant-client package not installed")

        qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')

        try:
            client = QdrantClient(url=qdrant_url)
            collections = client.get_collections()
            print(f"[OK] Qdrant reachable at {qdrant_url}")

        except Exception as e:
            pytest.skip(f"Qdrant not reachable: {e}")

    @skip_if_not_live()
    @skip_if_no_env('QDRANT_URL', 'QDRANT_URL not set')
    def test_qdrant_crud_operations(self):
        """Test Qdrant CRUD operations with minimal data."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
        except ImportError:
            pytest.skip("qdrant-client package not installed")

        qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        collection_name = "test_wave2_smoke"

        try:
            client = QdrantClient(url=qdrant_url)
        except Exception as e:
            pytest.skip(f"Qdrant not available: {e}")

        try:
            # Clean up any existing test collection
            try:
                client.delete_collection(collection_name=collection_name)
            except:
                pass

            # Create collection (simple 3D vectors for testing)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=3, distance=Distance.COSINE)
            )

            # Insert 5 test points
            points = [
                PointStruct(id=1, vector=[1.0, 0.0, 0.0], payload={"text": "Point A"}),
                PointStruct(id=2, vector=[0.0, 1.0, 0.0], payload={"text": "Point B"}),
                PointStruct(id=3, vector=[0.0, 0.0, 1.0], payload={"text": "Point C"}),
                PointStruct(id=4, vector=[0.5, 0.5, 0.0], payload={"text": "Point D"}),
                PointStruct(id=5, vector=[0.0, 0.5, 0.5], payload={"text": "Point E"}),
            ]

            client.upsert(collection_name=collection_name, points=points)

            # Search for similar points
            results = client.search(
                collection_name=collection_name,
                query_vector=[1.0, 0.1, 0.0],
                limit=2
            )

            # Assertions
            assert len(results) == 2
            assert results[0].id == 1  # Should be closest to [1, 0, 0]

            print(f"[OK] Qdrant CRUD operations successful")

        finally:
            # Clean up
            try:
                client.delete_collection(collection_name=collection_name)
                print(f"[OK] Test collection '{collection_name}' deleted")
            except Exception as e:
                print(f"[WARN] Failed to delete test collection: {e}")


@pytest.mark.live
class TestElasticsearchLive:
    """Test Elasticsearch (if running)."""

    @skip_if_not_live()
    @skip_if_no_env('ELASTICSEARCH_URL', 'ELASTICSEARCH_URL not set')
    def test_elasticsearch_connection(self):
        """Test Elasticsearch connection."""
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            pytest.skip("elasticsearch package not installed")

        es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')

        try:
            client = Elasticsearch([es_url])
            info = client.info()
            print(f"[OK] Elasticsearch reachable at {es_url}")
            print(f"     Version: {info.get('version', {}).get('number', 'unknown')}")

        except Exception as e:
            pytest.skip(f"Elasticsearch not reachable: {e}")
