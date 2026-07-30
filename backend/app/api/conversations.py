"""对话历史 API"""
from fastapi import APIRouter

from ..db.repository import list_conversations, delete_conversation

router = APIRouter()


@router.get("/conversations")
async def get_conversations(doc_id: str = None):
    """获取对话历史，可选按文档过滤"""
    conversations = list_conversations(doc_id)
    return {"conversations": conversations}


@router.delete("/conversations/{conv_id}")
async def remove_conversation(conv_id: int):
    """删除单条对话"""
    delete_conversation(conv_id)
    return {"message": "已删除", "id": conv_id}
