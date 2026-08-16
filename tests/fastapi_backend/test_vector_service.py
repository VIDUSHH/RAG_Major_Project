"""Regression tests for QdrantService collection dimension handling.

When the embedding model changes (e.g. gemini-embedding-2 768-dim -> local
all-MiniLM-L6-v2 384-dim), an existing collection must be recreated at the new
dimension so writes don't fail with a dimension mismatch.
"""

from types import SimpleNamespace

import pytest

from app.services.vector_service import QdrantService


class FakeQdrantClient:
    """Minimal stub of the qdrant-client surface used by QdrantService."""

    def __init__(self, collections: list[str], dims: dict[str, int]):
        self._collections = collections
        self._dims = dims
        self.deleted = []
        self.created = []

    def get_collections(self):
        return SimpleNamespace(collections=[SimpleNamespace(name=n) for n in self._collections])

    def get_collection(self, collection_name: str):
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=SimpleNamespace(size=self._dims.get(collection_name, 0))
                )
            )
        )

    def delete_collection(self, collection_name: str):
        self.deleted.append(collection_name)

    def create_collection(self, collection_name: str, vectors_config, **kwargs):
        self.created.append((collection_name, vectors_config.size))

    def create_payload_index(self, *args, **kwargs):
        pass


@pytest.fixture
def svc():
    service = QdrantService()
    service._client = FakeQdrantClient(
        collections=["postmortems_v1"],
        dims={"postmortems_v1": 768},
    )
    return service


def test_recreates_collection_when_dimension_changes(svc):
    assert svc.create_collection("postmortems_v1", dimension=384)
    assert svc._client.deleted == ["postmortems_v1"]
    assert svc._client.created == [("postmortems_v1", 384)]


def test_keeps_collection_when_dimension_matches(svc):
    assert svc.create_collection("postmortems_v1", dimension=768)
    assert svc._client.deleted == []
    assert svc._client.created == []


def test_creates_collection_when_missing():
    service = QdrantService()
    service._client = FakeQdrantClient(collections=[], dims={})
    assert service.create_collection("postmortems_v1", dimension=384)
    assert service._client.deleted == []
    assert service._client.created == [("postmortems_v1", 384)]
