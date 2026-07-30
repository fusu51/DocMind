"""请求/响应数据模型"""
from pydantic import BaseModel


# --- 聊天 ---
class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


# --- 文档 ---
class DocumentInfo(BaseModel):
    id: str
    name: str
    size: int
    chunks: int
    created_at: str
