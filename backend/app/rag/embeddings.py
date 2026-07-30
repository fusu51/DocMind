"""Embedding — 文本块 → 向量，批量调用 API"""
from typing import List
from openai import OpenAI

from ..config import (
    EMBEDDING_API_KEY,
    EMBEDDING_MODEL,
    EMBEDDING_BASE_URL,
)


def create_embedding_client() -> OpenAI:
    """创建 Embedding 客户端"""
    kwargs = {"api_key": EMBEDDING_API_KEY}
    if EMBEDDING_BASE_URL:
        kwargs["base_url"] = EMBEDDING_BASE_URL
    return OpenAI(**kwargs)


def embed_texts(texts: List[str], client: OpenAI = None) -> List[List[float]]:
    """
    批量将文本转为向量。
    返回 List[向量]，每个向量是 1536 维 float 列表。
    """
    if client is None:
        client = create_embedding_client()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return [item.embedding for item in response.data]


def embed_single(text: str, client: OpenAI = None) -> List[float]:
    """单条文本向量化"""
    return embed_texts([text], client)[0]
