"""Module-private persistent Chroma collection accessed through LlamaIndex's ChromaVectorStore.

Lives in storage/chroma, separate from rag_service/chroma_db. Every query is filtered by project_id
and by the active document ids that SQLite (the source of truth for versions) allows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

COLLECTION = "assistant_chunks"


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    project_id: str
    score: float


class ChromaChunkStore:
    def __init__(self, path: Path, collection: str = COLLECTION) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from llama_index.vector_stores.chroma import ChromaVectorStore

        path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path), settings=ChromaSettings(anonymized_telemetry=False))
        self._collection = client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})
        self._store = ChromaVectorStore(chroma_collection=self._collection)

    def count(self) -> int:
        return self._collection.count()

    def add(self, *, document_id: str, project_id: str, embedding_model: str, rows: list[tuple[str, str, np.ndarray]]) -> None:
        """rows: (chunk_id, embedded_text, vector)."""
        from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode

        nodes = []
        for chunk_id, text, vector in rows:
            node = TextNode(
                id_=chunk_id,
                text=text,
                metadata={"project_id": project_id, "embedding_model": embedding_model},
                relationships={NodeRelationship.SOURCE: RelatedNodeInfo(node_id=document_id)},
            )
            node.embedding = [float(x) for x in vector]
            nodes.append(node)
        self._store.add(nodes)

    def delete_document(self, document_id: str) -> None:
        self._store.delete(ref_doc_id=document_id)

    def query(self, *, vector: np.ndarray, project_id: str, document_ids: list[str], embedding_model: str, k: int) -> list[VectorHit]:
        from llama_index.core.vector_stores.types import (
            FilterCondition, FilterOperator, MetadataFilter, MetadataFilters, VectorStoreQuery,
        )

        if not document_ids:
            return []
        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="project_id", value=project_id, operator=FilterOperator.EQ),
                MetadataFilter(key="embedding_model", value=embedding_model, operator=FilterOperator.EQ),
                MetadataFilter(key="document_id", value=document_ids, operator=FilterOperator.IN),
            ],
            condition=FilterCondition.AND,
        )
        result = self._store.query(VectorStoreQuery(query_embedding=[float(x) for x in vector], similarity_top_k=k, filters=filters))
        hits = []
        for node, score in zip(result.nodes or [], result.similarities or []):
            hits.append(VectorHit(node.node_id, str(node.metadata.get("project_id")), float(score)))
        return hits
