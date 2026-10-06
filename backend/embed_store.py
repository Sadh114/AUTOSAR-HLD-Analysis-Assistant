"""Embedding generation + persistent local vector store (ChromaDB)."""
from backend import config  # must be imported first to redirect caches

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

_model = None
_client = None
_collection = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(
            config.EMBEDDING_MODEL_NAME,
            cache_folder=str(config.HF_CACHE_DIR),
        )
    return _model


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name="hld_chunks",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(chunks):
    """chunks: list[backend.ingestion.Chunk]"""
    if not chunks:
        return
    model = get_model()
    collection = get_collection()
    texts = [c.text for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True).tolist()
    collection.add(
        ids=[c.chunk_id for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "doc_id": c.doc_id,
                "filename": c.filename,
                "page": c.page,
                "section": c.section,
            }
            for c in chunks
        ],
    )


def query(question: str, doc_ids=None, top_k: int = None):
    top_k = top_k or config.TOP_K_RETRIEVAL
    model = get_model()
    collection = get_collection()
    q_embedding = model.encode([question], normalize_embeddings=True).tolist()

    where = None
    if doc_ids:
        where = {"doc_id": {"$in": doc_ids}} if len(doc_ids) > 1 else {"doc_id": doc_ids[0]}

    results = collection.query(
        query_embeddings=q_embedding,
        n_results=top_k,
        where=where,
    )

    hits = []
    if results.get("ids") and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            hits.append(
                {
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
            )
    return hits


def delete_document_chunks(doc_id: str):
    collection = get_collection()
    collection.delete(where={"doc_id": doc_id})


def collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0
