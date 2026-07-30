"""文本分块 — 语义分块（主）+ 规则分块（fallback）"""
import re
from typing import List, Dict, Tuple


class Chunk:
    """分块数据结构"""
    def __init__(self, text: str, metadata: dict):
        self.text = text
        self.metadata = metadata


# ============================================================
#  语义分块器（L0 主方案）
# ============================================================

class SemanticChunker:
    """
    基于 embedding 语义相似度的自适应分块。
    策略：逐句计算相邻句子的语义相似度，当相似度低于阈值时分块。
    避免在语义不连贯处强行切分。

    父子块策略：
    - 子块（child）：~300 token，入库做向量检索，精确匹配
    - 父块（parent）：子块所在的完整语义段落，~1200 token，送入 LLM
    """

    def __init__(
            self,
            child_size: int = 300,       # 子块目标大小（token 估算）
            parent_size: int = 1200,     # 父块目标大小（token 估算）
            similarity_threshold: float = 0.6,  # 语义相似度阈值，低于此值认为需要切分
            min_chunk_size: int = 100,   # 最小块大小
    ):
        self.child_size = child_size
        self.parent_size = parent_size
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size

    def chunk(
            self,
            text: str,
            doc_id: str,
            doc_name: str,
            file_type: str,
            total_pages: int,
    ) -> Tuple[List[Chunk], List[Chunk]]:
        """
        返回 (child_chunks, parent_chunks)
        - child_chunks: 精细子块，用于向量检索
        - parent_chunks: 语义段落父块，用于 LLM 上下文
        child.metadata["parent_index"] 关联到对应的父块
        """
        sentences = self._split_sentences(text)

        if len(sentences) <= 3:
            # 文本过短，子块和父块相同
            chunk = _make_single_chunk(text, doc_id, doc_name, file_type, 1, 0)
            chunk.metadata["parent_index"] = 0
            return [chunk], [chunk]

        # 计算相邻句子的语义相似度，确定分割点
        split_points = self._find_semantic_splits(sentences)

        # 构建父块（大语义段落）
        parent_chunks = self._build_parents(
            sentences, split_points, doc_id, doc_name, file_type, total_pages
        )

        # 构建子块（细粒度，关联父块）
        child_chunks = self._build_children(
            sentences, split_points, parent_chunks,
            doc_id, doc_name, file_type, total_pages
        )

        return child_chunks, parent_chunks

    def _split_sentences(self, text: str) -> List[Tuple[str, int]]:
        """
        按标点分句，返回 [(句子文本, 页码), ...]
        也会按空行做强制分割标记
        """
        # 先按空行预分割段落，每段内按标点分句
        paragraphs = re.split(r'\n\s*\n', text)
        result = []

        for para in paragraphs:
            if not para.strip():
                continue
            page = _extract_page_number(para)

            # 按中文/英文标点分句，保留标点
            raw_sentences = re.split(r'(?<=[。！？\.\!\?；;])\s*', para)
            for s in raw_sentences:
                s = s.strip()
                if s:
                    # 去掉页码标记（已记录在元数据中）
                    clean = re.sub(r'\[第\d+页\]\n?', '', s).strip()
                    if clean:
                        result.append((clean, page))

        return result

    def _find_semantic_splits(self, sentences: List[Tuple[str, int]]) -> List[int]:
        """
        使用 embedding 计算相邻句子相似度，找到语义断层点。
        返回分割位置列表（每个值表示在此索引之后分割）。
        """
        # 如果句子数很少，不做语义分割
        if len(sentences) <= 3:
            return []

        # 计算每句的 embedding（批量调用）
        from .embeddings import embed_texts

        texts = [s[0] for s in sentences]
        try:
            embeddings = embed_texts(texts)
        except Exception:
            # Embedding 不可用时，用规则法 fallback
            return self._rule_split_points(texts)

        # 计算相邻句子的余弦相似度
        split_points = []
        accumulated = 0  # 累积 token 数

        for i in range(1, len(sentences)):
            sim = self._cosine_sim(embeddings[i - 1], embeddings[i])
            accumulated += _estimate_tokens(sentences[i - 1][0])

            # 语义相似度低 OR 累积长度超过子块目标 → 分割
            if sim < self.similarity_threshold or accumulated >= self.child_size:
                split_points.append(i - 1)
                accumulated = 0

        return split_points

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)

    def _rule_split_points(self, texts: List[str]) -> List[int]:
        """规则法 fallback：按长度切分"""
        points = []
        accumulated = 0
        for i, t in enumerate(texts[:-1]):
            accumulated += _estimate_tokens(t)
            if accumulated >= self.child_size:
                points.append(i)
                accumulated = 0
        return points

    def _build_parents(
            self,
            sentences: List[Tuple[str, int]],
            split_points: List[int],
            doc_id: str,
            doc_name: str,
            file_type: str,
            total_pages: int,
    ) -> List[Chunk]:
        """构建父块：合并若干个相邻句子为大语义段落"""
        parents = []
        # 用 split_points 确定语义段落边界
        boundaries = sorted(set([-1] + split_points + [len(sentences) - 1]))

        pi = 0
        for start, end in _pairwise(boundaries):
            seg_sentences = sentences[start + 1:end + 1]
            merged = "".join(s[0] for s in seg_sentences)
            if merged.strip():
                page = seg_sentences[0][1] if seg_sentences else 1
                parents.append(
                    _make_single_chunk(merged, doc_id, doc_name, file_type, page, pi)
                )
                pi += 1

        return parents

    def _build_children(
            self,
            sentences: List[Tuple[str, int]],
            split_points: List[int],
            parents: List[Chunk],
            doc_id: str,
            doc_name: str,
            file_type: str,
            total_pages: int,
    ) -> List[Chunk]:
        """构建子块：控制在 child_size 左右，关联到父块"""
        children = []
        boundaries = sorted(set([-1] + split_points + [len(sentences) - 1]))
        segment_map = list(_pairwise(boundaries))  # [(start, end), ...] 对应到 parent index

        ci = 0
        for pi, (start, end) in enumerate(segment_map):
            seg_sentences = sentences[start + 1:end + 1]
            # 在语义段落内按长度继续切子块
            current_text = ""
            for s_text, s_page in seg_sentences:
                if _estimate_tokens(current_text + s_text) > self.child_size and current_text:
                    children.append(_make_child(
                        current_text.strip(), doc_id, doc_name, file_type, s_page, ci, pi
                    ))
                    ci += 1
                    current_text = s_text
                else:
                    current_text += s_text

            if current_text.strip():
                children.append(_make_child(
                    current_text.strip(), doc_id, doc_name, file_type,
                    seg_sentences[-1][1] if seg_sentences else 1,
                    ci, pi
                ))
                ci += 1

        return children


