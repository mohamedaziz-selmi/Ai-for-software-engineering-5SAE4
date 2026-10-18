"""Local semantic retrieval API. This intentionally contains no BM25 or reranking."""

from contextlib import asynccontextmanager
from typing import Literal

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from hybrid_retrieval import BM25Index, distribution, fuse_rrf

Category = Literal["client_requirements", "freelancer_proposals", "evaluation_knowledge_base"]


def collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL),
    )


def build_bm25_index(active_collection):
    data = active_collection.get(include=["documents", "metadatas"])
    records = [
        {"id": chunk_id, "text": text, "source": metadata}
        for chunk_id, text, metadata in zip(data["ids"], data["documents"], data["metadatas"])
    ]
    return BM25Index(records)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.collection = collection()
        app.state.bm25 = build_bm25_index(app.state.collection)
    except ValueError:
        app.state.collection = None
        app.state.bm25 = None
    yield


app = FastAPI(title="Cerebro Semantic RAG API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=4000)
    limit: int = Field(default=5, ge=1, le=20)
    category: Category | None = None
    mode: Literal["semantic", "hybrid"] = "hybrid"


@app.get("/health")
def health():
    active_collection = app.state.collection
    return {
        "ready": active_collection is not None,
        "retrieval": "hybrid_rrf",
        "collection": COLLECTION_NAME,
        "chunk_count": active_collection.count() if active_collection else 0,
        "bm25_chunk_count": len(app.state.bm25.records) if app.state.bm25 else 0,
    }


@app.post("/search")
def search(request: SearchRequest):
    active_collection = app.state.collection
    if active_collection is None:
        raise HTTPException(status_code=503, detail="Knowledge base has not been indexed. Run `python ingest.py --reset` first.")

    candidate_limit = max(request.limit * 4, 20)
    semantic_results = active_collection.query(
        query_texts=[request.query],
        n_results=candidate_limit,
        where={"category": request.category} if request.category else None,
        include=["documents", "metadatas", "distances"],
    )
    semantic = [
        {"id": chunk_id, "text": document, "distance": distance, "source": metadata}
        for chunk_id, document, metadata, distance in zip(
            semantic_results["ids"][0], semantic_results["documents"][0], semantic_results["metadatas"][0], semantic_results["distances"][0]
        )
    ]
    lexical = app.state.bm25.search(request.query, candidate_limit, request.category) if request.mode == "hybrid" else []
    results = fuse_rrf(semantic, lexical, request.limit) if request.mode == "hybrid" else semantic[:request.limit]
    return {
        "query": request.query,
        "retrieval": "hybrid_rrf" if request.mode == "hybrid" else "semantic_only",
        "fusion": {"method": "reciprocal_rank_fusion", "rrf_k": 60, "semantic_candidates": len(semantic), "bm25_candidates": len(lexical)} if request.mode == "hybrid" else None,
        "results": [
            {
                "text": result["text"],
                "distance": result.get("distance"),
                "bm25_score": result.get("bm25_score"),
                "rrf_score": result.get("rrf_score"),
                "ranks": result.get("ranks", {"semantic": index + 1}),
                "source": result["source"],
            }
            for index, result in enumerate(results)
        ],
    }
