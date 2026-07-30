"""数据库 — 表定义和初始化"""
import sqlite3
import os

from ..config import DATABASE_URL


def get_db_path() -> str:
    """从 DATABASE_URL 提取文件路径"""
    # sqlite:///./data/conversations.db → ./data/conversations.db
    return DATABASE_URL.replace("sqlite:///", "")


def init_db():
    """初始化数据库表"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 文档表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            total_pages INTEGER DEFAULT 1,
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 对话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT,           -- JSON 格式的来源引用
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 迁移：reasoning 和 pipeline 列（如果不存在则添加）
    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN reasoning TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # 列已存在

    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN pipeline TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
