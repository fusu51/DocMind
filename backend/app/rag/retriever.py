"""检索 — Dense 通路 (ChromaDB) + BM25 索引同步"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
import os

from ..config import CHROMA_PERSIST_DIR
from .embeddings import embed_texts, embed_single, create_embedding_client
from .bm25_index import get_bm25_index


# 全局 ChromaDB 客户端（懒加载）
_chroma_client = None
_collection = None


def _get_collection():
    """获取或初始化 ChromaDB collection"""
    global _chroma_client, _collection
    if _collection is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
            ),
        )
        _collection = _chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def dense_search(
        query: str,
        top_k: int = 100,
        score_threshold: float = 0.0,
        doc_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Dense 语义搜索（ChromaDB）。
    被 hybrid_search 调用。
    """
    collection = _get_collection()
    query_embedding = embed_single(query)

    where_filter = {"doc_id": doc_id} if doc_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            similarity = 1 - (distance / 2)

            if similarity >= score_threshold:
                meta = results["metadatas"][0][i]
                chunks.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "doc_name": meta.get("doc_name", "未知"),
                    "page_number": meta.get("page_number", 1),
                    "score": round(similarity, 4),
                    "doc_id": meta.get("doc_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "parent_index": meta.get("parent_index"),
                })

    return chunks


def add_chunks(chunks: List[Dict[str, Any]]):
    """批量存入 ChromaDB，同时更新 BM25 索引"""
    collection = _get_collection()
    client = create_embedding_client()

    texts = [c["text"] for c in chunks]
    embeddings = []
    batch_size = 20

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings.extend(embed_texts(batch, client=client))

    metadatas = []
    for c in chunks:
        meta = {
            "doc_id": c["doc_id"],
            "doc_name": c["doc_name"],
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
        }
        if "parent_index" in c:
            meta["parent_index"] = c["parent_index"]
        if "chunk_type" in c:
            meta["chunk_type"] = c["chunk_type"]
        metadatas.append(meta)

    collection.add(
        ids=[f"{c['doc_id']}_{c['chunk_index']}" for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    # 同步 BM25
    try:
        bm25 = get_bm25_index()
        bm25.add(chunks)
    except Exception as e:
        print(f"[Retriever] BM25 sync add failed: {e}")


def delete_by_doc_id(doc_id: str):
    """删除某文档：ChromaDB + BM25"""
    collection = _get_collection()
    try:
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        pass

    # 同步 BM25
    try:
        bm25 = get_bm25_index()
        bm25.delete_by_doc_id(doc_id)
    except Exception as e:
        print(f"[Retriever] BM25 sync delete failed: {e}")


def rebuild_bm25() -> int:
    """
    从 ChromaDB 读取所有已索引的 chunk 元数据和文本，重建 BM25 索引。
    用于后端重启后恢复内存索引。
    返回重建的 chunk 数量。
    """
    collection = _get_collection()
    bm25 = get_bm25_index()

    # 获取所有文档的所有 chunk
    try:
        results = collection.get(
            include=["documents", "metadatas"],
        )
    except Exception:
        return 0

    if not results or not results.get("ids"):
        return 0

    chunks = []
    for i in range(len(results["ids"])):
        meta = results["metadatas"][i] if results.get("metadatas") else {}
        chunks.append({
            "text": results["documents"][i] if results.get("documents") else "",
            "doc_id": meta.get("doc_id", ""),
            "doc_name": meta.get("doc_name", ""),
            "page_number": meta.get("page_number", 1),
            "chunk_index": meta.get("chunk_index", i),
        })

    bm25.add(chunks)
    return len(chunks)
