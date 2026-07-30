"""文档管理 API — 列表、删除"""
import os
from fastapi import APIRouter, HTTPException

from ..db.repository import list_documents, get_document, delete_document
from ..rag.retriever import delete_by_doc_id

router = APIRouter()


@router.get("/documents")
async def get_documents():
    """获取文档列表"""
    docs = list_documents()
    return {"documents": docs}


@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: str):
    """删除文档（向量 + 文件 + 记录）"""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")

    # 1. 删向量
    delete_by_doc_id(doc_id)

    # 2. 删文件
    try:
        os.remove(doc["file_path"])
    except FileNotFoundError:
        pass

    # 3. 删数据库记录
    delete_document(doc_id)

    return {"message": "删除成功", "id": doc_id}
