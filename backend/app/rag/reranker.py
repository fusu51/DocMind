"""
L3 重排序 — BGE-Reranker-v2-m3 批量打分
通过阿里云 MaaS OpenAI 兼容接口的 /rerank 端点调用。
一次 API 调用输入 (question, [15 条候选文本])，一次出全部排序结果。
"""
from typing import List, Dict, Any
import requests

from ..config import (
    RERANKER_MODEL,
    RERANKER_BASE_URL,
    RERANKER_API_KEY,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
)


def rerank(
        question: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 6,
) -> List[Dict[str, Any]]:
    """
    批量重排序。
    参数:
        question: 用户问题
        candidates: 候选片段列表 [{text, score, ...}, ...]
        top_k: 返回数量
    返回:
        按新分数降序排列的 top_k 片段
    """
    if not candidates:
        return []

    # 候选列表 ≤ top_k 时直接返回
    if len(candidates) <= top_k:
        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)

    texts = [c["text"][:2000] for c in candidates]  # 截断长文本

    try:
        scored = _call_reranker(question, texts)
        # 将新分数写回 candidates
        for item in scored:
            idx = item["index"]
            if idx < len(candidates):
                candidates[idx]["score"] = round(item["score"], 4)

        # 按新分数降序排序
        sorted_candidates = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
        return sorted_candidates[:top_k]

    except Exception:
        # Reranker 不可用时，按原始相似度排序
        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)[:top_k]


def _call_reranker(query: str, documents: List[str]) -> List[Dict[str, Any]]:
    """
    调用 OpenAPI 兼容的 /rerank 端点（阿里云 MaaS）
    请求格式:
        POST /rerank
        {
            "model": "bge-reranker-v2-m3",
            "query": "question",
            "documents": ["doc1", "doc2", ...]
        }
    响应格式:
        {
            "results": [
                {"index": 0, "relevance_score": 0.95},
                ...
            ]
        }
    """
    base_url = RERANKER_BASE_URL or EMBEDDING_BASE_URL
    api_key = RERANKER_API_KEY or EMBEDDING_API_KEY

    if not base_url or not api_key:
        raise ValueError("Reranker 未配置：请设置 RERANKER_BASE_URL 和 RERANKER_API_KEY")

    # 确保 base_url 以 /v1 结尾
    if not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    url = f"{base_url.rstrip('/')}/rerank"

    payload = {
        "model": RERANKER_MODEL,
        "query": query,
        "documents": documents,
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])

    return [
        {"index": r["index"], "score": r.get("relevance_score", 0)}
        for r in results
    ]