def _make_single_chunk(text, doc_id, doc_name, file_type, page, index):
    return Chunk(text=text.strip(), metadata={
        "doc_id": doc_id,
        "doc_name": doc_name,
        "file_type": file_type,
        "page_number": page,
        "chunk_index": index,
        "chunk_type": "parent",
    })


def _make_child(text, doc_id, doc_name, file_type, page, child_index, parent_index):
    return Chunk(text=text.strip(), metadata={
        "doc_id": doc_id,
        "doc_name": doc_name,
        "file_type": file_type,
        "page_number": page,
        "chunk_index": child_index,
        "chunk_type": "child",
        "parent_index": parent_index,
    })


def _pairwise(boundaries):
    """[-1, 3, 7, 10] → [(-1, 3), (3, 7), (7, 10)]"""
    return [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]


# ============================================================
#  规则分块器（L0 Fallback）
# ============================================================

def chunk_text(
        text: str,
        doc_id: str,
        doc_name: str,
        file_type: str,
        total_pages: int,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
) -> List[Chunk]:
    """规则分块器，作为语义分块的 fallback"""
    paragraphs = _split_by_paragraphs(text)
    chunks = []

    for para in paragraphs:
        if not para.strip():
            continue
        page_num = _extract_page_number(para)

        if _estimate_tokens(para) <= chunk_size:
            chunks.append(_make_rule_chunk(para, doc_id, doc_name, file_type, page_num))
        else:
            sub_chunks = _split_long_paragraph(para, chunk_size, chunk_overlap)
            for sc in sub_chunks:
                chunks.append(_make_rule_chunk(sc, doc_id, doc_name, file_type, page_num))

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["chunk_type"] = "rule"

    return chunks


def _make_rule_chunk(text, doc_id, doc_name, file_type, page_num):
    return Chunk(text=text.strip(), metadata={
        "doc_id": doc_id,
        "doc_name": doc_name,
        "file_type": file_type,
        "page_number": page_num,
        "chunk_type": "rule",
    })


# ============================================================
#  统一入口
# ============================================================

def chunk_document(
        text: str,
        doc_id: str,
        doc_name: str,
        file_type: str,
        total_pages: int,
        use_semantic: bool = True,
) -> Tuple[List[Chunk], List[Chunk]]:
    """
    统一分块入口。
    返回 (检索用子块, LLM用父块)
    - 如果 use_semantic=True 且文本足够长，用语义分块
    - 否则用规则分块（子块=父块）
    """
    if use_semantic and _estimate_tokens(text) > 500:
        chunker = SemanticChunker()
        children, parents = chunker.chunk(text, doc_id, doc_name, file_type, total_pages)

        # 重新设置 children 的 chunk_index（全局递增）
        for i, c in enumerate(children):
            c.metadata["chunk_index"] = i
        for i, p in enumerate(parents):
            p.metadata["chunk_index"] = i

        return children, parents
    else:
        # 规则模式：子块=父块
        chunks = chunk_text(text, doc_id, doc_name, file_type, total_pages)
        return chunks, chunks


# ============================================================
#  工具函数
# ============================================================

def _split_by_paragraphs(text: str) -> List[str]:
    return re.split(r'\n\s*\n', text)


def _split_long_paragraph(text: str, chunk_size: int, overlap: int) -> List[str]:
    sentences = re.split(r'(?<=[。！？\.\!\?])\s*', text)
    result = []
    current = ""

    for sent in sentences:
        if _estimate_tokens(current + sent) <= chunk_size:
            current += sent
        else:
            if current.strip():
                result.append(current.strip())
            if result:
                current = result[-1][-overlap:] + sent if len(result[-1]) > overlap else sent
            else:
                current = sent

    if current.strip():
        result.append(current.strip())

    return result if result else [text]


def _estimate_tokens(text: str) -> int:
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    return int(chinese_chars * 1.5 + english_words * 1.3 + len(text) * 0.3)


def _extract_page_number(text: str) -> int:
    match = re.search(r'\[第(\d+)页\]', text)
    return int(match.group(1)) if match else 1
