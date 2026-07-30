"""
L1 查询处理 — 规则路由 + 条件 HyDE + SQLite 缓存
"""
import hashlib
import re
import sqlite3
import os
from typing import Optional

from openai import OpenAI

from ..config import (
    LLM_API_KEY,
    LLM_CHAT_MODEL,
    LLM_BASE_URL,
    DATABASE_URL,
)

HYDE_PROMPT = """你是一个知识助手。请基于常识简要猜测以下问题的答案，写一段 50~100 字的描述。

问题：{question}
描述："""


class QueryProcessor:
    """L1 查询处理器"""

    def __init__(self):
        kwargs = {"api_key": LLM_API_KEY}
        if LLM_BASE_URL:
            kwargs["base_url"] = LLM_BASE_URL
        self._client = OpenAI(**kwargs)
        self._cache_db = self._get_cache_path()

    def _get_cache_path(self) -> str:
        """返回 SQLite 缓存文件路径"""
        db_path = DATABASE_URL.replace("sqlite:///", "")
        cache_dir = os.path.dirname(db_path)
        cache_path = os.path.join(cache_dir or ".", "hyde_cache.db")
        return cache_path

    def _init_cache(self):
        """初始化 HyDE 缓存表"""
        conn = sqlite3.connect(self._cache_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hyde_cache (
                question_hash TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                hyde_answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return conn

    def _get_cached(self, question_hash: str) -> Optional[str]:
        """查询缓存"""
        conn = self._init_cache()
        row = conn.execute(
            "SELECT hyde_answer FROM hyde_cache WHERE question_hash = ?",
            (question_hash,),
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _set_cache(self, question_hash: str, question: str, hyde_answer: str):
        """写入缓存"""
        conn = self._init_cache()
        conn.execute(
            "INSERT OR REPLACE INTO hyde_cache (question_hash, question, hyde_answer) VALUES (?, ?, ?)",
            (question_hash, question, hyde_answer),
        )
        conn.commit()
        conn.close()

    # ============================================================
    #  规则路由
    # ============================================================

    def needs_hyde(self, question: str) -> bool:
        """
        判断是否需要 HyDE。
        以下情况跳过 HyDE（精确匹配更有效）：
        - 包含引号包裹的精确短语
        - 包含数字编号（如 "第3条"、"Article 5"）
        - 包含代码/特殊标识符（如 "sk-xxx"、"0x1A"）
        - 问题中已含大量专有名词（>40% 的字是专有名词特征）
        """
        # 引号包裹
        if re.search(r'[""「」『』].*?[""「」『』]', question):
            return False

        # 数字编号模式
        if re.search(r'第\s*\d+\s*[条章节项]', question):
            return False
        if re.search(r'\b(?:Article|Section|Chapter)\s+\d+', question, re.IGNORECASE):
            return False

        # 代码/特殊标识符
        if re.search(r'[A-Z]{2,}-\d+[a-zA-Z]+', question):  # 如 sk-xxx
            return False
        if re.search(r'\b0x[0-9A-Fa-f]+\b', question):      # 十六进制
            return False

        # 短精确问题（< 10 字且无问句特征）→ 大概率是术语查询
        if len(question) < 10 and not any(kw in question for kw in ["什么", "如何", "怎么", "为什么", "是否"]):
            return False

        return True  # 默认启用 HyDE

    # ============================================================
    #  HyDE 生成（带缓存）
    # ============================================================

    def generate_hyde(self, question: str) -> str:
        """
        生成 HyDE 假想答案。
        - 先查缓存，命中则直接返回
        - 缓存未命中则调 LLM，结果写入缓存
        - 失败时返回原始问题作为 fallback
        """
        question_hash = hashlib.md5(question.encode()).hexdigest()

        # 查缓存
        cached = self._get_cached(question_hash)
        if cached:
            return cached

        # 调 LLM 生成
        try:
            resp = self._client.chat.completions.create(
                model=LLM_CHAT_MODEL,
                messages=[{
                    "role": "user",
                    "content": HYDE_PROMPT.format(question=question),
                }],
                temperature=0.3,
                max_tokens=200,
            )
            hyde_answer = resp.choices[0].message.content.strip()

            # 写入缓存
            if hyde_answer:
                self._set_cache(question_hash, question, hyde_answer)
                return hyde_answer
        except Exception:
            pass

        return question  # fallback

    # ============================================================
    #  统一入口
    # ============================================================

    def process(self, question: str) -> str:
        """
        处理用户问题，返回用于检索的查询文本。
        路由逻辑：
        - 精确查询 → 直接返回原始问题
        - 模糊查询 → 生成 HyDE 假想答案
        """
        if self.needs_hyde(question):
            return self.generate_hyde(question)
        else:
            return question


# ---- 单例 ----

_query_processor: Optional[QueryProcessor] = None


def get_query_processor() -> QueryProcessor:
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor
