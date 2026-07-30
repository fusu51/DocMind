"""数据访问层 — 封装 SQLite CRUD"""
import uuid
import json
from typing import List, Optional

from .models import get_connection, init_db
from ..models.schemas import DocumentInfo


def add_document(name: str, file_path: str, file_type: str,
                 file_size: int, total_pages: int, chunk_count: int) -> str:
    """添加文档记录，返回 doc_id"""
    init_db()
    doc_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        """INSERT INTO documents (id, name, file_path, file_type, file_size, total_pages, chunk_count)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, name, file_path, file_type, file_size, total_pages, chunk_count),
    )
    conn.commit()
    conn.close()
    return doc_id


def list_documents() -> List[DocumentInfo]:
    """文档列表"""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, file_size, chunk_count, created_at FROM documents ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [
        DocumentInfo(
            id=row["id"],
            name=row["name"],
            size=row["file_size"],
            chunks=row["chunk_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_document(doc_id: str) -> Optional[dict]:
    """获取单个文档信息"""
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_document(doc_id: str):
    """删除文档记录"""
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


def save_conversation(doc_id: Optional[str], question: str,
                      answer: str, sources: list,
                      reasoning: str = "", pipeline: dict = None):
    """保存对话记录"""
    init_db()
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (doc_id, question, answer, sources, reasoning, pipeline) VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, question, answer,
         json.dumps(sources, ensure_ascii=False),
         reasoning,
         json.dumps(pipeline, ensure_ascii=False) if pipeline else ""),
    )
    conn.commit()
    conn.close()


def list_conversations(doc_id: Optional[str] = None) -> list:
    """对话历史"""
    init_db()
    conn = get_connection()
    if doc_id:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE doc_id = ? ORDER BY created_at DESC",
            (doc_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_conversation(conv_id: int):
    """删除单条对话记录"""
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()


def clear_conversations(doc_id: Optional[str] = None):
    """清空对话历史，可选按文档过滤"""
    init_db()
    conn = get_connection()
    if doc_id:
        conn.execute("DELETE FROM conversations WHERE doc_id = ?", (doc_id,))
    else:
        conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()
