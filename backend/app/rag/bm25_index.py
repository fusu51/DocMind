"""
BM25 稀疏检索 — 内存索引，jieba 分词，支持自定义词典
"""
import os
from typing import List, Dict, Any, Optional

import jieba
from rank_bm25 import BM25Okapi

# 加载自定义词典（项目目录下的 user_dict.txt）
_DICT_PATH = os.path.join(os.path.dirname(__file__), "user_dict.txt")
if os.path.exists(_DICT_PATH) and os.path.getsize(_DICT_PATH) > 0:
    jieba.load_userdict(_DICT_PATH)


class BM25Index:
    """内存 BM25 索引，支持按文档增删"""

    def __init__(self):
        self._corpus: List[List[str]] = []       # 分词后的语料
        self._chunks: List[Dict[str, Any]] = []  # 对应的 chunk 元数据
        self._bm25: Optional[BM25Okapi] = None

    def _rebuild(self):
        """重建 BM25 模型"""
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)
        else:
            self._bm25 = None

    def _tokenize(self, text: str) -> List[str]:
        """jieba 分词 + 字符级 2-gram 混合，保证索引和查询一致"""
        words = [w for w in jieba.cut(text) if len(w.strip()) > 1]

        # 始终补充字符 2-gram，确保索引和查询对齐
        clean = text.replace(" ", "").replace("\n", "")
        seen = set(words)
        for i in range(len(clean) - 1):
            bigram = clean[i:i + 2]
            if bigram not in seen:
                seen.add(bigram)
                words.append(bigram)

        return words



    def add(self, chunks: List[Dict[str, Any]]):
        """批量添加文档片段"""
        for c in chunks:
            tokens = self._tokenize(c["text"])
            self._corpus.append(tokens)
            self._chunks.append(c)
        self._rebuild()

    def delete_by_doc_id(self, doc_id: str):
        """按 doc_id 删除所有关联片段"""
        keep_idx = [
            i for i, c in enumerate(self._chunks)
            if c.get("doc_id") != doc_id
        ]
        self._corpus = [self._corpus[i] for i in keep_idx]
        self._chunks = [self._chunks[i] for i in keep_idx]
        self._rebuild()

    def search(self, query: str, top_k: int = 30) -> List[Dict[str, Any]]:
        """BM25 搜索"""
        if not self._bm25:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)

        # 按分数降序，过滤零分
        ranked = sorted(
            [(i, s) for i, s in enumerate(scores) if s > 0],
            key=lambda x: x[1],
            reverse=True,
        )

        results = []
        for idx, score in ranked[:top_k]:
            chunk = self._chunks[idx].copy()
            chunk["bm25_score"] = round(float(score), 4)
            results.append(chunk)

        return results

    @property
    def size(self) -> int:
        return len(self._corpus)


# ---- 全局单例 ----

_bm25_index: Optional[BM25Index] = None


def get_bm25_index() -> BM25Index:
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index
