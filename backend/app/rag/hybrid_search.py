"""
三层混合检索编排 — L1 查询处理 → L2 双路召回 → L3 重排序
"""
from typing import List, Dict, Any, Optional, Tuple
from ..config import ABSTAIN_HARD_THRESHOLD, ABSTAIN_SOFT_THRESHOLD
from .retriever import dense_search
from .bm25_index import get_bm25_index
from .query_processor import get_query_processor
from .reranker import rerank

RRF_K = 60


def hybrid_search(
        question: str,
        top_k: int = 6,
        score_threshold: float = 0.5,
        doc_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    三层混合检索统一入口。
    返回 (chunks, pipeline_info)
    """

    pipeline = {
        "l1": {"enabled": False, "method": "原始问题"},
        "l2": {"dense": 0, "sparse": 0, "method": "RRF融合"},
        "l3": {"enabled": False, "candidates": 0, "final": 0, "method": "BGE-Reranker-v2-m3"},
        "l4": {"original": 0, "compressed": 0, "max_tokens": 0},
    }

    # ===== L1: 查询处理 =====
    processor = get_query_processor()
    search_query = processor.process(question)

    if search_query != question:
        pipeline["l1"]["enabled"] = True
        pipeline["l1"]["method"] = "HyDE 假想答案"

    # ===== L2: 双路召回 + RRF 融合 =====
    dense_results = dense_search(
        query=search_query,
        top_k=100,
        score_threshold=0.0,
        doc_id=doc_id,
    )

    bm25 = get_bm25_index()
    sparse_results = bm25.search(question, top_k=30)

    pipeline["l2"]["dense"] = len(dense_results)
    pipeline["l2"]["sparse"] = len(sparse_results)

    candidate_map = _rrf_fusion(dense_results, sparse_results)
    candidate_list = sorted(
        candidate_map.values(),
        key=lambda x: x.get("rrf_score", 0),
        reverse=True,
    )[:20]

    # ===== L3: 重排序 =====
    if len(candidate_list) > top_k:
        pipeline["l3"]["enabled"] = True
        pipeline["l3"]["candidates"] = len(candidate_list)
        final = rerank(question, candidate_list, top_k=top_k)
        pipeline["l3"]["final"] = len(final)
    else:
        final = sorted(candidate_list, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
        pipeline["l3"]["final"] = len(final)

    # ===== 基于 L3 最高分的拒答判定 =====
    pipeline["abstain_level"] = "none"
    pipeline["top1_score"] = 0.0

    result = [c for c in final if c.get("score", 0) >= score_threshold]

    if result:
        max_score = max(c.get("score", 0) for c in result)
        pipeline["top1_score"] = round(max_score, 4)

        if max_score < ABSTAIN_HARD_THRESHOLD:
            pipeline["abstain_level"] = "hard"
        elif max_score < ABSTAIN_SOFT_THRESHOLD:
            pipeline["abstain_level"] = "soft"

    return result, pipeline


def _rrf_fusion(dense, sparse):
    merged: Dict[str, Dict[str, Any]] = {}

    def _add(ranked_list, weight=1.0):
        for rank, chunk in enumerate(ranked_list, start=1):
            cid = chunk.get("id", f"{chunk.get('doc_id', '')}_{chunk.get('chunk_index', rank)}")
            score = weight / (RRF_K + rank)
            if cid in merged:
                merged[cid]["rrf_score"] = merged[cid].get("rrf_score", 0) + score
                if chunk.get("score", 0) > merged[cid].get("score", 0):
                    merged[cid].update(chunk)
            else:
                chunk_copy = chunk.copy()
                chunk_copy["rrf_score"] = score
                merged[cid] = chunk_copy

    _add(dense)
    _add(sparse)
    return merged
